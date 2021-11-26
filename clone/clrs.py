#!/usr/bin/python3
#
import gi
import locale
import gettext
import re
import getpass
import subprocess as subp
import os
import shutil

import netutils

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

dir_prefix = '/var/www/html/clone'

pxelinux = """default clone
say Booting for LIOS clone/restore
prompt 0
timeout 30
label clone
    menu label clone
    kernel linux
    append vga=788 initrd=initrd-clone.gz auto url=http://$SERVER/clone/preseed-net-clone.cfg
"""
conn = """ACTION=$ACTION
USER=$USER
SERVER=$SERVER
DEPOT=$DEPOT
KEY=$PRVKEY
"""

username = getpass.getuser()
homedir = os.environ['HOME']

class EchoInfo(Gtk.MessageDialog):
    def __init__(self, rootwin, info):
        super().__init__(parent=rootwin,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text=info
                )

class MWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title=_("LIOS Clone/Restore"))
        self.set_border_width(10)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        self.add(vbox)
        vbox.show()

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        vbox.pack_start(hbox, True, True, 10)
        hbox.show()
        self.clone_but = Gtk.RadioButton.new_with_label_from_widget(None, _("Clone"))
        hbox.pack_start(self.clone_but, True, True, 10)
        self.clone_but.show()
        self.restore_but = Gtk.RadioButton.new_with_label_from_widget(self.clone_but, _("Restore"))
        hbox.pack_start(self.restore_but, True, True, 10)
        self.restore_but.show()
        maclabel = Gtk.Label(label=_("Client MAC:"))
        hbox.pack_start(maclabel, True, True, 5)
        maclabel.show()
        self.mac_entry = Gtk.Entry()
        self.mac_entry.set_max_width_chars(18)
        self.mac_entry.show()
        hbox.pack_start(self.mac_entry, True, True, 0)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=30)
        vbox.pack_start(hbox, True, True, 10)
        hbox.show()
        svrlabel = Gtk.Label(label=_("Server:"))
        hbox.pack_start(svrlabel, True, True, 10)
        svrlabel.show()
        self.svrip = Gtk.Entry()
        hbox.pack_start(self.svrip, True, True, 10)
        self.svrip.set_max_width_chars(16)
        self.svrip.set_editable(False)
        self.svrip.show()
        ips = netutils.enum_ips()
        ipcombo = Gtk.ComboBoxText()
        ipcombo.set_entry_text_column(0)
        idx = -1
        for ip in ips:
            idx += 1
            ipcombo.append_text(ip)
        if idx >= 0:
            ipcombo.set_active(idx)
            self.svrip.set_text(ipcombo.get_active_text())
        else:
            echo =EchoInfo(self, "No active IP now")
            echo.run()
            echo.destroy()
            quit(0)
        ipcombo.show()
        hbox.pack_start(ipcombo, True, True, 10)
        ipcombo.connect("changed", self.on_ip_changed)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        vbox.pack_start(hbox, True, True, 10)
        hbox.show()
        svrlabel = Gtk.Label(label=_("Directory: "))
        hbox.pack_start(svrlabel, True, True, 10)
        svrlabel.show()
        self.svrdir = Gtk.Entry()
        self.svrdir.set_text(dir_prefix)
        self.svrdir.set_editable(False)
        self.svrdir.set_max_width_chars(24)
        hbox.pack_start(self.svrdir, True, True, 0)
        self.svrdir.show()
        selbut = Gtk.Button(label=_("Select"))
        hbox.pack_start(selbut, True, True, 20)
        selbut.show()
        selbut.connect("clicked", self.on_select_folder)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=30)
        vbox.pack_start(hbox, True, True, 10)
        hbox.show()
        okbut = Gtk.Button(label=_("Begin"))
        hbox.pack_start(okbut, True, True, 10)
        okbut.show()
        okbut.connect("clicked", self.operation_setup)

        self.pxefile = None
        self.parmfile = None
        self.keyfile = None

    def operation_finish(self, bug):
        if self.pxefile:
            os.remove(self.pxefile)
        if self.parmfile:
            os.remove(self.parmfile)
        if self.keyfile:
            os.remove(self.keyfile)
        Gtk.main_quit()

    def operation_setup(self, but):
        global pxelinux, conn, dir_prefix

        macaddr = self.mac_entry.get_text()
        if not macaddr or len(macaddr) == 0:
            echo = EchoInfo(self, "No Client Mac Address");
            echo.run()
            echo.destroy()
            return
        mack = re.fullmatch('([0-9a-f][0-9a-f]:){5}[0-9a-f][0-9a-f]', macaddr)
        if not mack:
            echo = EchoInfo(self, "Not a valid Mac Address");
            echo.run()
            echo.destroy()
            return
        svrip = self.svrip.get_text()
        svrdir = self.svrdir.get_text()
        action = 'clone'
        if self.restore_but.get_active():
            action = 'restore'
        macaddr = macaddr.replace(':', '-')
        backup_dir = svrdir + '/' + macaddr
        if action == 'clone' and os.path.isdir(backup_dir):
            echo = EchoInfo(self, "Backup directory "+backup_dir+' already exists')
            echo.run()
            echo.destroy()
            return
        if action == 'restore' and not os.path.isdir(backup_dir):
            echo = EchoInfo(self, "Backup directory "+backup_dir+' does not exist')
            echo.run()
            echo.destroy()
            return

        self.pxefile = '/var/svr/tftp/debian-installer/amd64/pxelinux.cfg/01-'+macaddr
        with open(self.pxefile, "w") as pxe:
            pxecfg = pxelinux.replace('$SERVER', svrip)
            pxe.write(pxecfg)
        self.keyfile = dir_prefix + '/operation.id'
        self.parmfile = dir_prefix + '/conn-' + macaddr + '.txt'
        coninfo = conn.replace('$ACTION', action)
        coninfo = coninfo.replace('$USER', username)
        coninfo = coninfo.replace('$SERVER', svrip)
        coninfo = coninfo.replace('$DEPOT', svrdir)
        coninfo = coninfo.replace('$PRVKEY', 'operation.id')
        with open(self.parmfile, "w") as parm:
            parm.write(coninfo)
        if os.path.isfile('operation.id'):
            os.remove('operation.id')
        if os.path.isfile('operation.id.pub'):
            os.remove('operation.id.pub')
        res = subp.run(['ssh-keygen', '-t', 'ecdsa',  '-N',  '', '-f', 'operation.id'], text=True,
                stdout=subp.PIPE, stderr=subp.STDOUT)
        if res.returncode != 0:
            echo = EchoInfo(self, res.stdout)
            echo.run()
            echo.destroy()
            return
        shutil.copyfile('operation.id', self.keyfile)
        if not os.path.isdir(homedir+'/.ssh'):
            os.mkdir(homedir+'/.ssh', mode=0o700)
        trustfile = homedir+'/.ssh/authorized_keys'
        pr = 0
        trust_key = ''
        if os.path.isfile(trustfile):
            pr = 1
            with open(trustfile, 'r') as trust:
                trust_key = trust.read()
        with open('operation.id.pub', 'r') as pub:
            trust_key += pub.read()
        with open(homedir+'/.ssh/authorized_keys', 'w') as trust:
            trust.write(trust_key)
#        os.remove('operation.id')
#        os.remove('operation.id.pub')
        if pr == 0:
            os.chmod(homedir+'/.ssh/authorized_keys', 0o600)
        rexp = "'s/([0-9][0-9]*\.){3}[0-9][0-9]*/"+svrip+"/g'"
        res = subp.run("sed -i -E -e "+rexp+" "+dir_prefix+"/preseed-net-clone.cfg",
                shell=True, text=True, stdout=subp.PIPE, stderr=subp.STDOUT)
        if res.returncode != 0:
            echo =EchoInfo(self, res.stdout)
            echo.run()
            echo.destroy()
            return
        echo = EchoInfo(self, _("Setup Complete\nDo not click OK until the clone/restore is finished"))
        echo.run()
        echo.destroy()

        self.operation_finish(1)

    def on_select_folder(self, widget):
        diag = Gtk.FileChooserDialog(
                title=_("Please select a folder"),
                parent=self,
                action=Gtk.FileChooserAction.SELECT_FOLDER
                )
        diag.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, _("Select"), Gtk.ResponseType.OK)
        diag.set_current_folder(dir_prefix)
        resp = diag.run()
        if resp == Gtk.ResponseType.OK:
            dirname = diag.get_filename()
            if not dirname.startswith(dir_prefix):
                echo =EchoInfo(self, "Directory must start with " + dir_prefix)
                echo.run()
                echo.destroy()
            else:
                self.svrdir.set_text(dirname)
        diag.destroy()

    def on_ip_changed(self, widget):
        self.svrip.set_text(widget.get_active_text())


locale.setlocale(locale.LC_ALL, '')
_ = gettext.gettext
gettext.bindtextdomain("lios-clone")
gettext.textdomain('lios-clone')

win = MWindow()
win.connect("destroy", Gtk.main_quit)
win.show()
Gtk.main()
quit(0)
