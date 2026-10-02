"""Fetch the team form's answers (site/team-form/, kept by the Ask chat's Worker in KV) and fill app/web/team.json.

    .venv/bin/python -m scripts.pull_team        (or ./demo.sh team)

Needs wrangler logged in to the Cloudflare account (npx wrangler@3 login). It:
- adds each new person (name and LinkedIn) to app/web/team.json, keeping the people and the order already there;
- saves every full answer (role, skills, tools, bio, photo) to app/data/team_answers.json, which is not committed;
- prints who covers which skill and which skills nobody has ticked.
Then rebuild the site (./demo.sh site) so the names show on the cover, the blog and the readme.
"""
import json
import os
import subprocess

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # app/ (this script lives in app/scripts/)
WORKER = os.path.join(os.path.dirname(HERE), "worker")
TEAM = os.path.join(HERE, "web", "team.json")
ANSWERS = os.path.join(HERE, "data", "team_answers.json")
SKILLS = ["Python", "SQL / data analysis", "AI and prompting", "Web", "Design / UX", "Writing and documentation",
          "Presenting", "Project management", "Testing"]   # the same list as the form and worker/src/index.js


def wrangler(*args):
    out = subprocess.run(["npx", "--yes", "wrangler@3", "kv", "key", *args, "--binding", "LIMITS", "--remote"],
                         cwd=WORKER, capture_output=True, text=True, check=True).stdout
    return out[out.index("[") if args[0] == "list" else 0:]   # list prints a banner before its JSON


def fetch():
    keys = [k["name"] for k in json.loads(wrangler("list", "--prefix", "team:"))]
    answers = [json.loads(wrangler("get", k)) for k in keys]
    return sorted(answers, key=lambda a: a.get("at", ""))


def same(a, b):
    norm = lambda u: u.lower().split("?")[0].rstrip("/").split("linkedin.com")[-1]
    return (a.get("linkedin") and b.get("linkedin") and norm(a["linkedin"]) == norm(b["linkedin"])) \
        or a.get("name", "").strip().lower() == b.get("name", "").strip().lower()


def main():
    answers = fetch()
    os.makedirs(os.path.dirname(ANSWERS), exist_ok=True)
    with open(ANSWERS, "w", encoding="utf-8") as f:
        json.dump(answers, f, indent=2, ensure_ascii=False)

    with open(TEAM, encoding="utf-8") as f:
        team = json.load(f)
    members, added = team.get("members", []), []
    for a in answers:
        person = {"name": a["name"], "linkedin": a["linkedin"]}
        old = next((m for m in members if same(m, person)), None)
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
