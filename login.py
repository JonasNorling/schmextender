#!/usr/bin/python3
#
# This is an implementation of the SonicWALL NetExtender (Mobile Connect)
# protocol. Use at your own risk!
#

import argparse
import logging
import requests
import sys

log = logging.getLogger("schmextender")

class Login(object):
    def __init__(self, hostname, port, username, password, domain, noverify=False):
        self.log = logging.getLogger("schmextender")
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.domain = domain
        self.noverify = noverify

    def run(self):
        server = "%s:%d" % (self.hostname, self.port)

        # Using a session for all HTTPS requests in order to persist cookies   
        s = requests.Session()
        s.verify = not self.noverify
    
        # Must use a recognised user agent string, otherwise the server thinks
        # it's an old unsupported client
        s.headers.update({"User-Agent": "Dell SonicWALL NetExtender for Linux 8.1.787"})
    
        # Make a POST request with login information
        # Content-Type: application/x-www-form-urlencoded
        # User-Agent: Dell SonicWALL NetExtender for Linux 8.1.787
        self.log.info("Posting login information to %s" % server)
        loginform = { "username": self.username, "password": self.password,
                      "domain": self.domain }
        try:
            r = s.post("https://%s/cgi-bin/userLogin" % server, data=loginform)
        except requests.exceptions.SSLError as e:
            self.log.fatal("SSL error (bad certificate?)")
            self.log.info(e)
            return None
        except requests.exceptions.ConnectionError as e:
            self.log.fatal("Connection error")
            self.log.info(e)
            return None
        self.log.debug(r.status_code)
        self.log.debug(r.text)
        self.log.debug(r.headers)
    
        if "swap" in r.cookies:
            self.log.debug("Swap cookie: %s", r.cookies["swap"])
    
        if r.status_code != 200 or "swap" not in r.cookies:
            self.log.fatal("Bad status (%d) or cookie when posting login information", r.status_code)
            self.log.info(r.text)
            return None
    
        # The client would now do a
        # GET /cgi-bin/sslvpnclient?epcversionquery=nxx HTTP/1.0
        # We skip that here, because I don't know what it is.

        # Make a GET request to receive some settings. We also get a new
        # "swap" cookie with the key for the actual tunnel.
        self.log.info("Getting settings")
        r = s.get("https://%s/cgi-bin/sslvpnclient?launchplatform=mac&neProto=3&supportipv6=yes" % server, data=loginform)
        self.log.debug(r.status_code)
        self.log.debug(r.text)
        self.log.debug(r.headers)

        if "swap" in r.cookies:
            self.log.info("Swap cookie: %s", r.cookies["swap"])

        if r.status_code != 200:
            self.log.fatal("Status %d when posting login information", r.status_code)
            self.log.info(r.text)
            return None

        s.close()

        # Finished!
        self.log.info("Got authorization code")
        self.log.debug("Now set up the tunnel using this authorization code: %s",
                       r.cookies["swap"])

        return r.cookies["swap"]

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

    print("Authorization code: %s" % auth)
