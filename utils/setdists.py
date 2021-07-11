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

    def __init__(self):
        super().__init__(title="VDI Client Selection")
        self.set_border_width(10)

        box = Gtk.Box(spacing=6, orientation=Gtk.Orientation.VERTICAL)
        box.show()
        self.add(box)

        hbox = Gtk.Box(spacing=5)
        hbox.show()
        box.pack_start(hbox, True, True, 10)
        self.r_lidc = Gtk.RadioButton(label="LIDC Client")
        self.r_lidc.connect("toggled", self.on_toggled)
        self.r_lidc.show()
        hbox.pack_start(self.r_lidc, True, True, 0)
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
        elif client == 'citrix':
            self.r_citx.set_active(True)
        elif client == 'vmware':
            self.r_vmwa.set_active(True)
        elif client == 'firefox':
            self.r_firefox.set_active(True)
        else:
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

        self.client = self.r_lidc

    def on_toggled(self, rbut):
        if rbut.get_active():
            self.client = rbut

    def ok_clicked(self, button):
        sedcmd = "sed -i -e 's/\(sh post-task-net.sh \)"
        sedcmd += "\(lidcc\|citrix\|vmware\)/\\1"
        if self.client == self.r_lidc:
            sedcmd += "lidcc/'"
        elif self.client == self.r_citx:
            sedcmd += "citrix/'"
        elif self.client == self.r_vmwa:
            sedcmd += "vmware/'"
        elif self.client == self.r_firefox:
            sedcmd += "firefox/'"
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
        Gtk.main_quit()

    def cancel_clicked(self, button):
        Gtk.main_quit()

win = MainWin()
win.connect("destroy", Gtk.main_quit)
win.show()
Gtk.main()
sys.exit(0)
