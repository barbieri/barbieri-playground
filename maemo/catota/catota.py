#!/usr/bin/env python

import sys
import gtk
import catota.client
from catota.client import PlayerApp, PlayerUI
import logging as log


if __name__ == "__main__":
    #gtk.gdk.threads_init()

    log_level = log.WARNING
    for p in sys.argv[1:]:
        if p == "-v" or p == "--verbose":
            log_level -= 10

    log.basicConfig(level=log_level,
                    format="### %(asctime)s %(levelname)-8s %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")


    catota.client.load_plugins_sources("catota/plugins/client/sources")
    catota.client.load_plugins_engines("catota/plugins/client/engines")

    log.debug("Started")
    app = PlayerApp("Catota Player")
    ui = PlayerUI(app)
    ui.show()

    gtk.main()
    log.debug("Ended")
