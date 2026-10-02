#!/bin/bash
# Double-click me (once) on a Mac to set up the demo. Takes about 5 minutes.
cd "$(dirname "$0")/app" || exit 1
echo "== Business Performance Analyst Agent: setup (Mac) =="
step() { STEP="$1"; printf '\033]0;Setup %s\007' "$STEP"; echo; echo "[$STEP] $2"; }
fail() {
  printf '\033]0;Setup FAILED\007'
  echo; echo "===== SETUP FAILED at step $STEP ====="
  echo "See the message above. Check your internet connection and double-click this file again."
  echo "Finished steps are quick on a re-run."
  read -r -p "Press Enter to close this window." _; exit 1
}
if ! python3 -c "import sys; assert sys.version_info >= (3, 10)" 2>/dev/null; then
  echo
  echo "Python 3.10 or newer is not installed yet."
  echo "Your browser will now open python.org. Download and install Python for macOS,"
  echo "then double-click this file again."
  open "https://www.python.org/downloads/macos/"
  read -r -p "Press Enter to close this window." _; exit 1
fi
step "1/4 Creating the Python environment" "in app/.venv ..."
python3 -m venv .venv || fail
step "2/4 Updating pip" "..."
.venv/bin/pip install --upgrade pip --disable-pip-version-check || fail
step "3/4 Installing Python packages" "This is the slow part, a few minutes. Progress shows below."
.venv/bin/pip install -r requirements.txt --disable-pip-version-check || fail
[ -f .env ] || cp .env.example .env
step "4/4 Preparing the AdventureWorks database" "..."
.venv/bin/python -c "from analyst import data; print('Database ready:', data.DB_FILES['real'])" || fail
printf '\033]0;Setup done\007'
echo
echo "===== SETUP DONE ====="
echo
echo "Last step: your free AI key for Live AI (get one at https://console.groq.com/keys)."
echo "TextEdit opens a file called .env. Paste the key after GROQ_API_KEY= and save it (Cmd S)."
echo "(No key? Skip this: Replay mode works without one.)"
open -e .env
read -r -p "When you have saved it (or to skip), press Enter here to check the key." _
.venv/bin/python -m scripts.check_key
echo
echo "Next: double-click 'Mac - 2 Start.command'."
read -r -p "Press Enter to close this window." _
