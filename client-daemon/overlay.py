import gi
import time
import threading
import json
import requests
import subprocess
import math
import hashlib
import atexit
from gi.repository import GLib

gi.require_version('Gtk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import Gtk, Gdk, GtkLayerShell
import cairo

POCKETBASE_URL = "https://mmos.retrotechspecs.com"
MY_ID = None
CURRENT_CONTEXT = ""

# Simulated local settings (Later this will be loaded from a settings.json file during OS login)
LOCAL_SETTINGS = {
    "privacy": "all",  # Options: "all", "friends", "none"
    "friends_list": [] # List of friend Record IDs
}

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
        # Force click-through on every frame (The "Nuclear Fix")
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

    def remove_player(self, player_id):
        """Removes a player from the screen when they leave the app"""
        if player_id in self.other_players:
            del self.other_players[player_id]
            self.queue_draw()


# --- NETWORK & SYSTEM LOGIC ---

def join_server():
    """Tells PocketBase we are online and gets a unique Record ID"""
    global MY_ID
    print("Joining MMOS Server...")
    try:
        response = requests.post(f"{POCKETBASE_URL}/api/collections/presence/records", json={
            "x": 0,
            "y": 0,
            "context_hash": "desktop"
        })
        response.raise_for_status()
        MY_ID = response.json().get("id")
        print(f"Successfully joined! My ID is: {MY_ID}")
        return True
    except Exception as e:
        print(f"Failed to join server: {e}")
        return False

def leave_server():
    """Deletes our presence record from the database when we close the OS"""
    if MY_ID:
        print(f"Shutting down... deleting record {MY_ID} from server.")
        try:
            # Send a fast DELETE request to PocketBase
            requests.delete(f"{POCKETBASE_URL}/api/collections/presence/records/{MY_ID}", timeout=2)
        except Exception:
            pass # Ignore errors if the internet is already disconnected

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

def get_active_context():
    """Gets the currently focused window class and hashes it for privacy"""
    try:
        result = subprocess.run(["hyprctl", "activewindow", "-j"], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip() and result.stdout.strip() != "{}":
            window_data = json.loads(result.stdout)
            app_class = window_data.get("class", "desktop")
            return hashlib.sha256(app_class.encode()).hexdigest()
    except Exception:
        pass # Not running Hyprland or no active window

    # Fallback for KDE testing
    return hashlib.sha256(b"kde-desktop").hexdigest()

def sender_loop():
    """Constantly reads the mouse/context and updates PocketBase"""
    global CURRENT_CONTEXT
    while MY_ID is None:
        time.sleep(1)

    url = f"{POCKETBASE_URL}/api/collections/presence/records/{MY_ID}"

    while True:
        # PRIVACY CHECK: Do not broadcast if set to none
        if LOCAL_SETTINGS["privacy"] == "none":
            time.sleep(1)
            continue

        x, y = get_local_mouse()
        CURRENT_CONTEXT = get_active_context()

        try:
            requests.patch(url, json={"x": x, "y": y, "context_hash": CURRENT_CONTEXT})
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
                            requests.post(url, json={"clientId": data["clientId"], "subscriptions": ["presence"]})

                        record = data.get("record", {})
                        record_id = record.get("id")

                        if record_id and record_id != MY_ID:
                            their_context = record.get("context_hash")

                            # 1. CONTEXT CHECK: Same app?
                            if their_context != CURRENT_CONTEXT:
                                GLib.idle_add(overlay.remove_player, record_id)
                                continue

                            # 2. FRIEND CHECK
                            if LOCAL_SETTINGS["privacy"] == "friends":
                                if record_id not in LOCAL_SETTINGS["friends_list"]:
                                    continue

                            # Draw them!
                            x, y = record.get("x", 0), record.get("y", 0)
                            GLib.idle_add(overlay.update_player, record_id, int(x), int(y))

                    except json.JSONDecodeError:
                        continue
        except:
            time.sleep(3) # Wait 3 seconds before trying to reconnect


if __name__ == '__main__':
    app = MMOSClient()

    if join_server():
        # Tell Python to ALWAYS run leave_server() right before the script dies
        atexit.register(leave_server)

        threading.Thread(target=sender_loop, daemon=True).start()
        threading.Thread(target=receiver_loop, args=(app,), daemon=True).start()

    # Run the UI. Wrap it in a try/except so Ctrl+C closes it cleanly.
    try:
        Gtk.main()
    except KeyboardInterrupt:
        pass
