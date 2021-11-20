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

def get_ostype():
    ostype = 'Unknown'
    with open('/etc/os-release', 'r') as os:
        for line in os:
            idx = line.find('ID=')
            if idx != 0:
                continue
            line = line.rstrip('\n')
            ostype = line[3:]
            break
    return ostype

def xorriso(isotop, **kargs):
    if not os.path.isdir(isotop):
        return False
    if not kargs["label"]:
        label = "ISO DSCAO"
    else:
        label = kargs["label"]

    ostype = get_ostype()
    if ostype == 'debian':
        isolxbin = '/usr/lib/ISOLINUX/isolinux.bin'
        efiimage = 'boot/grub/efi.img'
        hdpfxbin = '/usr/lib/ISOLINUX/isohdpfx.bin'
    elif ostype == 'fedora':
        isolxbin = '/usr/share/syslinux/isolinux.bin'
        efiimage = 'images/efiboot.img'
        hdpfxbin = '/usr/share/syslinux/isohdpfx.bin'
    else:
        return False
    isolinux_bin = isotop + '/isolinux/isolinux.bin'
    os.chmod(isolinux_bin, 0o644)

    if kargs["iso"] != 'None':
        isoout = '-'
        isofile = '/dev/' + kargs["iso"]
    else:
        isoout = '/tmp/hybrid.iso'
        try:
            if os.path.isfile(isoout):
                os.remove(isoout)
        except:
            return (10, "Cannot remove file: "+isoout)

    cmd = 'xorriso -as mkisofs -r -volid "' + label + '"'
    cmd += ' -isohybrid-mbr ' + hdpfxbin
    cmd += ' -b isolinux/isolinux.bin -c isolinux/boot.cat -boot-load-size 4'
    cmd += ' -boot-info-table -no-emul-boot  -eltorito-alt-boot'
    cmd += ' -e ' + efiimage + ' -no-emul-boot -isohybrid-gpt-basdat'
    cmd += ' -o ' + isoout + ' ' + isotop
    if isoout == '-':
        cmd += '| dd obs=128K oflag=direct conv=nocreat of=' + isofile
    print(cmd)
    res = subp.run(cmd, shell=True, text=True, stdout=subp.PIPE, stderr=subp.STDOUT)
    print(res.stdout)
    if res.returncode == 0:
        shutil.rmtree(isotop)
    return (res.returncode, res.stdout)

ks_text = """#use command line install mode
graphical
#vnc --port=8001
# accept license
eula --agreed
# System authorization information
auth --enableshadow --passalgo=sha512
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
network --device=public --activate --bootproto=static --ip=$public_ip --netmask=255.255.255.0 --nodefroute --nodns --noipv6 --teamslaves="$pport1'{\\"prio\\":-10, \\"sticky\\": true}',$pport2'{\\"prio\\":100}'" --teamconfig="{\\"runner\\": {\\"name\\": \\"activebackup\\"}}"
network --device=ovirt --bootproto=static --ip=$ovirt_ip --netmask=255.255.255.0 --nodefroute --nodns --noipv6 --teamslaves="$oport1'{\\"prio\\":-10, \\"sticky\\": true}',$oport2'{\\"prio\\":100}'" --teamconfig="{\\"runner\\": {\\"name\\": \\"activebackup\\"}}"
network --device=gluster --bootproto=static --ip=$gluster_ip --netmask=255.255.255.0 --nodefroute --nodns --noipv6 --teamslaves="$gport1'{\\"prio\\":-10, \\"sticky\\": true}',$gport2'{\\"prio\\":100}'" --teamconfig="{\\"runner\\": {\\"name\\": \\"activebackup\\"}}"
network --hostname=$namezeus

# ignore all other disks
ignoredisk --only-use=$rootdisk
# System bootloader configuration
bootloader --append="nopti noibrs noibpb crashkernel=auto" --location=mbr --boot-drive=$rootdisk
# Partition clearing information
zerombr
clearpart --drives=$rootdisk --initlabel 
# Disk partitioning information
autopart --type=thinp

# Use Live Image installation media
liveimg --url=file:///run/install/repo/ovirt-node-ng-image.squashfs.img

%post --erroronfail

[ -d /etc/multipath/conf.d ] || mkdir -p /etc/multipath/conf.d
cat > /etc/multipath/conf.d/49-usb_cdrom.conf <<EOD
blacklist {
	property "ID_USB_INTERFACE_NUM"
	property "ID_CDROM"
}
EOD
cat > /etc/multipath/conf.d/10-nvme.conf <<EOD
blacklist {wwid 1234567890
}
EOD

mkdir /var/log/journal

sed -i -e '$a127.0.1.1\\t$namezeus\\n' /etc/hosts
sed -i $sedcmd /etc/ntp.conf

imgbase layout --init

%end

%anaconda
pwpolicy root --minlen=6 --minquality=1 --notstrict --nochanges --notempty
pwpolicy user --minlen=6 --minquality=1 --notstrict --nochanges --emptyok
pwpolicy luks --minlen=6 --minquality=1 --notstrict --nochanges --notempty
%end
"""
def remove_vg(disk):
    vgres = subp.run('sudo vgdisplay  -c', shell=True, text=True, stdout=subp.PIPE, stderr=subp.PIPE)
    for vg in vgres.stdout.split('\n'):
        if len(vg) == 0:
            continue
        vgname = vg.split(':')[0]
        findpv = subp.run('sudo vgdisplay -v ' + vgname, shell=True, text=True, stdout=subp.PIPE, stderr=subp.PIPE)
        if findpv.returncode != 0:
            print(findpv.stderr)
            continue
        pvdisks = []
        for pvinfo in findpv.stdout.split('\n'):
            if pvinfo.find('PV Name') == -1:
                continue
            pvname = pvinfo.split()[-1]
            if pvname.find(disk) == -1:
                continue
            pvdisks.append(pvname)
        if len(pvdisks) == 0:
            continue
        vgchg = subp.run('sudo vgchange -a n ' + vgname, shell=True, text=True, stdout=subp.PIPE, stderr=subp.PIPE)
        if vgchg.returncode != 0:
            print(vgchg.stderr)
            continue
        vgrm = subp.run('sudo vgremove --force ' + vgname, shell=True, text=True, stdout=subp.PIPE, stderr=subp.PIPE)
        if vgrm.returncode != 0:
            print(vgrm.stderr)
            continue
        for pvdisk in pvdisks:
            pvrm = subp.run('sudo pvremove ' + pvdisk, shell=True, text=True, stdout=subp.PIPE, stderr=subp.PIPE)
            if pvrm.returncode != 0:
                print(pvrm.stderr)

def wipe_disk(disks, dsk):
    found = 0
    for disk in disks:
        if dsk != disk[0]:
            continue
        found = 1
    if found == 0:
        return

    remove_vg(disk[1])
    fd = os.open(disk[1], os.O_WRONLY)
    if fd >= 0:
        buf = b'\000'*(256*1024)
        for i in range(16384):
            os.write(fd, buf)
        os.close(fd)
        os.sync()
        print(f'Disk {disk[1]} cleaned')

def getnet(nicpci):
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
 
def getdisk(dsk):
    dpath = '/dev/md/' + dsk
    if os.path.islink(dpath):
        return 'md/'+dsk
    dpath = '/dev/disk/by-path/' + dsk
    tname = os.readlink(dpath)
    slash = tname.rfind('/')
    tname = tname[slash+1:]
    return tname

class Process_KS(threading.Thread):
    def __init__(self, mwin):
        self.win = mwin
        super().__init__()

    def run(self):
        global ks_text
        ovirt_iso = 'ovirt-node-install.iso'
        ovirt_iso_path = '/run/initramfs/live/LiveOS/' + ovirt_iso
        with open(ovirt_iso_path, "rb") as isoh:
            isoh.seek(0x8028, 0)
            isolabel = isoh.read(32).decode('utf-8').rstrip()
        srcmnt = "/tmp/ovirt_src"
        os.mkdir(srcmnt, mode=0o755)
        res = subp.run("sudo mount -o ro "+ovirt_iso_path+" "+srcmnt,
                shell=True, text=True, stdout=subp.PIPE, stderr=subp.STDOUT)
        if res.returncode != 0:
            os.rmdir(srcmnt)
            GLib.idle_add(self.win.task_error, _("Operation Failed\n")+res.stdout)
            return
        isodir = "/tmp/isotop-"+str(os.getpid())
        copyfailed = False
        try:
            shutil.copytree(srcmnt, isodir, symlinks=True)
        except:
            copyfailed = True
        subp.run("sudo umount " + srcmnt, shell=True, text=True, stdout=subp.PIPE, stderr=subp.STDOUT)
        os.rmdir(srcmnt)
        if copyfailed:
            shutil.rmtree(isodir)
            GLib.idle_add(self.win.task_error, _("Operation Failed\n"))
            return

        kscfg = isodir + "/interactive-defaults.ks"
        os.chmod(kscfg, 0o644)
        ks_text = ks_text.replace("$namezeus", self.win.ks_info["hostname"])
        ks_text = ks_text.replace("$ovirt_ip", self.win.ks_info["ovirt"]["ip"])
        ks_text = ks_text.replace("$gluster_ip", self.win.ks_info["gluster"]["ip"])
        ks_text = ks_text.replace("$public_ip", self.win.ks_info["public"]["ip"])
        rootdisk = self.win.ks_info["rootdisk"]
        ks_text = ks_text.replace("$rootdisk", rootdisk)
        ks_text = ks_text.replace("$oport1", self.win.ks_info["ovirt"]["port1"])
        ks_text = ks_text.replace("$oport2", self.win.ks_info["ovirt"]["port2"])
        ks_text = ks_text.replace("$gport1", self.win.ks_info["gluster"]["port1"])
        ks_text = ks_text.replace("$gport2", self.win.ks_info["gluster"]["port2"])
        ks_text = ks_text.replace("$pport1", self.win.ks_info["public"]["port1"])
        ks_text = ks_text.replace("$pport2", self.win.ks_info["public"]["port2"])

        nvme_wwids = []
        rdsk = '/dev/' + rootdisk
        if os.path.islink(rdsk):
            rdsk = os.readlink(rdsk)
            rslash = rdsk.rfind('/')
            if rslash != -1:
                rdsk = rdsk[rslash+1:]
        if rdsk.startswith('/dev/sd'):
            res = subp.run('sudo /lib/udev/scsi_id -gus3 ' + rdsk, shell=True, text=True, stdout=subp.PIPE, stderr=subp.PIPE)
            if res.returncode == 0 and len(res.stdout) > 0:
                nvme_wwids.append(res.stdout)
        with os.scandir('/sys/block') as blkdirs:
            for blkdir in blkdirs:
                devnam = blkdir.name
                if not devnam.startswith('nvme'):
                    continue
                wwid_file = '/sys/block/'+devnam+'/wwid'
                if not os.path.isfile(wwid_file):
                    continue
                wwid = ''
                with open(wwid_file) as fin:
                    wwid = fin.read().rstrip('\n')
                if len(wwid) > 0:
                    nvme_wwids.append(wwid)
        repl_string = ''
        for wwid in nvme_wwids:
            repl_string += '\n\twwid ' + wwid
        ks_text = ks_text.replace('wwid 1234567890', repl_string)

        idx = 0
        row = self.win.ntplist.get_row_at_index(idx)
        sedcmd = '-e \'/^server [0-9]/d\' '
        ntpsvrs = ''
        while row:
            label = row.get_children()[0]
            svr = label.get_text()
            ntpsvrs += 'server ' + svr + ' iburst\\n'
            idx += 1
            row = self.win.ntplist.get_row_at_index(idx)
        if idx > 0:
            sedcmd += '-e \'/^#manycastclient/a' + ntpsvrs + '\' '
        sedcmd += '-e \'$a#\\n# use local clock\\nserver 127.127.1.0\\nfudge 127.127.1.0 stratum 10\\n\''
        ks_text = ks_text.replace("$sedcmd", sedcmd);

        with open(kscfg, "w") as ksfile:
            ksfile.write(ks_text)

        destiso = self.win.ks_info["usbdisk"]
        self.res = xorriso(isodir, iso=destiso, label=isolabel)

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
    slaves = []
    devpairs = [('None', 'None')]
    tpath = '/dev/md'
    if os.path.isdir(tpath):
        with os.scandir(tpath) as lndevs:
            for lndev in lndevs:
                pname = lndev.name
                if not lndev.is_symlink():
                    continue
                tname = os.readlink(tpath + '/' + pname)
                slash = tname.rfind('/')
                if slash != -1:
                    tname = tname[slash+1:]
                sizfile = '/sys/block/'+tname+'/size'
                if not os.path.isfile(sizfile):
                    continue
                with open(sizfile, 'r') as fin:
                    fsize = int(fin.read())
                if fsize < 33554432:
                    continue
                with os.scandir('/sys/block/'+tname+'/slaves') as subors:
                    for slave in subors:
                        if slave in slaves:
                            continue
                        slaves.append(slave.name)
                curtup = (pname, '/dev/'+tname)
                skip = 0
                for tup in devpairs:
                    if tup[1] == curtup[1]:
                        skip = 1
                        break
                if skip == 1:
                    continue
                devpairs.append(curtup)

    tpath = '/dev/disk/by-path'
    with os.scandir(tpath) as lndevs:
        for lndev in lndevs:
            pname = lndev.name
            if not lndev.is_symlink():
                continue
            usb = pname.find("usb")
            if usb != -1:
                continue
            if iscdrom(tpath+'/'+pname, rootwin):
                continue

            tname = os.readlink(tpath+'/'+pname)
            slash = tname.rfind('/')
            if slash != -1:
                tname = tname[slash+1:]
            sizfile = '/sys/block/'+tname+'/size'
            if not os.path.isfile(sizfile):
                continue
            if tname in slaves:
                continue
            with open(sizfile, 'r') as fin:
                fsize = int(fin.read())
            if fsize < 33554432:
                continue
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

def lsusb_disk(rootwin):
    usbdisks = ['None']
    tpath = '/sys/block'
    mnts = []
    with open('/proc/mounts', 'r') as mounts:
        for mnt in mounts:
            if mnt.find('/dev/') != 0:
                continue
            mnts.append(mnt.split()[0])

    with os.scandir(tpath) as direntries:
        for lndev in direntries:
            devnam = lndev.name
            if not lndev.is_symlink():
                continue
            tname = os.readlink(tpath+'/'+devnam)
            if tname.find('/usb') == -1:
                continue
            if iscdrom('/dev/'+devnam, rootwin):
                continue
            mntpoint = 0
            for mnt in mnts:
                if mnt.find(devnam) == -1:
                    continue
                mntpoint = 1
                break
            if mntpoint == 0:
                usbdisks.append(devnam)
    return usbdisks

class MainWin(Gtk.Window):
    def ntpadd_clicked(self, button):
        svr = self.ntpentry.get_text()
        check = re.compile('([0-9]+\.){3}[0-9]+|([a-z][0-9a-z]*\.)*[a-z][0-9a-z]*')
        match = check.match(svr)
        if not match or match.start() != 0 or match.end() != len(svr):
            echo = EchoInfo(self, _("Invalid NTP address"))
            echo.run()
            echo.destroy()
            return
        idx = 0
        row = self.ntplist.get_row_at_index(idx)
        while row:
            label = row.get_children()[0]
            if svr == label.get_text():
                break
            idx += 1
            row = self.ntplist.get_row_at_index(idx)
        if row:
            return
        if idx == 3:
            echo = EchoInfo(self, _("Three Servers at Most!"))
            echo.run()
            echo.destroy()
            return
        row = Gtk.ListBoxRow()
        label = Gtk.Label(label=svr)
        label.show()
        row.add(label)
        row.show()
        self.ntplist.add(row)

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
        elif combo == self.public_port1:
            label = self.public_port1_label
        elif combo == self.public_port2:
            label = self.public_port2_label
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
        grid.attach(label, 0, 0, 1, 1)
        self.hentry = Gtk.Entry()
        self.hentry.set_max_width_chars(12)
        self.hentry.show()
        grid.attach(self.hentry, 1, 0, 1, 1)
        label = Gtk.Label(label=_("USB Media: "))
        label.show()
        grid.attach(label, 2, 0, 1, 1)
        self.usbmedia = Gtk.ComboBoxText()
        self.usbmedia.set_entry_text_column(0)
        usbdisks = lsusb_disk(self)
        idx = -1
        for usbdsk in usbdisks:
            idx += 1
            self.usbmedia.append_text(usbdsk)
        self.usbmedia.set_active(idx)
        grid.attach(self.usbmedia, 3, 0, 1, 1)
        self.usbmedia.show()

        row = 1

        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.show()
        grid.attach(sep, 0, row, 4, 1)
        row += 1
        sep = Gtk.Label(label=_("\nOS Root Disk"))
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
        sel += 1
        for port in self.nports:
            self.ovirt_port2.append_text(port[0])
        if len(self.nports) <= sel:
            sel = 0
        self.ovirt_port2.set_active(sel)
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
        sel += 1
        if len(self.nports) <= sel:
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
        sel += 1
        for port in self.nports:
            self.gluster_port2.append_text(port[0])
        if len(self.nports) <= sel:
            sel = 0
        self.gluster_port2.set_active(sel)
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
        sep = Gtk.Label(label=_("\nPublic/Display Network: "))
        sep.show()
        grid.attach(sep, 0, row, 4, 1)
        row += 1

        label = Gtk.Label(label=_('public port:'), halign=Gtk.Align.END)
        label.show()
        grid.attach(label, 0, row, 1, 2)

        self.public_port1 = Gtk.ComboBoxText()
        self.public_port1.set_entry_text_column(0)
        for port in self.nports:
            self.public_port1.append_text(port[0])
        sel += 1
        if sel >= len(self.nports):
            sel = 0
        self.public_port1.set_active(sel)
        self.public_port1.show()
        grid.attach(self.public_port1, 1, row, 1, 1)
        self.public_port1.connect("changed", self.port_changed)
        self.public_port1_label = Gtk.Label(label=self.nports[sel][1], halign=Gtk.Align.START)
        self.public_port1_label.show()
        grid.attach(self.public_port1_label, 2, row, 1, 1)

        self.public_ip = Gtk.Entry()
        self.public_ip.set_text("0.0.0.0")
        self.public_ip.show()
        grid.attach(self.public_ip, 3, row, 1, 2)
        row += 1

        self.public_port2 = Gtk.ComboBoxText()
        self.public_port2.set_entry_text_column(0)
        sel += 1
        for port in self.nports:
            self.public_port2.append_text(port[0])
        if sel >= len(self.nports):
            sel = 0
        self.public_port2.set_active(sel)
        self.public_port2.show()
        grid.attach(self.public_port2, 1, row, 1, 1)
        self.public_port2.connect("changed", self.port_changed)
        self.public_port2_label = Gtk.Label(label=self.nports[sel][1], halign=Gtk.Align.START)
        self.public_port2_label.show()
        grid.attach(self.public_port2_label, 2, row, 1, 1)
        row += 1

        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.show()
        grid.attach(sep, 0, row, 4, 1)
        row += 1
        label = Gtk.Label(label=_("\nNTP Server Setup"))
        label.show()
        grid.attach(label, 0, row, 4, 1)
        row += 1

        label = Gtk.Label(label=_("NTP Server:"), halign=Gtk.Align.END)
        label.show()
        grid.attach(label, 0, row+1, 1, 1)
        self.ntplist = Gtk.ListBox()
        self.ntplist.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.ntplist.show()
        grid.attach(self.ntplist, 1, row, 1, 3)
        self.ntpentry = Gtk.Entry()
        self.ntpentry.set_width_chars(16)
        grid.attach(self.ntpentry, 3, row+1, 1, 1)
        self.ntpentry.show()
        self.ntpentry.connect("activate", self.ntpadd_clicked)
        but = Gtk.Button(label=_("<<Add"))
        grid.attach(but, 2, row+1, 1, 1)
        but.show()
        but.connect("clicked", self.ntpadd_clicked)
        row += 3

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
        public_ip = self.public_ip.get_text()
        match = ipre.match(public_ip)
        if not match or match.start() != 0 or match.end() != len(public_ip):
            echo = EchoInfo(self, _("Invalid Public IP"))
            echo.run()
            echo.destroy()
            return False
        return True

    def ok_clicked(self, widget):
        if not self.check_data():
            return
        hostname = self.hentry.get_text()
        usbstick = self.usbmedia.get_active_text()
        if usbstick == 'None':
            echo = Gtk.MessageDialog(transient_for=self,
                    flags=0, message_type=Gtk.MessageType.WARNING,
                    buttons=Gtk.ButtonsType.OK_CANCEL,
                    text=_("No USB Storage Selected"))
            echo.format_secondary_text(_("Scan USB Again?"))
            response = echo.run()
            if response == Gtk.ResponseType.OK:
                self.usbmedia.remove_all()
                usbdisks = lsusb_disk(self)
                idx = -1
                for usbdsk in usbdisks:
                    idx += 1
                    self.usbmedia.append_text(usbdsk)
                self.usbmedia.set_active(idx)
                echo.destroy()
                return
            echo.destroy()

        disk = 'None'
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

        public_port1 = self.public_port1.get_active_text()
        public_port2 = self.public_port2.get_active_text()
        public_ip = self.public_ip.get_text()

        self.ks_info = {"hostname": hostname, "rootdisk": getdisk(disk),
                "ovirt": {"ip": ovirt_ip, "port1": getnet(ovirt_port1), "port2": getnet(ovirt_port2)},
                "gluster": {"ip": gluster_ip, "port1": getnet(gluster_port1), "port2": getnet(gluster_port2)},
                "public": {"ip": public_ip, "port1": getnet(public_port1), "port2": getnet(public_port2)},
                "usbdisk": usbstick
                }
        self.set_sensitive(False)
        wcursor = Gdk.Cursor(Gdk.CursorType.WATCH)
        self.get_window().set_cursor(wcursor)
        self.wipe1 = threading.Thread(target=wipe_disk, args=(self.disks, disk))
        self.wipe1.start()
        self.task = Process_KS(self)
        self.task.start()
        GLib.idle_add(self.check_task)

    def check_task(self):
        if not self.task:
            return False
        if self.task.is_alive() or self.wipe1.is_alive():
            time.sleep(0.3)
            return True
        self.task.join()
        self.wipe1.join()

        if self.task.res[0] == 0:
            echo = EchoInfo(self, _("Task Ended"));
        else:
            echo = EchoInfo(self, _("Task Failed\n")+self.task.res[1])
        echo.run()
        echo.destroy()

        self.get_window().set_cursor(self.cursor)
        self.set_sensitive(True)
        self.task = None
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
