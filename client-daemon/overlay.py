import gi
import time
import threading
from gi.repository import GLib

gi.require_version('Gtk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import Gtk, Gdk, GtkLayerShell
import cairo

class MultiplayerOverlay(Gtk.Window):
    def __init__(self):
        super().__init__()

        # Setup the Wayland Layer Shell
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.BOTTOM, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, True)

        # 1. Force the layer shell to ignore keyboards
        GtkLayerShell.set_keyboard_interactivity(self, False)

        # 2. Tell the window manager to ignore us completely
        self.set_accept_focus(False)
        self.set_can_focus(False)

        # Make it transparent
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)
        self.set_app_paintable(True)

        # Canvas for players
        self.fixed_layout = Gtk.Fixed()
        self.add(self.fixed_layout)

        # Player 2 Red Box
        self.player2 = Gtk.EventBox()
        self.player2.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("red"))
        self.player2.set_size_request(16, 16)
        self.fixed_layout.put(self.player2, 100, 100)

        self.connect('draw', self.on_draw)

        self.show_all()

        # 3. Apply the click-through mask AFTER the GTK main loop starts
        GLib.idle_add(self.apply_click_through)

    def apply_click_through(self):
        """Forces the window to be completely invisible to the mouse"""
        empty_region = cairo.Region()
        self.input_shape_combine_region(empty_region)
        return False # Returning False stops the idle loop from repeating

    def on_draw(self, widget, cr):
        # Clears the background so it remains fully transparent
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()
        return False

    def move_player(self, x, y):
        """Moves Player 2 to the new coordinates"""
        self.fixed_layout.move(self.player2, x, y)


def simulate_network_updates(overlay):
    """Fakes receiving coordinates from PocketBase"""
    x, y = 100, 100
    while True:
        time.sleep(0.05) # 20 fps update rate
        x += 5
        y += 3
        # GTK requires UI updates to happen on the main thread
        GLib.idle_add(overlay.move_player, x % 1920, y % 1080)

if __name__ == '__main__':
    app = MultiplayerOverlay()
    threading.Thread(target=simulate_network_updates, args=(app,), daemon=True).start()
    Gtk.main()
