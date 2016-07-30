#!/usr/bin/env python

import gtk

from kiwi.ui.views import BaseView
from kiwi.ui.gadgets import quit_if_last
from kiwi.controllers import BaseController

class ExampleController(BaseController):
    def __init__(self, view):
        keyactions = {gtk.keysyms.Escape: quit_if_last}
        BaseController.__init__(self, view, keyactions)

    def on_ok__clicked(self, button, *args):
        self.view.label_last_button.set_text("Ok")

    def on_cancel__clicked(self, button, *args):
        self.view.label_last_button.set_text("Cancel")

    def after_entry_name__content_changed(self, entry, *args):
        self.view.label_name.set_text(entry.get_text())


view = BaseView(gladefile="example03",
                 widgets=("label_last_button", "ok", "cancel",
                           "entry_name", "label_name"),
                 delete_handler=quit_if_last)

controller = ExampleController(view)
view.show_all()
view.focus_topmost()
gtk.main()
