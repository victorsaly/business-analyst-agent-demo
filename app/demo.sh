#!/usr/bin/env bash
# Local demo helper.  Usage: ./demo.sh [setup|app|prepare|video|video-dry|pitch|timings|story|site|test]
set -euo pipefail
cd "$(dirname "$0")"
PY=.venv/bin/python

case "${1:-app}" in
  setup)
    python3 -m venv .venv
    .venv/bin/pip install -q -r requirements.txt
    $PY -m playwright install chromium
    [ -f .env ] || cp .env.example .env
    $PY -c "from analyst import data; print('Database ready:', data.DB_FILES['real'])"
    echo "Setup done. Put your key in app/.env, then: ./demo.sh app"
    ;;
  app)        echo "Open http://localhost:8501"; (sleep 2; open http://localhost:8501 2>/dev/null || true) & $PY server.py ;;
  prepare)    shift; $PY prepare_recordings.py "$@" ;;
  video)      shift; $PY record_video.py --mode replay "$@" ;;
  video-dry)  shift; $PY record_video.py --mode dry "$@" ;;
  pitch)      shift; $PY make_promo.py "$@" ;;
  timings)    $PY make_explain_timings.py ;;     # after changing an Explain line or its mp3
  story)      $PY make_story_answers.py ;;       # prepared answers for the online Story chat (uses the AI)
  site)       $PY build_site.py ;;               # rebuild ../site (the online copy) from the recordings
  test)       $PY test_demo.py ;;
  *) echo "Usage: ./demo.sh [setup|app|prepare|video|video-dry|pitch|timings|story|site|test]"; exit 1 ;;
esac
