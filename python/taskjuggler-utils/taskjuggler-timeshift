#!/usr/bin/env python

import sys, os, re
from datetime import date, timedelta

def usage():
    print """\
Usage:

    %(prg)s <offset> <input> [output]

Where offset is in the format:

    <+|-><number><unit>

     + or -: operation (add or subtract)
     <number>: amount to operate
     <unit>: one of d, w, m or y:
             d: day
             w: week (7 days)
             m: month (30 days)
             y: year (365 days)

Examples:

   %(prg)s +1w file.tjp   # adds one week
   %(prg)s -1d file.tjp   # remove one day
   %(prg)s +1d file.tjp file.tjp # replace file in-place (it is safe)
""" % {"prg": sys.argv[0]}


def parse_offset(offset):
    """Convert string representing offset to a datetime.timedelta

    offset format is described in usage()
    """
    m = re.match(r"([+-])([0-9]+)([dwmy])", offset)
    if not m:
        raise SystemExit("invalid offset format: %r" % offset)
    signal, number, unit = m.groups()
    number = int(number)
    if signal == '-':
        number = -number

    unit_map = {
        "d": 1,
        "w": 7,
        "m": 30,
        "y": 365
        }
    number *= unit_map[unit]
    return timedelta(number)



try:
    offset = sys.argv[1]
    input = sys.argv[2]
    if len(sys.argv) > 3:
        output = sys.argv[3]
    else:
        output = None
except IndexError:
    usage()
    raise SystemExit()

offset = parse_offset(offset)
input = open(input, "rb")

if not output:
    output = sys.stdout
else:
    try:
        os.unlink(output)
    except OSError:
        pass
    output = open(output, "wb")

# dates:
#     2008-09-25
#     2008-9-25
#     2008-09-02
#     2008-9-2
# ...
r = re.compile(r"((2[0-9]{3})-(1[0-2]|0?[0-9])-([12][0-9]|3[0-1]|0?[0-9]))")

def timeshift(match):
    txt, year, month, day = match.groups()
    orig = date(int(year), int(month), int(day))
    new = orig + offset
    return "%04d-%02d-%02d" % (new.year, new.month, new.day)

for line in input:
    output.write(r.sub(timeshift, line))

input.close()
output.close()
