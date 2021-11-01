#!/usr/bin/python3
#
import gi
import locale
import gettext
import os, fcntl
import re
import threading
import subprocess as subp
import time
import shutil

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk

locale.setlocale(locale.LC_ALL, '')
_ = gettext.gettext
gettext.bindtextdomain("ovinst")
gettext.textdomain('ovinst')

ks_text = """#use command line install mode
cmdline
# accept license
eula --agreed
# System authorization information
auth --enableshadow --passalgo=sha512
# Use Live Image installation media
liveimg --url=file:///run/install/repo/ovirt-node-ng-image.squashfs.img
# Keyboard layouts
keyboard --vckeymap=us --xlayouts='us'
# System language
lang en_US.UTF-8
# System timezone
timezone Asia/Shanghai --isUtc --nontp
# Root password
rootpw --iscrypted $6$RKC5W15k3K/cXBJf$4rEaKMZF/EtjIl0zZvjpGeZJjFlYpKzy76svDzH2DaDRE7XTADpiSvUMARYj0Zcsqay9RjI4UOFr7djw34XHR1
# System services
services --disabled="chronyd" --enabled="ntpd"
# User Information and password
user --groups=wheel --name=lenovo --password=$6$dBtyehHvnQ6ss$VhiwJ1ISBLZvdnudHjvrglTCcvTkJovn8cNXS9G.BvolZBlBmUOqBrxqUvtpWVL2NRSCzKp8K1obYMgKgcMvD/ --iscrypted --gecos="Lenovo Administrator"
# disable firewall and selinux
firewall --disabled
selinux --disabled
# Network information
network --hostname=$namezeus

%include /tmp/custom.ks

%post --erroronfail
imgbase layout --init

[ -d /etc/multipath/conf.d ] || mkdir -p /etc/multipath/conf.d
cat > /etc/multipath/conf.d/usb-storage.conf <<EOD
blacklist {
	property "ID_USB_INTERFACE_NUM"
	property "ID_CDROM"
}

systemctl disable iscsid.socket iscsid.service fcoe.service
EOD

%end

%anaconda
pwpolicy root --minlen=6 --minquality=1 --notstrict --nochanges --notempty
pwpolicy user --minlen=6 --minquality=1 --notstrict --nochanges --emptyok
pwpolicy luks --minlen=6 --minquality=1 --notstrict --nochanges --notempty
%end

%pre --interpreter=/usr/bin/python
import os

precmd = \"\"\"network --device=ovirt --activate --bootproto=static --ip=$ovirt_ip --netmask=255.255.255.0 --nodefroute --nodns --noipv6 --teamslaves="$ovirt_port1'{\\\\"prio\\\\":-10, \\\\"sticky\\\\": true}',$ovirt_port2'{\\\\"prio\\\\":100}'" --teamconfig="{\\\\"runner\\\\": {\\\\"name\\\\": \\\\"activebackup\\\\"}}"
network --device=gluster --activate --bootproto=static --ip=$gluster_ip --netmask=255.255.255.0 --nodefroute --nodns --noipv6 --teamslaves="$gluster_port1'{\\\\"prio\\\\":-10, \\\\"sticky\\\\": true}',$gluster_port2'{\\\\"prio\\\\":100}'" --teamconfig="{\\\\"runner\\\\": {\\\\"name\\\\": \\\\"activebackup\\\\"}}"
# ignore all other disks
ignoredisk --only-use=$rootdisk
# System bootloader configuration
bootloader --append=" crashkernel=auto" --location=mbr --boot-drive=$rootdisk
# Partition clearing information
clearpart --all --initlabel --drives=$rootdisk
# Disk partitioning information
part /boot/efi --fstype="efi" --ondisk=$rootdisk --size=200 --label="EFI_SP"
part /boot --fstype="ext2" --ondisk=$rootdisk --size=1024 --label="BOOTFS"
#
part pv.407 --fstype="lvmpv" --ondisk=$rootdisk --size=70000 --grow
volgroup onn_$namezeus --pesize=4096 pv.407
logvol none  --fstype="None" --size=60000 --thinpool --metadatasize=4096 --chunksize=65536 --name=pool00 --vgname=onn_$namezeus
#
logvol swap  --fstype="swap" --size=1024  --label="SWAP" --name=swap --vgname=onn_$namezeus
logvol /     --fstype="xfs" --size=10240  --label="ROOTFS" --thin --poolname=pool00 --name=root --vgname=onn_$namezeus
logvol /var  --fstype="xfs" --size=10240  --label="VARFS"  --thin --poolname=pool00 --name=var  --vgname=onn_$namezeus
logvol /home  --fstype="xfs" --size=1024 --label="HOMEFS" --thin --poolname=pool00 --name=home --vgname=onn_$namezeus
logvol /tmp   --fstype="xfs" --size=1024 --label="TMPFS"  --thin --poolname=pool00 --name=tmp  --vgname=onn_$namezeus
#
logvol /var/log   --fstype="xfs" --size=8192  --label="LOGFS"  --thin --poolname=pool00 --name=var_log  --vgname=onn_$namezeus
logvol /var/log/audit --fstype="xfs" --size=2048 --label="AUDITFS" --thin --poolname=pool00 --name=var_log_audit --vgname=onn_$namezeus
\"\"\"

rootdisk = '$rootpath'
ovirt_port1 = '$oport1'
ovirt_port2 = '$oport2'
gluster_port1 = '$gport1'
gluster_port2 = '$gport2'

def lsnet(nicpci):
    netdir = '/sys/class/net'
    ports = os.listdir(netdir)
    for port in ports:
        nicpath = netdir + '/' + port
        if not os.path.islink(nicpath):
            continue
        link = os.readlink(nicpath)
        if link.find('virtual') != -1 or link.find('usb') != -1:
            continue
        if link.find(nicpci) != -1:
            return port
    return None
 
def lsdisk(dsk):
    dpath = '/dev/disk/by-path' + '/' + dsk
    tname = os.readlink(dpath)
    slash = tname.rfind('/')
    tname = tname[slash+1:]
    return tname

with open('/tmp/custom.ks', 'w') as ks:
    devname = lsdisk(rootdisk)
    precmd = precmd.replace('$rootdisk', devname)
    nic = lsnet(ovirt_port1)
    precmd = precmd.replace('$ovirt_port1', nic)
    nic = lsnet(ovirt_port2)
    precmd = precmd.replace('$ovirt_port2', nic)
    nic = lsnet(gluster_port1)
    precmd = precmd.replace('$gluster_port1', nic)
    nic = lsnet(gluster_port2)
    precmd = precmd.replace('$gluster_port2', nic)
    ks.write(precmd)

exit(0)
%end
"""

class Process_KS(threading.Thread):
    def __init__(self, mwin):
        self.win = mwin
        super().__init__()

    def run(self):
        global ks_text
        ovirt_iso = 'ovirt-node-ng-installer-4.3.10-2020060117.el7.iso'
        ovirt_iso_path = '/run/initramfs/live/LiveOS/' + ovirt_iso
        with open(ovirt_iso_path, "rb") as isoh:
            isoh.seek(0x8028, 0)
            label = isoh.read(32).decode('utf-8')
        print(f'Label: {label}')
        srcmnt = "/tmp/ovirt_src"
        os.mkdir(srcmnt, mode=0o755)
        res = subp.run("sudo mount -o ro "+ovirt_iso_path+" "+srcmnt,
                shell=True, text=True, stdout=subp.PIPE, stderr=subp.STDOUT)
        if res.returncode != 0:
            GLib.idle_add(self.win.task_error, _("Operation Failed\n")+res.stdout)
            return
        isodir = "/tmp/isotop-"+str(os.getpid())
        shutil.copytree(srcmnt, isodir, symlinks=True)
        subp.run("sudo umount " + srcmnt, shell=True, text=True, stdout=subp.PIPE, stderr=subp.STDOUT)
        os.rmdir(srcmnt)

        kscfg = isodir + "/interactive-defaults.ks"
        os.chmod(kscfg, 0o644)
        ks_text = ks_text.replace("$namezeus", self.win.ks_info["hostname"])
        ks_text = ks_text.replace("$ovirt_ip", self.win.ks_info["ovirt"]["ip"])
        ks_text = ks_text.replace("$gluster_ip", self.win.ks_info["gluster"]["ip"])
        ks_text = ks_text.replace("$rootpath", self.win.ks_info["rootdisk"])
        ks_text = ks_text.replace("$oport1", self.win.ks_info["ovirt"]["port1"])
        ks_text = ks_text.replace("$oport2", self.win.ks_info["ovirt"]["port2"])
        ks_text = ks_text.replace("$gport1", self.win.ks_info["gluster"]["port1"])
        ks_text = ks_text.replace("$gport2", self.win.ks_info["gluster"]["port2"])

        with open(kscfg, "w") as ksfile:
            ksfile.write(ks_text)

class EchoInfo(Gtk.MessageDialog):
    def __init__(self, rootwin, info):
        super().__init__(parent=rootwin, flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text=info)

def iscdrom(path, rootwin):
    try:
        cdrom = open(path, 'rb')
    except PermissionError:
        echo = EchoInfo(rootwin, "Permission Denied! Please try SUDO")
        echo.run()
        echo.destroy()
        exit(1)

    cdfd = cdrom.fileno()
    CDROM_GET_CAPABILITY = 0x5331
    try:
        res = fcntl.ioctl(cdfd, CDROM_GET_CAPABILITY, 0)
        iscd = True
    except:
        iscd = False
    return iscd

def lsdisk(rootwin):
    tpath = '/dev/disk/by-path'
    with os.scandir(tpath) as lndevs:
        devpairs = [('None', 'None')]
        for lndev in lndevs:
            pname = lndev.name
            if not lndev.is_symlink():
                continue
            part = pname.find("-part")
            usb = pname.find("usb")
            if part != -1 or usb != -1:
                continue
            if iscdrom(tpath+'/'+pname, rootwin):
                continue

            tname = os.readlink(tpath+'/'+pname)
            slash = tname.rfind('/')
            if slash != -1:
                tname = tname[slash+1:]
            curtup = (pname, '/dev/'+tname)
            skip = 0
            for tup in devpairs:
                if tup[1] == curtup[1]:
                    skip = 1
                    break
            if skip == 1:
                continue
            devpairs.append(curtup)

    return devpairs

def lsnet(rootwin):
    tpath = '/sys/class/net'
    nports = []
    with os.scandir(tpath) as lndevs:
        pcire = re.compile('[0-9a-f]{4}:[0-9a-f]{2}:[0-9a-f]{2}\.[0-7]')
        for lndev in lndevs:
            pname = lndev.name
            if not lndev.is_symlink():
                continue
            tname = os.readlink(tpath+'/'+pname)
            usb = tname.find("usb")
            virtual = tname.find("virtual")
            pci = tname.find("/pci")
            if virtual != -1 or usb != -1 or pci == -1:
                continue

            slash = tname.rfind('/net')
            if slash == -1:
                continue
            tname = tname[:slash]

            pcihit = 0
            while pcihit == 0:
                slash = tname.rfind('/')
                nic = tname[slash+1:]
                res = pcire.match(nic)
                if not res or res.start() != 0 or res.end() != len(nic):
                    tname = tname[:slash]
                    continue
                pcihit = 1

            skip = 0
            for nport in nports:
                if nic == nport[0]:
                    skip = 1
                    break
            if skip == 1:
                continue
            nports.append((nic, pname))
    return nports

class MainWin(Gtk.Window):
    def port_changed(self, combo):
        label = None
        port = combo.get_active_text()
        for nic in self.nports:
            if nic[0] == port:
                sport = nic[1]
                break
        if combo == self.ovirt_port1:
            label = self.ovirt_port1_label
        elif combo == self.ovirt_port2:
            label = self.ovirt_port2_label
        elif combo == self.gluster_port1:
            label = self.gluster_port1_label
        elif combo == self.gluster_port2:
            label = self.gluster_port2_label
        label.set_text(sport)
        
    def __init__(self):
        super().__init__(title=_("Ovirt Installation Setup"))
        self.ks_info = {}
        
        grid = Gtk.Grid()
        grid.set_column_homogeneous(False)
        grid.set_row_homogeneous(False)
        grid.show()
        self.add(grid)

        label = Gtk.Label(label=_("  Host Name: "), halign=Gtk.Align.END)
        label.set_max_width_chars(20)
        label.show()
        grid.attach(label, 1, 0, 1, 1)
        self.hentry = Gtk.Entry()
        self.hentry.set_max_width_chars(12)
        self.hentry.show()
        grid.attach(self.hentry, 2, 0, 1, 1)
        row = 1

        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.show()
        grid.attach(sep, 0, row, 4, 1)
        row += 1
        sep = Gtk.Label(label=_("OS Root Disk"))
        sep.show()
        grid.attach(sep, 0, row, 4, 1)
        row += 1

        label = Gtk.Label(label=_('OS Disk:'), halign=Gtk.Align.END)
        label.show()
        grid.attach(label, 0, row, 1, 2)
        self.disks = lsdisk(self)
        self.seldsk1 = Gtk.ComboBoxText()
        self.seldsk1.set_entry_text_column(0)
        actnum = 0
        idx = 0
        for disk in self.disks:
            self.seldsk1.append_text(disk[0])
            if actnum == 0 and disk[0].find("nvme") != -1:
                actnum = idx
            idx += 1
        self.seldsk1.set_active(actnum)
        self.seldsk1.connect("changed", self.on_disk_changed)
        self.seldsk1.show()
        grid.attach(self.seldsk1, 1, row, 1, 1)
        self.ddev1 = Gtk.Entry()
        self.ddev1.set_text(self.disks[actnum][1])
        self.ddev1.set_max_width_chars(12)
        self.ddev1.set_editable(False)
        self.ddev1.show()
        grid.attach(self.ddev1, 2, row, 2, 1)
        row += 1

        self.seldsk2 = Gtk.ComboBoxText()
        self.seldsk2.set_entry_text_column(0)
        for disk in self.disks:
            self.seldsk2.append_text(disk[0])
        self.seldsk2.set_active(0)
        self.seldsk2.connect("changed", self.on_disk_changed)
        self.seldsk2.show()
        grid.attach(self.seldsk2, 1, row, 1, 1)
        self.ddev2 = Gtk.Entry()
        self.ddev2.set_text(self.disks[0][1])
        self.ddev2.set_max_width_chars(12)
        self.ddev2.set_editable(False)
        self.ddev2.show()
        grid.attach(self.ddev2, 2, row, 2, 1)
        row += 1

        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.show()
        grid.attach(sep, 0, row, 4, 1)
        row += 1
        sep = Gtk.Label(label=_("\nOvirt Management Network"))
        sep.show()
        grid.attach(sep, 0, row, 4, 1)
        row += 1

        self.nports = lsnet(self)
        label = Gtk.Label(label=_('ovirt port:'), halign=Gtk.Align.END)
        label.show()
        grid.attach(label, 0, row, 1, 2)

        self.ovirt_port1 = Gtk.ComboBoxText()
        self.ovirt_port1.set_entry_text_column(0)
        for port in self.nports:
            self.ovirt_port1.append_text(port[0])
        sel = 0
        self.ovirt_port1.set_active(sel)
        self.ovirt_port1.show()
        grid.attach(self.ovirt_port1, 1, row, 1, 1)
        self.ovirt_port1.connect("changed", self.port_changed)
        self.ovirt_port1_label = Gtk.Label(label=self.nports[sel][1], halign=Gtk.Align.START)
        self.ovirt_port1_label.set_max_width_chars(12)
        self.ovirt_port1_label.show()
        grid.attach(self.ovirt_port1_label, 2, row, 1, 1)

        self.ovirt_ip = Gtk.Entry()
        self.ovirt_ip.set_text("192.168.98.1")
        self.ovirt_ip.show()
        grid.attach(self.ovirt_ip, 3, row, 1, 2)
        row += 1

        self.ovirt_port2 = Gtk.ComboBoxText()
        self.ovirt_port2.set_entry_text_column(0)
        for port in self.nports:
            self.ovirt_port2.append_text(port[0])
        if len(self.nports) > 1:
            sel = 1
            self.ovirt_port2.set_active(1)
        else:
            sel = 0
            self.ovirt_port2.set_active(0)
        grid.attach(self.ovirt_port2, 1, row, 1, 1)
        self.ovirt_port2.show()
        self.ovirt_port2.connect("changed", self.port_changed)
        self.ovirt_port2_label = Gtk.Label(label=self.nports[sel][1], halign=Gtk.Align.START)
        self.ovirt_port2_label.set_max_width_chars(12)
        self.ovirt_port2_label.show()
        grid.attach(self.ovirt_port2_label, 2, row, 1, 1)
        row += 1

        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.show()
        grid.attach(sep, 0, row, 4, 1)
        row += 1
        sep = Gtk.Label(label=_("\nGlusterFS Network"))
        sep.show()
        grid.attach(sep, 0, row, 4, 1)
        row += 1

        label = Gtk.Label(label=_('gluster port:'), halign=Gtk.Align.END)
        label.show()
        grid.attach(label, 0, row, 1, 2)

        self.gluster_port1 = Gtk.ComboBoxText()
        self.gluster_port1.set_entry_text_column(0)
        for port in self.nports:
            self.gluster_port1.append_text(port[0])
        sel = 0
        self.gluster_port1.set_active(sel)
        self.gluster_port1.show()
        grid.attach(self.gluster_port1, 1, row, 1, 1)
        self.gluster_port1.connect("changed", self.port_changed)
        self.gluster_port1_label = Gtk.Label(label=self.nports[sel][1], halign=Gtk.Align.START)
        self.gluster_port1_label.show()
        grid.attach(self.gluster_port1_label, 2, row, 1, 1)

        self.gluster_ip = Gtk.Entry()
        self.gluster_ip.set_text("192.168.99.1")
        self.gluster_ip.show()
        grid.attach(self.gluster_ip, 3, row, 1, 2)
        row += 1

        self.gluster_port2 = Gtk.ComboBoxText()
        self.gluster_port2.set_entry_text_column(0)
        for port in self.nports:
            self.gluster_port2.append_text(port[0])
        if len(self.nports) > 1:
            self.gluster_port2.set_active(1)
            sel = 1
        else:
            self.gluster_port2.set_active(0)
            sel = 0
        self.gluster_port2.show()
        grid.attach(self.gluster_port2, 1, row, 1, 1)
        self.gluster_port2.connect("changed", self.port_changed)
        self.gluster_port2_label = Gtk.Label(label=self.nports[sel][1], halign=Gtk.Align.START)
        self.gluster_port2_label.show()
        grid.attach(self.gluster_port2_label, 2, row, 1, 1)
        row += 1

        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.show()
        grid.attach(sep, 0, row, 4, 1)
        row += 1
        hbox = Gtk.Box(spacing=10)
        hbox.show()
        grid.attach(hbox, 0, row, 4, 1)
        row += 1

        but = Gtk.Button.new_with_label(_("OK"))
        but.connect("clicked", self.ok_clicked)
        but.show()
        hbox.pack_start(but, True, True, 0)
        but = Gtk.Button.new_with_label(_("Cancel"))
        but.connect("clicked", Gtk.main_quit)
        but.show()
        hbox.pack_start(but, True, True, 0)

    def check_data(self):
        hostname = self.hentry.get_text()
        fqnre = re.compile('[a-z][_a-z0-9]{3,7}')
        res = fqnre.match(hostname)
        if not res or res.start() != 0 or res.end() != len(hostname):
            echo = EchoInfo(self, _("Invalid Host Name"))
            echo.run()
            echo.destroy()
            return False

        disk1 = self.seldsk1.get_active_text()
        disk2 = self.seldsk2.get_active_text()
        if disk1 == 'None' and disk2 == 'None':
            echo = EchoInfo(self, _("At lease one disk must be selected as root disk"))
            echo.run()
            echo.destroy()
            return False
        if disk1 == disk2:
            echo = EchoInfo(self, _("Two disks for the rootfs cannot be the same"))
            echo.run()
            echo.destroy()
            return False
        if disk1 != 'None' and disk2 != 'None':
            echo = EchoInfo(self, _("Disk mirror for rootfs is currently not supported"))
            echo.run()
            echo.destroy()
            return False
        
        ovirt_port1 = self.ovirt_port1.get_active_text()
        ovirt_port2 = self.ovirt_port2.get_active_text()
        gluster_port1 = self.gluster_port1.get_active_text()
        gluster_port2 = self.gluster_port2.get_active_text()
        ports_used = [ovirt_port1, ovirt_port2, gluster_port1, gluster_port2]
        ports_set = set(ports_used)
        if ovirt_port1 == ovirt_port2 or gluster_port1 == gluster_port2:
            echo = EchoInfo(self, _("Two NIC ports of one team cannot be the same"))
            echo.run()
            echo.destroy()
            return False
        if len(ports_used) > len(ports_set):
            echo = EchoInfo(self, _("No NIC ports can be used twice"))
            echo.run()
            echo.destroy()
            return False
        ovirt_ip = self.ovirt_ip.get_text()
        ipre = re.compile('([0-9]+\.){3}[0-9]+')
        match = ipre.match(ovirt_ip)
        if not match or match.start() != 0 or match.end() != len(ovirt_ip):
            echo = EchoInfo(self, _("Invalid Ovirt Management IP"))
            echo.run()
            echo.destroy()
            return False
        gluster_ip = self.gluster_ip.get_text()
        match = ipre.match(gluster_ip)
        if not match or match.start() != 0 or match.end() != len(gluster_ip):
            echo = EchoInfo(self, _("Invalid Gluster IP"))
            echo.run()
            echo.destroy()
            return False
        return True

    def ok_clicked(self, widget):
        if not self.check_data():
            print("Check Failed")
        hostname = self.hentry.get_text()

        disk1 = self.seldsk1.get_active_text()
        disk2 = self.seldsk2.get_active_text()
        if disk1 != 'None':
            disk = disk1
        elif disk2 != 'None':
            disk = disk2

        ovirt_port1 = self.ovirt_port1.get_active_text()
        ovirt_port2 = self.ovirt_port2.get_active_text()
        ovirt_ip = self.ovirt_ip.get_text()

        gluster_port1 = self.gluster_port1.get_active_text()
        gluster_port2 = self.gluster_port2.get_active_text()
        gluster_ip = self.gluster_ip.get_text()
        self.ks_info = {"hostname": hostname, "rootdisk": disk,
                "ovirt": {"ip": ovirt_ip, "port1": ovirt_port1, "port2": ovirt_port2},
                "gluster": {"ip": gluster_ip, "port1": gluster_port1, "port2": gluster_port2}
                }
        self.set_sensitive(False)
        wcursor = Gdk.Cursor(Gdk.CursorType.WATCH)
        self.get_window().set_cursor(wcursor)
        self.task = Process_KS(self)
        self.task.start()
        GLib.idle_add(self.check_task)

    def check_task(self):
        if not self.task:
            return False
        if self.task.is_alive():
            time.sleep(0.3)
            return True
        self.task.join()
        self.task = None
        self.get_window().set_cursor(self.cursor)
        self.set_sensitive(True)
        echo = EchoInfo(self, _("Task Ended"));
        echo.run()
        echo.destroy()
        Gtk.main_quit()

    def on_disk_changed(self, combo):
        text = combo.get_active_text()
        if text:
            for disk in self.disks:
                if text == disk[0]:
                    break
            if combo == self.seldsk1:
                self.ddev1.set_text(disk[1])
            else:
                self.ddev2.set_text(disk[1])

    def task_error(self, mesg):
        echo = EchoInfo(self, mesg)
        echo.run()
        echo.destroy()
        Gtk.main_quit()

win = MainWin()
win.show()
win.connect("destroy", Gtk.main_quit)
res = subp.run("sudo ls", shell=True, text=True, stdout=subp.PIPE, stderr=subp.STDOUT)
win.cursor = win.get_window().get_cursor()
if res.returncode == 0:
    Gtk.main()
else:
    win.destroy()
exit(0)
