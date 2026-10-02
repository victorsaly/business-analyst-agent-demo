#!/bin/bash
# Double-click me on a Mac to start the demo. Close this window to stop it.
cd "$(dirname "$0")/app" || exit 1
if [ ! -x .venv/bin/python ]; then
  echo "Run 'Mac - 1 Setup.command' first."; read -r -p "Press Enter to close this window." _; exit 1
fi
.venv/bin/python -m scripts.check_key
echo
echo "Starting the demo... your browser will open http://localhost:8501"
echo "Keep this window open while you present. Close it to stop the demo."
(sleep 3; open http://localhost:8501) &
.venv/bin/python server.py
