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

ovirt_trust = """#!/bin/bash
#
ROOTCA=$1
#cp $ROOTCA /etc/ssl/certs/oVirt_root_ca.pem
idxname=$(openssl x509 -noout -in $ROOTCA -subject_hash)
cd /etc/ssl/certs
[ -L ${idxname}.0 ] && rm ${idxname}.0
#ln -s oVirt_root_ca.pem ${idxname}.0
cd -
echo "Index: ${idxname}.0"
exit 1
"""

citrix_trust = """#!/bin/bash
#
ROOTCA=$1
ICAROOT=/opt/Citrix/ICAClient
echo cp $ROOTCA $ICAROOT/keystore/cacerts
echo $ICAROOT/util/ctx_rehash
exit 1
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
        stack.add_titled(label, "svcset", "VDI Server")

        label = Gtk.Label()
        label.set_markup("<big>Set Time Syncronization</big>")
        stack.add_titled(label, "timesync", "Time Sync")

        stack_switcher = Gtk.StackSwitcher()
        stack_switcher.set_stack(stack)

        vbox.pack_start(stack_switcher, True, True, 0)
        vbox.pack_start(stack, True, True, 0)

win = MainWin()
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()
quit(0)
