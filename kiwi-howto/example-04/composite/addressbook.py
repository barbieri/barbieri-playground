#!/usr/bin/env python

import gtk

from kiwi.ui.delegates import Delegate, SlaveDelegate, ProxySlaveDelegate
from kiwi.ui.gadgets import quit_if_last
from kiwi.ui.objectlist import Column
from kiwi.model import Model


class EntryEditor(ProxySlaveDelegate):
    def __init__(self):
        ProxySlaveDelegate.__init__(self, None,
                                    gladefile="entry_editor",
                                    widgets=("name", "address", "phone"))

    def proxy_updated(self, widget, attribute, value):
        self.emit("result", self.model)

    def set_sensitive(self, v):
        self.toplevel.set_sensitive(v)


class ListEntries(SlaveDelegate):
    def __init__(self):
        SlaveDelegate.__init__(self,
                               gladefile="list_entries",
                               widgets=("table",))
        self.table.set_columns([Column("name", title="Name"),
                                Column("address", title="Address"),
                                Column("phone", title="Phone")])

    def add(self, obj, selected=True):
        self.table.append(obj, selected)

    def get_selected(self):
        return self.table.get_selected()

    def remove(self, obj):
        self.table.remove(obj)

    def on_table__selection_changed(self, table, obj):
        self.emit("result", obj)

    def update(self, *a):
        self.table.refresh()


class Addressbook(Delegate):
    def __init__(self):
        keyactions = {gtk.keysyms.Escape: quit_if_last,
                      gtk.keysyms.F1: self.my_f1_handler,
                      gtk.keysyms.F2: self.my_f2_handler}
        Delegate.__init__(self,
                           gladefile="addressbook",
                           widgets=("add", "remove"),
                           delete_handler=quit_if_last,
                           keyactions=keyactions)

        self.entry_editor = EntryEditor()
	self.entry_editor.set_sensitive(False)
        self.attach_slave("entry_editor", self.entry_editor)

        self.list_entries = ListEntries()
        self.list_entries.connect("result", self.entry_selected)
        self.attach_slave("list", self.list_entries)

        self.entry_editor.connect("result", self.list_entries.update)

    def entry_selected(self, table, obj):
        if obj is not None:
            self.entry_editor.set_model(obj)
            self.entry_editor.set_sensitive(True)

    def add_entry(self):
        self.list_entries.add(Person())

    def del_entry(self):
        obj = self.list_entries.get_selected()
        if obj is not None:
            self.list_entries.remove(obj)
            self.entry_editor.set_model(None)
            self.entry_editor.set_sensitive(False)

    def on_add__clicked(self, *args):
        self.add_entry()

    def on_remove__clicked(self, *args):
        self.del_entry()

    def my_f1_handler(self, widget, event):
        self.add_entry()

    def my_f2_handler(self, widget, event):
        self.del_entry()


class Person(Model):
    def __init__(self, name="", address="", phone=""):
        self.name = name
        self.address = address
        self.phone = phone


addressbook = Addressbook()
addressbook.show_all()
addressbook.focus_topmost()
gtk.main()
