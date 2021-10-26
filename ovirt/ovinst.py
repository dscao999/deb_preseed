#!/usr/bin/python3
#
import gi
import locale
import gettext
import os

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

locale.setlocale(locale.LC_ALL, '')
_ = gettext.gettext
gettext.bindtextdomain("ovinst")
gettext.textdomain('ovinst')

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
        entry = Gtk.Entry()
        entry.set_max_width_chars(12)
        entry.show()
        grid.attach(entry, 1, 0, 2, 1)

        label = Gtk.Label(label=_('OS Disk 1:'))
        label.show()
        grid.attach(label, 0, 1, 1, 1)
        self.disks = lsdisk()
        seldsk = Gtk.ComboBoxText()
        seldsk.set_entry_text_column(0)
        for disk in self.disks:
            seldsk.append_text(disk[0])
        seldsk.set_active(0)
        seldsk.connect("changed", self.on_disk_changed)
        seldsk.show()
        grid.attach(seldsk, 1, 1, 1, 1)
        self.ddev = Gtk.Entry()
        self.ddev.set_text(self.disks[0][1])
        self.ddev.set_max_width_chars(12)
        self.ddev.set_editable(False)
        self.ddev.show()
        grid.attach(self.ddev, 2, 1, 1, 1)

    def on_disk_changed(self, combo):
        text = combo.get_active_text()
        if text:
            for disk in self.disks:
                if text == disk[0]:
                    break
            self.ddev.set_text(disk[1])

win = MainWin()
win.show()
win.connect("destroy", Gtk.main_quit)
Gtk.main()
devs = lsdisk()
exit(0)
