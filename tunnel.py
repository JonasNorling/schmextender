#!/usr/bin/python3 -u
#
# This implements the PPP forwarding part of the SonicWALL NetExtender
# (Mobile Connect) protocol.
#
# This script establishes a TLS connection and shovels data between the
# server and stdio. Use with pppd pty <script>
#
# Note: we're running with -u for unbuffered I/O. FIXME: Solve in code.
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

log = logging.getLogger("schmextender")


def gotLocalData(data):
    global conn
    # Prepend the length field and send to the server
    log.debug("Local: %s" % data)
    lenstr = struct.pack("!I", len(data))
    sendlen = conn.send(lenstr + data)
    if sendlen != len(data) + 4:
        log.error("Sent too little to server")

more = 0
def gotRemoteData(data):
    global more
    if more > 0:
        sys.stdout.buffer.write(data[:more])
        more -= len(data[:more])
    while len(data) > 0:
        lenfield = struct.unpack("!I", data[0:4])[0]
        log.debug("Remote %d B" % lenfield)
        data = data[4:]
        sendlen = sys.stdout.buffer.write(data[:lenfield])
        if sendlen != len(data[:lenfield]):
            log.error("Sent too little on stdout")
        more = lenfield - len(data)
        data = data[lenfield:]
    if more > 0:
        log.debug("Waiting for %d B" % more)

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
        log.setLevel('DEBUG')

    serversplit = server.split(":")
    hostname = serversplit[0]
    try:
        port = int(serversplit[1])
    except IndexError:
        port = 443

    context = ssl.create_default_context()
    if args.noverify:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    
    conn = context.wrap_socket(socket.socket(socket.AF_INET),
                               server_hostname=hostname)
    conn.connect((hostname, port))
    log.info("Connected to %s:%d" % (hostname, port))

    connectstr = "CONNECT localhost:0 HTTP/1.0\r\nX-SSLVPN-PROTOCOL: 2.0\r\nX-SSLVPN-SERVICE: NETEXTENDER\r\nProxy-Authorization:%s\r\nX-NX-Client-Platform: Linux\r\nConnection-Medium: MacOS\r\nUser-Agent: Dell SonicWALL NetExtender for Linux 8.1.787\r\nFrame-Encode: off\r\nX-NE-PROTOCOL: 2.0\r\n\r\n" % args.auth
    conn.write(bytes(connectstr, "ascii"))
    log.debug("Wrote: %s", connectstr)
    
    # Set the socket and stdio non-blocking so we can react to data
    # on either one of them
    conn.setblocking(False)
    fd = sys.stdin.fileno()
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
    
    # Let's shovel some data!
    sel = selectors.DefaultSelector()
    sel.register(conn, selectors.EVENT_READ)
    sel.register(sys.stdin, selectors.EVENT_READ)

    while True:
        events = sel.select()
        local = sys.stdin.buffer.read(1500)
        remote = b''
        try:
            remote = conn.recv(4096)
        except ssl.SSLWantReadError:
            log.debug("Want read")
        
        if local is not None and len(local) > 0:
            gotLocalData(local)
        
        if len(remote) > 0:
            gotRemoteData(remote)
