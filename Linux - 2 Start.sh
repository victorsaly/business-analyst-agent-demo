#!/bin/bash
# Run me on Linux to start the demo:  bash "Linux - 2 Start.sh"   Press Ctrl C (or close the window) to stop it.
cd "$(dirname "$0")/app" || exit 1
if [ ! -x .venv/bin/python ]; then
  echo "Run 'Linux - 1 Setup.sh' first."; read -r -p "Press Enter to close this window." _; exit 1
fi
.venv/bin/python -m scripts.check_key
echo
echo "Starting the demo... open http://localhost:8501 in your browser"
echo "Keep this window open while you present. Press Ctrl C or close it to stop the demo."
command -v xdg-open >/dev/null && (sleep 3; xdg-open http://localhost:8501 >/dev/null 2>&1) &
.venv/bin/python server.py
