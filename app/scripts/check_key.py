"""Check the AI key in app/.env and say plainly what to do if it is missing or wrong. Always exits 0:
Replay mode works without a key, so this only warns."""
import os
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # app/, so `python scripts/<name>.py` works too

from analyst import agent  # noqa: E402

FIX = ("  Open app/.env, put your key after GROQ_API_KEY= (free at https://console.groq.com/keys),\n"
       "  save the file, then start the demo again. Without a key only Replay mode works.")


def check():
    if not agent.PROVIDERS:
        return "NO AI KEY: app/.env has no GROQ_API_KEY (or other AI key) yet.\n" + FIX
    lines = []
    for p in agent.PROVIDERS:
        headers = {"Authorization": f"Bearer {p['key']}"} if p["key"] else {}
        try:
            r = requests.get(f"{p['base']}/models", headers=headers, timeout=10)
        except requests.RequestException:
            lines.append(f"AI key for {p['name']}: could not reach {p['base']} to check it (offline?).")
            continue
        if r.status_code in (401, 403):
            return f"AI KEY REJECTED by {p['name']}: the key in app/.env is wrong or expired.\n" + FIX
        lines.append(f"AI key for {p['name']}: OK (model {p['model']})." if r.ok
                     else f"AI key for {p['name']}: could not confirm (HTTP {r.status_code}).")
    return "\n".join(lines)


if __name__ == "__main__":
    print()
    print(check())
