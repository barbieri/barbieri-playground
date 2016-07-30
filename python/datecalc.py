#!/usr/bin/python

import sys
from datetime import date, timedelta

today = date.today

def parse_date(txt):
    if txt == "today":
        return today()

    parts = txt.split("-")
    if len(parts) != 2 and len(parts) != 3:
        raise ValueError("invalid number of dashes")

    parts = [int(x) for x in parts]
    if len(parts) == 2:
        parts.insert(0, today().year)
    elif parts[0] < 100:
        parts[0] += int(today().year / 100) * 100

    return date(*parts)

unit_map = {
    "d": 1,
    "w": 7,
    "m": 30,
    "y": 365
    }

def parse_amount(txt):
    unit = txt[-1]
    value = int(txt[:-1])
    try:
        value *= unit_map[unit]
    except KeyError:
        raise ValueError("invalid amount unit '%s'" % unit)
    return timedelta(value)


def fmt_date(date):
    return "%s, week %d, %s" % (
        date.isoformat(),
        date.isocalendar()[1],
        date.strftime("%A, %B"))


def fmt_amount(amount):
    days = amount.days
    txt = ["%+dd" % days]
    if days > 0:
        sign = "+"
    elif days < 0:
        sign = "-"
    else:
        sign = None

    abs_days = abs(days)
    if sign:
        for u in ("w", "m", "y"):
            v = int(abs_days / unit_map[u])
            if v == 0:
                break
            txt.append("%c%d%s" % (sign, v, u))

    return " ".join(txt)


def print_date(date):
    print fmt_date(date)


def print_amount(date, amount):
    print "%s: %s" % (fmt_amount(amount), fmt_date(date))


def usage():
    print """\
Usage:

    %(prg)s <end-date> - <start-date|amount>
    %(prg)s <end-date> + <amount>
    %(prg)s <date> ?

Where <date> may be specified in full or abbreviated forms:

     YYYY-mm-dd: 4-digit year, 1-2 digit month, 1-2 digit day
       YY-mm-dd: 2-digit year, 1-2 digit month, 1-2 digit day
          mm-dd: 1-2 digit month, 1-2 digit day
          today: current year, month and day

For <amount> must be specified using the proper units:
              d: day
              w: week (7 days)
              m: month (30 days)
              y: year (365 days)

Examples:

    %(prg)s 2009-10-05 - 2009-10-01
    %(prg)s 2009-10-05 - 4d
    %(prg)s 2009-10-01 + 4d
    %(prg)s 2009-10-01 + 1w
    %(prg)s 2009-10-01 ?

""" % {"prg": sys.argv[0]}

try:
    a = sys.argv[1]
    op = sys.argv[2]
    if op != "?":
        b = sys.argv[3]
except IndexError:
    usage()
    raise SystemExit()

if op not in ("-", "+", "?"):
    usage()
    raise SystemExit("invalid operation '%s': not one of '-', '+' or '?')")

try:
    a = parse_date(a)
except ValueError, e:
    usage()
    raise SystemExit("invalid date format '%s': %s" % (a, e))



if op == "?":
    print_date(a)
elif op == "+":
    amount = parse_amount(b)
    print_amount(a + amount, amount)
elif op == "-":
    try:
        amount = - parse_amount(b)
        b = a + amount
    except ValueError:
        try:
            b = parse_date(b)
            amount = a - b
        except ValueError:
            raise SystemExit("second operand not date or amount: '%s'!" % b)

    print_amount(b, amount)

else:
    raise SystemExit("unknown operation: '%s'" % op)

