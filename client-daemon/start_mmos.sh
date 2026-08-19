#!/bin/bash

# Define where the settings file lives
SETTINGS_FILE="$HOME/.config/mmos/settings.json"

# Check if the user has already installed/setup their character
if [ -f "$SETTINGS_FILE" ]; then
    echo "Profile found! Starting MMOS overlay..."
    python /opt/mmos/overlay.py
else
    echo "First boot detected! Starting Installer..."
    python /opt/mmos/installer.py

    # After the installer finishes and closes, automatically launch the overlay
    if [ -f "$SETTINGS_FILE" ]; then
        python /opt/mmos/overlay.py
    fi
fi
