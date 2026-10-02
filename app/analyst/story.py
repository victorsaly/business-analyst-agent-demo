"""The Ask chat: answers course students' questions about the task, its steps, the course material and how
this project was built.

Every question gets our notes: docs/requirements.md (the brief, line by line), docs/history.md (the project
timeline) and docs/build-guide.md (the task as numbered steps: its outline plus the sections that match the
question best, code left out). It also gets COURSE MATERIAL: the passages that best match the question from
the course's training guide and starting notebook and our finished notebook (analyst/knowledge.py), cited as
[1], [2]. Locally the AI is the service in .env. Online, worker/ asks the same way, using fixed_prompt() and
the knowledge base exported by scripts/make_knowledge.py; scripts/make_story_answers.py prepares fallback answers.
"""
import json
import os
import re

import requests

from . import knowledge
from .agent import LLMError, _chat, _estimate_tokens, current

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCS = os.path.join(ROOT, "docs")
HISTORY = os.path.join(DOCS, "history.md")
BRIEF = os.path.join(DOCS, "requirements.md")
GUIDE = os.path.join(DOCS, "build-guide.md")
TEAM = os.path.join(ROOT, "app", "web", "team.json")   # who built it; ./demo.sh team fills it from the team form
GUIDE_SECTIONS = 3               # build-guide sections sent with each question
COURSE_PASSAGES = 6              # course-material passages sent with each question
GROQ_BUDGET = 8000               # estimated tokens; keeps a question plus answer under Groq's free 8,000 per minute
NOTES = {"docs/requirements.md", "docs/history.md", "docs/build-guide.md"}   # already sent in full or by section

STORY_PROMPT = """You answer questions about a course project: the "Business Performance Analyst Agent",
Capstone 2 of the Agentic AI Workshop 2026. Most askers are students on the course. People ask four kinds of question:
- THE TASK: what the brief asks for, and whether each requirement is met (see THE BRIEF);
- THE STEPS: how to do the task, step by step (see THE STEP-BY-STEP GUIDE);
- THE STORY: how the project got to where it is (see PROJECT HISTORY);
- THE COURSE: what the training guide, the starting notebook or our finished notebook say or do (see COURSE MATERIAL);
- THE TEAM: who is on the project team and what each person did (see THE TEAM).

RULES
1. Answer ONLY from the notes and course material below. If they don't cover it, say "The course
   material and our notes don't cover that" and suggest what they do cover.
2. Plain English for a non-technical reader: 2 to 5 short sentences, or a few bullets. Explain any
   technical word in passing. Use times and numbers exactly as the notes give them.
3. For a step: name it ("Step 2: Load AdventureWorks"), then say what to do, why, and how to check it
   worked, in that order. Don't paste code: say "the code is in docs/build-guide.md, Step N".
   For "what are the steps", list every step with its number and a few words each.
4. If asked about the company or the data: it is a course demonstration; AdventureWorks is Microsoft's
   public sample data about a made-up bicycle company.
5. No markdown headings. **Bold** is fine.
6. When you use a COURSE MATERIAL passage, cite it by its number, like [2] or [1][3], right after the
   sentence it supports. A short code snippet from it is fine when the question is about code.

THE BRIEF (docs/requirements.md)
{brief}

THE STEP-BY-STEP GUIDE (docs/build-guide.md: its outline, then the sections that match this question)
{guide}

PROJECT HISTORY (docs/history.md)
{history}

THE TEAM (app/web/team.json, in the order the site shows them)
{team}

COURSE MATERIAL (numbered passages picked for this question)
{passages}
"""

_STOP = set("a an and are as at be but by can did do does for from how i in is it its me my of on or our so "
            "that the this to was we what when where which who why will with you your step steps".split())


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def team_text():
    """One line per team member: name, role, what they did, LinkedIn."""
    try:
        with open(TEAM, encoding="utf-8") as f:
            members = [m for m in json.load(f).get("members", []) if m.get("name", "").strip()]
    except (OSError, ValueError):
        members = []
    lines = []
    for m in members:
        bio = re.sub(r"\s+", " ", m.get("bio") or "").strip()
        lines.append("- " + " | ".join(x for x in (m["name"].strip(), (m.get("role") or "").strip(), bio,
                                                    (m.get("linkedin") or "").strip()) if x))
    return f"{len(members)} people:\n" + "\n".join(lines) if members else "(not listed yet)"


def _words(text):
    return {w.rstrip("s") for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _STOP and len(w) > 1}


def _guide_sections(guide):
    """[(heading, text)] for every '## ' and '### ' section, with code blocks replaced by a pointer."""
    guide = re.sub(r"```.*?```", "[code: see docs/build-guide.md]", guide, flags=re.S)
    parts = re.split(r"^(?=#{2,3} )", guide, flags=re.M)
    return [(p.splitlines()[0].lstrip("# ").strip(), p.strip()) for p in parts if p.startswith("##")]


def guide_for(question, guide, n=GUIDE_SECTIONS):
    """The guide's outline plus the sections that best match the question (a step named by number always wins)."""
    sections = _guide_sections(guide)
    named = {int(n) for n in re.findall(r"\bstep\s*(\d+)", question.lower())}
    q = _words(question)

    def score(item):
        h, text = item
        m = re.match(r"Step (\d+)", h)
        if m and int(m.group(1)) in named:
            return 1000
        return 3 * len(q & _words(h)) + len(q & _words(text)) / 10

    best = [s for s in sorted(sections, key=score, reverse=True)[:n] if score(s) > 0]
    def line(h, text):
        pri = re.search(r"\*\*Priority:\*\*\s*(P\d)", text)
        return f"- {h}" + (f" ({pri.group(1)})" if pri else "")

    return ("OUTLINE (P1 = must have, P2 = should have, P3 = stretch)\n" + "\n".join(line(h, t) for h, t in sections)
            + "\n\n" + "\n\n".join(t for _, t in best))


def course_passages(question, k=COURSE_PASSAGES):
    """The knowledge-base passages that best match the question, leaving out the notes sent anyway."""
    found = knowledge.index().search(question, k=k + 6)
    return [p for p in found if p["source"] not in NOTES][:k]


def passages_text(passages):
    return "\n\n".join(f"[{i}] ({p['source']} · {p['title']})\n{p['text']}" for i, p in enumerate(passages, 1)) or "(none matched)"


def cited(text, passages):
    """The passages the answer cites, as {n, source, title, url}."""
    nums = sorted({int(n) for n in re.findall(r"\[(\d+)\]", text) if 0 < int(n) <= len(passages)})
    return [{"n": n, "source": passages[n - 1]["source"], "title": passages[n - 1]["title"],
             "url": passages[n - 1].get("url", "")} for n in nums]


def fixed_prompt(marker="@@PASSAGES@@"):
    """The prompt for the online chat (worker/): the guide as an outline only, and a marker where the
    Worker puts the passages it picks for each question."""
    return STORY_PROMPT.format(brief=_read(BRIEF), guide=guide_for("", _read(GUIDE)), history=_read(HISTORY),
                               team=team_text(), passages=marker)


def _prepare(question, history):
    """The messages for the AI, and the course passages they include."""
    asked = " ".join([str(m.get("content", "")) for m in list(history)[-4:] if m.get("role") == "user"] + [question])
    found, sections = course_passages(asked), GUIDE_SECTIONS
    turns = [{"role": m["role"], "content": str(m["content"])[:1500]} for m in list(history)[-4:]
             if m.get("role") in ("user", "assistant")]
    while True:
        system = STORY_PROMPT.format(brief=_read(BRIEF), guide=guide_for(asked, _read(GUIDE), sections),
                                     history=_read(HISTORY), team=team_text(), passages=passages_text(found))
        messages = [{"role": "system", "content": system}, *turns, {"role": "user", "content": question}]
        if current()["name"] != "groq" or _estimate_tokens(messages) <= GROQ_BUDGET:
            return messages, found
        # trim the extras least likely to matter first
        if len(found) > 2:
            found = found[:-1]
        elif sections > 1:
            sections -= 1
        elif turns:
            turns = turns[2:]
        elif found:
            found = found[:-1]
        elif sections:
            sections -= 1
        else:
            return messages, found


def _tidy(text):
    text = re.sub(r"^#+\s*", "", (text or "").strip(), flags=re.M)
    return text or "The course material and our notes don't cover that."


EMPTY = "Ask about the task, a step, the course material, or how the project was built."


def answer(question, history=()):
    """question -> {"answer", "sources", "model"} or {"error"}. history: earlier [{"role", "content"}] turns."""
    question = (question or "").strip()[:500]
    if not question:
        return {"error": EMPTY}
    messages, found = _prepare(question, history)
    try:
        msg = _chat(messages, with_tools=False, max_tokens=800)
    except LLMError as exc:
        return {"error": str(exc)}
    text = _tidy(msg.get("content"))
    return {"answer": text, "sources": cited(text, found), "model": f"{current()['name']} · {current()['model']}"}


def stream_answer(question, history=()):
    """The same answer, as events while it's written: {"type": "delta", "text"} pieces, then
    {"type": "done", "answer", "sources", "model"} (or {"type": "error", "message"})."""
    question = (question or "").strip()[:500]
    if not question:
        yield {"type": "error", "message": EMPTY}
        return
    yield {"type": "status", "stage": "searching"}
    messages, found = _prepare(question, history)
    yield {"type": "status", "stage": "found", "passages": [{"source": x["source"], "title": x["title"]} for x in found]}
    p, text = current(), ""
    body = {"model": p["model"], "messages": messages, "stream": True}
    body["max_completion_tokens" if p["name"] == "openai" else "max_tokens"] = 800
    try:
        with requests.post(f"{p['base']}/chat/completions", json=body, stream=True, timeout=120,
                           headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {p['key']}"} if p["key"] else {})}) as r:
            if r.status_code != 200:
                raise LLMError(f"{r.status_code}")
            for line in r.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data: ") or line == "data: [DONE]":
                    continue
                piece = (json.loads(line[6:]).get("choices") or [{}])[0].get("delta", {}).get("content") or ""
                if piece:
                    text += piece
                    yield {"type": "delta", "text": piece}
    except Exception:
        if not text:   # nothing streamed yet (e.g. this service is out of allowance): the normal call switches services
            r = answer(question, history)
            if "error" in r:
                yield {"type": "error", "message": r["error"]}
                return
            yield {"type": "delta", "text": r["answer"]}
            yield {"type": "done", **r}
            return
    text = _tidy(text)
    yield {"type": "done", "answer": text, "sources": cited(text, found), "model": f"{p['name']} · {p['model']}"}
