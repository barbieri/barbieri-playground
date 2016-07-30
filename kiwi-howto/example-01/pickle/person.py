#!/usr/bin/env python
import gtk

from kiwi.model import PickledModel
from kiwi.ui.views import BaseView
from kiwi.ui.gadgets import quit_if_last

# define the class that holds our application data
class Person(PickledModel):
    name = ""
    address = ""
    phone = ""


person = Person.unpickle() # load person instance

view = BaseView(delete_handler=quit_if_last,
                widgets=("name", "address", "phone"),
                gladefile="person")

# create and run a proxy interface attached to person
view.add_proxy(person, ("name", "address", "phone"))
view.focus_topmost()
view.show_all()

# Enter main lopp, where GTK will handle events
gtk.main()

# save changes done to theinstance
person.save()

