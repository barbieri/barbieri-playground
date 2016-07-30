#!/usr/bin/env python
import gtk
import os

from sqlobject import *

from kiwi.ui.views import BaseView
from kiwi.ui.gadgets import quit_if_last


dbfile = os.path.realpath("db.sqlite")
__connection__ = "sqlite://%s" % dbfile


# define the class that holds our application data
class Person(SQLObject):
    name    = StringCol(default=None)
    address = StringCol(default=None)
    phone   = StringCol(default=None)


try:
    # create table if it doesn't exist
    Person.createTable()
except:
    # table already exists
    pass

try:
    # Get the first record
    person = Person.get(1)
except SQLObjectNotFound:
    # Create a new, Empty, record
    person = Person()


view = BaseView(delete_handler=quit_if_last,
                widgets=("name", "address", "phone"),
                gladefile="person")

# create and run a proxy interface attached to person
view.add_proxy(person, ("name", "address", "phone"))
view.focus_topmost()
view.show_all()

# Enter main lopp, where GTK will handle events
gtk.main()

