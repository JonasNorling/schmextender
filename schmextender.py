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
import subprocess
import _thread
import time

log = logging.getLogger("schmextender")

# Prepare the interface by adding routes
# This is something that is usually done in the ppp ip-up script
def prepare_interface(name, data):
    # Try for a few seconds
    up = False
    for _ in range(6):
        try:
            if subprocess.check_output(["/usr/sbin/ip", "link", "show", "up", "dev", name], stderr=sys.stderr):
                up = True
                break
        except CalledProcessError:
            pass
        time.sleep(0.5)

    if not up:
        return

    for r in data.setdefault("Route", []):
        log.info("Adding route to %s", r)
        subprocess.call(["/usr/sbin/ip", "route", "add", r, "dev", name], stdout=sys.stderr, stderr=sys.stderr)

    for a in data.setdefault("GlobalIPv6Addr", []):
        log.info("Adding IPv6 address %s", a)
        subprocess.call(["/usr/sbin/ip", "address", "add", a, "dev", name], stdout=sys.stderr, stderr=sys.stderr)

    for r in data.setdefault("Ipv6Route", []):
        if r == "::/64":
            log.info("Ignoring IPv6 route %s", r)
            continue
        log.info("Adding IPv6 route to %s", r)
        subprocess.call(["/usr/sbin/ip", "route", "add", r, "dev", name], stdout=sys.stderr, stderr=sys.stderr)

    if data["TunnelAllMode"][0] == "1":
        log.info("Server asked us to add a default route...")

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

    log.warning("Assuming ppp0 interface");
    _thread.start_new_thread(prepare_interface, ("ppp0", auth[1]))

    tunnel = Tunnel(hostname, port)
    tunnel.connect(auth[0], noverify=args.noverify)
    tunnel.run()
