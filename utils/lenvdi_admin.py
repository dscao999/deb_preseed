#!/usr/bin/python3
#
import os
import subprocess as subproc
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

os.environ['SUDO_ASKPASS'] = '/usr/lib/ssh/x11-ssh-askpass'

citrix_file = '/usr/share/applications/selfservice.desktop'
vmware_file = '/usr/share/applications/vmware-view.desktop'
lidcc_file = '/usr/share/applications/lidc-client.desktop'

timeconf = '/etc/systemd/timesyncd.conf'

vdiadm = 'vdi-admin.sh'

def vdi_admin(action, **kargs):
    cmd = 'sudo -A ' + vdiadm
    if action == 'import_ca':
        cmd += ' --client=' + kargs["client"]
        cmd += ' --rootca=' + kargs["rootca"]
    elif action == 'setvdi':
        cmd += ' --sname=' + kargs["sname"]
        cmd += ' --sip=' + kargs["sip"]
    elif action == 'time_sync':
        cmd += ' --ntp="' + kargs["ntp"] + '"'
    elif action == 'set-hostname':
        cmd += ' --hostname=' + kargs["hostname"]
    else:
        print("Not a valid action")
        return

    cmd += ' ' + action
    res = subproc.run(cmd, stdout=subproc.PIPE, stderr=subproc.STDOUT,
            shell=True, text=True)
    return (res.returncode, res.stdout)

class EchoInfo(Gtk.MessageDialog):
    def __init__(self, rootwin, info):
        super().__init__(parent=rootwin,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text=info
                )


class CABox(Gtk.Box):
    def __init__(self, rootwin):
        super().__init__(spacing=6, orientation=Gtk.Orientation.VERTICAL)
        self.rootwin = rootwin

        hbox = Gtk.Box(spacing=5)
        hbox.show()
        self.pack_start(hbox, True, True, 0)
        label = Gtk.Label(label="Client: ")
        label.show()
        hbox.pack_start(label, True, True, 0)
        entry = Gtk.Entry()
        if os.path.isfile(citrix_file):
            self.client = 'citrix'
        elif os.path.isfile(vmware_file):
            self.client = 'vmware'
        elif os.path.isfile(lidcc_file):
            self.client = 'lidcc'
        else:
            self.client = 'unknown'
        entry.set_text(self.client)
        entry.set_editable(False)
        entry.show()
        hbox.pack_start(entry, True, True, 0)

        label = Gtk.Label(label="Please Select Your ROOT CA File")
        label.show()
        self.pack_start(label, True, True, 0)

        pemfilter = Gtk.FileFilter()
        pemfilter.set_name("PEM Files")
        pemfilter.add_pattern("*.pem")
        allfilter = Gtk.FileFilter()
        allfilter.set_name("All Files")
        allfilter.add_pattern("*")
        button = Gtk.FileChooserButton(title="Select the CA file")
        button.add_filter(pemfilter)
        button.add_filter(allfilter)
        button.show()
        button.connect("selection-changed", self.on_file_selected)
        self.pack_start(button, True, True, 0)

        self.cafile = ''
        self.exbutton = Gtk.Button(label="Import CA")
        self.exbutton.connect("clicked", self.on_import_clicked)
        if self.client == 'unknown' or not button.get_filename():
            self.exbutton.set_sensitive(False)
        self.exbutton.show()
        self.pack_start(self.exbutton, True, True, 0)

    def on_file_selected(self, widget):
        self.cafile = widget.get_filename()
        if self.cafile and len(self.cafile) > 0 and self.client != 'unknown':
            self.exbutton.set_sensitive(True)

    def on_import_clicked(self, widget):
        if self.client != 'lidcc' and self.client != 'citrix':
            dialog = Gtk.MessageDialog(
                    parent=self.rootwin,
                    flags=0,
                    message_type=Gtk.MessageType.INFO,
                    buttons=Gtk.ButtonsType.OK,
                    text="CA import for " + self.client + " not implemented yet"
                    )
            dialog.run()
            dialog.destroy()
            return
        if not os.path.isfile(self.cafile):
            return

        if self.client == 'citrix':
            cadir = '/opt/Citrix/ICAClient/keystore/cacerts/'
        elif self.client == 'lidcc':
            cadir = '/etc/ssl/certs/'
        elif self.client == 'vmware':
            cadir = '/etc/noexistent/'
        cafile = os.path.basename(self.cafile)
        if os.path.isfile(cadir + cafile):
            dialog = Gtk.MessageDialog(
                    parent=self.rootwin,
                    flags=0,
                    message_type=Gtk.MessageType.WARNING,
                    buttons=Gtk.ButtonsType.OK_CANCEL,
                    text="File Already Exists"
                    )
            dialog.format_secondary_text('Trusted CA File exits for ' + self.client + ". Overwrite?")
            resp = dialog.run()
            dialog.destroy()
            if resp == Gtk.ResponseType.CANCEL:
                    return

        res = vdi_admin("import_ca", client=self.client, rootca=self.cafile)
        if res[0] != 0:
            dialog = Gtk.MessageDialog(
                    parent=self.rootwin,
                    flags=0,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.CANCEL,
                    text="CA Import Failed"
                    )
            dialog.format_secondary_text(res[1])
            dialog.run()
            dialog.destroy()
        else:
            dialog = EchoInfo(self.rootwin, "CA Import Success!")
            dialog.run()
            dialog.destroy()

class TimerBox(Gtk.Box):
    def __init__(self, rootwin):
        super().__init__(spacing=6, orientation=Gtk.Orientation.VERTICAL)
        self.set_homogeneous(False)
        self.rootwin = rootwin
        label = Gtk.Label(label="Time Server Address")
        label.show()
        self.pack_start(label, True, True, 0)

        box = Gtk.Box()
        box.set_homogeneous(False)
        box.show()
        self.pack_start(box, True, True, 0)

        vbox1 = Gtk.VBox(spacing=11)
        vbox1.show()
        box.pack_start(vbox1, True, True, 0)
        vbox2 = Gtk.VBox()
        vbox2.show()
        box.pack_start(vbox2, False, False, 0)

        self.ip_entry = Gtk.Entry()
        self.ip_entry.show()
        vbox1.pack_start(self.ip_entry, False, False, 0)
        but = Gtk.Button(label="Add")
        but.connect("clicked", self.add_ip)
        but.show()
        vbox2.pack_start(but, False, False, 0)

        self.ip_list = Gtk.ListBox()
        self.ip_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.ip_list.show()
        sips = []
        with open(timeconf, "r") as fin:
            for ln in fin:
                recs = ln.split('=')
                if recs[0] == 'NTP':
                    sips = recs[1].split()
                    break
 
        numrow = 0
        for sip in sips:
            row = Gtk.ListBoxRow()
            label = Gtk.Label(label=sip)
            label.show()
            row.add(label);
            row.show()
            self.ip_list.add(row)
            numrow += 1

        vbox1.pack_start(self.ip_list, True, True, 0)
        but = Gtk.Button(label="Remove")
        but.connect("clicked", self.remove_ip)
        but.show()
        vbox2.pack_start(but, False, False, 0)

        but = Gtk.Button(label="Save")
        but.show()
        but.connect("clicked", self.save_config)
        self.pack_start(but, True, True, 0)

    def add_ip(self, but): 
        ip = self.ip_entry.get_text()
        if len(ip) == 0:
            return
        label = None
        idx = 0
        row = self.ip_list.get_row_at_index(idx)
        while row:
            label = row.get_children()[0]
            if ip == label.get_text():
                break
            idx += 1
            row = self.ip_list.get_row_at_index(idx)

        if row:
            return

        row = Gtk.ListBoxRow()
        label = Gtk.Label(label=ip)
        label.show()
        row.add(label)
        row.show()
        self.ip_list.add(row)

    def remove_ip(self, but):
        sel = self.ip_list.get_selected_row()
        if sel:
            self.ip_list.remove(sel)

    def save_config(self, but):
        ntp_line = ''
        idx = 0
        row = self.ip_list.get_row_at_index(idx)
        while row:
            label = row.get_children()[0]
            ip = label.get_text()
            if len(ntp_line) > 0:
                ntp_line += ' '
            ntp_line += ip
            idx += 1
            row = self.ip_list.get_row_at_index(idx)
        res = vdi_admin('time_sync', ntp=ntp_line)
        if res[0] != 0:
            dialog = Gtk.MessageDialog(
                    parent=self.rootwin,
                    flags=0,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.CANCEL,
                    text="Failed to change /etc/systemd/timesyncd.conf"
                    )
            dialog.format_secondary_text(res[1])
            dialog.run()
            dialog.destroy()
        else:
            dialog = EchoInfo(self.rootwin, "/etc/systemd/timesyncd.conf Changed.")
            dialog.run()
            dialog.destroy()

def get_hostname():
    cmd = 'hostnamectl --static'
    res = subproc.run(cmd, stdout=subproc.PIPE, stderr=subproc.STDOUT,
            shell=True, text=True)
    return res.stdout.rstrip('\n')

class HostBox(Gtk.Box):
    def set_hostname(self, but):
        newname = self.hostname.get_text()
        if newname == self.cur_hostname:
            dialog = EchoInfo(self.rootwin, "No Change in Hostname, Ignored")
            dialog.run()
            dialog.destroy()
            return
        res = vdi_admin('set-hostname', hostname=newname);
        if res[0] != 0:
            dialog = Gtk.MessageDialog(
                    parent=self.rootwin,
                    flags=0,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.CANCEL,
                    text="Fail to Change host name"
                    )
            dialog.format_secondary_text(res[1])
            dialog.run()
            dialog.destroy()
        else:
            dialog = EchoInfo(self.rootwin, "hostname changed to: "+newname)
            dialog.run()
            dialog.destroy()

    def __init__(self, rootwin):
        super().__init__(spacing=6, orientation=Gtk.Orientation.VERTICAL)
        self.set_homogeneous(False)
        self.rootwin = rootwin

        box = Gtk.Box(spacing=6)
        box.show()
        self.pack_start(box, True, True, 0)

        label = Gtk.Label(label="Host Name: ")
        label.show()
        box.pack_start(label, True, True, 0)
        self.cur_hostname = get_hostname()
        self.hostname = Gtk.Entry(text=self.cur_hostname)
        self.hostname.set_width_chars(24)
        self.hostname.show()
        box.pack_start(self.hostname, True, True, 0)

        box = Gtk.Box(spacing=6)
        box.show()
        self.pack_start(box, True, True, 0)
        but = Gtk.Button(label="Set")
        but.connect("clicked", self.set_hostname)
        but.show()
        box.pack_start(but, True, True, 0)

class VDIBox(Gtk.Box):
    def __init__(self, rootwin):
        super().__init__(spacing=6, orientation=Gtk.Orientation.VERTICAL)
        self.set_homogeneous(False)
        self.rootwin = rootwin

        box = Gtk.Box(spacing=6)
        box.show()
        self.pack_start(box, True, True, 0)
        label = Gtk.Label(label="Server Name(FQDN): ")
        label.show()
        box.pack_start(label, True, True, 0)
        self.name_entry = Gtk.Entry()
        self.name_entry.set_width_chars(24)
        self.name_entry.show()
        box.pack_start(self.name_entry, True, True, 0)

        box = Gtk.Box(spacing=6)
        box.show()
        self.pack_start(box, True, True, 0)
        label = Gtk.Label(label="Service IP: ")
        label.set_max_width_chars(20)
        label.show()
        box.pack_start(label, True, True, 0)
        self.ip_entry = Gtk.Entry()
        self.ip_entry.set_width_chars(16)
        self.ip_entry.show()
        box.pack_start(self.ip_entry, True, True, 0)

        box = Gtk.Box(spacing=6)
        box.show()
        self.pack_start(box, True, True, 0)
        self.dns_chkbox = Gtk.CheckButton(label="Use DNS")
        self.dns_chkbox.connect("toggled", self.dns_toggled)
        self.dns_chkbox.set_active(False)
        self.use_dns = False
        self.dns_chkbox.show()
        box.pack_start(self.dns_chkbox, True, True, 0)
        but = Gtk.Button(label="Save")
        but.connect("clicked", self.save_service_ip)
        but.show()
        box.pack_start(but, True, False, 0)

    def dns_toggled(self, but):
        if but.get_active():
            self.use_dns = True
            self.ip_entry.set_editable(False)
            self.name_entry.set_editable(False)
        else:
            self.use_dns = False
            self.ip_entry.set_editable(True)
            self.name_entry.set_editable(True)

    def save_service_ip(self, but):
        if self.use_dns:
            return
        svrname = self.name_entry.get_text()
        ip = self.ip_entry.get_text()
        if not svrname or not ip:
            return

        with open("/etc/hosts", "r") as fin:
            for ln in fin:
                recs = ln.split()
                if len(recs) == 0 or recs[0][0] == '#':
                    continue
                if recs[1] and recs[1] == svrname:
                    dialog = Gtk.MessageDialog(
                            parent=self.rootwin,
                            flags=0,
                            message_type=Gtk.MessageType.WARNING,
                            buttons=Gtk.ButtonsType.OK_CANCEL,
                            text=svrname + "Already exits"
                            )
                    dialog.format_secondary_text("Overwrite It?")
                    resp = dialog.run()
                    dialog.destroy()
                    if resp == Gtk.ResponseType.CANCEL:
                        return
                
        res = vdi_admin('setvdi', sname=svrname, sip=ip)
        if res[0] != 0:
            dialog = Gtk.MessageDialog(
                    parent=self.rootwin,
                    flags=0,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.CANCEL,
                    text="Fail to Change /etc/hosts"
                    )
            dialog.format_secondary_text(res[1])
            dialog.run()
            dialog.destroy()
        else:
            dialog = EchoInfo(self.rootwin, "IP and FQDN added to /etc/hosts")
            dialog.run()
            dialog.destroy()


class MainWin(Gtk.Window):
    def __init__(self):
        super().__init__(title="LENVDI Admin")
        self.set_border_width(10)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(vbox)
        vbox.show()

        stack = Gtk.Stack()
        stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        stack.set_transition_duration(1000)
        stack.show()

        cabox = CABox(self)
        cabox.show()
        stack.add_titled(cabox, "catrust", "Import CA")

        vdibox = VDIBox(self)
        vdibox.show()
        stack.add_titled(vdibox, "svcset", "VDI Service")

        tmbox = TimerBox(self);
        tmbox.show()
        stack.add_titled(tmbox, "timerset", "Timer Sync")

        hostbox = HostBox(self);
        hostbox.show()
        stack.add_titled(hostbox, "sethost", "Set Hostname")

        stack_switcher = Gtk.StackSwitcher()
        stack_switcher.set_stack(stack)
        stack_switcher.show()

        vbox.pack_start(stack_switcher, True, True, 0)
        vbox.pack_start(stack, True, True, 0)

try:
    fd = os.open("/run/lock/lenvdi_admin.lock", os.O_WRONLY|os.O_CREAT|os.O_EXCL)
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
os.remove("/run/lock/lenvdi_admin.lock")
quit(0)
