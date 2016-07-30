#!/usr/bin/python

WIDTH = 800
HEIGHT = 480
FS = False
TITLE = "Virtual Keyboard"
WM_INFO = ("Virtual Keyboard", "vkbd")

import os
import sys
import evas
import edje
import ecore
import ecore.evas

def on_resize(ee):
    x, y, w, h = ee.evas.viewport
    ee.data["main"].size = w, h


def on_delete_request(ee):
    ecore.main_loop_quit()


def on_key_down(obj, event, ee):
    if event.keyname in ("F6", "f"):
        ee.fullscreen = not ee.fullscreen
    elif event.keyname == "Escape":
        ecore.main_loop_quit()


class VirtualKeyboard(edje.Edje):
    def __init__(self, canvas):
        edje.Edje.__init__(self, canvas)
        self.text = []
        f = os.path.splitext(sys.argv[0])[0] + ".edj"
        self.file_set(f, "main")
        self.obj = {
            "alpha": self.part_swallow_get("alpha"),
            "special-1": self.part_swallow_get("special-1"),
            "special-2": self.part_swallow_get("special-2"),
            }
        self.pressed_keys = {}
        self.is_shift_down = False
        self.is_mouse_down = False
        self._setup_events()
        self.press_shift()

    def _setup_events(self):
        self.signal_callback_add("key_down", "*", self.on_edje_signal_key_down)
        self.signal_callback_add("mouse_over_key", "*",
                                 self.on_edje_signal_mouse_over_key)
        self.signal_callback_add("mouse_out_key", "*",
                                 self.on_edje_signal_mouse_out_key)
        self.signal_callback_add("mouse,down,1", "*",
                                 self.on_edje_signal_mouse_down_key)
        self.signal_callback_add("mouse,down,1,*", "*",
                                 self.on_edje_signal_mouse_down_key)
        self.signal_callback_add("mouse,up,1", "*",
                                 self.on_edje_signal_mouse_up_key)
        self.on_mouse_down_add(self.on_mouse_down)
        self.on_mouse_up_add(self.on_mouse_up)
        self.on_key_down_add(self.on_key_down)

    def press_shift(self):
        self.obj["alpha"].signal_emit("press_shift", "")
        self.is_shift_down = True

    def release_shift(self):
        self.obj["alpha"].signal_emit("release_shift", "")
        self.is_shift_down = False

    def toggle_shift(self):
        if self.is_shift_down:
            self.release_shift()
        else:
            self.press_shift()

    @staticmethod
    def on_edje_signal_key_down(self, emission, source):
        if ':' in source:
            key = source.split(":", 1)[1]
        else:
            key = source
        if key == "enter":
            self.text.append("<br>")
            self.part_text_set("field", "".join(self.text))
            self.press_shift()
        elif key == "backspace":
            self.text = self.text[:-1]
            self.part_text_set("field", "".join(self.text))
        elif key == "shift":
            self.toggle_shift()
        elif key in (".?123", "ABC", "#+=", ".?12"):
            pass
        elif key in "&":
            self.text.append("&amp;")
            self.part_text_set("field", "".join(self.text))
        elif key in "<":
            self.text.append("&lt;")
            self.part_text_set("field", "".join(self.text))
        elif key in ">":
            self.text.append("&gt;")
            self.part_text_set("field", "".join(self.text))
        else:
            if self.is_shift_down:
                self.release_shift()
                key = key.upper()
            else:
                key = key.lower()
            self.text += key
            self.part_text_set("field", "".join(self.text))

    @staticmethod
    def on_edje_signal_mouse_over_key(self, emission, source):
        if not self.is_mouse_down:
            return
        if ':' not in source:
            return
        part, subpart = source.split(':', 1)
        o = self.obj[part]

        if subpart in self.pressed_keys:
            return

        for k in self.pressed_keys.values():
            o.signal_emit("release_key", k)
        self.pressed_keys.clear()
        self.pressed_keys[subpart] = subpart
        o.signal_emit("press_key", subpart)

    @staticmethod
    def on_edje_signal_mouse_out_key(self, emission, source):
        if not self.is_mouse_down:
            return
        if ':' not in source:
            return
        part, subpart = source.split(':', 1)
        o = self.obj[part]

        if subpart in self.pressed_keys:
            del self.pressed_keys[subpart]
            o.signal_emit("release_key", subpart)

    @staticmethod
    def on_edje_signal_mouse_down_key(self, emission, source):
        if ':' not in source:
            return
        part, subpart = source.split(':', 1)
        o = self.obj[part]
        self.is_mouse_down = True

        if subpart in self.pressed_keys:
            return

        for k in self.pressed_keys.values():
            o.signal_emit("release_key", k)
        self.pressed_keys.clear()
        self.pressed_keys[subpart] = subpart
        o.signal_emit("press_key", subpart)

    @staticmethod
    def on_edje_signal_mouse_up_key(self, emission, source):
        if ':' not in source:
            return
        part, subpart = source.split(':', 1)
        o = self.obj[part]
        self.is_mouse_down = False
        if subpart in self.pressed_keys:
            del self.pressed_keys[subpart]
            o.signal_emit("release_key", subpart)
            o.signal_emit("activated_key", subpart)

    @staticmethod
    def on_mouse_down(self, event):
        if event.button != 1:
            return
        self.is_mouse_down = True

    @staticmethod
    def on_mouse_up(self, event):
        if event.button != 1:
            return
        self.is_mouse_down = False

    @staticmethod
    def on_key_down(self, event):
        k = event.keyname.lower()
        if k == "return":
            k = "enter"
        elif k == "backspace":
            pass
        elif k.startswith("shift"):
            k = "shift"
        elif k.startswith("alt_"):
            return
        elif k.startswith("control_"):
            return
        else:
            k = event.string

        if k:
            o.signal_emit("key_down", k)


if ecore.evas.engine_type_supported_get("software_x11_16") and \
   '-x11' not in sys.argv:
    ee = ecore.evas.SoftwareX11_16(w=WIDTH, h=HEIGHT)
else:
    ee = ecore.evas.SoftwareX11(w=WIDTH, h=HEIGHT)

canvas = ee.evas
o = VirtualKeyboard(canvas)
o.size = canvas.size
o.focus = True
o.show()
o.on_key_down_add(on_key_down, ee)


ee.data["main"] = o
ee.callback_delete_request = on_delete_request
ee.callback_resize = on_resize
ee.title = TITLE
ee.name_class = WM_INFO
ee.fullscreen = FS
ee.show()

ecore.main_loop_begin()
