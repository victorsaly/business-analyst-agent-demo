"""The Ask chat's knowledge base: everything a course student might ask about, cut into short passages.

Sources: the course's training guide and starting notebook (read from your local copy of the course repo,
never committed here), our finished notebook, and every docs/*.md. Built by make_knowledge.py into
data/knowledge.json (git-ignored, because it contains course material) and bundled into the online chat's
Cloudflare Worker. search() finds the passages that best match a question (BM25, no extra libraries);
worker/src/index.js does the same in JavaScript.
"""
import json
import math
import os
import re
import zipfile
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(HERE)
ROOT = os.path.dirname(APP)
KB_FILE = os.path.join(APP, "data", "knowledge.json")
BLOG = "https://victorsaly.github.io/business-analyst-agent-demo/blog/"
REPO = "https://github.com/victorsaly/business-analyst-agent-demo/blob/main/"
MAX_CHARS = 1400
ALIASES = {   # extra words that find a source when a student names it their own way
    "Course training guide": "course original training guide workshop",
    "Course starting notebook": "course original starting starter notebook lab old",
    "Our finished notebook": "our new finished adventureworks notebook section",
}

STOP = set("""a about after all also an and any are as at be been but by can could did do does for from had has have how i
if in into is it its just me more most my no not of on or our out so some such than that the their them then there
these they this to up use used using was we were what when where which who why will with would you your""".split())


def words(text):
    return [w for w in re.findall(r"[a-z0-9_]+", text.lower()) if len(w) > 1 and w not in STOP]


def _chunks(source, title, text, url=""):
    """Split one section into passages of at most MAX_CHARS, on paragraph breaks where possible."""
    out, buf = [], ""
    for para in re.split(r"\n\s*\n", text.strip()):
        while len(para) > MAX_CHARS:                       # a very long paragraph or code cell
            if buf:
                out.append(buf); buf = ""
            out.append(para[:MAX_CHARS]); para = para[MAX_CHARS:]
        if len(buf) + len(para) + 2 > MAX_CHARS and buf:
            out.append(buf); buf = ""
        buf = f"{buf}\n\n{para}" if buf else para
    if buf.strip():
        out.append(buf)
    return [{"source": source, "title": title, "text": t.strip(), "url": url} for t in out if t.strip()]


def from_markdown(path, source, url=""):
    text = open(path, encoding="utf-8").read()
    out, title, buf = [], os.path.basename(path), []
    for line in text.splitlines():
        m = re.match(r"^(#{1,3})\s+(.*)", line)
        if m:
            out += _chunks(source, title, "\n".join(buf), url)
            title, buf = m.group(2).strip(), []
        else:
            buf.append(line)
    return out + _chunks(source, title, "\n".join(buf), url)


def from_notebook(path, source, url=""):
    """Markdown cells as text; code cells as code, under the nearest heading."""
    cells = json.load(open(path, encoding="utf-8"))["cells"]
    out, title, buf = [], source, []
    for c in cells:
        src = "".join(c["source"]).strip()
        if not src:
            continue
        if c["cell_type"] == "markdown":
            head = re.match(r"^#{1,4}\s+(.*)", src)
            if head:
                out += _chunks(source, title, "\n\n".join(buf), url)
                title, buf = head.group(1).strip(), []
            buf.append(src)
        else:
            buf.append("```python\n" + src[:3000] + "\n```")
    return out + _chunks(source, title, "\n\n".join(buf), url)


def from_docx(path, source):
    """Plain text from a .docx (no extra libraries); short lines without a full stop count as headings."""
    xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8")
    paras = ["".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p)) for p in re.findall(r"<w:p[ >].*?</w:p>", xml, re.S)]
    paras = [re.sub(r"\s+", " ", p).strip() for p in paras if p.strip()]
    out, title, buf = [], source, []
    for p in paras:
        if len(p) < 70 and not p.endswith((".", ":", ";", ",")) and not p[0].isdigit():
            out += _chunks(source, title, "\n\n".join(buf))
            title, buf = p, []
        else:
            buf.append(p)
    return out + _chunks(source, title, "\n\n".join(buf))


def build(course_dir=None):
    """All passages, from our docs and notebook plus (if course_dir is given) the course's own files."""
    passages = []
    docs = os.path.join(ROOT, "docs")
    for name in sorted(os.listdir(docs)):
        if name.endswith(".md"):
            passages += from_markdown(os.path.join(docs, name), f"docs/{name}", BLOG + name[:-3] + ".html")
    nb = os.path.join(ROOT, "notebooks", "capstone2_business_analyst_adventureworks.ipynb")
    passages += from_notebook(nb, "Our finished notebook", REPO + "notebooks/capstone2_business_analyst_adventureworks.ipynb")
    if course_dir:
        guide = os.path.join(course_dir, "Training_guide.docx")
        start = os.path.join(course_dir, "capstone2_business_analyst.ipynb")
        if os.path.exists(guide):
            passages += from_docx(guide, "Course training guide")
        if os.path.exists(start):
            passages += from_notebook(start, "Course starting notebook")
    for i, p in enumerate(passages):
        p["id"] = i
    return passages


class Index:
    """BM25 over passage text plus its title (titles count double)."""

    def __init__(self, passages, k1=1.4, b=0.75):
        self.passages, self.k1, self.b = passages, k1, b
        self.docs = [Counter(words(p["text"]) + 2 * words(p["title"]) + words(p["source"] + " " + ALIASES.get(p["source"], "")))
                     for p in passages]
        self.lens = [sum(d.values()) for d in self.docs]
        self.avg = sum(self.lens) / max(1, len(self.lens))
        df = Counter(w for d in self.docs for w in d)
        n = len(self.docs)
        self.idf = {w: math.log(1 + (n - f + 0.5) / (f + 0.5)) for w, f in df.items()}

    def search(self, question, k=8, max_chars=11000):
        q = set(words(question))
        scored = []
        for i, d in enumerate(self.docs):
            s = sum(self.idf[w] * d[w] * (self.k1 + 1) / (d[w] + self.k1 * (1 - self.b + self.b * self.lens[i] / self.avg))
                    for w in q if w in d)
            if s > 0:
                scored.append((s, i))
        out, total = [], 0
        for s, i in sorted(scored, reverse=True):
            p = self.passages[i]
            if total + len(p["text"]) > max_chars:
                continue
            out.append(p); total += len(p["text"])
            if len(out) >= k:
                break
        return out


_INDEX = {}


def index():
    """The knowledge base if built (with the course files), else our own docs and notebook."""
    mtime = os.path.getmtime(KB_FILE) if os.path.exists(KB_FILE) else 0
    if _INDEX.get("mtime") != mtime:
        passages = json.load(open(KB_FILE, encoding="utf-8"))["passages"] if mtime else build()
        _INDEX.update(mtime=mtime, index=Index(passages))
    return _INDEX["index"]
