#!/bin/bash
# Run me (once) on Linux to set up the demo:  bash "Linux - 1 Setup.sh"   Takes about 5 minutes.
cd "$(dirname "$0")/app" || exit 1
echo "== Business Performance Analyst Agent: setup (Linux) =="
step() { STEP="$1"; printf '\033]0;Setup %s\007' "$STEP"; echo; echo "[$STEP] $2"; }
fail() {
  printf '\033]0;Setup FAILED\007'
  echo; echo "===== SETUP FAILED at step $STEP ====="
  echo "${1:-See the message above. Check your internet connection and run this file again.}"
  echo "Finished steps are quick on a re-run."
  read -r -p "Press Enter to close this window." _; exit 1
}
if ! python3 -c "import sys; assert sys.version_info >= (3, 10)" 2>/dev/null; then
  echo
  echo "Python 3.10 or newer is not installed yet. Install it with your package manager, for example:"
  echo "  Ubuntu/Debian:  sudo apt install python3 python3-venv"
  echo "  Fedora:         sudo dnf install python3"
  echo "Then run this file again."
  read -r -p "Press Enter to close this window." _; exit 1
fi
step "1/4 Creating the Python environment" "in app/.venv ..."
# Ubuntu/Debian ship Python without venv; a half-made .venv would break the next try
python3 -m venv .venv || { rm -rf .venv; fail "Install Python's venv module (Ubuntu/Debian: sudo apt install python3-venv), then run this file again."; }
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
echo "A text editor opens app/.env. Paste the key after GROQ_API_KEY= and save it."
echo "(No key? Skip this: Replay mode works without one.)"
if [ -n "$DISPLAY$WAYLAND_DISPLAY" ] && command -v xdg-open >/dev/null; then
  xdg-open .env >/dev/null 2>&1 &
  read -r -p "When you have saved it (or to skip), press Enter here to check the key." _
else
  "${EDITOR:-nano}" .env
fi
.venv/bin/python check_key.py
echo
echo "Next: bash \"Linux - 2 Start.sh\""
read -r -p "Press Enter to close this window." _
