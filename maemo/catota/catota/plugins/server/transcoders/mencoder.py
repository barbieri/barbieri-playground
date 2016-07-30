import catota.utils
import catota.server
import os
import signal
import subprocess

__all__ = ("TranscoderMencoder",)

class TranscoderMencoder(catota.server.Transcoder):
    mencoder_path = catota.utils.which("mencoder")
    def_mencoder_outfile = os.path.join(os.path.sep, "tmp",
                                        "mencoder-fifo-%(uid)s-%(pid)s")
    name = "mencoder"
    priority = -1

    def __init__(self, params):
        catota.server.Transcoder.__init__(self, params)
        self.proc = None
        self.args = None

        vars = {"uid": os.getuid(), "pid": os.getpid()}
        mencoder_outfile_base = self.def_mencoder_outfile % vars
        mencoder_outfile = mencoder_outfile_base
        i = 0
        while os.path.exists(mencoder_outfile):
            i += 1
            mencoder_outfile = mencoder_outfile_base + ".%s" % i

        self.mencoder_outfile = mencoder_outfile
        os.mkfifo(self.mencoder_outfile)

        args = [self.mencoder_path, "-really-quiet",
                "-o", self.mencoder_outfile]

        params_first = self.params_first

        type = params_first("type")
        location = params_first("location")
        args.append("%s://%s" % (type, location))

        mux = params_first("mux", "avi")
        args.extend(["-of", mux])

        acodec = params_first("acodec", "mp3")
        abitrate = params_first("abitrate", "128")
        if acodec == "mp3lame":
            args.extend(["-oac", "mp3lame", "-lameopts",
                         "cbr:br=%s" % abitrate])
        else:
            args.extend(["-oac", "lavc", "-lavcopts",
                         "acodec=%s:abitrate=%s" % (acodec, abitrate)])

        vcodec = params_first("vcodec", "mpeg4")
        vbitrate = params_first("vbitrate", "400")
        args.extend(["-ovc", "lavc", "-lavcopts",
                     "vcodec=%s:vbitrate=%s" % (vcodec, vbitrate)])

        fps = params_first("fps", "24")
        args.extend(["-ofps", fps])

        width = params_first("width", "320")
        height = params_first("height", "240")
        args.extend(["-vf", "scale=%s:%s" % (width, height)])

        self.args = args
    # __init__()


    def _unlink_fifo(self):
        try:
            os.unlink(self.mencoder_outfile)
        except Exception, e:
            pass
    # _unlink_fifo()


    def start(self, outfd):
        cmd = " ".join(self.args)
        self.log.info("Mencoder: %s" % cmd)

        try:
            self.proc = subprocess.Popen(self.args, close_fds=True)
        except Exception, e:
            self.log.error("Error executing mencoder: %s" % cmd)
            return False

        try:
            fifo_read = open(self.mencoder_outfile)
        except Exception, e:
            self.log.error("Error opening fifo: %s" % cmd)
            return False

        try:
            while self.proc and self.proc.poll() == None:
                d = fifo_read.read(1024)
                outfd.write(d)
        except Exception, e:
            self.log.error("Problems handling data: %s" % e)
            self._unlink_fifo()
            return False

        self._unlink_fifo()
        return True
    # start()


    def stop(self):
        if self.proc:
            try:
                os.kill(self.proc.pid, signal.SIGTERM)
            except OSError, e:
                pass

            try:
                self.proc.wait()
            except Exception, e:
                pass

            self.proc = None

        self._unlink_fifo()
    # stop()
# TranscoderMencoder
