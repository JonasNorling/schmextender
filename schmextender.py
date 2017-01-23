#!/usr/bin/python3
#
# This is an implementation of the SonicWALL NetExtender (Mobile Connect)
# protocol. Use at your own risk!
#
# Login and establish tunnel. Use with pppd pty schmextender.py
#

import argparse
import logging
from login import Login
from tunnel import Tunnel
import sys

log = logging.getLogger("schmextender")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    parser = argparse.ArgumentParser(description="NetExtender NetSchmextender")
    parser.add_argument(dest="server", nargs=1, metavar="SERVER[:PORT]",
                        help="Server and port")
    parser.add_argument("--username", "-u", required=True)
    parser.add_argument("--password", "-p", required=True)
    parser.add_argument("--domain", "-d", required=True,
                         help="Domain (specified by the VPN gateway)")
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

    login = Login(hostname, port, args.username, args.password, args.domain,
                  noverify=args.noverify)
    auth = login.run()
    if auth is None:
        sys.exit(-1)

    tunnel = Tunnel(hostname, port)
    tunnel.connect(auth[0], noverify=args.noverify)
    tunnel.run()
