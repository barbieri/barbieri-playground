#!/usr/bin/env python
import gtk

from kiwi.ui.views import BaseView
from kiwi.ui.gadgets import quit_if_last

# define the class that holds our application data
class Person:
    name = ""
    address = ""
    phone = ""


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

print "name=%s, address=%s, phone=%s" % (person.name, person.address,
                                         person.phone)
