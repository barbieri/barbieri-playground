#!/usr/bin/env python

import gtk
import catota.ui
from catota.client import PlayerSource, PreferencesProvider

class PlayerSourcePassThrough(PlayerSource, PreferencesProvider):
    priority = 99999
    name = "pass-through"
    pretty_name = "Pass Through"

    preferences_section = "PassThrough"
    def_preferences = {
        "address": "",
        }

    def __init__(self, parent_win):
        PreferencesProvider.__init__(self)
        PlayerSource.__init__(self, parent_win)
    # __init__()


    @classmethod
    def handles(cls, url):
        return True
    # handles()


    def setup_gui_url_chooser(self):
        d = catota.ui.Dialog("Choose Location", self.parent_win)
        label = catota.ui.Label("<small><b>Enter location</b> to be "
                                "handled directly to underlying player engine"
                                "</small>")
        d.vbox.pack_start(label, fill=True, expand=False)
        label.show()

        self.gui_url_chooser_entry = gtk.TextBuffer()

        textview = gtk.TextView(self.gui_url_chooser_entry)
        textview.set_editable(True)
        textview.set_cursor_visible(True)
        textview.set_left_margin(2)
        textview.set_right_margin(2)
        textview.set_wrap_mode(gtk.WRAP_CHAR)

        sw = gtk.ScrolledWindow()
        sw.set_policy(hscrollbar_policy=gtk.POLICY_NEVER,
                      vscrollbar_policy=gtk.POLICY_AUTOMATIC)
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.add(textview)

        d.vbox.pack_start(sw, fill=True, expand=True)
        sw.show_all()

        self.gui_url_chooser = d
    # setup_gui_url_chooser()


    def get_url_from_chooser(self):
        self.gui_url_chooser_entry.set_text(self.preferences["address"])

        self.gui_url_chooser.show()
        r = self.gui_url_chooser.run()
        self.gui_url_chooser.hide()

        if r == gtk.RESPONSE_ACCEPT:
            b = self.gui_url_chooser_entry
            t = b.get_text(b.get_start_iter(), b.get_end_iter())
            self.preferences["address"] = t
            return t
        else:
            return None
    # get_url_from_chooser()


    def setup_gui_button_contents(self):
        msg = ("<big><b>Pass Through</b></big>\n"
               "<small>Player knows it, just pass through "
               "filename to player</small>")
        self.gui_button_contents = catota.ui.MultiLineLabel(msg)
        self.gui_button_contents.show()
    # setup_gui_button_contents()


    def get_player_engine_input_handler(self):
        return self.url
    # get_player_engine_input_handler()
# PlayerSourcePassThrough()
