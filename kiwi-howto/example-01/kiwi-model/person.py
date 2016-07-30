#!/usr/bin/env python
import gtk

from threading import Thread

from kiwi.model import Model
from kiwi.ui.views import BaseView
from kiwi.ui.gadgets import quit_if_last

# define the class that holds our application data
class Person(Model):
    name = ""
    address = ""
    phone = ""


person = Person()

view1 = BaseView(delete_handler=quit_if_last,
                 widgets=("name", "address", "phone"),
                 gladefile="person")

# create and run a proxy interface attached to person
view1.add_proxy(person, ("name", "address", "phone"))
view1.focus_topmost()
view1.show_all()

view2 = BaseView(delete_handler=quit_if_last,
                 widgets=("name", "address", "phone"),
                 gladefile="person")

# create and run a proxy interface attached to person
view2.add_proxy(person, ("name", "address", "phone"))
view2.focus_topmost()
view2.show_all()

gtk.main()
