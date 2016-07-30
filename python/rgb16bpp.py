#!/usr/bin/python

import sys

if len(sys.argv) != 2 and len(sys.argv) != 4:
    raise SystemExit("Usage: %s <color>" % sys.argv[0])

def parse_color(color):
    try:
        return int(color, 0)
    except ValueError:
        raise ValueError(("unsupported color component: %s, "
                          "use a valid integer value/representation.") % color)

def parse_from_tuple(components):
    if len(components) != 3:
        raise ValueError("components should be red, green and blue")
    r, g, b = components
    r = parse_color(r)
    g = parse_color(g)
    b = parse_color(b)
    return (r << 16) | (g << 8) | b

if len(sys.argv) == 2:
    color = sys.argv[1]
    if color.startswith("0x"):
        color = int(color, 16)
    elif color.startswith("#"):
        color = color.replace("#", "0x")
        color = int(color, 16)
    elif ',' in color:
        color = parse_from_tuple(color.split(','))
    else:
        try:
            color = int(color)
        except ValueError:
            raise ValueError(("unsupported color: %s, use either #rrggbb, "
                              "0xrrggbb or rr,gg,bb") % color)
else:
    color = parse_from_tuple(sys.argv[1:])

r = (color >> 16) & 0xff
g = (color >> 8) & 0xff
b = color & 0xff

print "Original color: %#06x (#%06x) (%02d, %02d, %02d)" % \
    (color, color, r, g, b)

dr = (r >> 3) << 3
dg = (g >> 2) << 2
db = (b >> 3) << 3

downcolor = (dr << 16) | (dg << 8) | db
print "16bpp color...: %#06x (#%06x) (%02d, %02d, %02d)" % \
    (downcolor, downcolor, dr, dg, db)
