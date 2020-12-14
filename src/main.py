
import sys
import gi

gi.require_version('Gtk', '3.0')

from gi.repository import Gtk, Gio

from .window import WaspCompanionWindow


class Application(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='com.arteeh.Companion',
                         flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = WaspCompanionWindow(application=self)
        win.present()


def main(version):
    app = Application()
    return app.run(sys.argv)
