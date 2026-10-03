#!/usr/bin/env bash
# =============================================================
#  localconvert — Android / Termux start script
#  Run this in Termux, then open Chrome → http://127.0.0.1:5001
# =============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Kill any previous instance on that port
pkill -f "python app.py" 2>/dev/null || true

echo
echo "  Starting localconvert..."

python app.py &
SERVER_PID=$!

sleep 2

# Try Termux:API browser launch (needs Termux:API app from F-Droid)
if command -v termux-open-url &>/dev/null; then
    termux-open-url http://127.0.0.1:5001
else
    echo
    echo "  ─────────────────────────────────────────"
    echo "  Open Chrome/Firefox and go to:"
    echo "  ➜  http://127.0.0.1:5001"
    echo "  ─────────────────────────────────────────"
    echo "  (Install Termux:API from F-Droid for auto-open)"
fi

echo
echo "  Server running. Press Ctrl+C to stop."
echo

wait $SERVER_PID
