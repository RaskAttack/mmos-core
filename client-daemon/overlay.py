import gi
import time
import threading
import json
import requests
import subprocess
from gi.repository import GLib
import math

gi.require_version('Gtk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import Gtk, Gdk, GtkLayerShell
import cairo

POCKETBASE_URL = "https://mmos.retrotechspecs.com"
MY_ID = None  # We will get this from the server on startup

class MMOSClient(Gtk.Window):
    def __init__(self):
        super().__init__()

        # Setup Layer Shell
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.BOTTOM, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, True)

        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.NONE)
        self.set_accept_focus(False)
        self.set_can_focus(False)

        # Transparency
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)
        self.set_app_paintable(True)

        # Dictionary to store everyone else's coordinates { "record_id": (x, y) }
        self.other_players = {}

        self.connect('draw', self.on_draw)
        self.show_all()

    def on_draw(self, widget, cr):
        # Force click-through on every frame
        empty_region = cairo.Region()
        self.input_shape_combine_region(empty_region)

        # Clear screen
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()

        # Draw all OTHER players
        cr.set_source_rgba(1.0, 0.0, 0.0, 1.0) # Red color
        cr.set_operator(cairo.OPERATOR_OVER)

        for player_id, coords in self.other_players.items():
            cr.rectangle(coords[0], coords[1], 16, 16)
            cr.fill()

        return False

    def update_player(self, player_id, x, y):
        """Updates a player's position and triggers a screen redraw"""
        self.other_players[player_id] = (x, y)
        self.queue_draw()


# --- NETWORK LOGIC ---

def join_server():
    """Tells PocketBase we are online and gets a unique Record ID"""
    global MY_ID
    print("Joining MMOS Server...")
    try:
        response = requests.post(f"{POCKETBASE_URL}/api/collections/presence/records", json={
            "x": 0,
            "y": 0,
            "context_hash": "desktop" # Hardcoded for now
        })
        response.raise_for_status()
        MY_ID = response.json().get("id")
        print(f"Successfully joined! My ID is: {MY_ID}")
        return True
    except Exception as e:
        print(f"Failed to join server: {e}")
        return False

def get_local_mouse():
    """Gets local mouse coordinates. Uses hyprctl on the OS, fakes it on KDE"""
    try:
        result = subprocess.run(["hyprctl", "cursorpos"], capture_output=True, text=True)
        if result.returncode == 0:
            coords = result.stdout.strip().split(", ")
            return int(coords[0]), int(coords[1])
    except FileNotFoundError:
        pass # Not running Hyprland right now

    # Fallback for testing on KDE: Just orbit in a circle
    t = time.time() * 2
    return int(960 + 300 * math.cos(t)), int(540 + 300 * math.sin(t))

def sender_loop():
    """Constantly reads the mouse and updates PocketBase"""
    while MY_ID is None:
        time.sleep(1) # Wait until we have joined

    url = f"{POCKETBASE_URL}/api/collections/presence/records/{MY_ID}"

    while True:
        x, y = get_local_mouse()
        try:
            requests.patch(url, json={"x": x, "y": y})
        except:
            pass # Ignore temporary network drops
        time.sleep(0.1) # Update 10 times a second

def receiver_loop(overlay):
    """Listens to PocketBase for everyone else's movements"""
    url = f"{POCKETBASE_URL}/api/realtime"
    while True:
        try:
            response = requests.get(url, stream=True, headers={"Accept": "text/event-stream"})
            response.raise_for_status()

            for line in response.iter_lines():
                if not line: continue
                decoded_line = line.decode('utf-8')

                if decoded_line.startswith("data:"):
                    data_str = decoded_line.split(":", 1)[1].strip()
                    try:
                        data = json.loads(data_str)
                        if data.get("clientId"):
                            # Handshake complete, subscribe to presence
                            requests.post(url, json={"clientId": data["clientId"], "subscriptions": ["presence"]})

                        # Handle live updates
                        record = data.get("record", {})
                        record_id = record.get("id")

                        # Only update if it's NOT us!
                        if record_id and record_id != MY_ID:
                            x, y = record.get("x", 0), record.get("y", 0)
                            GLib.idle_add(overlay.update_player, record_id, int(x), int(y))

                    except json.JSONDecodeError:
                        continue
        except:
            time.sleep(3)


if __name__ == '__main__':
    # 1. Start the overlay
    app = MMOSClient()

    # 2. Join the server
    if join_server():
        # 3. Start sending and receiving data in the background
        threading.Thread(target=sender_loop, daemon=True).start()
        threading.Thread(target=receiver_loop, args=(app,), daemon=True).start()

    # 4. Start the UI
    Gtk.main()
