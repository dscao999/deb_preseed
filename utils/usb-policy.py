#!/usr/bin/python3
#
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

class MainWin(Gtk.Window):
    def __init__(self):
        super().__init__(title="USB Device Policy")
        self.set_border_width(10)

        box =Gtk.Box(spacing=6, orientation=Gtk.Orientation.VERTICAL)
        box.show()
        self.add(box)

        label = Gtk.Label(label="Sorry, USB Device Policy")
        label.show()
        box.pack_start(label, True, True, 0)
        label = Gtk.Label(label="Not Implemented Yet")
        label.show()
        box.pack_start(label, True, True, 0)

        self.set_default_size(400, 100)

win = MainWin()
win.connect("destroy", Gtk.main_quit)
win.show()
Gtk.main()
quit(0)
