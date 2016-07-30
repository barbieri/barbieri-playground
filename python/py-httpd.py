#!/usr/bin/python

from SocketServer import ThreadingMixIn
from SimpleHTTPServer import SimpleHTTPRequestHandler
from BaseHTTPServer import HTTPServer

run = True

class StoppableHTTPServer(ThreadingMixIn, HTTPServer):
    def get_request(self):
        try:
            return HTTPServer.get_request(self)
        except KeyboardInterrupt:
            global run
            run = False
            raise SystemExit("Stop!")

    def serve_forever(self):
        global run
        while run:
            self.handle_request()

httpd = StoppableHTTPServer(("", 8000), SimpleHTTPRequestHandler)
sa = httpd.socket.getsockname()
print "Serving HTTP on", sa[0], "port", sa[1], "..."
httpd.serve_forever()
