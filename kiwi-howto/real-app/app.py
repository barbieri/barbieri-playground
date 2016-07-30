import gtk
import models
import views
import os

connection = "sqlite://%s" % os.path.realpath("db.sqlite")

models.setConnection(connection)
models.createTables()

view = views.Shell()
view.show_all()
view.focus_topmost()

gtk.main()
