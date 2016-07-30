import sys
import socket
import fcntl
import struct

SIOCGIFADDR = 0x8915 # from bits/ioctls.h
IF_NAMESIZE = 16 # from net/if.h

sockaddr_in_fmt = "HHI"
# struct sockaddr_in is:
#    unsigned short (sa_family_t) "sin_family"
#    unsigned short "sin_port"
#    unsigned int   "sin_addr"

ifreq_fmt = "16s" + sockaddr_in_fmt
# struct ifreq is:
#    char ifname[16]
#    struct sockaddr_in

def get_ip(ifname):
    sk = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
    blob = struct.pack(ifreq_fmt, ifname, 0, 0, 0)
    r = fcntl.ioctl(sk.fileno(), SIOCGIFADDR, blob)
    ifreq = struct.unpack(ifreq_fmt, r)
    ip = socket.inet_ntoa(struct.pack("I", ifreq[3]))
    return ip

if __name__ == "__main__":
    print get_ip(sys.argv[1])
