#!/usr/bin/env python

import gtk
from datetime import datetime

from kiwi.model import Model
from kiwi.datatypes import ValidationError
from kiwi.ui.delegates import ProxyDelegate
from kiwi.ui.gadgets import quit_if_last

class Data(Model):
    def __init__(self, text_entry="", int_entry=0, float_entry=0.0,
                  date_entry=None, mandatory_entry=""):
        self.text_entry = text_entry
        self.int_entry = int_entry
        self.float_entry = float_entry
        self.mandatory_entry = mandatory_entry
        self.date_entry = date_entry or datetime.today()

    def __str__(self):
        return ('<Data '
                 'text_entry="%(text_entry)s" '
                 'int_entry="%(int_entry)s" '
                 'float_entry="%(float_entry)s" '
                 'date_entry="%(date_entry)s" '
                 'mandatory_entry="%(mandatory_entry)s" '
                 '/>') % self.__dict__

class App(ProxyDelegate):
    def __init__(self, model=None):
        ProxyDelegate.__init__(self, model,
                                gladefile="form",
                                delete_handler=quit_if_last,
                                widgets=("text_entry",
                                          "int_entry",
                                          "float_entry",
                                          "date_entry",
                                          "mandatory_entry",
                                          "ok"),
                                proxy_widgets=("text_entry",
                                                "int_entry",
                                                "float_entry",
                                                "date_entry",
                                                "mandatory_entry"))
        self.register_validate_function(self.validity)
        self.force_validation()

    def validity(self, is_valid):
        self.ok.set_sensitive(is_valid)

    def on_ok__clicked(self, btn, *args):
        print self.model
        quit_if_last()

    def on_text_entry__validate(self, text_entry, data):
        if "@" not in data:
            return ValidationError("Missing '@' character.")

    def on_int_entry__validate(self, int_entry, data):
        if not (5 <= data <= 10):
            return ValidationError("Value must be between 5 and 10")

    def on_float_entry__validate(self, float_entry, data):
        if not (-1.0 <= data <= 1.0):
            return ValidationError("Value must be between -1.0 and 1.0")


data = Data()
app = App(data)
app.show_all()
app.focus_topmost()

gtk.main()
