"""Run every demo case LIVE once and save it, so Replay mode and the video use real AI answers.

  .venv/bin/python prepare_recordings.py              # all cases + scorecard extras + briefing
  .venv/bin/python prepare_recordings.py northwest_margin guard_forecast   # just these cases

Uses about 120-160k tokens on the free Groq plan (the daily allowance is about 200k per model).
"""
import sys
import time

from analyst import agent, briefing, cases

PAUSE = 20   # seconds between questions, to stay under the free plan's tokens-per-minute limit


def show(i, name, args, result):
    print(f"   step {i}: {name} -> {agent.describe_step(name, args, result)[:160]}")


def main(only):
    if not agent.llm_ready():
        sys.exit("No AI key. Put GROQ_API_KEY=... in app/.env first.")
    todo = [c for c in cases.CASES if (not only and c["id"] != "planted_anomaly") or c["id"] in only]
    extras = [] if only else ["What is our return rate by territory?"]   # the scorecard question with no case
    for c in todo:
        print(f"\n== {c['title']}: {c['question']}")
        hist = []
        if c.get("follow_up_of"):
            parent = cases.load_recording(cases.case_key(cases.CASE_BY_ID[c["follow_up_of"]]))
            hist = [parent] if parent else []
        res = cases.answer(c["question"], "live", case=c, history=hist, on_step=show, on_wait=print)
        print(res["answer"][:500], f"\n   ({res['tokens']:,} tokens, {res['seconds']}s)")
        time.sleep(PAUSE)
    for q in extras:
        print(f"\n== Scorecard extra: {q}")
        res = cases.answer(q, "live", on_step=show, on_wait=print)
        print(res["answer"][:300])
        time.sleep(PAUSE)
    if not only or "briefing" in only:
        print("\n== Weekly briefing (latest full week)")
        b = briefing.build(mode="live", on_step=show, on_wait=print)
        print(b["answer"][:500])
    print("\nDone. Recordings are in app/recordings/. Now: ./demo.sh video")


if __name__ == "__main__":
    main(sys.argv[1:])
