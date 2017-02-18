## schmextender
This is a proof of concept client for Sonicwall SSL VPN. The official client is called Net Extender.

## Usage
Something like this should get you started.
```
# The quoting around PASSWORD is for supporting stuff like "$! and so in the password.
sudo pppd nodetach file ppp_conf pty "./schmextender.py --username USERNAME --password '"'PASSWORD'"' --domain 'DOMAIN' sslvpn.example.net:4433 --noverify"
```


## Limitation
- Issue with blocking write, sometimes it casues an exception.
- No keep alive, if the client is to slient, the connection will be closed.
- Doesn't install defualt routes if asked by the server
- Doesn't install DNS related information, such as resolvers and search domains.
- Doesn't support EPC, End Point Control. I.e. the firewall dictates how the client should be managed. Does it have this and that software/setting/whatever turned on/off.

