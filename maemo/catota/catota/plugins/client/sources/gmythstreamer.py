#!/usr/bin/env python

import os
import hildon
import gtk
import urlparse
import urllib
import socket
import gobject
import catota.ui
from catota.client import PlayerSource, PreferencesProvider

class PlayerSourceGMythStreamer(PlayerSource, PreferencesProvider):
    priority = -1
    name = "gmyth-streamer"
    pretty_name = "GMyth Streamer"

    timeout = 10
    def_fifo_name = "/tmp/catota-gmythstreamer-%d.fifo" % os.getuid()
    preferences_section = "GMyth"
    def_preferences = {
        "address": "",
        "port": 50000,
        "type": "",
        "location": "",
        "mux": "avi",
        "vcodec": "mpeg4",
        "vbitrate": 400,
        "fps": 24,
        "acodec": "mp3lame",
        "abitrate": 128,
        }

    def __init__(self, parent_win):
        PreferencesProvider.__init__(self)
        PlayerSource.__init__(self, parent_win)
        self.host = None
        self.control = None
        self.data = None
        self.fifo = None
        self.fifo_name = None
        self.io_watcher_id = None
    # __init__()


    @classmethod
    def handles(cls, url):
        d = urlparse.urlparse(url)
        return d.scheme == "mythstreamer"
    # handles()


    def setup_gui_url_chooser(self):
        self.media_model = gtk.ListStore(str)
        self.media_type = gtk.ComboBox(self.media_model)
        cell = gtk.CellRendererText()
        self.media_type.pack_start(cell, True)
        self.media_type.add_attribute(cell, "text", 0)

        for t in ("file", "dvd", "tv", "dvb", "vcd", "radio", "cdda", "tivo"):
            self.media_model.append((t,))

        self.media_location = gtk.Entry()
        self.media_server = gtk.Label()
        self.media_server.set_alignment(0, 0.5)

        d = catota.ui.Dialog("Choose Location", self.parent_win,
                             extra_buttons=(gtk.STOCK_PREFERENCES, 1))

        t = catota.ui.new_table((("Server:", self.media_server),
                                 ("Type:", self.media_type),
                                 ("Location:", self.media_location)))
        d.vbox.pack_start(t, True, True)

        self.gui_url_chooser = d
    # setup_gui_url_chooser()


    def _set_media_type(self, type):
        for i, row in enumerate(self.media_model):
            if row[0] == type:
                self.media_type.set_active(i)
                break
    # _set_media_type()


    def get_url_from_chooser(self):
        self.media_location.set_text(self.preferences["location"])
        self._set_media_type(self.preferences["type"])

        self.gui_url_chooser.show()
        while 1:
            self.media_server.set_label("%s:%s" % (self.preferences["address"],
                                                   self.preferences["port"]))
            r = self.gui_url_chooser.run()
            if r != 1:
                break
            else:
                self.parent_win.show_preferences(self.address)

        self.gui_url_chooser.hide()

        if r == gtk.RESPONSE_ACCEPT:
            l = self.media_location.get_text()
            self.preferences["location"] = l
            t = self.media_type.get_active()
            if t < 0:
                return l
            else:
                m = self.media_model[t][0]
                self.preferences["type"] = m

                parms = {"type": self.preferences["type"],
                         "location": self.preferences["location"]}
                parms = urllib.urlencode(parms)
                return "mythstreamer://%s:%d/?%s" % \
                       (self.preferences["address"], self.preferences["port"],
                        parms)
        else:
            return None
    # get_url_from_chooser()


    def setup_gui_button_contents(self):
        msg = ("<big><b>GMyth Streamer</b></big>\n"
               "<small>Connects to GMyth Streamer server.</small>")

        self.gui_button_contents = catota.ui.MultiLineLabel(msg)
        self.gui_button_contents.show()
    # setup_gui_button_contents()


    def setup_gui_preferences(self):
        self.address = gtk.Entry()
        self.port = hildon.NumberEditor(0, 100000)

        wids = ("GMyth Streamer",
                ("Address:", self.address),
                ("Port:", self.port))

        self.gui_preferences = wids
    # setup_gui_preferences()


    def preferences_load(self, d):
        PreferencesProvider.preferences_load(self, d)

        self.address.set_text(self.preferences["address"])
        self.port.set_value(self.preferences["port"])
    # preferences_load()


    def preferences_save(self, d):
        self.preferences["address"] = self.address.get_text()
        self.preferences["port"] = self.port.get_value()

        PreferencesProvider.preferences_save(self, d)
    # preferences_save()


    def _log_and_raise(self, msg):
        self.log.error(msg)
        raise Exception(msg)
    # _log_and_raise()


    def open(self, url, options=None):
        PlayerSource.open(self, url, options)
        if url.startswith("mythstreamer://"):
            url = "http://" + url[len("mythstreamer://"):]

        d = urlparse.urlparse(url)
        params = {}
        for k, v in parse_qsl(d.query):
            t = params.setdefault(k, [])
            t.append(v)

        self.host = d.hostname
        try:
            self.control = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.control.settimeout(self.timeout)
            self.control.connect((d.hostname, d.port))

        except Exception, e:
            self.close()
            msg = "Could not connect to GMythStreamer at %s:%s: %s" % \
                  (d.hostname, d.port, e)
            self._log_and_raise(msg)
            return False


        self.fifo_name = self.def_fifo_name
        if os.path.exists(self.fifo_name):
            try:
                os.unlink(self.fifo_name)
            except Exception, e:
                self.close()
                msg = "Could not remove existing fifo \"%s\": %s" % \
                      (self.fifo_name, e)
                self._log_and_raise(msg)
                return False

        try:
            os.mkfifo(self.fifo_name, 0600)
        except Exception, e:
            self.close()
            msg = "Could not create fifo \"%s\": %s" % (self.fifo_name, e)
            self._log_and_raise(msg)
            return False

        return self._open_data(url, params, options)
    # open()


    def _recv_line(self):
        line = []
        while 1:
            c = self.control.recv(1)
            line.append(c)
            if not c or c == "\n":
                break

        line = "".join(line)
        return line
    # _recv_line()


    def _cmd(self, msg):
        if not self.control:
            self._log_and_raise("No PlayerSourceGMythStreamer control channel")
            return None

        self.log.debug("SEND: %s" % msg)
        self.control.send("%s\n" % msg)

        line = self._recv_line()
        self.log.debug("RECV: %s" % line)


        ret = line.split()
        if ret[0] == "NOTOK":
            return (False, " ".join(ret[1:]))
        elif ret[0] == "OK":
            has_payload = int(ret[1])
            payload = None
            if has_payload:
                payload = []
                while True:
                    line = self._recv_line()
                    if line[0] == "+":
                        if line[-1] == "\n":
                            line = line[:-1]
                        payload.append(line[1:])
                    elif line[0] == ".":
                        break

            return (True, payload)
    # _cmd()


    def _register_io_handlers(self):
        def handler(source, cond):
            if cond & gobject.IO_IN:
                if not self.fifo:
                    self.fifo = open(self.fifo_name, "w")

                self.fifo.write(source.recv(1024))
                return True
            else:
                self.log.debug("Error communicating with MPlayer")
                return False

        flags = gobject.IO_IN | gobject.IO_ERR | gobject.IO_HUP
        self.io_watcher_id = gobject.io_add_watch(self.data,
                                                  flags,
                                                  handler)
    # _register_io_handlers()


    def _open_data(self, url, params, options):
        cmd_opts = {
            "type": params["type"][0],
            "location": params["location"][0],
            "mux": self.preferences["mux"],
            "vcodec": self.preferences["vcodec"],
            "vbitrate": self.preferences["vbitrate"],
            "fps": self.preferences["fps"],
            "acodec": self.preferences["acodec"],
            "abitrate": self.preferences["abitrate"],
            "width": self.parent_win.data["Media"]["width"],
            "height": self.parent_win.data["Media"]["height"],
            }
        self._cmd(("SETUP %(type)s://%(location)s %(mux)s %(vcodec)s "
                   "%(vbitrate)s %(fps)s %(acodec)s %(abitrate)s "
                   "%(width)s %(height)s") %
                  cmd_opts)
        ok, payload = self._cmd("PLAY")
        if not ok:
            self._log_and_raise("Could not play: %s" % (payload,))
            return False

        port = int(payload[0])

        try:
            self.data = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.data.settimeout(self.timeout)
            self.data.connect((self.host, port))
        except Exception, e:
            self.close()
            msg = "Could not connect to GMythStreamer at %s:%s" % \
                  (self.host, port)
            self._log_and_raise(msg)
            return False

        self._register_io_handlers()
        return True
    # _open_data()


    def get_player_engine_input_handler(self):
        return self.fifo_name
    # get_player_engine_input_handler()


    def close(self):
        PlayerSource.close(self)

        if self.io_watcher_id is not None:
            gobject.source_remove(self.io_watcher_id)
            self.io_watcher_id = None

        if self.data:
            self.data.close()
            self.data = None

        if self.control:
            self.control.close()
            self.control = None

        if self.fifo:
            self.fifo.close()
            self.fifo = None

        self.fifo_name = None

        return True
    # close()
# PlayerSourceGMythStreamer
