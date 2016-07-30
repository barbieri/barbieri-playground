import gtk
from kiwi.ui.delegates import Delegate, SlaveDelegate, ProxyDelegate
from kiwi.ui.objectlist import Column
from kiwi.ui.gadgets import quit_if_last

import models

class Shell(Delegate):
    def __init__(self):
        Delegate.__init__(self,
                          gladefile="shell",
                          delete_handler=self.delete_handler,
                          widgets=("edit", "add", "remove", "quit"))
        self.list = List(toplevel=self)
        self.attach_slave("list_placeholder", self.list)
        self.list.focus_toplevel()
        self.list.connect("result", self._on_list__result)

        self.editor = Editor()
        self.editor.connect("result", self._on_editor__result)

    def on_quit__activate(self, *args):
        self.delete_handler()

    def on_edit__activate(self, *args):
        model = self.list.get_selected()
        if model is not None:
            self._edit_object(model)

    def on_add__activate(self, *args):
        self._edit_object()

    def on_remove__activate(self, *args):
        model = self.list.get_selected()
        if model is not None:
            models.Person.delete(model.id)
            self.list.load_data()

    def _on_editor__result(self, editor, result):
        self.list.update(result)

    def _on_list__result(self, list, model):
        self._edit_object(model)

    def _edit_object(self, model=None):
        if model is None:
            person_id = None
        else:
            person_id = model.id

        self.editor.set_person(person_id)
        self.editor.show_all()
        self.editor.focus_topmost()

    def delete_handler(self, *args):
        gtk.main_quit()


class List(SlaveDelegate):
    def __init__(self, toplevel=None):
        SlaveDelegate.__init__(self,
                               gladefile="list",
                               toplevel=toplevel,
                               widgets=("table",))
        self.table.set_columns([Column("name", title="Name"),
                                Column("address", title="Address"),
                                Column("phones", title="Phones",
                                       format_func=self._phones_format),
                                Column("birthday", title="Birthday"),
                                Column("category", title="Category",
                                       format_func=self._category_format)])
        self.load_data()

    def update(self, obj):
        if obj is not None:
            try:
                self.table.update(obj)
            except ValueError, e:
                self.load_data()

    def load_data(self):
        self.table.add_list(models.Person.select())

    def get_selected(self):
        return self.table.get_selected()

    def on_table__double_click(self, widget, *args):
        self.emit("result", self.get_selected())

    def _phones_format(self, phones):
        p = []
        for e in phones:
            p.append(e.number)
        return ", ".join(p)

    def _category_format(self, category):
        if category is not None:
            return category.name
        else:
            return ""


class Editor(ProxyDelegate):
    def __init__(self, toplevel=None):
        ProxyDelegate.__init__(self,
                               model=None,
                               toplevel=toplevel,
                               delete_handler=self.hide,
                               gladefile="editor",
                               widgets=("name",
                                        "address",
                                        "phones",
                                        "add_phone",
                                        "edit_phone",
                                        "remove_phone",
                                        "birthday",
                                        "category",
                                        "cancel",
                                        "ok"),
                               proxy_widgets=("name",
                                              "address",
                                              "birthday"))
        self.phones.set_columns([Column("number",
                                        title="Number",
                                        editable=True,
                                        expand=True)])

    def set_person(self, person_id):
        self.trans = models.transaction()
        if person_id:
            model = self.trans.Person.get(person_id)
        else:
            model = self.trans.Person()

        categories = [c.name for c in self.trans.Category.select()]
        categories.insert(0, "")
        self.category.prefill(categories)
        if model.category:
            self.category.select(model.category.name)
        else:
            self.category.select("")
        self.phones.add_list(model.phones)
        self.set_model(model)

    def on_cancel__clicked(self, *args):
        self.trans.rollback()
        self.trans.begin()
        self.emit("result", None)
        self.hide()

    def on_ok__clicked(self, widget, *args):
        self.trans.commit()
        self.emit("result", self.model)
        self.hide()

    def on_add_phone__clicked(self, *args):
        phone = self.trans.Phone(person=self.model)
        self.phones.append(phone, select=True)
        self._edit_phone_selected()

    def on_remove_phone__clicked(self, *args):
        phone = self.phones.get_selected()
        if phone is not None:
            self.trans.Phone.delete(phone.id)
            self.phones.add_list(self.model.phones)

    def on_edit_phone__clicked(self, *args):
        self._edit_phone_selected()

    def _edit_phone_selected(self):
        tv = self.phones.get_treeview()
        s = tv.get_selection()
        model, itr = s.get_selected()
        if itr is not None:
            path = model.get_path(itr)
            col = self.phones.get_columns()[0]
            col = self.phones.get_treeview_column(col)
            tv.set_cursor(path, focus_column=col, start_editing=True)

    def on_category__changed(self, *a):
        selected = self.category.get_selected()
        if selected:
            c = self.trans.Category.byName(selected)
            self.model.category = c
        else:
            self.model.category = None
