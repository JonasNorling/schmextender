#!/usr/bin/python3
#
# This implements the PPP forwarding part of the SonicWALL NetExtender
# (Mobile Connect) protocol.
#
# This script establishes a TLS connection and shovels data between the
# server and stdio. Use with pppd pty <script>
#

import argparse
import logging
import socket
import ssl
import fcntl
import os
import selectors
import struct
import sys

class Tunnel(object):
    def __init__(self, hostname, port):
        self.log = logging.getLogger("schmextender")
        self.more_remote = 0
        self.hostname = hostname
        self.port = port

    def gotLocalData(self, data):
        # Prepend the length field and send to the server
        self.log.debug("Local: %d B" % len(data))
        lenstr = struct.pack("!I", len(data))
        sendlen = self.conn.send(lenstr + data)
        if sendlen != len(data) + 4:
            self.log.error("Sent too little to server")

    def gotRemoteData(self, data):
        if self.more_remote > 0:
            sys.stdout.buffer.write(data[:self.more_remote])
            self.more_remote -= len(data[:self.more_remote])
        while len(data) > 0:
            lenfield = struct.unpack("!I", data[0:4])[0]
            self.log.debug("Remote %d B" % lenfield)
            data = data[4:]
            sendlen = sys.stdout.buffer.write(data[:lenfield])
            if sendlen != len(data[:lenfield]):
                self.log.error("Sent too little on stdout")
            self.more_remote = lenfield - len(data)
            data = data[lenfield:]
        if self.more_remote > 0:
            self.log.debug("Waiting for %d B" % self.more_remote)

    def connect(self, auth, noverify=False):
        context = ssl.create_default_context()
        if noverify:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
    
        self.conn = context.wrap_socket(socket.socket(socket.AF_INET),
                                        server_hostname=self.hostname)
        self.conn.connect((self.hostname, self.port))
        self.log.info("Connected to %s:%d" % (self.hostname, self.port))

        connectstr = "CONNECT localhost:0 HTTP/1.0\r\nX-SSLVPN-PROTOCOL: 2.0\r\nX-SSLVPN-SERVICE: NETEXTENDER\r\nProxy-Authorization:%s\r\nX-NX-Client-Platform: Linux\r\nConnection-Medium: MacOS\r\nUser-Agent: Dell SonicWALL NetExtender for Linux 8.1.787\r\nFrame-Encode: off\r\nX-NE-PROTOCOL: 2.0\r\n\r\n" % auth
        self.conn.write(bytes(connectstr, "ascii"))
        self.log.debug("Wrote: %s", connectstr)

    def run(self):
        # Set the socket and stdio non-blocking so we can react to data
        # on either one of them
        self.conn.setblocking(False)
        fd = sys.stdin.fileno()
        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

        # Let's shovel some data!
        sel = selectors.DefaultSelector()
        sel.register(self.conn, selectors.EVENT_READ)
        sel.register(sys.stdin, selectors.EVENT_READ)

        while True:
            sel.select()

            local = sys.stdin.buffer.read(1024)
            while local is not None and len(local) > 0:
                self.gotLocalData(local)
                local = sys.stdin.buffer.read(1024)

            try:
                # This should be a no-op in most cases
                sys.stdout.flush()
                remote = self.conn.recv(4096)
                while len(remote) > 0:
                    self.gotRemoteData(remote)
                    sys.stdout.flush()
                    remote = self.conn.recv(4096)
            except ssl.SSLWantReadError:
                self.log.debug("Want read")
            except BlockingIOError:
                self.log.debug("Would block")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    parser = argparse.ArgumentParser(description="NetExtender NetSchmextender")
    parser.add_argument(dest="server", nargs=1, metavar="SERVER[:PORT]",
                        help="Server and port")
    parser.add_argument("--auth", required=True,
                        help="Authorization code from login cookie")
    parser.add_argument("--noverify", default=False, action="store_true",
                        help="Do not check TLS certificates")
    parser.add_argument("--debug", default=False, action="store_true",
                        help="Enable debug printouts")
    args = parser.parse_args()
    server = args.server[0]

    if args.debug:
        logging.getLogger().setLevel('DEBUG')

    serversplit = server.split(":")
    hostname = serversplit[0]
    try:
        port = int(serversplit[1])
    except IndexError:
        port = 443

    tunnel = Tunnel(hostname, port)
    tunnel.connect(self.auth, noverify=args.noverify)
    tunnel.run()
