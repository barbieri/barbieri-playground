#!/usr/bin/env python

import sys
import os
import logging as log
from catota.server import serve_forever, load_plugins_transcoders

log_level = log.WARNING
for p in sys.argv[1:]:
    if p == "-v" or p == "--verbose":
        log_level -= 10

log.basicConfig(level=log_level,
                format=("### %(asctime)s %(name)-18s %(levelname)-8s "
                        "%(message)s"),
                datefmt="%Y-%m-%d %H:%M:%S")

pd = os.path.join("catota", "plugins", "server", "transcoders")
load_plugins_transcoders(pd)
serve_forever()
