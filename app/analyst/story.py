"""The Story chat: answers questions about how this project was built, from our own notes only.

The notes are docs/history.md, the project timeline. Locally the
answer comes from the AI service in .env; the online copy uses answers prepared by make_story_answers.py.
"""
import os
import re

from .agent import LLMError, _chat, current

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NOTES = os.path.join(ROOT, "docs", "history.md")

STORY_PROMPT = """You tell the story of a course project: how a team built the "Business Performance Analyst
Agent" for Capstone 2 of the Agentic AI Workshop 2026. People ask how the project got to where it is.

RULES
1. Answer ONLY from the project notes below. If they don't cover it, say "Our notes don't cover that"
   and suggest what they do cover.
2. Plain English for a non-technical reader: 2 to 5 short sentences, or a few bullets. Explain any
   technical word in passing. Use times and numbers exactly as the notes give them.
3. If asked about the company or the data: it is a course demonstration; AdventureWorks is Microsoft's
   public sample data about a made-up bicycle company.
4. No markdown headings. **Bold** is fine.

PROJECT NOTES
{notes}
"""


def notes():
    with open(NOTES, encoding="utf-8") as f:
        return f.read()


def answer(question, history=()):
    """question -> {"answer", "model"} or {"error"}. history: earlier [{"role", "content"}] turns."""
    question = (question or "").strip()[:500]
    if not question:
        return {"error": "Ask a question about the project."}
    messages = [{"role": "system", "content": STORY_PROMPT.format(notes=notes())}]
    messages += [{"role": m["role"], "content": str(m["content"])[:1500]} for m in list(history)[-4:]
                 if m.get("role") in ("user", "assistant")]
    messages.append({"role": "user", "content": question})
    try:
        msg = _chat(messages, with_tools=False, max_tokens=700)
    except LLMError as exc:
        return {"error": str(exc)}
    text = re.sub(r"^#+\s*", "", (msg.get("content") or "").strip(), flags=re.M)
    return {"answer": text or "Our notes don't cover that.", "model": f"{current()['name']} · {current()['model']}"}
