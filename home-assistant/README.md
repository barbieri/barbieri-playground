# Barbieri's Home Assistant Scripts

These are a collections of scripts [Barbieri](https://github.com/barbieri)
uses to manage his https://www.home-assistant.io/ setup.

## gen-delayed-service-sequence.py

There are some scripts that are annoying to write because they are
a long list of "turn on an entity, wait a bit, turn off that entity",
repeated many times. For example when creating an irrigation of many
zones, each you want to keep watering for a different amount of time.

It can turn to be even more annoying if you need to have some
interval between each step, say you need to wait engines to cool down.

Last but not least, it can turn to be **very annoying** if you need to
overlap some steps, for instance my irrigation setup works better if
I turn on the next area **before** I turn off the previous.

To solve those annoyances there is the `gen-delayed-service-sequence.py`
that takes a simple list of steps composed of `duration=entity_id`
and will do everything for you (turn on, delay, turn off).

### Basic Usage:

The following script will turn on lights 1, 2 and 3 after one minute each,
the duration syntax supports both `HH:MM`, `HH:MM:SS` and human readable,
such as `1h 2m 3s` (one hour, two minutes and 3 seconds).

```sh
$ ./gen-delayed-service-sequence.py -- \
    "00:01:00=switch.light1" \
    "1m=switch.light2" \
    "60s=switch.light3"
```

Output:

```yaml
alias: Sequence (2m)
mode: single
sequence:
- service: switch.turn_on
  target:
    entity_id: switch.light1
- delay: 0:01:00
- service: switch.turn_off
  target:
    entity_id: switch.light1
- service: switch.turn_on
  target:
    entity_id: switch.light2
- delay: 0:01:00
- service: switch.turn_off
  target:
    entity_id: switch.light2
- service: switch.turn_on
  target:
    entity_id: switch.light3
- delay: 0:00:00
- service: switch.turn_off
  target:
    entity_id: switch.light3
```

### Add Interval Between Each Step

Same as the previous example, but will introduce a 5 seconds interval
between each step, that is, after `light1` is turned off, wait 5 seconds
and just then turn `light2`.

```sh
$ ./gen-delayed-service-sequence.py --inter-step-delay=5s -- \
    "00:01:00=switch.light1" \
    "1m=switch.light2" \
    "60s=switch.light3"
```

Output:

```yaml
alias: Sequence (2m 10s)
mode: single
sequence:
- service: switch.turn_on
  target:
    entity_id: switch.light1
- delay: 0:01:00
- service: switch.turn_off
  target:
    entity_id: switch.light1
- delay: 0:00:05
- service: switch.turn_on
  target:
    entity_id: switch.light2
- delay: 0:01:00
- service: switch.turn_off
  target:
    entity_id: switch.light2
- delay: 0:00:05
- service: switch.turn_on
  target:
    entity_id: switch.light3
- delay: 0:00:00
- service: switch.turn_off
  target:
    entity_id: switch.light3
```

### Overlap Strategy

If you must turn on the next entity before turning off the previous one,
with an optional delay duration, then use `----overlap-steps[=DURATION]`.

**NOTE:** The `--overlap-steps` cannot be used alongside ` --inter-step-delay`.

Example without any delay. You can also use ` --overlap-steps=0s`,
` --overlap-steps=true`, ` --overlap-steps=yes` or ` --overlap-steps=on`:

```sh
./gen-delayed-service-sequence.py --overlap-steps -- \
    "00:01:00=switch.light1" \
    "1m=switch.light2" \
    "60s=switch.light3"
```

Output:
```yaml
alias: Sequence (2m)
mode: single
sequence:
- service: switch.turn_on
  target:
    entity_id: switch.light1
- delay: 0:01:00
- service: switch.turn_on
  target:
    entity_id: switch.light2
- service: switch.turn_off
  target:
    entity_id: switch.light1
- delay: 0:01:00
- service: switch.turn_on
  target:
    entity_id: switch.light3
- service: switch.turn_off
  target:
    entity_id: switch.light2
- delay: 0:00:00
- service: switch.turn_off
  target:
    entity_id: switch.light3
```

Example with 5s delay:

```sh
./gen-delayed-service-sequence.py --overlap-steps=5s -- \
    "00:01:00=switch.light1" \
    "1m=switch.light2" \
    "60s=switch.light3"
```

Output:

```yaml
alias: Sequence (2m 10s)
mode: single
sequence:
- service: switch.turn_on
  target:
    entity_id: switch.light1
- delay: 0:01:00
- service: switch.turn_on
  target:
    entity_id: switch.light2
- delay: 0:00:05
- service: switch.turn_off
  target:
    entity_id: switch.light1
- delay: 0:01:00
- service: switch.turn_on
  target:
    entity_id: switch.light3
- delay: 0:00:05
- service: switch.turn_off
  target:
    entity_id: switch.light2
- delay: 0:00:00
- service: switch.turn_off
  target:
    entity_id: switch.light3
```

### Aliases

As the script grows it may be cumbersome to remember about all of
the entity ids and understand what's happening. To help with that one
may use steps in the format `DURATION=ENTITY_ID=ALIAS` or specify
a default alias to use for every step. Aliases support formatting, so
this is often the best option.

**NOTE:** The lovelace UI doesn't support aliases and will render the
script as YAML.

```sh
$ ./gen-delayed-service-sequence.py \
    --overlap-steps=5s \
    --default-step-alias="{start} {action} {friendly_name} ({duration_human})" \
    -- \
    "00:01:00=switch.light1" \
    "1m=switch.light2" \
    "60s=switch.light3=Custom Alias ({duration})"
```

Output:

```yaml
alias: Sequence (2m 10s)
mode: single
sequence:
- alias: 0:00:00 turn on switch.light1 (1m)
  service: switch.turn_on
  target:
    entity_id: switch.light1
- alias: 0:00:00 keep on switch.light1 (1m)
  delay: 0:01:00
- alias: 0:01:00 turn on switch.light2 (1m)
  service: switch.turn_on
  target:
    entity_id: switch.light2
- alias: 0:01:00 overlap switch.light1 (5s)
  delay: 0:00:05
- alias: 0:01:05 turn off switch.light1 (1m)
  service: switch.turn_off
  target:
    entity_id: switch.light1
- alias: 0:01:05 keep on switch.light2 (1m)
  delay: 0:01:00
- alias: Custom Alias (0:00:00)
  service: switch.turn_on
  target:
    entity_id: switch.light3
- alias: 0:02:05 overlap switch.light2 (5s)
  delay: 0:00:05
- alias: 0:02:10 turn off switch.light2 (1m)
  service: switch.turn_off
  target:
    entity_id: switch.light2
- alias: Custom Alias (0:00:00)
  delay: 0:00:00
- alias: Custom Alias (0:00:00)
  service: switch.turn_off
  target:
    entity_id: switch.light3
```
