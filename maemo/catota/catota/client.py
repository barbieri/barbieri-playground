#!/usr/bin/env python

__author__ = "Gustavo Sverzut Barbieri"
__author_email__ = "barbieri@gmail.com"
__license__ = "GPL"
__version__ = "0.2"

import sys
import os
import gtk
import gobject
import hildon
import pango
import logging
import cPickle as Pickle
import catota.utils
import catota.ui

log = logging.getLogger("catota.client")

DEF_BIN_PATH = "/usr/bin"


class PreferencesProvider(object):
    preferences_section = None
    def_preferences = {}

    def __init__(self):
        self.gui_preferences = None
        self.preferences = {}
        self.preferences.update(self.def_preferences)
        self.setup_gui_preferences()
    # __init__()


    def setup_gui_preferences(self):
        pass
    # setup_gui_preferences()


    def preferences_load(self, d):
        my_sec = d.get(self.preferences_section, None)
        if not my_sec:
            return

        self.preferences.update(my_sec)
    # preferences_load()


    def preferences_save(self, d):
        my_sec = d.setdefault(self.preferences_section, {})
        my_sec.update(self.preferences)
    # preferences_save()
# PreferencesProvider


class PlayerEngine(gobject.GObject):
    name = None
    priority = 0

    log = logging.getLogger("catota.engine")

    catota.utils.gsignal("state-changed", int)
    catota.utils.gsignal("error", str)
    catota.utils.gsignal("eos")
    catota.utils.gsignal("pos", float)
    catota.utils.gsignal("media-info", object)

    STATE_NONE = 0
    STATE_PLAYING = 1
    STATE_PAUSED = 2
    STATE_ERROR = 3
    def __init__(self, parent_win, xid=0):
        gobject.GObject.__init__(self)
        self.parent_win = parent_win
        self.xid = xid
        self.playing = None
        self.paused = False
        self.volume = 0
        self.mute = False
        self.pos = 0.0
        self.length = None
        self.info = {}
        self.fullscreen = False
        self.state = PlayerEngine.STATE_NONE
        self.menu_items = None
        self.setup_menu_items()
    # __init__()


    def setup_menu_items(self):
        pass
    # setup_menu_items()


    def play(self, filename):
        self.playing = filename
        self.emit("state-changed", PlayerEngine.STATE_PLAYING)
        return True
    # play()


    def pause(self):
        self.paused = not self.paused
        self.emit("state-changed", PlayerEngine.STATE_PAUSED)
        return True
    # paused()


    def stop(self):
        self.playing = None
        self.emit("state-changed", PlayerEngine.STATE_NONE)
        return True
    # stop()


    SEEK_RELATIVE = 0
    SEEK_PERCENT = 1
    SEEK_ABSOLUTE = 2
    def seek(self, pos, type):
        return True
    # seek()


    def set_volume(self, value):
        self.volume = value
        return True
    # set_volume()


    def set_mute(self, status):
        self.mute = status
        return True
    # set_mute()


    def set_fullscreen(self, status):
        self.fullscreen = status
        return True
    # set_fullscreen()


    def show_osd_message(self, msg, duration):
        return True
    # show_osd_message()
# PlayerEngine



class PlayerSource(object):
    priority = 0
    name = None
    pretty_name = None

    log = logging.getLogger("catota.source")

    def __init__(self, parent_win):
        self.url = None
        self.parent_win = parent_win
        self.options = None
        self.gui_url_chooser = None
        self.gui_button_contents = None
        self.setup_gui_url_chooser()
        self.setup_gui_button_contents()
    # __init__()


    @classmethod
    def handles(cls, url):
        return False
    # handles()


    def setup_gui_url_chooser(self):
        pass
    # setup_gui_url_chooser()


    def get_url_from_chooser(self):
        return None
    # get_url_from_chooser()


    def setup_gui_button_contents(self):
        self.gui_button_contents = gtk.Label(self.__class__.__name__)
        self.gui_button_contents.show()
    # setup_gui_button_contents()


    def open(self, url, options=None):
        self.url = url
        self.options = options
        return True
    # open()


    def get_player_engine_input_handler(self):
        return None
    # get_player_engine_input_handler()


    def close(self):
        self.url = None
        self.options = None
        return True
    # close()
# PlayerSource



class PlayerPreferences(catota.ui.Dialog):
    def __init__(self, parent):
        catota.ui.Dialog.__init__(self, "Preferences", parent)
        self.player = parent
        self._setup_ui()
    # __init__()


    def _setup_ui(self):
        self.set_has_separator(False)

        self.tab = gtk.Notebook()
        self.vbox.pack_start(self.tab, fill=True, expand=True)
        self._setup_ui_sources()
        self._setup_ui_advanced()
        self._setup_ui_player_conf()
        self.tab.show()
    # _setup_ui()


    def _setup_ui_sources(self):
        wids = []
        for o in self.player.sources:
            if isinstance(o, PreferencesProvider) and o.gui_preferences:
                wids.extend(o.gui_preferences)

        self.tab.append_page(catota.ui.new_table(wids), gtk.Label("Sources"))
    # _setup_ui_sources()


    def _setup_ui_advanced(self):
        self.width = hildon.NumberEditor(100, 400)
        self.height = hildon.NumberEditor(100, 240)

        wids = ("Media",
                ("Width:", self.width),
                ("Height:", self.height),
                )

        self.tab.append_page(catota.ui.new_table(wids), gtk.Label("Advanced"))
    # _setup_ui_advanced()


    def _setup_ui_player_conf(self):
        wids = []

        if isinstance(self.player.current_engine, PreferencesProvider):
            wids.extend(self.player.current_engine.gui_preferences)

        self.tab.append_page(catota.ui.new_table(wids), gtk.Label("Player"))
    # _setup_ui_player_conf()


    def _setup_connections(self):
        self.connect("response", self._do_response)
    # _setup_connections()


    def _fill_data(self):
        d = self.player.data

        # Advanced
        self.width.set_value(d["Media"]["width"])
        self.height.set_value(d["Media"]["height"])

        if isinstance(self.player.current_engine, PreferencesProvider):
            self.player.current_engine.preferences_load(d)

        for o in self.player.sources:
            if isinstance(o, PreferencesProvider):
                o.preferences_load(d)
    # _fill_data()


    def _save_data(self):
        d = self.player.data

        # Advanced
        d["Media"]["width"] = int(self.width.get_value())
        d["Media"]["height"] = int(self.height.get_value())

        if isinstance(self.player.current_engine, PreferencesProvider):
            self.player.current_engine.preferences_save(d)

        for o in self.player.sources:
            if isinstance(o, PreferencesProvider):
                o.preferences_save(d)
    # _save_data()


    def run(self, focus_widget=None):
        self.show()
        self._fill_data()
        if not focus_widget:
            self.tab.set_current_page(0)
        else:
            def has_widget(container, wid):
                for w in container.get_children():
                    if w == wid:
                        return True
                    elif isinstance(w, gtk.Container):
                        if has_widget(w, wid):
                            return True
                return False
            # has_widget()

            for i in xrange(self.tab.get_n_pages()):
                w = self.tab.get_nth_page(i)
                if has_widget(w, focus_widget):
                    self.tab.set_current_page(i)
                    break

            focus_widget.grab_focus()

        response = gtk.Dialog.run(self)
        self.hide()
        if response == gtk.RESPONSE_ACCEPT:
            self._save_data()
            return True
        else:
            return False
    # run()
# PlayerPreferences



class PlayerUI(hildon.Window):
    settings_file = os.path.expanduser("~/.catota-player.conf")
    plugins_source = catota.utils.PluginSet(PlayerSource)
    plugins_engine = catota.utils.PluginSet(PlayerEngine)

    def __init__(self, app):
        hildon.Window.__init__(self)
        self.app = app
        app.add_window(self)
        self.actions = {}
        self.is_fullscreen = False
        self.last_played = None

        self.accel_group = gtk.AccelGroup()
        self.add_accel_group(self.accel_group)
        self.action_group = gtk.ActionGroup("PlayerUI")
        self._setup_actions()

        self.current_engine = self.plugins_engine[0](self)
        self.current_source = None
        self.sources = []
        self.current_source = None
        for cls in self.plugins_source:
            try:
                o = cls(self)
                self.sources.append(o)
                log.info("loaded source: \"%s\"" % cls.__name__)
            except Exception, e:
                log.error("could not instantiate source \"%s\": %s" %
                          (cls.__name__, e))


        # BEG: APP Data
        ## Server
        self.data = {"Media":
                     {"width": 320,
                      "height": 240,
                      },
                     "Player":
                     {"volume": 80,
                      "mute": False,
                      }
                     }
        # END: of APP Data

        self.media_length = None
        self.media_title = None

        self._load_settings()

        for o in self.sources:
            if isinstance(o, PreferencesProvider):
                o.preferences_load(self.data)

        if isinstance(self.current_engine, PreferencesProvider):
            self.current_engine.preferences_load(self.data)

        self._setup_menus()
        self._setup_toolbar()
        self._setup_ui()
        self._setup_connections()

        # Be maemo-like
        settings = self.get_settings()
        settings.set_property("gtk-button-images", False)
        settings.set_property("gtk-menu-images", False)

        # Have Task Navigator to blink ;-)
        #self.set_urgency_hint(True)
    # __init__()


    @classmethod
    def load_plugins_sources(cls, directory):
        cls.plugins_source.load_from_directory(directory)
    # load_plugins_sources()


    @classmethod
    def load_plugins_engines(cls, directory):
        cls.plugins_engine.load_from_directory(directory)
    # load_plugins_engines()


    def _load_settings(self):
        if not os.path.exists(self.settings_file):
            return

        try:
            fd = open(self.settings_file)
        except Exception, e:
            log.error("Failed to open for reading config file: '%s': %s" %
                      (self.settings_file, e))
            return

        data = Pickle.load(fd)
        for sec, d in data.iteritems():
            n = self.data.setdefault(sec, {})
            n.update(d)

        log.debug("Settings loaded from %s" % self.settings_file)
        fd.close()
    # _load_settings()


    def _save_settings(self):
        try:
            fd = open(self.settings_file, "w")
        except Exception, e:
            log.error("Failed to open for writing config file: '%s': %s" %
                      (self.settings_file, e))
            return

        for o in self.sources:
            if isinstance(o, PreferencesProvider):
                o.preferences_save(self.data)

        if isinstance(self.current_engine, PreferencesProvider):
            self.current_engine.preferences_save(self.data)

        Pickle.dump(self.data, fd, -1)
        log.debug("Settings saved to %s" % self.settings_file)
        fd.close()
    # _save_settings()


    def _add_stock_action(self, name, label=None, tooltip=None, stock=None):
        act = gtk.Action(name, label, tooltip, stock)

        self.action_group.add_action_with_accel(act, None)
        act.set_accel_group(self.accel_group)
        act.connect_accelerator()

        self.actions[name] = act
    # _add_stock_action()


    def _setup_actions(self):
        self._add_stock_action("Quit", stock=gtk.STOCK_QUIT)
        self._add_stock_action("Preferences", stock=gtk.STOCK_PREFERENCES)
        self._add_stock_action("Open", stock=gtk.STOCK_OPEN)
        self._add_stock_action("Play", stock=gtk.STOCK_MEDIA_PLAY)
        self._add_stock_action("Stop", stock=gtk.STOCK_MEDIA_STOP)


        act = gtk.ToggleAction("Pause", None, None, gtk.STOCK_MEDIA_PAUSE)
        self.action_group.add_action_with_accel(act, None)
        act.set_accel_group(self.accel_group)
        act.connect_accelerator()
        self.actions["Pause"] = act
    # _setup_actions()


    def _setup_menus(self):
        menu = gtk.Menu()

        item = gtk.MenuItem("Player")
        menu.append(item)
        item.show()
        submenu = gtk.Menu()
        if self.current_engine.menu_items:
            for wid in self.current_engine.menu_items:
                submenu.append(wid)
        item.set_submenu(submenu)
        submenu.show_all()

        def add_action(name):
            item = self.actions[name].create_menu_item()
            menu.append(item)
            item.show()

        item = gtk.MenuItem("Source")
        menu.append(item)
        item.show()
        submenu = gtk.Menu()
        for o in self.sources:
            if o.pretty_name:
                subitem = gtk.MenuItem(o.pretty_name)
                submenu.append(subitem)
                subitem.connect("activate", self._source_activated, o)
        item.set_submenu(submenu)
        submenu.show_all()

        add_action("Preferences")

        item = gtk.SeparatorMenuItem()
        menu.append(item)
        item.show()

        add_action("Quit")

        self.set_menu(menu)
        menu.show()
    # _setup_menus()


    def _setup_toolbar(self):
        tb = gtk.Toolbar()
        tb.set_orientation(gtk.ORIENTATION_HORIZONTAL)
        tb.set_style(gtk.TOOLBAR_BOTH_HORIZ)

        self.add_toolbar(tb)
        self.toolbar = tb
        self.show_all() # Yep, otherwise toolbar don't show, hildon bug

        model = gtk.ListStore(str, object)
        for o in self.sources:
            if o.pretty_name:
                model.append((o.pretty_name, o))

        ti = gtk.ToolItem()
        self.source_selector = gtk.ComboBox(model)
        self.source_selector.connect("changed", self._source_selector_changed)
        r = gtk.CellRendererText()
        r.set_property("scale", pango.SCALE_SMALL)
        r.set_property("scale-set", True)
        self.source_selector.pack_start(r, True)
        self.source_selector.add_attribute(r, "text", 0)
        ti.add(self.source_selector)
        ti.show_all()
        tb.insert(ti, -1)

        ti = self.actions["Open"].create_tool_item()
        ti.show()
        tb.insert(ti, -1)

        self.infotext = catota.ui.Label()
        ti = gtk.ToolItem()
        ti.add(self.infotext)
        ti.set_expand(True)
        tb.insert(ti, -1)
        ti.show_all()

        self.timepos_popup = None
        self.timepos = gtk.ProgressBar()
        self.timepos.set_size_request(120, 30)
        self.timepos.set_text("00:00:00")
        self.timepos.add_events(gtk.gdk.BUTTON_PRESS_MASK)
        self.timepos.hide()
        ti = gtk.ToolItem()

        ### Work around gtk.ProgressBar() drawing with maemo theme:
        # maemo theme has a fixed height and starts to redraw the
        # bar if there is space, so have it to not expand/fill and
        # add 2 empty spaces before and after in a VBox.
        box = gtk.VBox()
        wid = gtk.EventBox()
        wid.show()
        box.pack_start(wid, True, True)
        box.pack_start(self.timepos, False, False)
        wid = gtk.EventBox()
        wid.show()
        box.pack_start(wid, True, True)
        box.show()

        ti.add(box)
        ti.set_expand(False)
        tb.insert(ti, -1)
        ti.show()
    # _setup_toolbar()


    def _setup_ui(self):
        self.top_layout = gtk.VBox(homogeneous=False, spacing=0)
        self.add(self.top_layout)

        self.pref_dialog = PlayerPreferences(self)
        self._setup_ui_chooser()
        self._setup_ui_player()
        self.chooser_layout.show()
        self.top_layout.show()

        self.current_engine.xid = self.video_container.window.xid
    # _setup_ui()


    def _setup_ui_chooser(self):
        self.chooser_layout = gtk.VBox(homogeneous=False, spacing=2)
        self.top_layout.pack_start(self.chooser_layout, fill=True, expand=True)

        msg = ("<big><b>Choose your media source</b></big>\n"
               "Click one of the buttons below to be able to "
               "select what to play")
        info = catota.ui.MultiLineLabel(msg)
        info.show()
        self.chooser_layout.pack_start(info, fill=True, expand=False)

        box = gtk.VBox(homogeneous=True, spacing=5)
        box.show()
        for o in self.sources:
            btn = gtk.Button()
            btn.add(o.gui_button_contents)
            btn.set_size_request(-1, 40)
            btn.show()
            btn.connect("clicked", self._source_activated, o)
            box.pack_start(btn, fill=True, expand=False)

        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_NONE)
        sw.set_policy(hscrollbar_policy=gtk.POLICY_NEVER,
                      vscrollbar_policy=gtk.POLICY_AUTOMATIC)
        sw.add_with_viewport(box)
        sw.show()

        self.chooser_layout.pack_start(sw, fill=True, expand=True)
    # _setup_ui_chooser()


    def _setup_ui_player(self):
        self.play_layout = gtk.HBox(homogeneous=False, spacing=2)
        self.top_layout.pack_start(self.play_layout, fill=True, expand=True)

        vbox = gtk.VBox(homogeneous=True, spacing=5)
        vbox.set_size_request(80, -1)
        for name, type in (("Play", gtk.Button),
                           ("Pause", gtk.ToggleButton),
                           ("Stop", gtk.Button)):
            act = self.actions[name]
            btn = gtk.Button()
            btn.set_image(act.create_icon(gtk.ICON_SIZE_DIALOG))
            vbox.pack_start(btn, fill=True, expand=False)
            act.connect_proxy(btn)

        vbox.show_all()
        self.play_layout.pack_start(vbox, fill=True, expand=False)
        self.controls = vbox

        self.video_container = gtk.EventBox()
        self.video_container.set_property("can-focus", True)
        self.video_container.set_events(gtk.gdk.ALL_EVENTS_MASK)

        self.video_container.modify_bg(gtk.STATE_NORMAL,
                                       gtk.gdk.color_parse("#000000"))
        self.play_layout.pack_start(self.video_container, expand=True,
                                   fill=True)
        self.video_container.show()

        self.volumebar = hildon.VVolumebar()
        self.volumebar.set_level(self.data["Player"]["volume"])
        self.volumebar.set_mute(self.data["Player"]["mute"])
        self.play_layout.pack_end(self.volumebar, expand=False, fill=True)
        self.volumebar.show()


        # Seek bar
        self.seekbar = hildon.Seekbar()
        self.seekbar.set_size_request(600, -1)

        vbox = gtk.VBox(homogeneous=False, spacing=3)
        self.seek_title = catota.ui.Label()
        vbox.pack_start(self.seek_title, fill=True, expand=True)

        self.cur_time = catota.ui.Label("<small>00:00:00</small>",
                                        ellipsize=None)

        self.total_time = catota.ui.Label("<small>00:00:00</small>",
                                          ellipsize=None)

        hbox = gtk.HBox(homogeneous=False, spacing=3)
        hbox.pack_start(self.cur_time, fill=True, expand=False)
        hbox.pack_start(self.seekbar, fill=True, expand=True)
        hbox.pack_start(self.total_time, fill=True, expand=False)
        vbox.pack_start(hbox, fill=True, expand=True)

        w = gtk.Window(gtk.WINDOW_POPUP)
        w.set_size_request(615, -1)
        w.set_transient_for(self)
        w.set_destroy_with_parent(True)
        w.set_decorated(False)
        w.set_border_width(6)
        w.set_gravity(gtk.gdk.GRAVITY_SOUTH_EAST)
        w.add(vbox)
        vbox.show_all()

        width, height = w.get_size()
        pheight = 58

        w.move(gtk.gdk.screen_width() - width,
               gtk.gdk.screen_height() - height - pheight)

        self.timepos_popup = w
        self.timepos_popup_visible = False
    # _setup_ui()


    def _setup_connections(self):
        self.connect("destroy", self.quit)
        self.connect("window-state-event", self._window_state_changed)
        self.connect("key-press-event", self._key_pressed)

        eng_conn = self.current_engine.connect
        eng_conn("eos", self._player_eos)
        eng_conn("error", self._player_error)
        eng_conn("pos", self._player_pos)
        eng_conn("state-changed", self._player_state_changed)
        eng_conn("media-info", self._player_media_info)
        self.timepos_sync_pos_handler = eng_conn("pos", self._seekbar_sync_pos)
        self.current_engine.handler_block(self.timepos_sync_pos_handler)

        def action_connect(name, callback):
            self.actions[name].connect("activate", callback)

        action_connect("Quit", self.quit)
        action_connect("Preferences", self._do_preferences)
        action_connect("Open", self._do_open)
        action_connect("Play", self._do_play)
        action_connect("Pause", self._do_pause)
        action_connect("Stop", self._do_stop)

        vb_conn = self.volumebar.connect
        vb_conn("mute_toggled", self._volume_mute_toggle)
        vb_conn("level_changed", self._volume_changed)

        self.video_container.connect_after("realize",
                                           self._video_container_realize)
        self.video_container.connect("key-press-event", self._key_pressed)


        self.seek_autohide = None
        self.timepos.connect("button-press-event", self._timepos_clicked)
        self.seekbar_seek_timeout = None
        self.seekbar_changed_handler = self.seekbar.connect(
            "value-changed", self._seekbar_changed)
    # _setup_connections()


    def _seek_available(self):
        return self.media_length and self.current_engine and \
                   self.current_engine.playing
    # _seek_available()


    def _seek_update_vals(self):
        if not self._seek_available():
            return

        self.seek_title.set_label("<b>%s</b>" % self._get_media_title())
        self.seekbar.set_position(int(self.current_engine.pos))
        self.seekbar.set_total_time(int(self.media_length))
        self.total_time.set_markup("<small>%s</small>" %
                                   self._time_to_str(self.media_length))
    # _seek_update_vals()


    def _seek_show(self):
        if not self._seek_available() or self.timepos_popup_visible:
            return

        self.timepos_popup_visible = True

        self._seek_update_vals()

        width, height = self.timepos_popup.get_size()
        pheight = 55

        self.timepos_popup.move(gtk.gdk.screen_width() - width,
                                gtk.gdk.screen_height() - height - pheight)

        self.timepos_popup.show()
        self.current_engine.handler_unblock(self.timepos_sync_pos_handler)

        if not self.seek_autohide:
            def f():
                self._seek_hide()
                self.seek_autohide = None
                return False
            self.seek_autohide = gobject.timeout_add(5000, f)
    # _seek_show()


    def _seek_hide(self):
        if not self.timepos_popup_visible:
            return

        self.timepos_popup_visible = False
        self.current_engine.handler_block(self.timepos_sync_pos_handler)
        self.timepos_popup.hide()
    # _seek_hide()


    def _timepos_clicked(self, wid, event):
        if not self._seek_available():
            return

        if not self.timepos_popup_visible:
            self._seek_show()
        else:
            self._seek_hide()
    # _timepos_clicked()


    def _do_seek(self):
        if self.current_engine and self.current_engine.playing:
            value = self.seekbar.get_value()
            self.current_engine.seek(value, PlayerEngine.SEEK_ABSOLUTE)
    # _do_seek()


    def _seekbar_changed(self, seekbar):
        if self.seekbar_seek_timeout:
            return

        def f():
            self._do_seek()
            self.seekbar_seek_timeout = None
            return False

        self.seekbar_seek_timeout = gobject.timeout_add(200, f)
    # _seekbar_changed()


    def _seekbar_sync_pos(self, player, pos):
        self.seekbar.set_position(int(pos))
        self.cur_time.set_markup("<small>%s</small>" % self._time_to_str(pos))
    # _seekbar_sync_pos()


    def _volume_changed(self, volumebar):
        value = int(volumebar.get_level())
        self.data["Player"]["volume"] = value
        self._save_settings()
        self.current_engine.set_volume(value)
    # _volume_changed()


    def _volume_mute_toggle(self, volumebar):
        state = volumebar.get_mute()
        self.data["Player"]["mute"] = state
        self._save_settings()
        self.current_engine.set_mute(state)
    # _volume_mute_toggle()


    def _window_state_changed(self, window, event):
        state = event.new_window_state & gtk.gdk.WINDOW_STATE_FULLSCREEN
        self.is_fullscreen = bool(state)
        if self.is_fullscreen:
            self.controls.hide()
            self.volumebar.hide()
            self.toolbar.hide()
        else:
            self.controls.show()
            self.volumebar.show()
            self.toolbar.show()

        if self.current_engine.playing:
            self.current_engine.set_fullscreen(self.is_fullscreen)

        return False
    # _window_state_changed()


    def _source_activated(self, wid, source):
        self.chooser_layout.hide()
        self.play_layout.show()

        idx = self.sources.index(source)
        self.source_selector.set_active(idx)

        self.current_source = source
    # _source_activated()


    def _source_selector_changed(self, wid):
        idx = wid.get_active()
        if idx < 0:
            return

        source = wid.get_model()[idx][1]
        self.current_source = source

        def f():
            self.choose_file()
            return False
        gobject.idle_add(f)
    # _source_selector_changed()


    def _key_pressed(self, window, event):
        log.debug("Key pressed %s, event=%s, keyval=%s" % \
                  (window, event, event.keyval))
        if event.keyval == gtk.keysyms.F6:
            if self.is_fullscreen:
                self.unfullscreen()
            else:
                self.fullscreen()
        elif event.keyval == gtk.keysyms.F8:
            level = self.volumebar.get_level()
            level = max(0, level - 10)
            self.volumebar.set_level(level)
        elif event.keyval == gtk.keysyms.F7:
            level = self.volumebar.get_level()
            level = min(100, level + 10)
            self.volumebar.set_level(level)

        return True # stop others handling it
    # _key_pressed()


    def _video_container_realize(self, wid):
        if not wid.window:
            return

        self.current_engine.xid = wid.window.xid
    # _video_container_realize()


    def _do_open(self, wid):
        self.choose_file()
    # _do_open()


    def _delayed_play(self, url):
        if self.current_source.open(url, self.data):
            self.last_played = url
            f = self.current_source.get_player_engine_input_handler()
            d = self.data
            eng = self.current_engine
            eng.play(f)
            eng.set_volume(d["Player"]["volume"])
            eng.set_mute(d["Player"]["mute"])
            eng.set_fullscreen(self.is_fullscreen)
        return False
    # _delayed_play()


    def _do_play(self, wid):
        if self.last_played:
            gobject.idle_add(self._delayed_play, self.last_played)
        else:
            self.choose_file()
    # _do_play()


    def _do_pause(self, wid):
        if self.current_engine:
            self.current_engine.pause()
    # _do_pause()


    def _do_stop(self, wid):
        if self.current_engine:
            self.current_engine.stop()
    # _do_stop()


    def quit(self, *ignored):
        if self.current_engine.playing:
            self.current_engine.stop()
        self._save_settings()
        gtk.main_quit()
    # quit()


    def _player_eos(self, player):
        self.current_source.close()
        self.media_length = None
    # _player_eos()


    def _player_error(self, player, msg):
        self.current_engine.stop()
        self.current_source.close()

        catota.ui.show_error(self, msg)
        self.infotext.set_label("<small>Stopped due player error.</small>")
        self.media_length = None
        self.timepos.set_text("00:00:00")
        self.timepos.set_fraction(0)
    # _player_error()


    @staticmethod
    def _time_to_str(time):
        time = int(time)
        seconds = time % 60
        t = time / 60
        minutes = t % 60
        hours = t / 60
        return "%02d:%02d:%02d" % (hours, minutes, seconds)
    # _time_to_str()


    def _player_pos(self, player, pos):
        elapsed = self._time_to_str(pos)
        self.timepos.set_text(elapsed)
        if self.media_length:
            self.timepos.set_fraction(pos / self.media_length)
    # _player_pos()


    def _get_media_title(self):
        playing = self.current_engine.playing
        if not playing:
            return ""

        if self.media_title:
            return self.media_title
        else:
            if playing.startswith("file://"):
                fname = playing[len("file://"):]
            else:
                fname = playing
            return os.path.basename(fname)
    # _get_media_title()


    def _player_state_changed(self, player, state):
        if state == PlayerEngine.STATE_NONE:
            msg = "<small>Idle.</small>"
            self.media_length = None
            self.timepos.set_text("00:00:00")
            self.timepos.set_fraction(0)
            self.timepos.hide()
        elif state == PlayerEngine.STATE_PLAYING:
            msg = "<small>Playing <b>%s</b>.</small>" % self._get_media_title()
            self._seek_update_vals()
            self.timepos.show()
        elif state == PlayerEngine.STATE_PAUSED:
            msg = "<small>Paused.</small>"

        self.infotext.set_markup(msg)
    # _player_state_changed()


    def _player_media_info(self, player, d):
        self.media_length = d.get("length", None)
        self.media_title = d.get("media_title", None)
        self._seek_update_vals()
    # _player_media_info()


    def choose_file(self):
        if not self.current_source:
            return

        url = self.current_source.get_url_from_chooser()
        if url:
            gobject.idle_add(self._delayed_play, url)
    # choose_file()


    def _do_preferences(self, wid):
        self.show_preferences()
    # _do_preferences()


    def show_preferences(self, focus_widget=None):
        if self.pref_dialog.run(focus_widget):
            self._save_settings()
    # show_preferences()
# PlayerUI


class PlayerApp(hildon.Program):
    def __init__(self, name=None):
        hildon.Program.__init__(self)
        if name:
            gtk.set_application_name(name)
    # __init__()
# PlayerApp



def load_plugins_sources(directory):
    PlayerUI.load_plugins_sources(directory)
# load_plugins_sources()



def load_plugins_engines(directory):
    PlayerUI.load_plugins_engines(directory)
# load_plugins_engines()
