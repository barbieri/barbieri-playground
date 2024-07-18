#!/usr/bin/python3

from hashlib import md5, file_digest
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler
from http.server import ThreadingHTTPServer
from io import BytesIO
from typing import BinaryIO


class SimpleETagHTTPRequestHandler(SimpleHTTPRequestHandler):
    # NOTE: overriding send_header() is an ugly hack!
    # but SimpleHTTPRequestHandler wasn't meant to be extended
    # and there is no other hook we could use to populate extra
    # headers before the end of headers
    def send_header(self, keyword: str, value: str) -> None:
        super().send_header(keyword, value)
        if keyword == "Last-Modified":
            etag = self._gen_etag()
            super().send_header("ETag", etag)

    def send_head(self) -> BytesIO | BinaryIO | None:
        if condition := self.headers.get("If-None-Match"):
            etag = self._gen_etag()
            if etag == condition:  # just simple conditions are handled
                self.send_response(HTTPStatus.NOT_MODIFIED)
                self.end_headers()

        return super().send_head()

    _etag = None

    def _gen_etag(self) -> str:
        if self._etag is None:
            path = self.translate_path(self.path)
            try:
                with open(path, "rb") as f:
                    h = md5(usedforsecurity=False)
                    etag_raw = file_digest(f, lambda: h).hexdigest()
                    self._etag = f'"{etag_raw}"'  # must have double quotes
            except OSError:
                return None

        return self._etag


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


httpd = StoppableHTTPServer(("", 8000), SimpleETagHTTPRequestHandler)
sa = httpd.socket.getsockname()
print("Serving HTTP on", sa[0], "port", sa[1], "...")
httpd.serve_forever()
