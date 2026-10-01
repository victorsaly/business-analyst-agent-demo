"""Prepared answers for the online Story chat (GitHub Pages has no server, so it can't call the AI).

Asks the AI each question below with the same notes and rules as the local chat, and saves the answers to
web/story/answers.json. Re-run after editing docs/history.md:   ./demo.sh story   (then ./demo.sh site)
"""
import json
import os
import time

from analyst import story

QUESTIONS = [
    "What is this project, in one minute?",
    "Is this a real company, with real data?",
    "Where did the project start?",
    "What did the brief ask us to build?",
    "Walk me through the timeline, step by step.",
    "Why didn't you rewrite the notebook from scratch?",
    "How did you cut the cost of the AI?",
    "What are the five tools, in plain English?",
    "What are the guardrails, and how are they enforced?",
    "How do we know the numbers are right?",
    "Why is there a Replay mode?",
    "Why does the agent switch from Groq to OpenAI?",
    "Why does it look like a cassette tape?",
    "What is the difference between the Stakeholder and Developer views?",
    "What went wrong, and what did you learn?",
    "What is still not done?",
]

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "story", "answers.json")


def main():
    out = []
    for q in QUESTIONS:
        r = story.answer(q)
        if "error" in r:
            raise SystemExit(f"Stopped at {q!r}: {r['error']}")
        out.append({"q": q, "a": r["answer"], "model": r["model"]})
        print(f"- {q}\n  {r['answer'][:120]}…")
        time.sleep(1)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump({"made": time.strftime("%Y-%m-%d %H:%M"), "answers": out}, open(OUT, "w", encoding="utf-8"), indent=1)
    print(f"Saved {len(out)} answers to {OUT}")


if __name__ == "__main__":
    main()
