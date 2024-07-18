#!/usr/bin/python3

import argparse
import os
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
    directory = None

    def handle_request(self):
        try:
            return super().handle_request()
        except KeyboardInterrupt:
            self.run = False
            raise SystemExit("Stop!")

    def serve_forever(self):
        while self.run:
            self.handle_request()

    def finish_request(self, request, client_address):
        self.RequestHandlerClass(
            request, client_address, self, directory=self.directory,
        )


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description=(
            "Serve local files over HTTP, "
            "supports If-Modified-Since and If-None-Match conditions"
        ),
    )
    ap.add_argument(
        "--address",
        help="Internet address to serve on, defaults to all",
        default="",
    )
    ap.add_argument(
        "--port",
        help="Port to listen on, default=%(default)s",
        type=int,
        default=8000,
    )
    ap.add_argument(
        "--directory",
        help="serve this directory (default: current directory)",
        default=os.getcwd(),
    )

    args = ap.parse_args()

    httpd = StoppableHTTPServer(
        (args.address, args.port),
        SimpleETagHTTPRequestHandler,
    )
    httpd.directory = args.directory
    sa = httpd.socket.getsockname()
    print(
        f"Serving directory {httpd.directory} HTTP on {sa[0]} port {sa[1]}..."
    )
    httpd.serve_forever()
