#!/usr/bin/env bash
# Local demo helper.  Usage: ./demo.sh [setup|app|prepare|video|video-dry|pitch|timings|knowledge|story|site|test]
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
  prepare)    shift; $PY -m scripts.prepare_recordings "$@" ;;
  video)      shift; $PY -m scripts.record_video --mode replay "$@" ;;
  video-dry)  shift; $PY -m scripts.record_video --mode dry "$@" ;;
  pitch)      shift; $PY -m scripts.make_promo "$@" ;;
  timings)    $PY -m scripts.make_explain_timings ;;     # after changing an Explain line or its mp3
  knowledge)  shift; $PY -m scripts.make_knowledge "$@" ;;        # the Ask chat's knowledge base: ./demo.sh knowledge --course <course repo>
  story)      shift; $PY -m scripts.make_story_answers "$@" ;;     # prepared answers for the online Story chat (uses the AI)
  site)       $PY -m scripts.build_site ;;               # rebuild ../site (the online copy) from the recordings
  team)       $PY -m scripts.pull_team ;;                # the team form's answers into web/team.json, plus the skills gaps
  test)       $PY test_demo.py ;;
  *) echo "Usage: ./demo.sh [setup|app|prepare|video|video-dry|pitch|timings|knowledge|story|site|team|test]"; exit 1 ;;
esac
