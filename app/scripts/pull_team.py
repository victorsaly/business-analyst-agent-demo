"""Fetch the team form's answers (site/team-form/, kept by the Ask chat's Worker in KV) and fill app/web/team.json.

    .venv/bin/python -m scripts.pull_team        (or ./demo.sh team)

Needs wrangler logged in to the Cloudflare account (npx wrangler@3 login). It:
- adds each new person (name, LinkedIn, role, bio) to app/web/team.json, keeping the people and the order already there;
- downloads each photo link into app/web/team/ and points team.json at that copy (LinkedIn photo links expire);
- saves every full answer (role, skills, tools, bio, photo) to app/data/team_answers.json, which is not committed;
- prints who covers which skill and which skills nobody has ticked.
Then rebuild the site (./demo.sh site) so the names show on the cover, the blog (with photos) and the readme.
"""
import json
import os
import re
import subprocess

import requests

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # app/ (this script lives in app/scripts/)
WORKER = os.path.join(os.path.dirname(HERE), "worker")
TEAM = os.path.join(HERE, "web", "team.json")
ANSWERS = os.path.join(HERE, "data", "team_answers.json")
PHOTOS = os.path.join(HERE, "web", "team")   # served as team/<name>.jpg next to team.json
PLACEHOLDERS = {"google", "linkedin", "your-name", "yourname", "name", "example", "test", "none", "na", "n-a"}   # not a real profile
IMAGE_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/gif": "gif"}
SKILLS = ["Python", "SQL / data analysis", "AI and prompting", "Web", "Design / UX", "Writing and documentation",
          "Presenting", "Project management", "Testing"]   # the same list as the form and worker/src/index.js


def wrangler(*args):
    out = subprocess.run(["npx", "--yes", "wrangler@3", "kv", "key", *args, "--binding", "LIMITS"],
                         cwd=WORKER, capture_output=True, text=True, check=True).stdout
    return out[out.index("[") if args[0] == "list" else 0:]   # list prints a banner before its JSON


def fetch():
    keys = [k["name"] for k in json.loads(wrangler("list", "--prefix", "team:"))]
    answers = [json.loads(wrangler("get", k)) for k in keys]
    return sorted(answers, key=lambda a: a.get("at", ""))


def save_photo(name, url):
    """Download a photo link into app/web/team/<name>.<ext> and return its path from team.json ("team/..."), or None."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "member"
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        kind = r.headers.get("Content-Type", "").split(";")[0].strip()
        if not r.ok or kind not in IMAGE_TYPES or len(r.content) > 5_000_000:
            raise ValueError(f"HTTP {r.status_code}, {kind or 'no type'}, {len(r.content)} bytes")
    except (requests.RequestException, ValueError) as exc:
        print(f"  photo for {name}: not saved ({exc})")
        return None
    os.makedirs(PHOTOS, exist_ok=True)
    for old in os.listdir(PHOTOS):   # an earlier copy with another extension
        if old.rsplit(".", 1)[0] == slug:
            os.remove(os.path.join(PHOTOS, old))
    file = f"{slug}.{IMAGE_TYPES[kind]}"
    with open(os.path.join(PHOTOS, file), "wb") as f:
        f.write(r.content)
    return f"team/{file}"


def same(a, b):
    """The same person: the same LinkedIn profile, or, when either has no LinkedIn (added to team.json by hand), the same name.
    Two people who share a name stay two people."""
    norm = lambda u: u.lower().split("?")[0].rstrip("/").split("linkedin.com")[-1]
    if a.get("linkedin", "").strip() and b.get("linkedin", "").strip():
        return norm(a["linkedin"]) == norm(b["linkedin"])
    return a.get("name", "").strip().lower() == b.get("name", "").strip().lower()


def main():
    answers = fetch()
    os.makedirs(os.path.dirname(ANSWERS), exist_ok=True)
    with open(ANSWERS, "w", encoding="utf-8") as f:
        json.dump(answers, f, indent=2, ensure_ascii=False)

    with open(TEAM, encoding="utf-8") as f:
        team = json.load(f)
    members, added = team.get("members", []), []
    for a in answers:
        handle = a.get("linkedin", "").lower().rstrip("/").rsplit("/", 1)[-1]
        if handle in PLACEHOLDERS:   # someone without LinkedIn typed a stand-in to get past the form
            print(f"  {a['name']}: LinkedIn {a['linkedin']} looks like a stand-in, left out")
            a["linkedin"] = ""
        person = {"name": a["name"], "linkedin": a["linkedin"], "role": a.get("role", ""), "bio": a.get("bio", "")}
        old = next((m for m in members if same(m, person)), None)
        if a.get("photo"):
            photo = save_photo(a["name"], a["photo"])
            if photo:
                person["photo"] = photo
        if old:
            old.update(person)
        else:
            members.append(person)
            added.append(a["name"])
    team["members"] = members
    text = json.dumps(team, indent=2, ensure_ascii=False)
    text = text.replace('"example": {\n    "name": "Full Name",\n    "linkedin": "https://www.linkedin.com/in/your-profile/"\n  }',
                        '"example": {"name": "Full Name", "linkedin": "https://www.linkedin.com/in/your-profile/"}')
    with open(TEAM, "w", encoding="utf-8") as f:
        f.write(text + "\n")

    print(f"answers: {len(answers)} (saved to app/data/team_answers.json)")
    print(f"team.json: {len(members)} people" + (f", new: {', '.join(added)}" if added else ", nobody new"))
    if not answers:
        return
    print("\nskills:")
    for s in SKILLS:
        who = [a["name"] for a in answers if s in a.get("skills", [])]
        print(f"  {s:<28} {', '.join(who) if who else '-- nobody --'}")
    other = [f"{a['name']}: {a['other_skills']}" for a in answers if a.get("other_skills")]
    if other:
        print("\nother skills:\n  " + "\n  ".join(other))
    gaps = [s for s in SKILLS if not any(s in a.get("skills", []) for a in answers)]
    thin = [s for s in SKILLS if sum(s in a.get("skills", []) for a in answers) == 1]
    print("\nmissing: " + (", ".join(gaps) or "none"))
    print("only one person: " + (", ".join(thin) or "none"))
    print("\nNext: ./demo.sh site  (then commit and push site/)")


if __name__ == "__main__":
    main()
