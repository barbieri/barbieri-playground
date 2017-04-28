#!/usr/bin/python3

import logging
import socket
import socketserver
import threading


log = logging.getLogger(__name__)


class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
    chunk_size = 16384

    def handle(self):
        self.thread = threading.current_thread()
        self.client_address_str =  "%s:%s" % self.client_address
        name = "C_{}_{}_{}".format(
            self.client_address_str,
            self.server.server_address_str,
            self.server.remote_address_str)
        self.thread.name = name

        log.info("Connect thread %s gateway %s: %s -> %s...",
                 self.thread.name,
                 self.client_address_str,
                 self.server.server_address_str,
                 self.server.remote_address_str)

        self.gw.connect(self.server.remote_address)

        log.info("Connected thread %s gateway %s: %s -> %s!",
                 self.thread.name,
                 self.client_address_str,
                 self.server.server_address_str,
                 self.server.remote_address_str)

        self.gw_thread = threading.Thread(target=self._gw_handle,
                                          name=name + "_GW")
        self.gw_thread.daemon = self.thread.daemon
        self.gw_thread.start()

        self.cn_thread = threading.Thread(target=self._cn_handle,
                                          name=name + "_CN")
        self.cn_thread.daemon = self.thread.daemon
        self.cn_thread.start()

        log.debug("Wait gateway thread=%s %s: %s -> %s!",
                  self.gw_thread.name,
                  self.client_address_str,
                  self.server.server_address_str,
                  self.server.remote_address_str)
        self.gw_thread.join()

        log.debug("Wait client thread=%s %s: %s -> %s!",
                  self.cn_thread.name,
                  self.client_address_str,
                  self.server.server_address_str,
                  self.server.remote_address_str)
        self.cn_thread.join()

        log.info("Finished thread %s gateway %s: %s -> %s!",
                 self.thread.name,
                 self.client_address_str,
                 self.server.server_address_str,
                 self.server.remote_address_str)

    def _shutdown(self):
        self.running = False
        try:
            self.request.shutdown(socket.SHUT_RDWR)
        except OSError as e:
            log.debug("Failed to shutdown client %s: %s",
                      self.client_address_str, e)
        try:
            self.gw.shutdown(socket.SHUT_RDWR)
        except OSError as e:
            log.debug("Failed to shutdown gateway %s: %s",
                      self.client_address_str, e)

    def _gw_handle(self):
        while self.running:
            data = self.gw.recv(self.chunk_size)
            if len(data) == 0:
                log.debug("Gateway %s EOF", self.gw_thread.name)
                self._shutdown()
                return
            log.debug("Gateway %s sent %s bytes",
                      self.gw_thread.name, len(data))
            if self.running:
                self.request.sendall(data)

    def _cn_handle(self):
        while self.running:
            data = self.request.recv(self.chunk_size)
            if len(data) == 0:
                log.debug("Client %s EOF", self.cn_thread.name)
                self._shutdown()
                return
            log.debug("Client %s sent %s bytes",
                      self.cn_thread.name, len(data))
            if self.running:
                self.gw.sendall(data)

    def setup(self):
        super(ThreadedTCPRequestHandler, self).setup()
        self.gw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.running = True

    def finish(self):
        super(ThreadedTCPRequestHandler, self).finish()
        self.running = False
        if self.gw_thread.is_alive():
            self.gw_thread.join()
        if self.cn_thread.is_alive():
            self.cn_thread.join()
        self.request.close()
        self.gw.close()
        log.info("Cleanup thread %s gateway %s: %s -> %s!",
                 self.thread.name,
                 self.client_address_str,
                 self.server.server_address_str,
                 self.server.remote_address_str)


class ThreadedTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, local_address, remote_address):
        self.local_address = local_address
        self.remote_address = remote_address
        self.thread = None
        super(ThreadedTCPServer, self).__init__(
            local_address, ThreadedTCPRequestHandler)
        self.local_address_str = "%s:%s" % self.local_address
        self.remote_address_str =  "%s:%s" % self.remote_address
        self.server_address_str =  "%s:%s" % self.server_address

    def serve_forever(self, *args):
        thread = threading.current_thread()
        assert self.thread == thread
        log.info("start %s -> %s [Thread: %s]",
                 self.server_address_str,
                 self.remote_address_str,
                 thread.name)
        super(ThreadedTCPServer, self).serve_forever(*args)
        log.info("end %s -> %s [Thread: %s]",
                 self.server_address_str,
                 self.remote_address_str,
                 thread.name)

    def start_thread(self):
        assert self.thread is None
        name = "SRV_{}_{}".format(
            self.server_address_str,
            self.remote_address_str)
        self.thread = threading.Thread(target=self.serve_forever,
                                       name=name)
        self.thread.daemon = self.daemon_threads
        self.thread.start()
        return self.thread


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="socket gateway",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
This server will listen for connections on a given local port and
then connect to a remote server, linking both sockets -- all that
that is received is sent to the other socket.

Mapping is one of:

    127.0.0.1:1234:server.com:80
    1234:server.com:80
    server.com:80

The first will listen to localhost at port 1234 and be a gateway to
server.com port 80.

The second will listen on any address at port 1234 and be a gateway
to server.com port 80.

The last will listen on any address at a random port and be a gateway
to server.com port 80. The assigned port is printed to standard
output.
""")
    parser.add_argument("-v", "--verbose", action="count", default=0,
                        help="increase verbosity")
    parser.add_argument("map", nargs="+",
                        help=("mapping of "
                              "[[localip:]localport:]"
                              "remoteip:remoteport. "
                              "If localip is omitted, 0.0.0.0 "
                              "is used. If localport is omitted, 0 "
                              "is used (random port is assigned)."))
    args = parser.parse_args()

    loglevel = logging.WARNING - args.verbose * 10
    logging.basicConfig(level=loglevel, format="%(levelname)s: %(message)s")

    threads = []

    for m in args.map:
        mapping = m.split(':')
        if len(mapping) > 4 or len(mapping) < 2:
            raise SystemExit("ERROR: invalid mapping format: {}"
                             .format(m))
        localip = "0.0.0.0"
        localport = 0
        if len(mapping) > 3:
            localip = mapping[-4]
        if len(mapping) > 2:
            localport = int(mapping[-3])
        remoteip = mapping[-2]
        remoteport = int(mapping[-1])

        server = ThreadedTCPServer((localip, localport),
                                   (remoteip, remoteport))
        ip, port = server.server_address
        thread = server.start_thread()
        threads.append(thread)

        print("{}:{} -> {}:{}  [Thread: {}]".
              format(ip, port, remoteip, remoteport, thread.name))

    try:
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        pass
