#!/usr/bin/python3
#
import sys
import gi
import locale
locale.setlocale(locale.LC_ALL, '')
import gettext
_ = gettext.gettext

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, GObject

import os.path

import time
import threading
from datetime import datetime

class MDateTime(threading.Thread):
    def __init__(self, win):
        super().__init__()
        self.now = datetime.now()
        self.win = win
        self.stop = 0

    def run(self):
        while self.stop == 0:
            time.sleep(1)
            self.now = datetime.now()
            GLib.idle_add(self.win.refresh_clock, self.now.ctime())

    def ok_done(self):
        self.stop = 1

host_name_file = '/etc/hostname'
os_file = '/etc/os-release'
mem_file = '/proc/meminfo'
cpu_file = '/proc/cpuinfo'

def hostname():
    if not os.path.isfile(host_name_file):
        return ''
    with open(host_name_file, "r") as fin:
        line = fin.readline()
    return line.rstrip('\n')

def osname():
    if not os.path.isfile(os_file):
        return oinf
    with open(os_file, 'r') as fin:
        for line in fin:
            if line.find("PRETTY_NAME") > -1:
                break
    osdesc = line.split('=')[1]
    return osdesc.strip('"').rstrip('\n').rstrip('"')

def memsize():
    if not os.path.isfile(mem_file):
        return 0
    with open(mem_file, "r") as fin:
        for line in fin:
            if line.find("MemTotal") == 0:
                break
    mems = line.split()
    skb = int(mems[1])
    return int((skb - 1)/(1024*1024)) + 1

def cpuinfo():
    aimp = {0x41: 'ARM'}
    aarch = {8: 'AArch64'}
    apart = {0xd08: 'Cortex-A72', 0xd03: 'Cortex-A53', 0xd07: 'Cortex-A57'}

    def same_cpu(cpu1, cpu2):
        if len(cpu1) != len(cpu2):
            return False

        equal = True
        for key in cpu1.keys():
            if key.find('processor') != -1 or key.find('apicid') != -1 \
                    or key.find('cpu MHz') != -1 or key.find('core id') != -1 \
                    or key.find('siblings') != -1 or key.find('cpu cores') != -1:
                continue

            try:
                if cpu1[key] != cpu2[key]:
#                    print("Key: {}. Not Equal: {}---{}".format(key, cpu1[key], cpu2[key]))
                    equal = False
                    break
            except:
                equal = False
                break
        return equal


    cinfo = []
    with open(cpu_file, 'r') as fin:
        ncpu = {}
        for line in fin:
            if len(line.rstrip('\n')) == 0:
                if len(ncpu) > 0:
                    cinfo.append(ncpu)
                    ncpu = {}
                continue

            rec = line.rstrip('\n').split(': ')
            while len(rec[0]) > 0 and rec[0][-1] == '\t':
                rec[0] = rec[0].rstrip('\t')
            if len(rec[0]) > 0 and len(rec) > 1:
                ncpu[rec[0]] = rec[1]

    pcpu = {}
    numc = 0
    sorted_cinfo = []
    for cpu in cinfo:
        if not same_cpu(cpu, pcpu):
            if numc > 0:
                sorted_cinfo.append((pcpu, numc))
            pcpu = cpu
            numc = 1
        else:
            numc += 1
    if numc > 0:
        sorted_cinfo.append((pcpu, numc))

    cpu_infos = []
    for cpu_tup in sorted_cinfo:
        cpu_keys = cpu_tup[0].keys()
        if 'model name' in cpu_keys:
            cpu_infos.append((cpu_tup[0]['model name'], cpu_tup[1]))
            continue
        if 'CPU implementer' in cpu_keys:
            for key, val in cpu_tup[0].items():
                if key == 'CPU implementer':
                    c_vendor = aimp[int(val, 0)]
                if key == 'CPU architecture':
                    c_arch = aarch[int(val, 0)]
                if key == 'CPU part':
                    c_model = apart[int(val, 0)]
                if key == 'CPU revision':
                    c_rev = int(val, 0)
        cpu_infos.append((c_vendor+' '+c_arch+' '+c_model+' '+'Rev '+str(c_rev), cpu_tup[1]))
    return cpu_infos

class SYSInfo:
    def __init__(self):
        self.hostname = hostname()
        self.osname = osname()
        self.memsize = str(memsize())+' GiB'
        self.cpuinfo = cpuinfo()

class MWindow(Gtk.Window):
    def __init__(self, sysinfo):
        super().__init__()
        self.set_border_width(2)
        self.set_default_size(400, 200)

        hb = Gtk.HeaderBar()
        hb.set_show_close_button(True)
        hb.props.title = _("System Info")
        self.set_titlebar(hb)

        grid = Gtk.Grid()
        self.add(grid)

        hbox1 = Gtk.Box(homogeneous=False)
        grid.attach(hbox1, 0, 0, 2, 1)
        hname_label = Gtk.Label(label=_("Hostname: "))
        hname_label.set_width_chars(13)
        hbox1.pack_start(hname_label, False, True, 0)
        hname_content = Gtk.Entry(text=sysinfo.hostname)
        hname_content.set_editable(False)
        hbox1.pack_start(hname_content, True, True, 0)
#        hname_content.set_justify(Gtk.Justification.LEFT)

        hbox2 = Gtk.Box(homogeneous=False)
        grid.attach(hbox2, 0, 1, 2, 1)
        os_label = Gtk.Label(label=_("OS Type: "))
        os_label.set_width_chars(13)
        hbox2.pack_start(os_label, False, False, 0)
        os_name = Gtk.Entry(text=sysinfo.osname)
        os_name.set_editable(False)
        hbox2.pack_start(os_name, True, True, 0)

        hbox3 = Gtk.Box(homogeneous=False)
        grid.attach(hbox3, 0, 2, 2, 1)
        mem_label = Gtk.Label(label=_("Memory Size: "))
        mem_label.set_width_chars(13)
        hbox3.pack_start(mem_label, False, True, 0)
        mem_size = Gtk.Entry(text=sysinfo.memsize)
        mem_size.set_editable(False)
        mem_size.set_width_chars(8)
        hbox3.pack_start(mem_size, False, True, 0)
        date_label = Gtk.Label(label=_("Date Time: "))
        hbox3.pack_start(date_label, False, True, 10)
        self.date_disp = Gtk.Entry(text=datetime.now().ctime())
        self.date_disp.set_editable(False)
        self.date_disp.set_width_chars(10)
        hbox3.pack_start(self.date_disp, True, True, 0)

        hseparator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        grid.attach(hseparator, 0, 3, 2, 1)

        vbox = Gtk.VBox()
        grid.attach(vbox, 1, 4, 1, 1)
        hbox = Gtk.Box()
        vbox.pack_start(hbox, True, True, 1)

        l_cpumod = Gtk.Label(_("CPU Model"))
        l_cpumod.set_width_chars(40)
        hbox.pack_start(l_cpumod, True, True, 0)
        l_cpunum = Gtk.Label(_("Count"))
        hbox.pack_start(l_cpunum, True, True, 5)

        ih = 1
        for cinfo, num in sysinfo.cpuinfo:
            hbox = Gtk.Box()
            vbox.pack_start(hbox, True, True, 0)
            info_label = Gtk.Entry(text=cinfo)
            info_label.set_width_chars(34)
            info_label.set_editable(False)
            hbox.pack_start(info_label, True, True, 0)
            num_label = Gtk.Entry(text=str(num))
            num_label.set_width_chars(3)
            num_label.set_editable(False)
            hbox.pack_start(num_label, False, True, 5)
            ih += 1

        hseparator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        grid.attach(hseparator, 0, 4+ih, 2, 1)

        img = Gtk.Image()
        img.set_from_file("./sysinfo-side.png")
        grid.attach(img, 0, 4, 1, ih+2)

        ver = Gtk.Label(label=_("Version: "))
        grid.attach(ver, 0, 6+ih, 1, 1)
        lic = Gtk.Label(label=_("LIDC Connector v3.7"))
        grid.attach(lic, 1, 6+ih, 1, 1)

        self.set_position(Gtk.WindowPosition.CENTER)

    def refresh_clock(self, dt):
        self.date_disp.set_text(dt)

if __name__ == '__main__':
    minfo = SYSInfo()
    win = MWindow(minfo)
    win.connect("destroy", Gtk.main_quit)
    win.show_all()

    watch = MDateTime(win)
    watch.start()

    Gtk.main()

    watch.ok_done()
    watch.join()

    sys.exit(0)
