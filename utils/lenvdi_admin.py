#!/usr/bin/python3
#
import os
import subprocess as subproc
import gi
import configparser

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

os.environ['SUDO_ASKPASS'] = '/usr/lib/ssh/x11-ssh-askpass'

citrix_file = '/usr/share/applications/selfservice.desktop'
vmware_file = '/usr/share/applications/vmware-view.desktop'
lidcc_file = '/usr/share/applications/lidc-client.desktop'

timeconf = '/etc/systemd/timesyncd.conf'

ovirt_trust = """#!/bin/bash
#
ROOTCA=$1
cp $ROOTCA /etc/ssl/certs/oVirt_root_ca.pem
idxname=$(openssl x509 -noout -in $ROOTCA -subject_hash)
cd /etc/ssl/certs
[ -L ${idxname}.0 ] && rm ${idxname}.0
ln -s oVirt_root_ca.pem ${idxname}.0
cd -
echo "Index: ${idxname}.0"
"""

citrix_trust = """#!/bin/bash
#
ROOTCA=$1
ICAROOT=/opt/Citrix/ICAClient
cp $ROOTCA $ICAROOT/keystore/cacerts
$ICAROOT/util/ctx_rehash
"""

def ca_import(rootca, script):
    tmpshell = '/tmp/' + 'import_ca.sh'
    with open(tmpshell, "w") as fout:
        fout.write(script)
    os.chmod(tmpshell, 0o755)
    cmd = 'sudo -A ' + tmpshell + ' ' + rootca
    res = subproc.run(cmd, stdout=subproc.PIPE, stderr=subproc.STDOUT, shell=True, text=True)
    os.remove(tmpshell)
    return (res.returncode, res.stdout)

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
        if len(self.cafile) > 0 and self.client != 'unknown':
            self.exbutton.set_sensitive(True)

    def on_import_clicked(self, widget):
        if self.client == 'lidcc':
            script = ovirt_trust
        elif self.client == 'citrix':
            script = citrix_trust
        else:
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

        res = ca_import(self.cafile, script)
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
        print('NTP='+ntp_line)
        cmd = '\'/^NTP=.*$/s//' + 'NTP=' + ntp_line + '/\''
        conf = '/etc/systemd/timesyncd.conf'
        res = subproc.run('sudo -A sed -e ' + cmd + ' ' + conf,
                shell=True, stdout=subproc.PIPE, stderr=subproc.STDOUT, text=True)
        if res.returncode != 0:
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

class MainWin(Gtk.Window):
    def __init__(self):
        super().__init__(title="LENVDI Admin")
        self.set_border_width(10)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(vbox)

        stack = Gtk.Stack()
        stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        stack.set_transition_duration(1000)

        cabox = CABox(self)
        cabox.show()
        stack.add_titled(cabox, "catrust", "Import CA")

        label = Gtk.Label()
        label.set_markup("<big>Set VDI Server Configuration</big>")
        stack.add_titled(label, "svcset", "VDI Service")

        tmbox = TimerBox(self);
        tmbox.show()
        stack.add_titled(tmbox, "timerset", "Timer Sync")

        stack_switcher = Gtk.StackSwitcher()
        stack_switcher.set_stack(stack)

        vbox.pack_start(stack_switcher, True, True, 0)
        vbox.pack_start(stack, True, True, 0)

win = MainWin()
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()
quit(0)
