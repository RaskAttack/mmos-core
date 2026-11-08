import sys
import os
import json
import time
import signal
import hashlib
import subprocess
import requests

from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QFont, QCursor

# PocketBase backend endpoint and local configuration paths
POCKETBASE_URL = "http://10.0.0.146:8090"
SETTINGS_PATH = os.path.expanduser("~/.config/mmos/settings.json")

# Standard headers to bypass Cloudflare bot challenges and request JSON payloads
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) MMOS-Daemon/1.0",
    "Accept": "application/json",
}


def load_settings() -> dict:
    """Loads player configuration saved during installation."""
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"[Settings] Failed to load local settings: {e}")
    # Fallback to an empty 16x16 grid and default ID if uninitialized
    return {
        "player_id": "test_local_player",
        "pixel_art": [["" for _ in range(16)] for _ in range(16)]
    }


def get_active_window_class() -> str:
    """Fetches the active window class under KDE/X11 using xdotool and xprop."""
    try:
        window_id = subprocess.check_output(
            ["xdotool", "getactivewindow"], stderr=subprocess.DEVNULL
        ).decode().strip()
        wm_class = subprocess.check_output(
            ["xprop", "-id", window_id, "WM_CLASS"], stderr=subprocess.DEVNULL
        ).decode().strip()

        # Example format: WM_CLASS(STRING) = "zen-browser", "zen-browser"
        parts = wm_class.split("=")[-1].strip().replace('"', '').split(", ")
        return parts[-1] if parts else "desktop"
    except Exception:
        return "desktop"


def get_app_hash() -> str:
    """Computes a 12-character SHA-256 hash representing the focused application window."""
    wm_class = get_active_window_class()
    return hashlib.sha256(wm_class.encode("utf-8")).hexdigest()[:12]


def safe_parse_json(response: requests.Response) -> dict | None:
    """Safely decodes JSON payloads without throwing line 1 column 1 errors on empty responses."""
    if not response or not response.text.strip():
        return None
    try:
        return response.json()
    except json.JSONDecodeError:
        return None


class PresenceSyncWorker(QThread):
    peers_updated = pyqtSignal(list)

    def __init__(self, player_id: str):
        super().__init__()
        self.player_id = player_id
        self.presence_record_id = None
        self.running = True

    def run(self):
        while self.running:
            try:
                # 1. Grab global cursor coordinates and context hash
                cursor = QCursor.pos()
                x, y = cursor.x(), cursor.y()
                app_hash = get_app_hash()

                # Add this debug print:
                print(f"[Debug] Live Pos: X={x}, Y={y} | App={app_hash}")
                # 2. Sync own coordinates to PocketBase presence collection
                self.sync_own_presence(app_hash, x, y)

                # 3. Pull other active players in the identical app_hash context
                peers = self.fetch_peers(app_hash)
                self.peers_updated.emit(peers)

                time.sleep(0.1)  # 10 FPS rate-limit
            except Exception as e:
                print(f"[Sync Worker] Loop exception: {e}")
                time.sleep(1)

    def sync_own_presence(self, app_hash: str, x: int, y: int):
        payload = {
            "player_id": self.player_id,
            "app_hash": app_hash,
            "x": x,
            "y": y
        }

        if not self.presence_record_id:
            check_url = f"{POCKETBASE_URL}/api/collections/presence/records?filter=(player_id='{self.player_id}')"
            try:
                res = requests.get(check_url, headers=REQUEST_HEADERS, timeout=2)
                data = safe_parse_json(res)
                if data and data.get("items"):
                    self.presence_record_id = data["items"][0]["id"]
                    print(f"[Sync] Found existing presence record: {self.presence_record_id}")
                else:
                    create_url = f"{POCKETBASE_URL}/api/collections/presence/records"
                    res_create = requests.post(create_url, json=payload, headers=REQUEST_HEADERS, timeout=2)
                    if res_create.status_code in (200, 201):
                        create_data = safe_parse_json(res_create)
                        self.presence_record_id = create_data.get("id")
                        print(f"[Sync] Created new presence record: {self.presence_record_id}")
                    else:
                        print(f"[Sync Error] PocketBase rejected creation ({res_create.status_code}): {res_create.text}")
                    return
            except requests.RequestException as e:
                print(f"[Sync Worker] Presence check/create failed: {e}")
                return

        update_url = f"{POCKETBASE_URL}/api/collections/presence/records/{self.presence_record_id}"
        try:
            res_patch = requests.patch(update_url, json=payload, headers=REQUEST_HEADERS, timeout=2)
            if res_patch.status_code not in (200, 204):
                print(f"[Sync Error] Patch failed ({res_patch.status_code}): {res_patch.text}")
        except requests.RequestException as e:
            print(f"[Sync Worker] Presence patch failed: {e}")

    def fetch_peers(self, app_hash: str) -> list:
        # Fetch presence records with matching app_hash, excluding self, expanding player metadata
        url = (
            f"{POCKETBASE_URL}/api/collections/presence/records"
            f"?filter=(app_hash='{app_hash}' && player_id!='{self.player_id}')"
            f"&expand=player_id"
        )
        try:
            res = requests.get(url, headers=REQUEST_HEADERS, timeout=2)
            data = safe_parse_json(res)
            if not data:
                return []

            items = data.get("items", [])
            valid_peers = []
            for item in items:
                player_rel = item.get("expand", {}).get("player_id", {})
                privacy = player_rel.get("privacy", "all")

                # Respect player privacy settings
                if privacy == "none":
                    continue

                valid_peers.append({
                    "x": item.get("x", 0),
                    "y": item.get("y", 0),
                    "username": player_rel.get("username", "Unknown"),
                    "pixel_art": player_rel.get("pixel_art", [])
                })
            return valid_peers
        except requests.RequestException:
            return []

    def stop(self):
        self.running = False


class CursorOverlay(QWidget):
    def __init__(self, player_id: str):
        super().__init__()
        self.peers = []
        self.init_window()

        self.worker = PresenceSyncWorker(player_id)
        self.worker.peers_updated.connect(self.on_peers_updated)
        self.worker.start()

    def init_window(self):
        # Configure pass-through, top-level transparent overlay
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowTransparentForInput |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.showFullScreen()

    def on_peers_updated(self, peers: list):
        self.peers = peers
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.setFont(QFont("Monospace", 9, QFont.Weight.Bold))

        for peer in self.peers:
            base_x = int(peer.get("x", 0))
            base_y = int(peer.get("y", 0))
            matrix = peer.get("pixel_art", [])

            # Draw 16x16 pixel matrix scaled by 2 (32x32 pixels)
            if isinstance(matrix, list):
                for row_idx, row in enumerate(matrix):
                    if not isinstance(row, list):
                        continue
                    for col_idx, hex_color in enumerate(row):
                        if hex_color and isinstance(hex_color, str) and hex_color.startswith("#"):
                            painter.fillRect(
                                base_x + (col_idx * 2),
                                base_y + (row_idx * 2),
                                2, 2,
                                QColor(hex_color)
                            )

            # Draw username badge with contrast outline
            username = peer.get("username", "")
            if username:
                painter.setPen(QColor("#000000"))
                painter.drawText(base_x + 1, base_y - 3, username)
                painter.setPen(QColor("#FFFFFF"))
                painter.drawText(base_x, base_y - 4, username)

        painter.end()

    def closeEvent(self, event):
        self.worker.stop()
        self.worker.wait()
        super().closeEvent(event)


if __name__ == "__main__":
    # Ensure terminal SIGINT (Ctrl+C) interrupts the PyQt event loop cleanly
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    settings = load_settings()
    app = QApplication(sys.argv)
    overlay = CursorOverlay(player_id=settings.get("player_id", "local_test_id"))
    sys.exit(app.exec())
