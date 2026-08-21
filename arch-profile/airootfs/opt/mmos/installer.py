import gi
import time
import json
import os
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

SETTINGS_FILE = os.path.expanduser("~/.config/mmos/settings.json")

class MMOSInstaller(Gtk.Window):
    def __init__(self):
        super().__init__(title="MMOS - Setup Wizard")
        self.set_default_size(520, 680)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_border_width(15)

        # Main Scroll Container to prevent button clipping
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.add(scrolled)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        scrolled.add(vbox)

        # 1. Title
        title = Gtk.Label()
        title.set_markup("<span size='x-large' weight='bold'>MMOS Character Setup</span>")
        vbox.pack_start(title, False, False, 5)

        # 2. Username Input with Label
        user_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        user_box.pack_start(Gtk.Label(label="Username:"), False, False, 0)
        self.username_entry = Gtk.Entry()
        self.username_entry.set_placeholder_text("Enter player name...")
        user_box.pack_start(self.username_entry, True, True, 0)
        vbox.pack_start(user_box, False, False, 0)

        # 3. Control Scheme
        mode_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        mode_box.pack_start(Gtk.Label(label="Control Mode:"), False, False, 0)
        self.mode_combo = Gtk.ComboBoxText()
        self.mode_combo.append("standard", "Standard Mouse")
        self.mode_combo.append("wasd", "WASD Keyboard Mouse")
        self.mode_combo.set_active(0)
        mode_box.pack_start(self.mode_combo, True, True, 0)
        vbox.pack_start(mode_box, False, False, 0)

        # 4. Visibility (Who I see)
        vis_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        vis_box.pack_start(Gtk.Label(label="Visibility (Who I see):"), False, False, 0)
        self.vis_combo = Gtk.ComboBoxText()
        self.vis_combo.append("all", "See Everyone")
        self.vis_combo.append("friends", "See Friends Only")
        self.vis_combo.append("none", "See Nobody")
        self.vis_combo.set_active(0)
        vis_box.pack_start(self.vis_combo, True, True, 0)
        vbox.pack_start(vis_box, False, False, 0)

        # 5. Broadcasting (Who sees me)
        broad_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        broad_box.pack_start(Gtk.Label(label="Broadcasting (Who sees me):"), False, False, 0)
        self.broad_combo = Gtk.ComboBoxText()
        self.broad_combo.append("all", "Broadcast to Everyone")
        self.broad_combo.append("friends", "Broadcast to Friends Only")
        self.broad_combo.append("none", "Do Not Broadcast (Offline)")
        self.broad_combo.set_active(0)
        broad_box.pack_start(self.broad_combo, True, True, 0)
        vbox.pack_start(broad_box, False, False, 0)

        # 6. Drag-to-Draw 16x16 Pixel Art Canvas
        vbox.pack_start(Gtk.Label(label="Draw Your Cursor (Click or Drag to Paint):"), False, False, 5)

        self.grid = Gtk.Grid()
        self.grid.set_halign(Gtk.Align.CENTER)
        self.pixels = {}

        for y in range(16):
            for x in range(16):
                box = Gtk.EventBox()
                box.set_size_request(20, 20)
                box.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.ENTER_NOTIFY_MASK)

                self.set_pixel_color(box, False)
                self.pixels[(x, y)] = {"widget": box, "active": False}

                box.connect("button-press-event", self.on_pixel_click, x, y)
                box.connect("enter-notify-event", self.on_pixel_drag, x, y)
                self.grid.attach(box, x, y, 1, 1)

        vbox.pack_start(self.grid, False, False, 5)

        # 7. Action Button
        finish_btn = Gtk.Button(label="Finish Installation")
        finish_btn.set_size_request(-1, 45)
        finish_btn.get_style_context().add_class("suggested-action")
        finish_btn.connect("clicked", self.save_and_exit)
        vbox.pack_start(finish_btn, False, False, 10)

    def set_pixel_color(self, widget, is_active):
        color = "red" if is_active else "#1e1e1e"
        rgba = Gdk.RGBA()
        rgba.parse(color)
        widget.override_background_color(Gtk.StateFlags.NORMAL, rgba)

    def paint_pixel(self, x, y, state):
        self.pixels[(x, y)]["active"] = state
        self.set_pixel_color(self.pixels[(x, y)]["widget"], state)

    def on_pixel_click(self, widget, event, x, y):
        if event.button == 1: # Left click toggles
            new_state = not self.pixels[(x, y)]["active"]
            self.paint_pixel(x, y, new_state)

    def on_pixel_drag(self, widget, event, x, y):
        # Paint while holding left mouse button down
        if event.state & Gdk.ModifierType.BUTTON1_MASK:
            self.paint_pixel(x, y, True)

    def save_and_exit(self, button):
        username = self.username_entry.get_text().strip()
        if not username:
            self.username_entry.set_placeholder_text("USERNAME REQUIRED!")
            return

        pixel_data = []
        for y in range(16):
            row = []
            for x in range(16):
                row.append(1 if self.pixels[(x, y)]["active"] else 0)
            pixel_data.append(row)

        settings = {
            "username": username,
            "mouse_mode": self.mode_combo.get_active_id(),
            "visibility": self.vis_combo.get_active_id(),
            "broadcasting": self.broad_combo.get_active_id(),
            "friends_list": [],
            "pixel_art": pixel_data
        }

        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=4)

        print("Setup complete! Saved to:", SETTINGS_FILE)
        Gtk.main_quit()

if __name__ == '__main__':
    app = MMOSInstaller()
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    Gtk.main()
