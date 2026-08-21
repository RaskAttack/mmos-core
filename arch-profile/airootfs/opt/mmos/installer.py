import gi
import json
import os
import sys
import requests
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

SETTINGS_FILE = os.path.expanduser("~/.config/mmos/settings.json")

class MMOSInstaller(Gtk.Window):
    def __init__(self):
        super().__init__(title="MMOS - Setup Wizard")
        self.set_default_size(520, 780)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_border_width(15)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.add(scrolled)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        scrolled.add(vbox)

        # 1. Title
        title = Gtk.Label()
        title.set_markup("<span size='x-large' weight='bold'>MMOS Character Setup</span>")
        vbox.pack_start(title, False, False, 5)

        # 2. Username Input
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

        # 4. Visibility & Broadcasting
        vis_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        vis_box.pack_start(Gtk.Label(label="Who I see:"), False, False, 0)
        self.vis_combo = Gtk.ComboBoxText()
        self.vis_combo.append("all", "See Everyone")
        self.vis_combo.append("friends", "See Friends Only")
        self.vis_combo.append("none", "See Nobody")
        self.vis_combo.set_active(0)
        vis_box.pack_start(self.vis_combo, True, True, 0)
        vbox.pack_start(vis_box, False, False, 0)

        broad_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        broad_box.pack_start(Gtk.Label(label="Who sees me:"), False, False, 0)
        self.broad_combo = Gtk.ComboBoxText()
        self.broad_combo.append("all", "Broadcast to Everyone")
        self.broad_combo.append("friends", "Broadcast to Friends Only")
        self.broad_combo.append("none", "Offline (Hidden)")
        self.broad_combo.set_active(0)
        broad_box.pack_start(self.broad_combo, True, True, 0)
        vbox.pack_start(broad_box, False, False, 0)

        # 5. PRESET CURSORS DROPDOWN
        vbox.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 5)
        preset_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        preset_box.pack_start(Gtk.Label(label="Select a Cursor:"), False, False, 0)

        self.preset_combo = Gtk.ComboBoxText()
        self.preset_combo.append("custom", "Custom (Draw your own!)")
        for i in range(1, 21):
            self.preset_combo.append(f"preset_{i}", f"Default Cursor {i}")
        self.preset_combo.set_active(0)
        self.preset_combo.connect("changed", self.on_preset_changed)
        preset_box.pack_start(self.preset_combo, True, True, 0)
        vbox.pack_start(preset_box, False, False, 0)

        # 6. NATIVE COLOR WHEEL
        palette_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        palette_box.set_halign(Gtk.Align.CENTER)
        palette_box.pack_start(Gtk.Label(label="Paint Color: "), False, False, 0)

        self.color_picker = Gtk.ColorButton()
        self.color_picker.set_rgba(Gdk.RGBA(1.0, 0.0, 0.0, 1.0)) # Default Red
        self.color_picker.connect("color-set", self.on_color_set)
        palette_box.pack_start(self.color_picker, False, False, 0)
        vbox.pack_start(palette_box, False, False, 0)

        self.current_color = "#FF0000"

        # 7. Native Canvas
        vbox.pack_start(Gtk.Label(label="Left Click: Draw | Right Click: Erase"), False, False, 0)
        self.canvas = Gtk.DrawingArea()
        self.canvas.set_size_request(320, 320)
        self.canvas.set_halign(Gtk.Align.CENTER)
        self.canvas.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.POINTER_MOTION_MASK)

        self.pixel_grid = [["" for _ in range(16)] for _ in range(16)]

        # PRESET DATA STORAGE (You can fill these 20 arrays in later)
        self.presets = {
            "preset_1": [["#FFFFFF" if x == y else "" for x in range(16)] for y in range(16)], # Example: Diagonal Line
            # Add "preset_2": [[...]], here later!
        }

        self.canvas.connect("draw", self.on_canvas_draw)
        self.canvas.connect("button-press-event", self.on_canvas_mouse)
        self.canvas.connect("motion-notify-event", self.on_canvas_mouse)
        vbox.pack_start(self.canvas, False, False, 5)

        # 8. Action Button
        finish_btn = Gtk.Button(label="Finish Installation")
        finish_btn.set_size_request(-1, 45)
        finish_btn.get_style_context().add_class("suggested-action")
        finish_btn.connect("clicked", self.save_and_exit)
        vbox.pack_start(finish_btn, False, False, 5)

    def on_color_set(self, widget):
        rgba = widget.get_rgba()
        r, g, b = int(rgba.red * 255), int(rgba.green * 255), int(rgba.blue * 255)
        self.current_color = f"#{r:02x}{g:02x}{b:02x}".upper()

    def on_preset_changed(self, combo):
        preset_id = combo.get_active_id()
        if preset_id in self.presets:
            self.pixel_grid = [row[:] for row in self.presets[preset_id]]
            self.canvas.queue_draw()
        elif preset_id == "custom":
            self.pixel_grid = [["" for _ in range(16)] for _ in range(16)]
            self.canvas.queue_draw()

    def hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16)/255.0 for i in (0, 2, 4))

    def on_canvas_draw(self, widget, cr):
        cr.set_source_rgb(0.12, 0.12, 0.12)
        cr.paint()

        for y in range(16):
            for x in range(16):
                color = self.pixel_grid[y][x]
                if color != "":
                    r, g, b = self.hex_to_rgb(color)
                    cr.set_source_rgb(r, g, b)
                    cr.rectangle(x * 20, y * 20, 20, 20)
                    cr.fill()

                cr.set_source_rgba(1.0, 1.0, 1.0, 0.05)
                cr.rectangle(x * 20, y * 20, 20, 20)
                cr.stroke()

    def on_canvas_mouse(self, widget, event):
        self.preset_combo.set_active_id("custom") # Force it to custom if they draw
        x, y = int(event.x // 20), int(event.y // 20)
        if 0 <= x < 16 and 0 <= y < 16:
            if event.state & Gdk.ModifierType.BUTTON1_MASK or (event.type == Gdk.EventType.BUTTON_PRESS and event.button == 1):
                self.pixel_grid[y][x] = self.current_color
                widget.queue_draw()
            elif event.state & Gdk.ModifierType.BUTTON3_MASK or (event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3):
                self.pixel_grid[y][x] = ""
                widget.queue_draw()

    def save_and_exit(self, button):
        username = self.username_entry.get_text().strip()
        if not username:
            self.username_entry.set_placeholder_text("USERNAME REQUIRED!")
            return

        print("Connecting to PocketBase to create player...")
        player_id = "OFFLINE_MODE"
        try:
            pb_url = "https://mmos.retrotechspecs.com"
            response = requests.post(f"{pb_url}/api/collections/players/records", json={
                "username": username,
                "pixel_art": self.pixel_grid,
                "privacy": self.vis_combo.get_active_id()
            }, timeout=5)
            response.raise_for_status()
            player_id = response.json().get("id")
            print(f"Success! Player ID: {player_id}")
        except Exception as e:
            print(f"Database error: {e}. Defaulting to offline mode.")

        settings = {
            "player_id": player_id,
            "username": username,
            "mouse_mode": self.mode_combo.get_active_id(),
            "visibility": self.vis_combo.get_active_id(),
            "broadcasting": self.broad_combo.get_active_id(),
            "friends_list": [],
            "pixel_art": self.pixel_grid
        }

        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=4)

        print("Setup complete! Saved to:", SETTINGS_FILE)
        sys.exit(0)

if __name__ == '__main__':
    app = MMOSInstaller()
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    Gtk.main()
