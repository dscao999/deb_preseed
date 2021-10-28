#!/usr/bin/python3
#
import gi
import locale
import gettext
import os
import re

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

locale.setlocale(locale.LC_ALL, '')
_ = gettext.gettext
gettext.bindtextdomain("ovinst")
gettext.textdomain('ovinst')

class EchoInfo(Gtk.MessageDialog):
    def __init__(self, rootwin, info):
        super().__init__(parent=rootwin, flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text=info)

def lsdisk():
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

            tname = os.readlink(tpath+'/'+pname)
            slash = tname.rfind('/')
            if slash != -1:
                tname = tname[slash+1:]
            curtup = (pname, '/dev/'+tname)
            skip = 0
            for tup in devpairs:
                if tup == curtup:
                    skip = 1
                    break
            if skip == 1:
                continue
            devpairs.append(curtup)

    return devpairs


class MainWin(Gtk.Window):
    def __init__(self):
        super().__init__(title=_("Ovirt Installation Setup"))
        
        grid = Gtk.Grid()
        grid.set_column_homogeneous(False)
        grid.set_row_homogeneous(True)
        grid.show()
        self.add(grid)

        label = Gtk.Label(label=_("  Host Name: "), halign=Gtk.Align.END)
        label.set_max_width_chars(20)
        label.show()
        grid.attach(label, 0, 0, 1, 1)
        self.hentry = Gtk.Entry()
        self.hentry.set_max_width_chars(12)
        self.hentry.show()
        grid.attach(self.hentry, 1, 0, 2, 1)

        label = Gtk.Label(label=_('OS Disk 1:'))
        label.show()
        grid.attach(label, 0, 1, 1, 1)
        self.disks = lsdisk()
        self.seldsk1 = Gtk.ComboBoxText()
        self.seldsk1.set_entry_text_column(0)
        for disk in self.disks:
            self.seldsk1.append_text(disk[0])
        self.seldsk1.set_active(0)
        self.seldsk1.connect("changed", self.on_disk_changed)
        self.seldsk1.show()
        grid.attach(self.seldsk1, 1, 1, 1, 1)
        self.ddev1 = Gtk.Entry()
        self.ddev1.set_text(self.disks[0][1])
        self.ddev1.set_max_width_chars(12)
        self.ddev1.set_editable(False)
        self.ddev1.show()
        grid.attach(self.ddev1, 2, 1, 1, 1)

        label = Gtk.Label(label=_('OS Disk 2:'))
        label.show()
        grid.attach(label, 0, 2, 1, 1)
        self.disks = lsdisk()
        self.seldsk2 = Gtk.ComboBoxText()
        self.seldsk2.set_entry_text_column(0)
        for disk in self.disks:
            self.seldsk2.append_text(disk[0])
        self.seldsk2.set_active(0)
        self.seldsk2.connect("changed", self.on_disk_changed)
        self.seldsk2.show()
        grid.attach(self.seldsk2, 1, 2, 1, 1)
        self.ddev2 = Gtk.Entry()
        self.ddev2.set_text(self.disks[0][1])
        self.ddev2.set_max_width_chars(12)
        self.ddev2.set_editable(False)
        self.ddev2.show()
        grid.attach(self.ddev2, 2, 2, 1, 1)

        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.show()
        grid.attach(sep, 0, 3, 3, 1)
        hbox = Gtk.Box(spacing=10)
        hbox.show()
        grid.attach(hbox, 0, 4, 3, 1)

        but = Gtk.Button.new_with_label(_("OK"))
        but.connect("clicked", self.ok_clicked)
        but.show()
        hbox.pack_start(but, True, True, 0)
        but = Gtk.Button.new_with_label(_("Cancel"))
        but.connect("clicked", Gtk.main_quit)
        but.show()
        hbox.pack_start(but, True, True, 0)

    def ok_clicked(self, widget):
        hostname = self.hentry.get_text()
        fqnre = re.compile('[a-z][_a-z0-9]{3,7}')
        res = fqnre.match(hostname)
        if res:
            span = res.span()
        if not res or span[0] != 0 or span[1] != len(hostname):
            echo = EchoInfo(self, "Invalid Host Name")
            echo.run()
            echo.destroy()
            return

        disk1 = self.seldsk1.get_active_text()
        disk2 = self.seldsk2.get_active_text()
        if disk1 == "None" and disk2 == "None":
            echo = EchoInfo(self, "Please select at lease one disk")
            echo.run()
            echo.destroy()
            return

        if disk1 == disk2:
            echo = EchoInfo(self, "Two sys disks must be different")
            echo.run()
            echo.destroy()
            return

        print("OK Clicked")

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

win = MainWin()
win.show()
win.connect("destroy", Gtk.main_quit)
Gtk.main()
devs = lsdisk()
exit(0)
