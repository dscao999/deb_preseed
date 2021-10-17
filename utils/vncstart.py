#!/usr/bin/python3
#
import os, time, secrets
import socket, struct, fcntl
import gi
import string

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

lock_file = "/run/lock/admin_assist.lock"

def get_ip(iface, sockfd):
    SIOCGIFADDR = 0x8915

    zerofill = (b'\x00')*14
    ifreq = struct.pack('16sH14s', iface.encode('utf-8'), socket.AF_INET, zerofill)
    try:
        res = fcntl.ioctl(sockfd, SIOCGIFADDR, ifreq)
    except:
        return None
    ip = struct.unpack('16sH2x4s8x', res)[2]
    return socket.inet_ntoa(ip)

def get_addr(sock):
    sockfd = sock.fileno()
    ifaces = socket.if_nameindex()
    addr = []

    for iface in ifaces:
        if iface[1] == 'lo':
            continue
        ip = get_ip(iface[1], sockfd)
        if ip:
            addr.append((iface[1], ip))
    return addr

class MainWin(Gtk.Window):
    def __init__(self):
        super().__init__(title="LENVDI Admin Assist")
        self.set_border_width(10)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        addr_info = get_addr(sock)
        grid = Gtk.Grid()
        grid.set_column_spacing(20)
        grid.show()
        self.add(grid)
        ypos = 0
        for addr in addr_info:
            label = Gtk.Label(label=addr[0]+':')
            label.set_max_width_chars(12)
            label.set_xalign(1)
            grid.attach(label, 0, ypos, 1, 1) 
            label.show()
            ip = Gtk.Label(label=addr[1])
            ip.set_max_width_chars(18)
            ip.set_xalign(0)
            grid.attach(ip, 1, ypos, 1, 1)
            ip.show()
            ypos += 1

        self.port = 5900
        pok = 0
        while pok == 0:
            try:
                sock.bind(('', self.port))
                pok = 1
            except:
                self.port += 1
        sock.close()
        label = Gtk.Label(label='Port:')
        label.set_max_width_chars(12)
        label.set_xalign(1)
        grid.attach(label, 0, ypos, 1, 1)
        label.show()
        ip = Gtk.Label(label=str(self.port))
        ip.set_max_width_chars(18)
        ip.set_xalign(0)
        grid.attach(ip, 1, ypos, 1, 1)
        ip.show()
        ypos += 1

        alphabet = string.ascii_letters + string.digits
        password = ''.join(secrets.choice(alphabet) for i in range(8))
        label = Gtk.Label(label='Password:')
        label.set_max_width_chars(12)
        label.set_xalign(1)
        grid.attach(label, 0, ypos, 1, 1)
        label.show()
        ip = Gtk.Label(label=password)
        ip.set_xalign(0)
        grid.attach(ip, 1, ypos, 1, 1)
        ip.show()
        ypos += 1

try:
    fd = os.open(lock_file, os.O_WRONLY|os.O_CREAT|os.O_EXCL)
except:
    win = Gtk.Window()
    dialog = Gtk.MessageDialog(parent=win,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Another instance is already running"
            )
    dialog.run()
    dialog.destroy()
    quit(2)
os.close(fd)

win = MainWin()
win.connect("destroy", Gtk.main_quit)
win.show()
Gtk.main()
os.remove(lock_file)
quit(0)
