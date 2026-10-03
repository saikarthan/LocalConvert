#!/usr/bin/env bash
cd "$(dirname "$0")"
if [ ! -d venv ]; then
  echo "Setting up environment (one-time)..."
  python3 -m venv venv
  venv/bin/pip install -r requirements.txt
fi
venv/bin/python app.py
