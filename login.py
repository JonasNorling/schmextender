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
    args = parser.parse_args()
    server = args.server[0]
    
    # Using a session for all HTTPS requests in order to persist cookies   
    s = requests.Session()
    s.verify = not args.noverify
    
    # Must use a recognised user agent string, otherwise the server thinks
    # it's an old unsupported client
    s.headers.update({"User-Agent": "Dell SonicWALL NetExtender for Linux 8.1.787"})
    
    # Make a POST request with login information
    # Content-Type: application/x-www-form-urlencoded
    # User-Agent: Dell SonicWALL NetExtender for Linux 8.1.787
    log.info("--------------------------------------")
    log.info("Posting login information to %s" % server)
    loginform = { "username": args.username, "password": args.password,
                 "domain": args.domain }
    try:
        r = s.post("https://%s/cgi-bin/userLogin" % server, data=loginform)
    except requests.exceptions.SSLError as e:
        log.fatal("SSL error (bad certificate?)")
        log.info(e)
        sys.exit(1)
    except requests.exceptions.ConnectionError as e:
        log.fatal("Connection error")
        log.info(e)
        sys.exit(1)
    log.debug(r.status_code)
    log.debug(r.text)
    log.debug(r.headers)
    
    if "swap" in r.cookies:
        log.info("Swap cookie: %s", r.cookies["swap"])
    
    if r.status_code != 200 or "swap" not in r.cookies:
        log.fatal("Bad status (%d) or cookie when posting login information", r.status_code)
        log.info(r.text)
        sys.exit(1)
    
    # The client would now do a
    # GET /cgi-bin/sslvpnclient?epcversionquery=nxx HTTP/1.0
    # We skip that here, because I don't know what it is.
    
    # Make a GET request to receive some settings. We also get a new
    # "swap" cookie with the key for the actual tunnel.
    log.info("--------------------------------------")
    log.info("Getting settings")
    r = s.get("https://%s/cgi-bin/sslvpnclient?launchplatform=mac&neProto=3&supportipv6=yes" % server, data=loginform)
    log.debug(r.status_code)
    log.debug(r.text)
    log.debug(r.headers)
    
    if "swap" in r.cookies:
        log.info("Swap cookie: %s", r.cookies["swap"])
    
    if r.status_code != 200:
        log.fatal("Status %d when posting login information", r.status_code)
        log.info(r.text)
        exit

    s.close()

    # Finished!
    log.info("--------------------------------------")
    log.info("Now set up the tunnel using this authorization code: %s",
             r.cookies["swap"])
    



