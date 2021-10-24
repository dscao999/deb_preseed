#!/usr/bin/python3
#
import os, time, secrets
import socket, struct, fcntl
import gi
import string
import threading
import subprocess as subp
import locale
import gettext

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

locale.setlocale(locale.LC_ALL, '')
_ = gettext.gettext
gettext.bindtextdomain("vncstart")
gettext.textdomain('vncstart')

lock_file = "/run/lock/admin_assist.lock"

class CheckConnection(threading.Thread):
    def __init__(self, win):
        print(f'passwd: {win.password}')
        self.win = win
        self.fin = 0
        super().__init__()
        mesg = open("./x11vnc.log", "w")
        self.offset = 0
        self.vnc = subp.Popen(['/usr/bin/x11vnc', '-once', '-nolookup', '-noipv6', 
            '-rfbport', str(win.port), '-passwd', win.password],
            stdout=mesg, stderr=subp.STDOUT, text=True, start_new_session=True, bufsize=1)
        self.gui_gone = 0
        mesg.close()

    def run(self):
        res = None
        mark = 0
        while self.fin == 0:
            mark += 1
            try:
                res = self.vnc.communicate(timeout=0.5)
                self.fin = 1
            except subp.TimeoutExpired:
                if self.gui_gone == 0:
                    mesg = open("./x11vnc.log", "r")
                    mesg.seek(self.offset, 0)
                    cot = mesg.read()
                    self.offset = mesg.tell()
                    mesg.close()
                    con = cot.find('Got connection from client')
                    if con != -1:
                        GLib.idle_add(self.win.win_quit)
                        self.gui_gone = 1
                    elif mark % 2 == 0:
                        GLib.idle_add(self.win.check_for_connection)
            if self.fin == 1:
                if self.vnc.returncode != 0 and self.win.user_fin == 0:
                    dialog = Gtk.MessageDialog(parent=win,
                            flags=0,
                            message_type=Gtk.MessageType.ERROR,
                            buttons=Gtk.ButtonsType.OK,
                            text=_("Cannot Startup X11VNC")
                            )
                    dialog.run()
                    dialog.destroy()
                    GLib.idle_add(self.win.win_quit)
            if self.gui_gone == 1:
                break

    def finish(self):
        self.vnc.kill()

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
        super().__init__(title=_("LENVDI Admin Assist"))
        self.set_border_width(10)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        addr_info = get_addr(sock)
        grid = Gtk.Grid()
        grid.set_column_spacing(20)
        grid.set_row_homogeneous(True)
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
        label = Gtk.Label(label=_('Port:'))
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
        self.password = ''.join(secrets.choice(alphabet) for i in range(6))
        label = Gtk.Label(label=_('Password:'))
        label.set_max_width_chars(12)
        label.set_xalign(1)
        grid.attach(label, 0, ypos, 1, 1)
        label.show()
        ip = Gtk.Label(label=self.password)
        ip.set_xalign(0)
        grid.attach(ip, 1, ypos, 1, 1)
        ip.show()
        ypos += 1

        self.echo = Gtk.Label(label=_('Waiting for connection'))
        grid.attach(self.echo, 0, ypos, 2, 1)
        self.echo.show()
        self.echo_show = 1
        self.user_fin = 0

    def check_for_connection(self):
        self.echo_show += 1
        if self.echo_show % 2 == 0:
            self.echo.set_text('----------------')
        else:
            self.echo.set_text(_('Waiting for connection'))
        return False

    def win_quit(self):
        Gtk.main_quit()
        return False

try:
    fd = os.open(lock_file, os.O_WRONLY|os.O_CREAT|os.O_EXCL)
except:
    win = Gtk.Window()
    dialog = Gtk.MessageDialog(parent=win,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=_("Another instance is already running")
            )
    dialog.run()
    dialog.destroy()
    quit(2)
os.close(fd)

def all_quit(widget, data=None):
    widget.user_fin = 1
    Gtk.main_quit()

win = MainWin()
win.connect("destroy", all_quit)
win.show()
watch = CheckConnection(win)
watch.start()
Gtk.main()
if win.user_fin == 1:
    watch.finish()
watch.join()
os.remove(lock_file)
quit(0)
