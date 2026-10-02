"""Build the Ask chat's knowledge base from the course files, our notebook and docs/.

    .venv/bin/python -m scripts.make_knowledge --course /path/to/your/copy/of/the/course/repo
    (or: ./demo.sh knowledge /path/to/course/repo)

The course folder must hold Training_guide.docx and capstone2_business_analyst.ipynb. Writes data/knowledge.json
(used by the local app) and ../worker/knowledge.json (bundled into the online chat's Cloudflare Worker). Both
are git-ignored: they contain course material, which stays out of the public repo.
"""
import sys
import argparse
import json
import os
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # app/, so `python scripts/<name>.py` works too

from analyst import knowledge, story  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # app/ (this script lives in app/scripts/)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--course", help="your local copy of the course repo (Training_guide.docx, capstone2_business_analyst.ipynb)")
    args = ap.parse_args()
    if args.course and not os.path.isdir(args.course):
        raise SystemExit(f"Not a folder: {args.course}")
    passages = knowledge.build(args.course)
    # The Worker searches and answers exactly like the local app: same passages, word lists and prompt.
    kb = {"prompt": story.fixed_prompt(), "marker": "@@PASSAGES@@", "skip_sources": ["docs/history.md", "docs/requirements.md"],   # sent in full; the guide goes by passage
          "course_passages": story.COURSE_PASSAGES, "stop": sorted(knowledge.STOP), "aliases": knowledge.ALIASES,
          "max_chars": 11000, "passages": passages}
    for path in (knowledge.KB_FILE, os.path.join(os.path.dirname(HERE), "worker", "knowledge.json")):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(kb, f, ensure_ascii=False, separators=(",", ":"))
    counts = Counter(p["source"] for p in passages)
    for source, n in sorted(counts.items()):
        print(f"  {n:4d} passages  {source}")
    size = os.path.getsize(knowledge.KB_FILE) / 1e6
    print(f"{len(passages)} passages, {size:.1f} MB -> data/knowledge.json and ../worker/knowledge.json")
    if not args.course:
        print("No --course folder: the course's training guide and starting notebook are NOT included.")


if __name__ == "__main__":
    main()
