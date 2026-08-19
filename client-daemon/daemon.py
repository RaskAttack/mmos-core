import subprocess
import time
import requests
import json

# Your Cloudflare Tunnel URL
POCKETBASE_URL = "https://mmos.retrotechspecs.com"
# We'll hardcode an ID for testing right now
RECORD_ID = "i5wf2gcyh0gszo2"

def get_mouse_position():
    """Asks Hyprland for the current X, Y coordinates"""
    try:
        # Runs `hyprctl cursorpos` in the terminal
        result = subprocess.run(["hyprctl", "cursorpos"], capture_output=True, text=True)
        # Returns something like "1920, 1080"
        coords = result.stdout.strip().split(", ")
        return int(coords[0]), int(coords[1])
    except Exception as e:
        print(f"Error reading mouse: {e}")
        return 0, 0

def send_position_to_server(x, y):
    """Sends the coordinates to PocketBase"""
    url = f"{POCKETBASE_URL}/api/collections/presence/records/{RECORD_ID}"

    # We will normalize these later based on screen resolution
    data = {
        "x": x,
        "y": y
    }

    try:
        requests.patch(url, json=data)
    except Exception as e:
        print(f"Connection failed: {e}")

# The Main Loop
if __name__ == "__main__":
    print("MMOS Daemon Started...")
    while True:
        x, y = get_mouse_position()
        print(f"Moving to: {x}, {y}")

        # Send to server (update 10 times a second)
        send_position_to_server(x, y)
        time.sleep(0.1)
