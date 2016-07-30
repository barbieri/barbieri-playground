#!/usr/bin/env python

import gtk
import pango

DEF_DIALOG_FLAGS = gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT
DEF_DIALOG_BUTTONS = (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                      gtk.STOCK_OK, gtk.RESPONSE_ACCEPT)


class Label(gtk.Label):
    def __init__(self, label="", ellipsize=pango.ELLIPSIZE_END):
        gtk.Label.__init__(self)
        self.set_use_markup(True)
        self.set_justify(gtk.JUSTIFY_LEFT)
        self.set_alignment(xalign=0.0, yalign=0.5)
        self.set_markup(label)
        if ellipsize:
            self.set_ellipsize(ellipsize)
    # __init__()
# Label


class MultiLineLabel(Label):
    def __init__(self, label=""):
        Label.__init__(self, label)
        self.set_line_wrap(True)
        self.set_single_line_mode(False)
        self.set_justify(gtk.JUSTIFY_FILL)
    # __init__()
# MultiLineLabel


class Dialog(gtk.Dialog):
    def __init__(self, title, parent, ok_button=True, cancel_button=True,
                 width=600, height=260, extra_buttons=None):
        buttons = []

        if extra_buttons:
            buttons.extend(extra_buttons)

        if ok_button:
            buttons.extend([gtk.STOCK_OK, gtk.RESPONSE_ACCEPT])

        if cancel_button:
            buttons.extend([gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT])

        buttons = tuple(buttons)
        gtk.Dialog.__init__(self, title, parent, DEF_DIALOG_FLAGS, buttons)
        self.set_size_request(width, height)
        self.set_has_separator(False)
    # __init__()
# Dialog


def new_label_for(label, field, align_right=True):
    """Creates a new gtk.Label and associates it to field"""
    wid = gtk.Label(label)
    wid.set_mnemonic_widget(field)
    if align_right:
        wid.set_justify(gtk.JUSTIFY_RIGHT)
        wid.set_alignment(xalign=1.0, yalign=0.5)
    return wid
# new_label_for()


def new_table(wids):
    """Creates a gtk.Table with two rows, use it for forms"""
    p = gtk.Table(rows=len(wids) or 1, columns=2, homogeneous=False)
    p.set_col_spacings(5)
    p.set_row_spacings(5)
    if len(wids) < 1:
        wid = gtk.Label("Empty")
        p.attach(wid, 0, 2, 0, 1)
        p.show_all()
        return p

    for i, row in enumerate(wids):
        if isinstance(row, basestring):
            wid = Label("<b>%s</b>" % row)
            p.attach(wid, 0, 2, i, i+1)
            wid.show()
            if i > 0:
                p.set_row_spacing(i-1, 10)

        elif isinstance(row, (tuple, list)):
            label, field = row
            wid = new_label_for(label, field)
            p.attach(wid, 0, 1, i, i+1, xoptions=gtk.FILL)
            p.attach(field, 1, 2, i, i+1)
            wid.show()
            field.show()

    sw = gtk.ScrolledWindow()
    sw.set_shadow_type(gtk.SHADOW_NONE)
    sw.set_policy(hscrollbar_policy=gtk.POLICY_NEVER,
                  vscrollbar_policy=gtk.POLICY_AUTOMATIC)
    sw.add_with_viewport(p)
    p.show()
    sw.show()
    return sw
# new_table()


def show_error(parent, msg):
    d = gtk.MessageDialog(parent,
                          DEF_DIALOG_FLAGS,
                          gtk.MESSAGE_ERROR,
                          gtk.BUTTONS_OK,
                          msg)
    d.show_all()
    d.run()
    d.hide()
    d.destroy()
# show_error()
