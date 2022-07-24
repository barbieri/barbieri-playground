#!/usr/bin/env python3

import argparse
import re
import sys
import yaml
import requests
from datetime import timedelta
from typing import (
    Dict, List, Literal, Mapping, NamedTuple, Sequence, Tuple, Union, TypedDict, Optional,
)


class InputStep(NamedTuple):
    duration: timedelta
    entity_id: str
    alias: str


class Step(NamedTuple):
    duration: timedelta
    entity_id: str
    alias: str
    friendly_name: str


def create_step(
    default_alias: str,
    entity_db: Mapping[str, str],
    input: InputStep,
) -> Step:
    entity_id = input.entity_id
    if not entity_id:
        friendly_name = 'Delay'
    else:
        friendly_name = entity_db.get(entity_id, entity_id)

    return Step(
        duration=input.duration,
        entity_id=entity_id,
        alias=input.alias or default_alias or '',
        friendly_name=friendly_name,
    )


Overlap = Union[timedelta, bool]


class BaseSequenceStep(TypedDict, total=False):
    alias: str


class DelayDict(BaseSequenceStep):
    delay: str


class TargetDict(TypedDict):
    entity_id: str


class ServiceDict(BaseSequenceStep):
    service: str
    target: TargetDict[TypedDict]


SequenceItem = Union[DelayDict, ServiceDict]


class ScriptDictBase(TypedDict, total=False):
    alias: str
    icon: str


class ScriptDict(ScriptDictBase):
    mode: str
    sequence: List[SequenceItem]


DURATION_KEYS = ('hours', 'minutes', 'seconds')

# all lower case
BOOL_MAPPING = {
    '1': True,
    '0': False,
    'yes': True,
    'no': True,
    'y': True,
    'n': True,
    'on': True,
    'off': False,
    'true': True,
    'false': False,
    't': True,
    'f': False,
}

def parse_bool(s: str) -> bool:
    return BOOL_MAPPING[s.lower()]


HUMAN_DURATION_RE = re.compile('\s*((?P<value>\d)+\s*(?P<unit>[hms]))')


def parse_duration(s: str) -> timedelta:
    if ':' in s:
        kwargs = dict(zip(DURATION_KEYS, (int(p) for p in s.split(':'))))
        return timedelta(**kwargs)
    else:
        values = {'h': 0, 'm': 0, 's': 0}
        for match in HUMAN_DURATION_RE.finditer(s):
            value = int(match.group('value'))
            unit = match.group('unit')
            values[unit] = value
        return timedelta(
            hours=values['h'],
            minutes=values['m'],
            seconds=values['s'],
        )


def parse_step(s: str) -> InputStep:
    parts = s.split('=', maxsplit=2)
    if len(parts) < 3:
        parts.extend([''] * (3 - len(parts)))

    duration_str, entity_id, alias = parts
    if not duration_str:
        raise ValueError('expected duration')

    duration = parse_duration(duration_str)
    return InputStep(duration, entity_id, alias)


def parse_overlap(s: str) -> Overlap:
    try:
        return parse_bool(s)
    except KeyError:
        return parse_duration(s)


def format_human_duration(duration: timedelta) -> str:
    mm, ss = divmod(duration.seconds, 60)
    hh, mm = divmod(mm, 60)
    r: List[str] = []
    if hh:
        r.append(f'{hh}h')
    if mm:
        r.append(f'{mm}m')
    if ss:
        r.append(f'{ss}s')
    return ' '.join(r)


def get_base_sequence_step(alias: str) -> BaseSequenceStep:
    return {'alias': alias } if alias else {}


def delay(
    duration: timedelta,
    alias: str,
) -> DelayDict:
    return {**get_base_sequence_step(alias), 'delay': str(duration)}


ACTION_FORMAT_MSG = {
    'turn_on': 'turn on',
    'turn_off': 'turn off',
    'keep_on': 'keep on',
    'keep_off': 'keep off',
    'delay': 'wait',
    'overlap': 'overlap',
}


def format_alias(
    alias: str,
    action: str,
    start: timedelta,
    duration: timedelta,
    **extras: Mapping[str, str],
) -> str:
    end = start + duration
    return alias.format(
        action=ACTION_FORMAT_MSG[action],
        duration=str(duration),
        duration_human=format_human_duration(duration),
        start=str(start),
        start_human=format_human_duration(start),
        end=str(end),
        end_human=format_human_duration(end),
        **extras,
    )


def service(
    domain: str,
    service: Union[Literal['turn_on'], Literal['turn_off']],
    step: Step,
    start: timedelta,
) -> ServiceDict:
    alias = format_alias(
        step.alias,
        service,
        start,
        step.duration,
        entity_id=step.entity_id,
        friendly_name=step.friendly_name,
    )
    return {
        **get_base_sequence_step(alias),
        'service': f'{domain}.{service}',
        'target': {
            'entity_id': step.entity_id,
        },
    }


def turn_off(
    domain: str,
    step: Step,
    start: timedelta,
) -> ServiceDict:
    return service(domain, 'turn_off', step, start)


def turn_on(
    domain: str,
    step: Step,
    start: timedelta,
) -> ServiceDict:
    return service(domain, 'turn_on', step, start)


class BaseSequence:
    domain: str
    result: List[SequenceItem]
    elapsed: timedelta
    last_service_step: Optional[Step]

    def __init__(
        self,
        domain: str,
    ) -> None:
        self.domain = domain
        self.result = []
        self.elapsed = timedelta()
        self.last_service_step = None

    def _format_alias(
        self,
        alias: str,
        action: str,
        duration: timedelta,
        **extras: Mapping[str, str],
    ) -> str:
        return format_alias(alias, action, self.elapsed, duration, **extras)

    def _turn_on(self, step: Step) -> None:
        self.result.append(turn_on(self.domain, step, self.elapsed))

    def _turn_off(self, step: Step) -> None:
        self.result.append(turn_off(self.domain, step, self.elapsed))

    def _delay(self, duration: timedelta, alias: str) -> None:
        self.result.append(delay(duration, alias))
        self.elapsed += duration

    def _keep_on(self, step: Step) -> None:
        msg = self._format_alias(
            step.alias,
            'keep_on',
            step.duration,
            entity_id=step.entity_id,
            friendly_name=step.friendly_name,
        )
        self._delay(step.duration, msg)

    def _will_turn_off_last_service(self) -> None:
        pass

    def _did_turn_off_last_service(self) -> None:
        pass

    def _start_service_step(self, step: Step) -> None:
        pass

    def _finish_service_step(self, step: Step) -> None:
        pass

    def _start_delay_step(self, step: Step) -> None:
        pass

    def _finish_delay_step(self, step: Step) -> None:
        msg = self._format_alias(step.alias, 'delay', step.duration)
        self._delay(step.duration, msg or 'Step is a delay')

    def add_step(self, step: Step) -> None:
        if step.entity_id:
            self._start_service_step(step)
        else:
            self._start_delay_step(step)

        if self.last_service_step:
            self._will_turn_off_last_service()
            self._turn_off(self.last_service_step)
            self._did_turn_off_last_service()

        if step.entity_id:
            self._finish_service_step(step)
            self.last_service_step = step
        else:
            self._finish_delay_step(step)
            self.last_service_step = None

    def close(self) -> Tuple[List[SequenceItem], timedelta]:
        if self.last_service_step:
            self._turn_off(self.last_service_step)
            self.last_service_step = None

        result = (self.result, self.elapsed)
        self.result = []
        self.elapsed = timedelta()
        return result

    def process(
        self,
        steps: Sequence[Step],
    ) -> Tuple[List[SequenceItem], timedelta]:
        for step in steps:
            self.add_step(step)
        return self.close()


class StandardSequence(BaseSequence):
    inter_step_delay: Optional[timedelta]

    def __init__(
        self,
        domain: str,
        inter_step_delay: Optional[timedelta],
    ) -> None:
        super().__init__(domain)
        self.inter_step_delay = inter_step_delay

    def _did_turn_off_last_service(self) -> None:
        if not self.inter_step_delay:
            return
        msg = self._format_alias(
            self.last_service_step.alias,
            'keep_off',
            self.inter_step_delay,
            entity_id=self.last_service_step.entity_id,
            friendly_name=self.last_service_step.friendly_name,
        )
        self._delay(self.inter_step_delay, msg)

    def _finish_service_step(self, step: Step) -> None:
        self._turn_on(step)
        self._keep_on(step)


class OverlapSequence(BaseSequence):
    overlap_delay: Optional[timedelta]

    def __init__(
        self,
        domain: str,
        overlap_delay: Optional[timedelta],
    ) -> None:
        super().__init__(domain)
        self.overlap_delay = overlap_delay

    def _will_turn_off_last_service(self) -> None:
        if not isinstance(self.overlap_delay, timedelta):
            return
        msg = self._format_alias(
            self.last_service_step.alias,
            'overlap',
            self.overlap_delay,
            entity_id=self.last_service_step.entity_id,
            friendly_name=self.last_service_step.friendly_name,
        )
        self._delay(self.overlap_delay, msg)

    def _start_service_step(self, step: Step) -> None:
        self._turn_on(step)

    def _finish_service_step(self, step: Step) -> None:
        self._keep_on(step)


def get_entity_db(api: str, access_token: Optional[str]) -> Dict[str, str]:
    headers = {'content-type': 'application/json'}
    if access_token:
        headers['authorization'] = f'Bearer {access_token}'

    response = requests.get(f'{api}/states', headers=headers)
    if not response.ok:
        response.raise_for_status()

    entities = {}
    for item in response.json():
        entity_id = item['entity_id']
        attributes = item['attributes']
        friendly_name = attributes.get('friendly_name')
        if friendly_name:
            entities[entity_id] = friendly_name

    return entities


parser = argparse.ArgumentParser(
    formatter_class=argparse.RawTextHelpFormatter,
    description='''\
Generates Home-Assistant scripts to execute a series of turn-on and turn-off \
of services interleaved with delays of given duration.

See: https://www.home-assistant.io/docs/scripts
''')

parser.add_argument(
    '-o', '--output',
    type=argparse.FileType('w', encoding='utf-8'),
    default=sys.stdout,
)

home_assistant_group = parser.add_argument_group('Home Assistant Access')
home_assistant_group.add_argument(
    '--api',
    help='''\
The Home Assistant API base URL, used to resolve entity names.\
''',
)
home_assistant_group.add_argument(
    '--access-token',
    help='''\
The Home Assistant API access token, used to resolve entity names.\
''',
)

script_group = parser.add_argument_group('Automation Script Configuration')
script_group.add_argument(
    '--alias',
    help='''\
Script alias (title) to produce, supports formatting with keys:
 - {total_duration}: example "12:34:56"
 - {total_duration_human}: example "12h 34m 56s"\

Defaults to %(default)r
''',
    default='Sequence ({total_duration_human})',
)
script_group.add_argument(
    '--default-step-alias',
    help='''\
If a step item has no alias, then use this one. Formatting keys:
 - {action}: example "turn on" and "turn off"
 - {duration}: example "12:34:56"
 - {duration_human}: example "12h 34m 56s"
 - {start}: example "12:34:56"
 - {start_human}: example "12h 34m 56s"
 - {end}: example "12:34:56"
 - {end_human}: example "12h 34m 56s"
 - {friendly_name}: example "Kitchen Lights"
 - {entity_id}: the given entity id
''',
)

script_group.add_argument(
    '--icon',
    help='MDI icon to use, if any',
)
script_group.add_argument(
    '--mode',
    help='''\
Script automation mode, see \
https://www.home-assistant.io/docs/automation/modes
Defaults to %(default)r
''',
    default='single',
    choices=('single', 'restart', 'queued', 'parallel'),
)
script_group.add_argument(
    '--domain',
    default='switch',
    help='''\
Changes the Home Assistant domain to operate on, it may be anything \
that takes the '.turn_on' and '.turn_off' services, see \
https://www.home-assistant.io/docs/scripts/service-calls
Defaults to %(default)r
'''
)

strategy = parser.add_mutually_exclusive_group()
strategy.add_argument(
    '--inter-step-delay',
    default=None,
    type=parse_duration,
    help='Use this delay between each step.',
)
strategy.add_argument(
    '--overlap-steps',
    type=parse_overlap,
    nargs='?',
    const=True,
    default=False,
    help='''\
Due some physical device limitations (ie: pumps) sometimes it's necessary \
to overlap some steps, keeping the previous entity on before turning the \
new entity and just then turn off the previous entity.

If specified, then the entities will overlap their state, that is, \
before turning the previous entity off, it will turn on the next entity, \
example: step1, step2 will result in:
 - turn on step 1
 - delay step 1
 - turn on step 2
 - delay overlap (if given)
 - turn off step 1
 - delay step 2

By default there is no overlap delay, but it may be given as a duration.

If not specified, or falsy, no overlap will be made and the standard \
sequence is generated, with the previous step's entity being turned off \
before the new entity is turned on.
'''
)

parser.add_argument(
    'step',
    nargs='+',
    help='''\
Step to add to sequence. Formats:
 - duration=entity_id
 - duration=entity_id=alias
 - duration (only a delay)
 - duration==alias (only a delay, with given alias)

where:
 - duration is in one of the formats:
   - HH:MM
   - HH:MM:SS
   - human readable composed of value and unit ("h", "m" or "s"), example
     "1h 2m 3s" will be 1 hour, 2 minutes and 3 seconds.
 - alias is optional with keys:
   - {action}: example "turn on" and "turn off"
   - {duration}: example "12:34:56"
   - {duration_human}: example "12h 34m 56s"
   - {start}: example "12:34:56"
   - {start_human}: example "12h 34m 56s"
   - {end}: example "12:34:56"
   - {end_human}: example "12h 34m 56s"
   - {friendly_name}: example "Kitchen Lights"
''',
    type=parse_step,
)

if __name__ == '__main__':
    args = parser.parse_args()
    domain = args.domain
    overlap_steps = args.overlap_steps
    default_alias = args.default_step_alias

    entity_db = get_entity_db(args.api, args.access_token) if args.api else {}
    steps = [create_step(default_alias, entity_db, s) for s in args.step]

    if overlap_steps is not False:
        generator = OverlapSequence(domain, args.overlap_steps)
    else:
        generator = StandardSequence(domain, args.inter_step_delay)


    sequence, total_duration = generator.process(steps)
    base: ScriptDictBase = {}
    if args.icon:
        base['icon'] = args.icon
    if args.alias:
        base['alias'] = args.alias.format(
            total_duration=str(total_duration),
            total_duration_human=format_human_duration(total_duration),
        )

    script: ScriptDict = {
        **base,
        'mode': args.mode,
        'sequence': sequence,
    }
    yaml.safe_dump(script, args.output, allow_unicode=True)
