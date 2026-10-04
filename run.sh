#!/usr/bin/env bash
cd "$(dirname "$0")"

echo ""
echo "==================================================="
echo "  LocalConvert - Privacy-First Local File Toolbox"
echo "==================================================="
echo ""

if command -v python3 &>/dev/null; then
    PY_CMD="python3"
elif command -v python &>/dev/null; then
    PY_CMD="python"
else
    echo "[ERROR] Python 3 is not installed!"
    echo "Please install Python 3 using your package manager or from python.org"
    exit 1
fi

if [ ! -f "venv/bin/python" ]; then
    echo "[+] Setting up local environment (one-time setup)..."
    $PY_CMD -m venv venv || true
fi

if [ -f "venv/bin/python" ]; then
    PY_EXE="venv/bin/python"
else
    PY_EXE=$PY_CMD
fi

echo "[+] Starting LocalConvert on http://127.0.0.1:5001 ..."
echo "[!] Keep this window open while using LocalConvert."
echo ""

"$PY_EXE" app.py
