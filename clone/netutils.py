#!/usr/bin/python3
#
import socket
import os
import struct
import fcntl

def enum_ips():
    ip_addrs = []
    SIOCGIFADDR = 0x8915
    zerofill = (b'\x00')*14

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    fd = sock.fileno()
    ifaces = socket.if_nameindex()
    for iface in ifaces:
        nic = iface[1]
        if nic == 'lo':
            continue
        ifreq = struct.pack('16sH14s', nic.encode('utf-8'), socket.AF_INET, zerofill)
        try:
            res = fcntl.ioctl(fd, SIOCGIFADDR, ifreq)
        except:
            continue
        ipv = struct.unpack('16sH2x4s8x', res)[2]
        ip = socket.inet_ntoa(ipv)
        ip_addrs.append(ip)
    return ip_addrs

if __name__ == '__main__':
    ips = enum_ips()
    print(ips)
    quit(0)
