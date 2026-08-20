# Force Wayland to work inside Virtual Machines
export WLR_NO_HARDWARE_CURSORS=1
export WLR_RENDERER_ALLOW_SOFTWARE=1
export LIBGL_ALWAYS_SOFTWARE=1
export XDG_SESSION_TYPE=wayland

# Auto-start Hyprland on login
if [ -z "$DISPLAY" ] && [ "$XDG_VTNR" -eq 1 ]; then
  Hyprland
fi
