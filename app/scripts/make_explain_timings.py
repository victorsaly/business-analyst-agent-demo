"""Word timings for the Explain captions, so the highlighted word keeps pace with the voice.

For each web/explain/<page>-<audience>.mp3: ffmpeg finds the pauses, each clear pause is pinned to the
nearest end of a phrase (a word ending in , . : ; ? !), and the words in between share the speaking
time by length. Writes web/explain/timings.json. Re-run after changing a line or its mp3:

    .venv/bin/python -m scripts.make_explain_timings
"""
import json
import os
import re
import subprocess

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # app/ (this script lives in app/scripts/)
DIR = os.path.join(HERE, "web", "explain")
MIN_PAUSE = 0.16          # seconds of quiet that count as a pause between phrases


def silences(path):
    out = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af", f"silencedetect=noise=-38dB:d={MIN_PAUSE}",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                               capture_output=True, text=True).stdout)
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", out)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", out)]
    ends += [dur] * (len(starts) - len(ends))
    return dur, list(zip(starts, ends))


def weight(word):
    return len(word) + 1


def timings(text, path):
    words = text.split()
    dur, quiet = silences(path)
    lead = quiet[0][1] if quiet and quiet[0][0] < 0.05 else 0.0
    tail = quiet[-1][0] if quiet and quiet[-1][1] >= dur - 0.05 else dur
    inner = [(a, b) for a, b in quiet if a > lead + 0.05 and b < tail - 0.05]
    # speaking time only: where each pause sits once the pauses are cut out
    speech = (tail - lead) - sum(b - a for a, b in inner)
    pos, cut = [], 0.0
    for a, b in inner:
        pos.append(a - lead - cut)
        cut += b - a
    w = [weight(x) for x in words]
    total = sum(w)
    cum = [sum(w[:i + 1]) / total * speech for i in range(len(words))]       # estimated end of each word
    phrase_ends = [i for i, x in enumerate(words[:-1]) if re.search(r"[,.:;?!]$", x)]
    # pin each pause to the nearest phrase end (in order, never reusing one, within a sensible distance)
    anchors, used = [], -1
    for p in pos:
        best = min((i for i in phrase_ends if i > used), key=lambda i: abs(cum[i] - p), default=None)
        if best is not None and abs(cum[best] - p) < 0.2 * speech:
            anchors.append((best, p))
            used = best
    # spread words between anchors by length, in speaking time
    ends_s, prev_i, prev_t = [0.0] * len(words), -1, 0.0
    for i, t in anchors + [(len(words) - 1, speech)]:
        seg = w[prev_i + 1:i + 1]
        acc = 0
        for j, ww in enumerate(seg):
            acc += ww
            ends_s[prev_i + 1 + j] = prev_t + (t - prev_t) * acc / sum(seg)
        prev_i, prev_t = i, t
    # back to clock time: add the pauses back in
    def clock(s, starting):
        """Speaking time -> clock time. A word that starts right at a pause starts after it."""
        t = lead + s
        for k, (a, b) in enumerate(inner):
            if s > pos[k] + 1e-6 or (starting and s >= pos[k] - 1e-6):
                t += b - a
        return t
    starts_s = [0.0] + ends_s[:-1]
    return {"duration": round(dur, 3), "pauses_pinned": f"{len(anchors)}/{len(inner)}",
            "start": [round(clock(x, True), 3) for x in starts_s],
            "end": [round(clock(x, False), 3) for x in ends_s]}


def main():
    scripts = json.load(open(os.path.join(DIR, "scripts.json"), encoding="utf-8"))
    out = {}
    for page, lines in scripts.items():
        if page.startswith("_"):
            continue
        for aud, text in lines.items():
            path = os.path.join(DIR, f"{page}-{aud}.mp3")
            if os.path.exists(path):
                out[f"{page}-{aud}"] = timings(text, path)
                print(f"{page}-{aud}: {out[f'{page}-{aud}']['duration']}s, pauses pinned {out[f'{page}-{aud}']['pauses_pinned']}")
    json.dump(out, open(os.path.join(DIR, "timings.json"), "w"), indent=0)


if __name__ == "__main__":
    main()
