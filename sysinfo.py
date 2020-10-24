#!/usr/bin/python3
#
import sys
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from gi.repository.GdkPixbuf import Pixbuf

class MWindow(Gtk.Window):
    def __init__(self, my_title):
        super().__init__(title=my_title)
        self.set_border_width(10)
        self.set_default_size(400, 200)

        hb = Gtk.HeaderBar()
        hb.set_show_close_button(True)
        hb.props.title = "HeaderBar example"
        self.set_titlebar(hb)

        self.box = Gtk.Box(spacing=6)
        self.add(self.box)

        button = Gtk.Button(label="Click")
        button.connect("clicked", self.on_button_clicked)
        self.box.pack_start(button, True, True, 0)

        button = Gtk.Label(label="Right Click")
        self.box.pack_start(button, True, True, 0)

        img = Gtk.Image()
        img.set_from_file("./sysinfo-side.png")
        self.box.pack_start(img, True, True, 0)

    def on_button_clicked(self, widget):
        label = widget.get_label()
        print(label)


win = MWindow("Hello Window")
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()

sys.exit(0)
