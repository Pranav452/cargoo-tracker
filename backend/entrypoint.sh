#!/bin/bash
# Clean up any stale X lock files
rm -f /tmp/.X99-lock /tmp/.X11-unix/X99
# Start Xvfb in background
Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &
# Wait for Xvfb to be ready
sleep 3
# Export DISPLAY
export DISPLAY=:99
# Execute the main command
exec "$@"
