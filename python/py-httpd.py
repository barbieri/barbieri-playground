#!/usr/bin/python3

from http.server import ThreadingHTTPServer
from http.server import SimpleHTTPRequestHandler

class StoppableHTTPServer(ThreadingHTTPServer):
    run = True

    def handle_request(self):
        try:
            return super().handle_request()
        except KeyboardInterrupt:
            self.run = False
            raise SystemExit("Stop!")

    def serve_forever(self):
        while self.run:
            self.handle_request()


httpd = StoppableHTTPServer(("", 8000), SimpleHTTPRequestHandler)
sa = httpd.socket.getsockname()
print("Serving HTTP on", sa[0], "port", sa[1], "...")
httpd.serve_forever()
