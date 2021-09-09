#!/usr/bin/python3
#
import gi
import sys
import subprocess as subproc

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

class MainWin(Gtk.Window):
    def current_client(self):
        with open("/var/www/html/lenvdi/preseed-net.cfg", "r") as fin:
            for ln in fin:
                if ln.find(" post-task-net.sh ") == -1:
                    continue
                fields = ln.split()
                if fields[0] != 'sh' or fields[1] != 'post-task-net.sh':
                    continue
                client = fields[2]
                break
        return client

    def current_lidm(self):
        retv = {"lidms": '', "lidmp": ''}
        with open("/var/www/html/lenvdi/post-task-net.sh", "r") as fin:
            for ln in fin:
                if ln.find("lidm_s=") != 0 and ln.find("lidm_p=") != 0:
                    continue
                fields = ln.rstrip('\n').split('=')
                if fields[0] == "lidm_s" and len(fields) > 1:
                    retv["lidms"] = fields[1]
                if fields[0] == "lidm_p" and len(fields) > 1:
                    retv["lidmp"] = fields[1]
        return retv


    def __init__(self):
        super().__init__(title="VDI Client Installation Setup")
        self.set_border_width(10)

        box = Gtk.Box(spacing=6, orientation=Gtk.Orientation.VERTICAL)
        box.show()
        self.add(box)

        lidm = self.current_lidm()
        hbox = Gtk.Box(spacing=5)
        hbox.show()
        box.pack_start(hbox, True, True, 10)
        label = Gtk.Label(label="LIDM IP: ")
        label.show()
        hbox.pack_start(label, False, False, 5)
        self.lidms = Gtk.Entry()
        self.lidms.set_width_chars(16)
        self.lidms.set_text(lidm["lidms"])
        self.lidms.show()
        hbox.pack_start(self.lidms, True, True, 5)
        label = Gtk.Label(label="Port: ")
        label.show()
        hbox.pack_start(label, False, False, 5)
        self.port = Gtk.Entry()
        self.port.set_width_chars(8)
        self.port.set_text(lidm["lidmp"])
        self.port.show()
        hbox.pack_start(self.port, False, False, 5)

        hbox = Gtk.Box(spacing=5)
        hbox.show()
        box.pack_start(hbox, True, True, 10)
        self.r_lidc = Gtk.RadioButton(label="LIDC Client")
        self.r_lidc.connect("toggled", self.on_toggled)
        self.r_lidc.show()
        hbox.pack_start(self.r_lidc, True, True, 0)
        self.r_educ = Gtk.RadioButton(label="LIDC Edu", group=self.r_lidc);
        self.r_educ.connect("toggled", self.on_toggled)
        self.r_educ.show()
        hbox.pack_start(self.r_educ, True, True, 0)
        self.r_citx = Gtk.RadioButton(label="Citrix Client", group=self.r_lidc);
        self.r_citx.connect("toggled", self.on_toggled)
        self.r_citx.show()
        hbox.pack_start(self.r_citx, True, True, 0)
        self.r_vmwa = Gtk.RadioButton(label="VMWare Client", group=self.r_lidc);
        self.r_vmwa.connect("toggled", self.on_toggled)
        self.r_vmwa.show()
        hbox.pack_start(self.r_vmwa, True, True, 0)
        self.r_firefox = Gtk.RadioButton(label="Firefox ESR", group=self.r_lidc);
        self.r_firefox.connect("toggled", self.on_toggled)
        self.r_firefox.show()
        hbox.pack_start(self.r_firefox, True, True, 0)

        client = self.current_client()
        if client == 'lidcc':
            self.r_lidc.set_active(True)
            self.client_but = self.r_lidc
        elif client == 'educ':
            self.r_educ.set_active(True)
            self.client_but = self.r_educ
        elif client == 'citrix':
            self.r_citx.set_active(True)
            self.client_but = self.r_citx
        elif client == 'vmware':
            self.r_vmwa.set_active(True)
            self.client_but = self.r_vmwa
        elif client == 'firefox':
            self.r_firefox.set_active(True)
            self.client_but = self.r_firefox
        else:
            self.client_but = None
            print(f"No such client: {client}")

        hbox = Gtk.Box(spacing=5)
        hbox.show()
        box.pack_start(hbox, True, True, 10)
        ok_but = Gtk.Button(label="OK")
        ok_but.connect("clicked", self.ok_clicked)
        ok_but.show()
        hbox.pack_start(ok_but, True, True, 0)
        cn_but = Gtk.Button(label="Cancel")
        cn_but.connect("clicked", self.cancel_clicked)
        cn_but.show()
        hbox.pack_start(cn_but, True, True, 0)


    def on_toggled(self, rbut):
        if rbut.get_active():
            self.client_but = rbut

    def ok_clicked(self, button):
        sedcmd = "sed -i -e 's/\(sh post-task-net.sh \)"
        sedcmd += "\(lidcc\|citrix\|vmware\|educ\|firefox\)/\\1"
        if self.client_but == self.r_lidc:
            sedcmd += "lidcc/'"
        elif self.client_but == self.r_citx:
            sedcmd += "citrix/'"
        elif self.client_but == self.r_vmwa:
            sedcmd += "vmware/'"
        elif self.client_but == self.r_firefox:
            sedcmd += "firefox/'"
        elif self.client_but == self.r_educ:
            sedcmd += "educ/'"
        else:
            print('Logic Error, No button active.')
            Gtk.main_quit()
        sedcmd += " /var/www/html/lenvdi/preseed-net.cfg"
        retv = subproc.run(sedcmd, shell=True, stdout=subproc.PIPE, stderr=subproc.STDOUT, text=True)
        if retv.returncode != 0:
            dialog = Gtk.MessageDialog(
                    parent=self,
                    flags=0,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.CANCEL,
                    text="Cannot set Installation Client Type"
                    )
            dialog.format_secondary_text(retv.stdout)
            dialog.run()
            dialog.destroy()
            return

        dstfile = " /var/www/html/lenvdi/post-task-net.sh"
        lidm_s = self.lidms.get_text()
        sedcmd = "sed -i -e 's/^\(lidm_s=\).*$/\\1" + lidm_s + "/'"
        sedcmd += dstfile
        retv = subproc.run(sedcmd, shell=True, stdout=subproc.PIPE, stderr=subproc.STDOUT, text=True)
        if retv.returncode != 0:
            dialog = Gtk.MessageDialog(
                    parent=self,
                    flags=0,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.CANCEL,
                    text="Cannot set LIDM server ip/port"
                    )
            dialog.format_secondary_text(retv.stdout)
            dialog.run()
            dialog.destroy()
            return
        lidm_p = self.port.get_text()
        sedcmd = "sed -i -e 's/^\(lidm_p=\).*$/\\1" + lidm_p + "/'"
        sedcmd += dstfile
        retv = subproc.run(sedcmd, shell=True, stdout=subproc.PIPE, stderr=subproc.STDOUT, text=True)
        if retv.returncode != 0:
            dialog = Gtk.MessageDialog(
                    parent=self,
                    flags=0,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.CANCEL,
                    text="Cannot set LIDM server ip/port"
                    )
            dialog.format_secondary_text(retv.stdout)
            dialog.run()
            dialog.destroy()
            return

        Gtk.main_quit()

    def cancel_clicked(self, button):
        Gtk.main_quit()

win = MainWin()
win.connect("destroy", Gtk.main_quit)
win.show()
Gtk.main()
sys.exit(0)
