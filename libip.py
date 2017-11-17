#!/usr/bin/python3

# Add addresses and routes using the ip utility on Linux and
# ifconfig and route utilities on Mac OS X.

import logging
import platform
import re
import subprocess
import sys

log = logging.getLogger("schmextender")

class IP:
    def __init__(self):
        self.ip_cmd = None
    def get_ip_cmd(self):
        if self.ip_cmd:
            return self.ip_cmd
        commands = ["/usr/sbin/ip", "/sbin/ip"]
        for cmd in commands:
            try:
                subprocess.call([cmd, "-V"], stdout=None, stderr=None)
                log.debug("Found: %s" % cmd)
                self.ip_cmd = cmd
                return cmd
            except FileNotFoundError:
                log.debug("Not found: %s" % cmd)
        log.error("ip tool not found, tried: %s" % ", ".join(commands))
        sys.exit(1)
    def run(self, cmd):
        log.debug("Running: %s" % (" ".join(cmd)))
        subprocess.call(cmd, stdout=sys.stderr, stderr=sys.stderr)
    def run_check(self, cmd):
        try:
            log.debug("Running: %s" % (" ".join(cmd)))
            if subprocess.check_output(cmd, stderr=sys.stderr):
                return True
        except subprocess.CalledProcessError:
            pass
        return False
    def is_link_up(self, dev):
        return self.run_check([self.get_ip_cmd(), "link", "show", "up", "dev", dev])
    def add_route(self, route, dev):
        self.run([self.get_ip_cmd(), "route", "add", route, "dev", dev])
    def add_route6(self, route, dev):
        self.add_route(route, dev)
    def add_address6(self, addr, dev):
        self.run([self.get_ip_cmd(), "address", "add", addr, "dev", dev])

class IPDarwin(IP):
    def is_link_up(self, dev):
        return self.run_check(["/sbin/ifconfig", "-u", dev])
    def add_route(self, route, dev):
        # Example of a route: 10.0.0.0/255.255.255.0
        # Translate this into: 10.0.0.0/24
        p = re.compile("^([\d.]+)/([\d.]+)$")
        res = p.findall(route)
        if not res:
            log.error("Non supported route format: %s" % route)
        net = res[0][0]
        netmask = res[0][1]
        self.run(["/sbin/route", "add", "-net", net, "-interface", dev, "-netmask", netmask])
    def add_route6(self, route, dev):
        # Example of a route: 2001:9b0:192:1::/64
        self.run(["/sbin/route", "add", "-inet6", route, "-interface", dev])
    def add_address6(self, addr, dev):
        self.run(["/sbin/ifconfig", dev, "inet6", "add", addr])

def get_impl():
    if platform.system() == "Darwin":
        log.info("Using Mac OS X commands for IP configuration")
        return IPDarwin()
    else:
        if platform.system() != "Linux":
            log.warning("Unknown platform, will try Linux anyway")
        log.info("Using Linux ip tool for IP configuration")
        return IP()

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    ip = get_impl()
    interfaces = ["lo", "eth0", "lo0", "en0"]
    for iface in interfaces:
        log.info("%s is %s", iface, ip.is_link_up(iface) and "up" or "down")
