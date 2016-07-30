#!/usr/bin/env python

import os
import subprocess
import gtk
import StringIO
import shlex
import select
import catota.utils
import gobject
import catota.client
from catota.client import PlayerEngine, PreferencesProvider


class PlayerEngineMPlayer(PlayerEngine, PreferencesProvider):
    priority = 0
    name = "mplayer"

    bufsize = 0
    preferences_section = "MPlayer"
    def_preferences = {
        "path": "",
        "params": "-hardframedrop",
        "audio_output": "esd",
        "audio_codecs": "ffmpeg",
        }

    def __init__(self, parent_win, xid=0):
        PreferencesProvider.__init__(self)
        PlayerEngine.__init__(self, parent_win, xid)
        self.proc = None
        self.m_items = {}
        self.out_watcher = None
        self.state_timeout = None
        self._setup_gui()
        self._setup_connections()
    # __init__()


    def _setup_gui(self):
        m_items = []
        for name in ("Play", "Pause", "Stop"):
            action = self.parent_win.actions[name]
            action.set_sensitive(False)

            m = action.create_menu_item()
            m.show()

            self.m_items[name] = m

            m_items.append(m)


        self.menu_items = m_items
    # _setup_gui()


    def _setup_connections(self):
        actions = self.parent_win.actions

        actions["Stop"].connect("activate", lambda *a: self.stop())
    # _setup_connections()


    def _choose_mplayer_path(self, btn):
        d = gtk.FileChooserDialog("Select MPlayer binary",
                                  buttons=DEF_DIALOG_BUTTONS)
        d.set_local_only(True)
        d.set_select_multiple(False)
        d.set_current_folder(catota.client.DEF_BIN_PATH)

        p = self.player_path.get_text()
        if p:
            d.set_filename(p)

        d.show()
        r = d.run()
        d.hide()
        if r == gtk.RESPONSE_ACCEPT:
            p = d.get_filename()
            if p:
                self.player_path.set_text(p)
    # _choose_mplayer_path()


    def setup_gui_preferences(self):
        self.player_path = gtk.Entry()
        self.player_params = gtk.Entry()

        self.player_ao_model = gtk.ListStore(str)
        self.player_ao = gtk.ComboBox(self.player_ao_model)
        cell = gtk.CellRendererText()
        self.player_ao.pack_start(cell, True)
        self.player_ao.add_attribute(cell, "text", 0)

        for t in ("esd", "gst"):
            self.player_ao_model.append((t,))


        self.player_acodec_model = gtk.ListStore(str)
        self.player_acodec = gtk.ComboBox(self.player_acodec_model)
        cell = gtk.CellRendererText()
        self.player_acodec.pack_start(cell, True)
        self.player_acodec.add_attribute(cell, "text", 0)

        for t in ("ffmpeg", "dspmp3"):
            self.player_acodec_model.append((t,))



        hbox = gtk.HBox(homogeneous=False, spacing=2)
        btn = gtk.Button(stock=gtk.STOCK_OPEN)
        hbox.pack_start(self.player_path, fill=True, expand=True)
        hbox.pack_start(btn, fill=True, expand=False)
        btn.connect("clicked", self._choose_mplayer_path)

        hbox.show_all()

        wids = ("MPlayer",
                ("Path:", hbox),
                ("Parameters:", self.player_params),
                ("Audio Output:", self.player_ao),
                ("Audio Codec:", self.player_acodec),
                )

        self.gui_preferences = wids
    # setup_gui_preferences()


    def preferences_load(self, d):
        PreferencesProvider.preferences_load(self, d)

        if not self.preferences["path"]:
            self.preferences["path"] = catota.utils.which("mplayer")

        self.player_path.set_text(self.preferences["path"])
        self.player_params.set_text(self.preferences["params"])

        def set_combo_item(wid, item):
            for i, row in enumerate(wid.get_model()):
                if row[0] == item:
                    wid.set_active(i)
                    break

        set_combo_item(self.player_ao, self.preferences["audio_output"])
        set_combo_item(self.player_acodec, self.preferences["audio_codecs"])
    # preferences_load()


    def preferences_save(self, d):
        self.preferences["path"] = self.player_path.get_text()
        self.preferences["params"] = self.player_params.get_text()

        def get_combo_item(wid):
            i = wid.get_active()
            if i < 0:
                return ""
            else:
                return wid.get_model()[i][0]

        self.preferences["audio_output"] = get_combo_item(self.player_ao)
        self.preferences["audio_codecs"] = get_combo_item(self.player_acodec)
        PreferencesProvider.preferences_save(self, d)
    # preferences_save()


    def _cmd(self, msg, pausing_keep=True):
        if not self.proc:
            self.log.error("Not playing, command ignored: %r" % msg)
            return

        if not pausing_keep or not self.paused:
            prefix = ""
        else:
            prefix = "pausing_keep "

        cmd = "%s%s\n" % (prefix, msg)
        try:
            self.log.debug("MPlayer command: %r" % cmd)
            self.proc.stdin.write(cmd)
            self.proc.stdin.flush()
        except Exception, e:
            self.log.error("Error writing MPlayer command %r: %s" %
                           (cmd, e))
            proc = self.proc
            self.proc = None
            try:
                proc.stdin.close()
            except Exception, e:
                pass
            try:
                os.kill(proc.pid, 15)
            except Exception, e:
                pass

            try:
                proc.wait()
            except Exception, e:
                pass

            self.emit("error", str(e))
    # _cmd()


    def _readline(self, timeout=0):
        if not self.proc:
            return None

        p = select.poll()
        flag_err = select.POLLERR | select.POLLHUP
        rfile = self.proc.stdout
        p.register(rfile, flag_err | select.POLLIN | select.POLLPRI)

        buf = StringIO.StringIO()
        while self.playing:
            lst = p.poll(timeout)
            if not lst:
                line = buf.getvalue()
                buf.close()
                self.log.debug("Time out!: %r" % line)
                return line

            for fd, flags in lst:
                if flags & flag_err:
                    self.log.debug("Error reading MPlayer: %s, flags=%x" %
                                   (fd, flags))
                    self.emit("error", "Problems reading MPlayer output")
                    return None

                c = rfile.read(1)
                buf.write(c)
                if c == "\n" or c == "\r":
                    line = buf.getvalue()
                    buf.close()
                    return line
    # _readline()


    def _read_ans(self, prefix="", timeout=0, tries=1):
        while tries and self.playing:
            tries -= 1
            line = self._readline(timeout)

            if line is None:
                return None


            if line == "":
                continue

            last = line[-1]
            if last == "\n" or last == "\r":
                line = line[: -1]

            if not prefix:
                return line
            elif line.startswith(prefix):
                return line[len(prefix):]
            else:
                self.log.debug("Ignored MPlayer output: %r" % line)
    # _read_ans()


    def _register_io_handlers(self):
        flags_err = gobject.IO_ERR | gobject.IO_HUP
        def handler(fd, flags):
            if flags & flags_err:
                return False
            else:
                while self.playing:
                    line = self._readline()

                    if not line:
                        return True
                    elif line[:2] == "A:" and line[-1] =="\r":
                        pieces = line.split()
                        pos = float(pieces[1])
                        self.emit("pos", pos)
                        return True
                    elif line == "Exiting... (Quit)\n":
                        self.proc.wait()
                        self.proc = None
                        self.emit("eos")
                        self.emit("state-changed", PlayerEngine.STATE_NONE)
                        return False
                    elif line == "Starting playback...\n":
                        # make buffer empty
                        while line:
                            line = self._readline(100)
                            if line and line[:2] == "A:" and line[-1] == "\r":
                                break

                        self.set_volume(self.volume)
                        self.set_mute(self.mute)
                        self.set_fullscreen(self.fullscreen)
                        self._query_media_info()
                        self._register_state_timeout()
                        self.emit("state-changed", PlayerEngine.STATE_PLAYING)
                        return True
                    else:
                        self.log.debug("Ignored MPlayer output: %r" % line)

                return True

        flags = gobject.IO_IN | gobject.IO_PRI | flags_err
        self.out_watcher = gobject.io_add_watch(self.proc.stdout,
                                                flags, handler)
    # _register_io_handlers()


    def _register_state_timeout(self):
        self.length_tries = 20
        def handler():
            if not self.proc or not self.playing:
                return False
            else:
                if self.length is None and self.length_tries:
                    self.length_tries -= 1

                    self._cmd("get_time_length")
                    v = self._read_ans("ANS_LENGTH=", timeout=1000)
                    if v:
                        self.length = float(v)
                        self.info["length"] = self.length
                        self.emit("media-info", self.info)


                self._cmd("get_time_pos")
                v = self._read_ans("ANS_TIME_POSITION=", timeout=1000)
                if not v:
                    return True

                self.pos = float(v)
                self.emit("pos", self.pos)

                return True

        self.state_timeout = gobject.timeout_add(500, handler)
    # _register_state_timeout()


    def _unregister_state_timeout(self):
        if self.state_timeout is not None:
            gobject.source_remove(self.state_timeout)
            self.state_timeout = None
    # _unregister_state_timeout()


    def _query_media_info(self):
        d = self.get_media_info()
        self.emit("media-info", d)
    # _query_media_info()


    def _setup_playing_ui(self):
        self.parent_win.actions["Play"].set_sensitive(False)
        self.parent_win.actions["Pause"].set_sensitive(True)
        self.parent_win.actions["Stop"].set_sensitive(True)
    # _setup_playing_ui()


    def _setup_paused_ui(self):
        pass
    # _setup_paused_ui()


    def _setup_stopped_ui(self):
        self.parent_win.actions["Play"].set_sensitive(True)
        self.parent_win.actions["Pause"].set_sensitive(False)
        self.parent_win.actions["Stop"].set_sensitive(False)
    # _setup_stopped_ui()


    def play(self, filename):
        if self.proc:
            self._cmd("quit")
            self.proc.wait()
            self.proc = None
        self.playing = None

        cmd = [self.preferences["path"], "-quiet", "-slave",
               "-noconsolecontrols", "-nojoystick", "-nolirc",
               "-nomouseinput",
               "-ao", self.preferences["audio_output"],
               "-afm", self.preferences["audio_codecs"],
               "-wid", "0x%x" % self.xid]
        if self.preferences["params"]:
            cmd.extend(shlex.split(self.preferences["params"]))

        cmd.append(filename)
        try:
            self.log.debug("Execute MPlayer %s" % (cmd,))
            self.proc = subprocess.Popen(cmd,
                                         stdin=subprocess.PIPE,
                                         stdout=subprocess.PIPE,
                                         bufsize=self.bufsize,
                                         close_fds=True)

            self._register_io_handlers()
            self._setup_playing_ui()
            self.playing = filename
        except Exception, e:
            self.log.error("Failed to execute \"%s\": %s" % (cmd, e))
            if self.proc:
                try:
                    os.kill(self.proc.pid, 15)
                except Exception, e:
                    log.error("Failed to kill MPlayer %s" % e)

                self.proc = None
            self.emit("error", str(e))
            return False
    # play()


    def pause(self):
        self._cmd("pause")
        if not self.paused:
            self._unregister_state_timeout()
        else:
            self._register_state_timeout()

        self._setup_paused_ui()
        return PlayerEngine.pause(self)
    # paused()


    def stop(self):
        if not self.playing:
            return
        self.playing = None

        self._unregister_state_timeout()
        if self.proc:
            self._cmd("quit")
            if self.proc:
                self.proc.wait()
                self.proc = None
        self._setup_stopped_ui()

        return PlayerEngine.stop(self)
    # stop()


    def seek(self, pos, type):
        self._cmd("seek %s %s" % (pos, type))
        return PlayerEngine.seek(self, pos, type)
    # seek()


    def set_volume(self, value):
        self._cmd("volume %d 1" % value)
        return PlayerEngine.set_volume(self, value)
    # set_volume()


    def set_mute(self, status):
        #self._cmd("mute %d" % status)
        if status:
            self._cmd("volume 0 1")
        else:
            self._cmd("volume %d 1" % self.volume)
        return PlayerEngine.set_mute(self, status)
    # set_mute()


    def set_fullscreen(self, status):
        self._cmd("vo_fullscreen %d" % status)
        return PlayerEngine.set_fullscreen(self, status)
    # set_fullscreen()


    def show_osd_message(self, msg, duration):
        self._cmd("osd_show_text \"%s\" %s" % (msg, duration))
        return PlayerEngine.show_osd_message(self, msg, duration)
    # show_osd_message()


    def get_media_info(self):
        def s(line):
            if line:
                return line

        def f(line):
            if line:
                return float(line)

        spec = (("audio_bitrate", "get_audio_bitrate", "ANS_AUDIO_BITRATE=", s),
                ("audio_codec", "get_audio_codec", "ANS_AUDIO_CODEC=", s),
                ("audio_samples", "get_audio_samples", "ANS_AUDIO_SAMPLES=", s),
                ("video_bitrate", "get_video_bitrate", "ANS_VIDEO_BITRATE=", s),
                ("video_res", "get_video_resolution", "ANS_VIDEO_RESOLUTION=", s),
                ("video_codec", "get_video_codec", "ANS_VIDEO_CODEC=", s),
                ("album", "get_meta_album", "ANS_META_ALBUM=", s),
                ("artist", "get_meta_artist", "ANS_META_ARTIST=", s),
                ("genre", "get_meta_genre", "ANS_META_GENRE=", s),
                ("comment", "get_meta_comment", "ANS_META_COMMENT=", s),
                ("title", "get_meta_title", "ANS_META_TITLE=", s),
                ("track", "get_meta_track", "ANS_META_TRACK=", s),
                ("year", "get_meta_year", "ANS_META_YEAR=", s),
                ("length", "get_time_length", "ANS_LENGTH=", f),
                )
        info = {}

        for key, cmd, ans_prefix, conv_func in spec:
            self._cmd(cmd)
            v = self._read_ans(ans_prefix, timeout=1000, tries=100)
            if not v:
                continue

            v = shlex.split(v)
            if len(v) == 1:
                v = v[0]
            info[key] = conv_func(v)

        self.info = info
        return info
    # get_media_info()
# PlayerEngineMPlayer
