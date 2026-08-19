import gi
import json
import os
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

# Where we will save the user's profile
SETTINGS_FILE = os.path.expanduser("~/.config/mmos/settings.json")

class MMOSInstaller(Gtk.Window):
    def __init__(self):
        super().__init__(title="MMOS - Create Your Player")
        self.set_default_size(500, 600)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_border_width(20)

        # Main Layout container
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        self.add(vbox)

        # 1. Title
        title = Gtk.Label()
        title.set_markup("<span size='x-large' weight='bold'>Welcome to MMOS</span>")
        vbox.pack_start(title, False, False, 0)

        # 2. Username Input
        self.username_entry = Gtk.Entry()
        self.username_entry.set_placeholder_text("Enter Username...")
        vbox.pack_start(self.username_entry, False, False, 0)

        # 3. Mouse Mode (Standard vs WASD)
        mode_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        mode_box.pack_start(Gtk.Label(label="Control Mode:"), False, False, 0)
        self.mode_combo = Gtk.ComboBoxText()
        self.mode_combo.append("standard", "Standard Mouse")
        self.mode_combo.append("wasd", "WASD Keyboard Mouse")
        self.mode_combo.set_active(0)
        mode_box.pack_start(self.mode_combo, True, True, 0)
        vbox.pack_start(mode_box, False, False, 0)

        # 4. Privacy Mode
        privacy_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        privacy_box.pack_start(Gtk.Label(label="Privacy:"), False, False, 0)
        self.privacy_combo = Gtk.ComboBoxText()
        self.privacy_combo.append("all", "Everyone can see me")
        self.privacy_combo.append("friends", "Friends Only")
        self.privacy_combo.append("none", "Offline (Hidden)")
        self.privacy_combo.set_active(0)
        privacy_box.pack_start(self.privacy_combo, True, True, 0)
        vbox.pack_start(privacy_box, False, False, 0)

        # 5. The 16x16 Pixel Art Grid
        vbox.pack_start(Gtk.Label(label="Draw Your Cursor (Click to toggle pixels):"), False, False, 10)

        self.grid = Gtk.Grid()
        self.grid.set_halign(Gtk.Align.CENTER)
        self.pixels = {} # Stores the state of our 16x16 grid

        for y in range(16):
            for x in range(16):
                # Create a clickable box for each pixel
                event_box = Gtk.EventBox()
                event_box.set_size_request(20, 20)

                # Start them all as black (0 = black, 1 = red/color)
                self.set_pixel_color(event_box, False)
                self.pixels[(x, y)] = {"widget": event_box, "active": False}

                # Listen for mouse clicks
                event_box.connect("button-press-event", self.on_pixel_clicked, x, y)
                self.grid.attach(event_box, x, y, 1, 1)

        vbox.pack_start(self.grid, True, True, 0)

        # 6. Finish Button
        finish_btn = Gtk.Button(label="Finish Installation")
        finish_btn.get_style_context().add_class("suggested-action") # Makes it blue
        finish_btn.connect("clicked", self.save_and_exit)
        vbox.pack_start(finish_btn, False, False, 0)

    def set_pixel_color(self, widget, is_active):
        """Helper to color the pixel blocks"""
        color = "red" if is_active else "black"
        rgba = Gdk.RGBA()
        rgba.parse(color)
        widget.override_background_color(Gtk.StateFlags.NORMAL, rgba)

    def on_pixel_clicked(self, widget, event, x, y):
        """Fires when a user clicks a pixel in the 16x16 grid"""
        current_state = self.pixels[(x, y)]["active"]
        new_state = not current_state # Toggle it
        self.pixels[(x, y)]["active"] = new_state
        self.set_pixel_color(widget, new_state)

    def save_and_exit(self, button):
        """Saves the settings and closes the installer"""
        username = self.username_entry.get_text()
        if not username:
            print("Please enter a username!")
            return

        # Extract the 16x16 grid into a simple array we can save
        pixel_data = []
        for y in range(16):
            row = []
            for x in range(16):
                row.append(1 if self.pixels[(x, y)]["active"] else 0)
            pixel_data.append(row)

        settings = {
            "username": username,
            "mouse_mode": self.mode_combo.get_active_id(),
            "privacy": self.privacy_combo.get_active_id(),
            "pixel_art": pixel_data
        }

        # Ensure the settings directory exists
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)

        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=4)

        print(f"Settings saved to {SETTINGS_FILE}")
        Gtk.main_quit()

if __name__ == '__main__':
    app = MMOSInstaller()
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    Gtk.main()
