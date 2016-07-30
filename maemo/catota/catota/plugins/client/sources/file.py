#!/usr/bin/env python

import gtk
import hildon
import urllib
from catota.client import PlayerSource, PreferencesProvider

class PlayerSourceFile(PlayerSource, PreferencesProvider):
    priority = -1
    name = "file"
    pretty_name = "Local Files"

    preferences_section = "File"
    def_preferences = {
        "uri": "file:///home/user/MyDocs/.videos/",
        }

    def __init__(self, parent_win):
        PreferencesProvider.__init__(self)
        PlayerSource.__init__(self, parent_win)
    # __init__()


    @classmethod
    def handles(cls, url):
        if url.startswith("file://"):
            return True
        elif "://" not in url:
            return True
        else:
            return False
    # handles()


    def setup_gui_url_chooser(self):
        d = hildon.FileChooserDialog(self.parent_win,
                                     gtk.FILE_CHOOSER_ACTION_OPEN)
        self.gui_url_chooser = d
    # setup_gui_url_chooser()


    def get_url_from_chooser(self):
        self.gui_url_chooser.set_uri(self.preferences["uri"])
        self.gui_url_chooser.show()
        r = self.gui_url_chooser.run()
        self.gui_url_chooser.hide()

        if r == gtk.RESPONSE_OK:
            t = self.gui_url_chooser.get_uri()
            self.preferences["uri"] = t
            return t
        else:
            self.gui_url_chooser.set_uri(self.preferences["uri"])
            return None
    # get_url_from_chooser()


    def setup_gui_button_contents(self):
        w = gtk.Label()
        w.set_markup("<big><b>Local File</b></big>\n"
                     "<small>Choose among local files</small>")
        w.set_line_wrap(True)
        w.set_single_line_mode(False)
        w.set_alignment(0.0, 0.5)
        w.show()

        self.gui_button_contents = w
    # setup_gui_button_contents()


    def get_player_engine_input_handler(self):
        return urllib.unquote(self.url)
    # get_player_engine_input_handler()
# PlayerSourceFile
