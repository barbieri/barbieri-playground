#!/usr/bin/env python

import gtk

from kiwi.ui.views import BaseView, SlaveView
from kiwi.ui.objectlist import Column
from kiwi.ui.gadgets import quit_if_last

# Main window
addressbook = BaseView(gladefile="addressbook",
                       widgets=("add", "del"),
                       delete_handler=quit_if_last)

## Slave Components:
# Entry editor GUI component
entry_editor = SlaveView(toplevel=addressbook,
                         widgets=("name", "address", "phone"),
                         gladefile="entry_editor")
# Entries list GUI component
list_entries = SlaveView(toplevel=addressbook,
                         widgets=("table",),
                         gladefile="list_entries")

list_entries.table.set_columns([Column("name", title="Name"),
                                Column("address", title="Address"),
                                Column("phone", title="Phone")])

## Attach slaves to main window
addressbook.attach_slave("entry_editor", entry_editor)
addressbook.attach_slave("list", list_entries)

addressbook.show_all()
addressbook.focus_topmost()
gtk.main()
