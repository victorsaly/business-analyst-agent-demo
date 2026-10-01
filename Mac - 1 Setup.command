#!/bin/bash
# Double-click me (once) on a Mac to set up the demo. Takes about 5 minutes.
cd "$(dirname "$0")/app" || exit 1
echo "== Business Performance Analyst Agent: setup (Mac) =="
if ! python3 -c "import sys; assert sys.version_info >= (3, 10)" 2>/dev/null; then
  echo
  echo "Python 3.10 or newer is not installed yet."
  echo "Your browser will now open python.org. Download and install Python for macOS,"
  echo "then double-click this file again."
  open "https://www.python.org/downloads/macos/"
  read -r -p "Press Enter to close this window." _; exit 1
fi
python3 -m venv .venv && .venv/bin/pip install -q --upgrade pip && .venv/bin/pip install -q -r requirements.txt || {
  echo; echo "Installing the Python packages failed. Check your internet connection and try again."
  read -r -p "Press Enter to close this window." _; exit 1; }
[ -f .env ] || cp .env.example .env
.venv/bin/python -c "from analyst import data; print('Database ready:', data.DB_FILES['real'])" || {
  echo; echo "Downloading the AdventureWorks database failed. Check your internet connection and try again."
  read -r -p "Press Enter to close this window." _; exit 1; }
echo
echo "Setup done."
echo "A text file called .env will open now. Paste your free Groq key after GROQ_API_KEY= and save it."
echo "(No key? Skip this: Replay mode works without one.)"
open -e .env
echo "Next: double-click 'Mac - 2 Start.command'."
read -r -p "Press Enter to close this window." _
