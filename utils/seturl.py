#!/usr/bin/python3
#
import gi
import os, sys

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk

class MainWin(Gtk.Window):
    def __init__(self):
        super().__init__(title="URL Specification")
        self.set_border_width(10)

        csstxt = b'* { font-size: 60px; }'
        cssprov = Gtk.CssProvider()
        cssprov.load_from_data(csstxt)
        ctxt = Gtk.StyleContext()
        scn = Gdk.Screen.get_default()
        ctxt.add_provider_for_screen(scn, cssprov,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        box = Gtk.Box(spacing=6, orientation=Gtk.Orientation.VERTICAL)
        box.show()
        self.add(box)

        hbox = Gtk.Box(spacing=5)
        hbox.show()
        box.pack_start(hbox, True, True, 10)
        lab = Gtk.Label(label="URL: ");
        lab.show()
        hbox.pack_start(lab, True, True, 0)
        self.url = Gtk.Entry();
        
        self.url.set_text("http://");
        self.url.set_width_chars(24);
        self.url.show();
        hbox.pack_start(self.url, True, True, 0);

        hbox = Gtk.Box(spacing=5)
        hbox.set_homogeneous(True)
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


    def ok_clicked(self, button):
        url = self.url.get_text()
        desktop = '/usr/share/applications/firefox-esr.desktop'
        if not os.path.isfile(desktop):
            dialog = Gtk.MessageDialog(
                    parent=self,
                    flags=0,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.CANCEL,
                    text="Firefox ESR not installed"
                    )
            dialog.run()
            dialog.destroy()
            Gtk.main_quit()
        contents = []
        with open(desktop, 'r') as fin:
            for ln in fin:
                if ln.find('Exec=') == 0:
                    fields = ln.split()
                    fields.insert(1, '--kiosk '+url)
                    ln = ''
                    for field in fields:
                        ln += field + ' '
                    ln = ln.rstrip(' ') + '\n'
                    print(ln)
                contents.append(ln)
        user_home = os.getenv("HOME")
        desktop = user_home + '/.config/autostart/firefox-esr.desktop'
        with open(desktop, 'w') as fout:
            for ln in contents:
                fout.write(ln)
        os.remove(user_home+'/.config/autostart/first-shot.desktop')
        Gtk.main_quit()

    def cancel_clicked(self, button):
        Gtk.main_quit()

win = MainWin()
win.connect("destroy", Gtk.main_quit)
win.show()
win.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
Gtk.main()
sys.exit(0)
