#!/usr/bin/env python

__author__ = "Gustavo Sverzut Barbieri"
__author_email__ = "barbieri@gmail.com"
__license__ = "GPL"
__version__ = "0.2"

import os
import threading
import SocketServer
import BaseHTTPServer
import socket
import urlparse
import cgi
import catota.utils
import logging as log

__all__ = ("Transcoder", "RequestHandler", "Server", "serve_forever",
           "load_plugins_transcoders")

class Transcoder(object):
    log = log.getLogger("catota.transcoder")
    priority = 0   # negative values have higher priorities
    name = None # to be used in requests

    def __init__(self, params):
        self.params = params
    # __init__()


    def params_first(self, key, default=None):
        if default is None:
            return self.params[key][0]
        else:
            try:
                return self.params[key][0]
            except:
                return default
    # params_first()


    def get_mimetype(self):
        mux = self.params_first("mux", "avi")

        if mux == "avi":
            return "video/x-msvideo"
        elif mux == "mpeg":
            return "video/mpeg"
        else:
            return "application/octet-stream"
    # get_mimetype()


    def start(self, outfile):
        return True
    # start()


    def stop(self):
        return True
    # stop()


    def __str__(self):
        return '%s("%s://%s", mux="%s", params=%s)' % \
               (self.__class__.__name__,
                self.params_first("type"),
                self.params_first("location"),
                self.params_first("mux", "avi"),
                self.params)
    # __str__()
# Transcoder



class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    log = log.getLogger("catota.request")
    def_transcoder = None
    transcoders = catota.utils.PluginSet(Transcoder)

    @classmethod
    def load_plugins_transcoders(cls, directory):
        cls.transcoders.load_from_directory(directory)

        if cls.def_transcoder is None and cls.transcoders:
            cls.def_transcoder = cls.transcoders[0].name
    # load_plugins_transcoders()


    def do_dispatch(self, body):
        self.url = self.path

        pieces = urlparse.urlparse(self.path)
        self.path = pieces[2]
        self.query = cgi.parse_qs(pieces[4])

        if self.path == "/":
            self.serve_main(body)
        elif self.path == "/shutdown.do":
            self.serve_shutdown(body)
        elif self.path == "/stop-transcoder.do":
            self.serve_stop_transcoder(body)
        elif self.path == "/status.do":
            self.serve_status(body)
        elif self.path == "/play.do":
            self.serve_play(body)
        elif self.path == "/stream.do":
            self.serve_stream(body)
        else:
            self.send_error(404, "File not found")
    # do_dispatch()


    def do_GET(self):
        self.do_dispatch(True)
    # do_GET()


    def do_HEAD(self):
        self.do_dispatch(False)
    # do_HEAD()


    def _nav_items(self):
        self.wfile.write("""\
   <li><a href="/play.do">Play</a></li>
   <li><a href="/status.do">Status</a></li>
   <li><a href="/stop-transcoder.do">Stop transcoders</a></li>
   <li><a href="/shutdown.do">Shutdown Server</a></li>
""")
    # _nav_items()


    def serve_main(self, body):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header('Connection', 'close')
        self.end_headers()
        if body:
            self.wfile.write("""\
<html>
   <head><title>Catota Server</title></head>
   <body>
<h1>Welcome to Catota Server</h1>
<ul>
""")
            self._nav_items()
            self.wfile.write("""\
</ul>
   </body>
</html>
""")
    # serve_main()


    def serve_play(self, body):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header('Connection', 'close')
        self.end_headers()
        if body:
            self.wfile.write("""\
<html>
   <head><title>Catota Server</title></head>
   <body>
   <h1>Play</h1>
   <form action="/stream.do" method="GET">
      <input type="text" name="type" value="file" />://<input type="text" name="location" value=""/>
      <input type="submit" />
   </form>
   <ul>
""")
            self._nav_items()
            self.wfile.write("""\
   </ul>
   </body>
</html>
""")
    # serve_play()


    def serve_shutdown(self, body):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header('Connection', 'close')
        self.end_headers()
        if body:
            self.wfile.write("""\
<html>
   <head><title>Catota Server Exited</title></head>
   <body>
      <h1>Catota is not running anymore</h1>
   </body>
</html>
""")
        self.server.server_close()
    # serve_shutdown()


    def serve_stop_all_transcoders(self, body):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header('Connection', 'close')
        self.end_headers()
        if body:
            self.server.stop_transcoders()
            self.wfile.write("""\
<html>
   <head><title>Catota Server Stopped Transcoders</title></head>
   <body>
      <h1>Catota stopped running transcoders</h1>
      <ul>
""")
            self._nav_items()
            self.wfile.write("""\
      </ul>
   </body>
</html>
    """)
    # serve_stop_all_transcoders()


    def serve_stop_selected_transcoders(self, body, requests):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header('Connection', 'close')
        self.end_headers()
        if body:
            self.wfile.write("""\
<html>
   <head><title>Catota Server Stopped Transcoders</title></head>
   <body>
      <h1>Catota stopped running transcoders:</h1>
      <ul>
    """)
            transcoders = self.server.get_transcoders()

            for req in requests:
                try:
                    host, port = req.split(":")
                except IndexError:
                    continue

                port = int(port)
                addr = (host, port)

                for t, r in transcoders:
                    if r.client_address == addr:
                        self.wfile.write("""\
         <li>%s: %s:%s</li>
""" % (t, addr[0], addr[1]))
                        t.stop()
                        break
            self.wfile.write("""\
      </ul>
      <ul>
""")
            self._nav_items()
            self.wfile.write("""\
      </ul>
   </body>
</html>
""")
    # serve_stop_selected_transcoders()


    def serve_stop_transcoder(self, body):
        req = self.query.get("request", None)
        if req and "all" in req:
            self.serve_stop_all_transcoders(body)
        elif req:
            self.serve_stop_selected_transcoders(body, req)
        else:
            self.serve_status(body)
    # serve_stop_transcoder()


    def serve_status(self, body):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header('Connection', 'close')
        self.end_headers()
        if body:
            self.wfile.write("""\
<html>
   <head><title>Catota Server Status</title></head>
   <body>
      <h1>Catota Status</h1>
""")
            tl = self.server.get_transcoders()
            if not tl:
                self.wfile.write("<p>No running transcoder.</p>\n")
            else:
                self.wfile.write("<p>Running transcoders:</p>\n")
                self.wfile.write("""\
      <ul>
         <li><a href="/stop-transcoder.do?request=all">[STOP ALL]</a></li>
""")
                for transcoder, request in tl:
                    self.wfile.write("""\
      <li>%s: %s:%s <a href="/stop-transcoder.do?request=%s:%s">[STOP]</a></li>
""" % (transcoder, request.client_address[0], request.client_address[1],
       request.client_address[0], request.client_address[1]))

                self.wfile.write("""\
      </ul>
      <ul>
""")
            self._nav_items()
            self.wfile.write("""\
      </ul>
   </body>
</html>
""")
    # serve_status()


    def _get_transcoder(self):
        request_transcoders = self.query.get("transcoder", ["mencoder"])

        for t in request_transcoders:
            transcoder = self.transcoders.get(t)
            if transcoder:
                return transcoder

        if not transcoder:
            return self.transcoders[self.def_transcoder]
    # _get_transcoder()


    def serve_stream(self, body):
        transcoder = self._get_transcoder()
        try:
            obj = transcoder(self.query)
        except Exception, e:
            self.send_error(500, str(e))
            return

        self.send_response(200)
        self.send_header("Content-Type", obj.get_mimetype())
        self.send_header('Connection', 'close')
        self.end_headers()

        if body:
            self.server.add_transcoders(self, obj)
            obj.start(self.wfile)
            self.server.del_transcoders(self, obj)
    # serve_stream()


    def log_request(self, code='-', size='-'):
        self.log.info('"%s" %s %s', self.requestline, str(code), str(size))
    # log_request()


    def log_error(self, format, *args):
        self.log.error("%s: %s" % (self.address_string(), format % args))
    # log_error()


    def log_message(self, format, *args):
        self.log.info("%s: %s" % (self.address_string(), format % args))
    # log_message()
# RequestHandler



class Server(SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer):
    log = log.getLogger("catota.server")
    run = True
    _transcoders = {}
    _lock = threading.RLock()

    def serve_forever(self):
        self.log.info("Catota serving HTTP on %s:%s" %
                      self.socket.getsockname())
        try:
            while self.run:
                self.handle_request()
        except KeyboardInterrupt, e:
            pass

        self.log.debug("Stopping all remaining transcoders...")
        self.stop_transcoders()
        self.log.debug("Transcoders stopped!")
    # serve_forever()


    def get_request(self):
        skt = self.socket
        old = skt.gettimeout()
        skt.settimeout(0.5)
        while self.run:
            try:
                r = skt.accept()
                skt.settimeout(old)
                return r
            except socket.timeout, e:
                pass
        raise socket.error("Not running")
    # get_request()


    def server_close(self):
        self.run = False
        self.stop_transcoders()

        BaseHTTPServer.HTTPServer.server_close(self)
    # server_close()


    def stop_transcoders(self):
        self._lock.acquire()
        for transcoder, request in self._transcoders.iteritems():
            self.log.info("Stop transcoder: %s, client=%s" %
                          (transcoder, request.client_address))
            transcoder.stop()
        self._lock.release()
    # stop_transcoders()


    def get_transcoders(self):
        self._lock.acquire()
        try:
            return self._transcoders.items()
        finally:
            self._lock.release()
    # get_transcoders()


    def add_transcoders(self, request, transcoder):
        self._lock.acquire()
        try:
            self._transcoders[transcoder] = request
        finally:
            self._lock.release()
    # add_transcoders()


    def del_transcoders(self, request, transcoder):
        self._lock.acquire()
        try:
            del self._transcoders[transcoder]
        finally:
            self._lock.release()
    # del_transcoders()
# Server



def serve_forever(host="0.0.0.0", port=40000):
    addr = (host, port)

    RequestHandler.protocol_version = "HTTP/1.0"
    httpd = Server(addr, RequestHandler)
    httpd.serve_forever()
# serve_forever()


def load_plugins_transcoders(directory):
    RequestHandler.load_plugins_transcoders(directory)
# load_plugins_transcoders()
