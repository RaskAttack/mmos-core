import gi
import time
import threading
import json
import requests
import subprocess
import math
import hashlib
import os
import atexit
from gi.repository import GLib

gi.require_version('Gtk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import Gtk, Gdk, GtkLayerShell
import cairo

POCKETBASE_URL = "https://mmos.retrotechspecs.com"
MY_ID = None
CURRENT_CONTEXT = ""

SETTINGS_FILE = os.path.expanduser("~/.config/mmos/settings.json")

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "player_id": "OFFLINE_MODE",
        "username": "Player",
        "visibility": "all",
        "broadcasting": "all",
        "friends_list": [],
        "pixel_art": []
    }

LOCAL_SETTINGS = load_settings()

class MMOSClient(Gtk.Window):
    def __init__(self):
        super().__init__()

        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.BOTTOM, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, True)

        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.NONE)
        self.set_accept_focus(False)
        self.set_can_focus(False)

        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)
        self.set_app_paintable(True)

        self.other_players = {}
        self.connect('draw', self.on_draw)
        self.show_all()

    def hex_to_rgb(self, hex_color):
        """Converts #FF0000 into Cairo-friendly (1.0, 0.0, 0.0)"""
        try:
            hex_color = hex_color.lstrip('#')
            return tuple(int(hex_color[i:i+2], 16)/255.0 for i in (0, 2, 4))
        except Exception:
            return (1.0, 0.0, 0.0) # Fallback to red if parsing fails

    def on_draw(self, widget, cr):
        empty_region = cairo.Region()
        self.input_shape_combine_region(empty_region)

        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()

        cr.set_operator(cairo.OPERATOR_OVER)

        for player_id, data in self.other_players.items():
            x, y = data["x"], data["y"]
            pixel_art = data.get("pixel_art", [])

            if not pixel_art:
                # Fallback solid box if no art exists
                cr.set_source_rgba(1.0, 0.0, 0.0, 1.0)
                cr.rectangle(x, y, 16, 16)
                cr.fill()
                continue

            # Render the 16x16 grid!
            scale = 2 # Multiplies the grid so it renders as a 32x32 cursor

            for row_idx, row in enumerate(pixel_art):
                for col_idx, color in enumerate(row):
                    if color and isinstance(color, str) and color.startswith("#"):
                        r, g, b = self.hex_to_rgb(color)
                        cr.set_source_rgba(r, g, b, 1.0)
                        # Draw the scaled pixel
                        cr.rectangle(x + (col_idx * scale), y + (row_idx * scale), scale, scale)
                        cr.fill()

        return False

    def update_player(self, player_id, x, y, pixel_art=None):
        self.other_players[player_id] = {"x": x, "y": y, "pixel_art": pixel_art}
        self.queue_draw()

    def remove_player(self, player_id):
        if player_id in self.other_players:
            del self.other_players[player_id]
            self.queue_draw()

def join_server():
    global MY_ID

    saved_player_id = LOCAL_SETTINGS.get("player_id")
    if not saved_player_id or saved_player_id == "OFFLINE_MODE":
        print("No valid player ID found. Running in offline mode.")
        return False

    print(f"Authenticating as {saved_player_id}...")
    try:
        response = requests.post(f"{POCKETBASE_URL}/api/collections/persistance/records", json={
            "player_id": saved_player_id,
            "x": 0,
            "y": 0,
            "app_hash": "desktop"
        }, timeout=5)
        response.raise_for_status()
        MY_ID = response.json().get("id")
        print(f"Successfully joined the map! Session ID: {MY_ID}")
        return True
    except Exception as e:
        print(f"Failed to join server: {e}")
        return False

def leave_server():
    if MY_ID:
        print(f"Shutting down... removing record {MY_ID}")
        try:
            requests.delete(f"{POCKETBASE_URL}/api/collections/persistance/records/{MY_ID}", timeout=2)
        except Exception:
            pass

def get_local_mouse():
    try:
        result = subprocess.run(["hyprctl", "cursorpos"], capture_output=True, text=True)
        if result.returncode == 0:
            coords = result.stdout.strip().split(", ")
            return int(coords[0]), int(coords[1])
    except FileNotFoundError:
        pass

    t = time.time() * 2
    return int(960 + 300 * math.cos(t)), int(540 + 300 * math.sin(t))

def get_active_context():
    try:
        result = subprocess.run(["hyprctl", "activewindow", "-j"], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip() and result.stdout.strip() != "{}":
            window_data = json.loads(result.stdout)
            app_class = window_data.get("class", "desktop")
            return hashlib.sha256(app_class.encode()).hexdigest()
    except Exception:
        pass

    return hashlib.sha256(b"kde-desktop").hexdigest()

def sender_loop():
    global CURRENT_CONTEXT
    while MY_ID is None:
        time.sleep(1)

    url = f"{POCKETBASE_URL}/api/collections/persistance/records/{MY_ID}"

    while True:
        if LOCAL_SETTINGS.get("broadcasting") == "none":
            time.sleep(1)
            continue

        x, y = get_local_mouse()
        CURRENT_CONTEXT = get_active_context()

        try:
            requests.patch(url, json={"x": x, "y": y, "app_hash": CURRENT_CONTEXT}, timeout=2)
        except Exception:
            pass
        time.sleep(0.1)

def receiver_loop(overlay):
    url = f"{POCKETBASE_URL}/api/realtime"
    while True:
        try:
            if LOCAL_SETTINGS.get("visibility") == "none":
                time.sleep(1)
                continue

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
                            requests.post(url, json={"clientId": data["clientId"], "subscriptions": ["persistance"]}, timeout=2)

                        record = data.get("record", {})
                        record_id = record.get("id")

                        if record_id and record_id != MY_ID:
                            their_context = record.get("app_hash")

                            if their_context != CURRENT_CONTEXT:
                                GLib.idle_add(overlay.remove_player, record_id)
                                continue

                            if LOCAL_SETTINGS.get("visibility") == "friends":
                                if record_id not in LOCAL_SETTINGS.get("friends_list", []):
                                    continue

                            x, y = record.get("x", 0), record.get("y", 0)

                            # TEMPORARY: For testing the graphics engine right now,
                            # we are rendering other players using YOUR local pixel art array!
                            # In the next step, we will wire this up to pull THEIR art from the 'players' collection.
                            pixel_art = LOCAL_SETTINGS.get("pixel_art", [])

                            GLib.idle_add(overlay.update_player, record_id, int(x), int(y), pixel_art)

                    except json.JSONDecodeError:
                        continue
        except Exception:
            time.sleep(3)

if __name__ == '__main__':
    app = MMOSClient()

    if join_server():
        atexit.register(leave_server)
        threading.Thread(target=sender_loop, daemon=True).start()
        threading.Thread(target=receiver_loop, args=(app,), daemon=True).start()

    try:
        Gtk.main()
    except KeyboardInterrupt:
        pass
