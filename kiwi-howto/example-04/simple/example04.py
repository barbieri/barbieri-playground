#!/usr/bin/env python

import gtk

from kiwi.ui.delegates import Delegate
from kiwi.ui.gadgets import quit_if_last

class ExampleDelegate(Delegate):
    def __init__(self):
        keyactions = {gtk.keysyms.Escape: quit_if_last}
        Delegate.__init__(self,
                           gladefile="example04",
                           widgets=("label_last_button", "ok", "cancel",
                                     "entry_name", "label_name"),
                           delete_handler=quit_if_last,
                           keyactions=keyactions)

    def on_ok__clicked(self, button, *args):
        self.view.label_last_button.set_text("Ok")

    def on_cancel__clicked(self, button, *args):
        self.view.label_last_button.set_text("Cancel")

    def after_entry_name__content_changed(self, entry, *args):
        self.view.label_name.set_text(entry.get_text())


delegate = ExampleDelegate()
delegate.show_all()
delegate.focus_topmost()
gtk.main()
