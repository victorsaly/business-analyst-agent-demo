"""Render the 60-second pitch video.

  .venv/bin/python -m scripts.make_promo            -> video/pitch.mp4

Needs: promo/audio/music.mp3 (the music bed) and promo/audio/vo_<key>.mp3 (one voiceover line per scene;
missing lines are simply left out), plus recorded live runs in recordings/ (./demo.sh prepare).
Scenes are cut on the music's 120 BPM grid: intro 0-8s, drop at 8s, breakdown 22-24s, final hit at 56s.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # app/ (this script lives in app/scripts/)
AUDIO = os.path.join(HERE, "promo", "audio")
PORT = 8633
REPLAY = "&mode=replay&delay=0.2"

SCENES = [
    {"start": 0, "dur": 4, "kind": "card", "vo": "hook", "lines": ["Your numbers", "know the answers."]},
    {"start": 4, "dur": 4, "kind": "card", "vo": "problem", "lines": ["So why does one question", "take days?"]},
    {"start": 8, "dur": 6, "kind": "app", "vo": "reveal", "url": "/?page=cover" + REPLAY,
     "actions": [{"t": 1.6, "zoom": ".cover h1"}], "caption": "Ask in plain English.", "captionAt": 2.6},
    {"start": 14, "dur": 8, "kind": "app", "vo": "sales", "url": "/?page=tracks&case=sales_territory&autorun=1" + REPLAY,
     "actions": [{"t": 2.6, "zoom": "figure.chart"}], "caption": "Writes the SQL. Runs it. Draws the chart.", "captionAt": 3.6},
    {"start": 22, "dur": 2, "kind": "card", "vo": None, "lines": ["Now ask why."]},
    {"start": 24, "dur": 8, "kind": "app", "vo": "why", "url": "/?page=tracks&case=northwest_margin&autorun=1" + REPLAY,
     "actions": [{"t": 3.4, "zoom": ".answer"}], "caption": "Finds what drove it.", "captionAt": 3.8},
    {"start": 32, "dur": 10, "kind": "app", "vo": "unusual", "url": "/?page=tracks&case=unusual_last_quarter&autorun=1" + REPLAY,
     "actions": [{"t": 3.6, "zoom": ".answer"}, {"t": 7.0, "zoom": "figure.chart"}], "caption": "Spots what's off.", "captionAt": 4.0},
    {"start": 42, "dur": 2, "kind": "app", "vo": "trust", "url": "/?page=tracks&case=sales_territory&autorun=1&mode=replay&delay=0",
     "actions": [{"t": 0.5, "zoom": ".notes li"}], "caption": "Shows its working.", "captionAt": 0.3},
    {"start": 44, "dur": 2, "kind": "app", "vo": None, "url": "/?page=tracks&case=guard_write&autorun=1&mode=replay&delay=0",
     "actions": [{"t": 0.5, "zoom": ".answer"}], "caption": "Read-only.", "captionAt": 0.3},
    {"start": 46, "dur": 2, "kind": "app", "vo": None, "url": "/?page=tracks&case=guard_competitors&autorun=1&mode=replay&delay=0",
     "actions": [{"t": 0.5, "zoom": ".answer"}], "caption": "Says when the data can't answer.", "captionAt": 0.3},
    {"start": 48, "dur": 12, "kind": "card", "vo": "close", "lines": ["Ask the numbers."],
     "sub": "Get the answer, the chart <b>and</b> the reason why.<br>Business Performance Analyst Agent"},
]
TOTAL = 60.0

# What each voiceover line claims, checked against the recording it plays over. Live runs re-record tracks,
# so a newer run might no longer say what the voice says: the renderer warns before it renders.
CLAIMS = {
    "sales_territory": {"charts": 1, "words": []},
    "northwest_margin": {"charts": 0, "words": ["reseller", "bike"]},
    "unusual_last_quarter": {"charts": 0, "words": ["reseller", ("incomplete", "partial", "missing the last")]},
    "guard_write": {"charts": 0, "words": ["read-only"]},
    "guard_competitors": {"charts": 0, "words": ["does not include"]},
}


def check_claims():
    sys.path.insert(0, HERE)
    from analyst import cases
    ok = True
    for cid, need in CLAIMS.items():
        rec = cases.load_recording(cases.case_key(cases.CASE_BY_ID[cid]))
        if not rec:
            print(f"   ! no recording for {cid}: run ./demo.sh prepare {cid}")
            ok = False
            continue
        text = rec["answer"].lower()
        missing = [w for w in need["words"] if not any(x in text for x in (w if isinstance(w, tuple) else (w,)))]
        if len(rec.get("charts", [])) < need["charts"] or missing:
            print(f"   ! {cid}: the voiceover's claim is not in the current recording "
                  f"(missing: {missing or 'a chart'}). Re-record it or change the line.")
            ok = False
    return ok
VO_AT = 0.35   # seconds after a scene starts before its line begins


def wait_for_server(url):
    for _ in range(60):
        try:
            urllib.request.urlopen(url + "/api/meta", timeout=5)
            return
        except Exception:
            time.sleep(1)
    raise RuntimeError("The app did not start.")


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True)
    return float(out.stdout.strip() or 0)


def main():
    if not check_claims() and "--force" not in sys.argv:
        sys.exit("Stopped: fix the recordings above, or run with --force.")
    music = os.path.join(AUDIO, "music.mp3")
    if not os.path.exists(music):
        sys.exit("Missing promo/audio/music.mp3")
    for i, sc in enumerate(SCENES):
        sc["tag"] = "Real AI run, replayed" if sc["kind"] == "app" else ""
        vo = sc.get("vo") and os.path.join(AUDIO, f"vo_{sc['vo']}.mp3")
        room = next((n["start"] for n in SCENES[i + 1:] if n.get("vo")), TOTAL) - sc["start"] - VO_AT
        if vo and os.path.exists(vo) and duration(vo) > room:   # a line may run over silent scenes, not into the next line
            print(f"   ! vo_{sc['vo']}.mp3 is {duration(vo):.1f}s but has {room:.1f}s before the next line")
    os.makedirs(os.path.join(HERE, "video"), exist_ok=True)
    work = tempfile.mkdtemp(prefix="pitch_")
    app = subprocess.Popen([os.path.join(HERE, ".venv", "bin", "python"), os.path.join(HERE, "server.py")],
                           env=dict(os.environ, PORT=str(PORT)), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=HERE)
    try:
        wait_for_server(f"http://localhost:{PORT}")
        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--force-device-scale-factor=1"])
            ctx = browser.new_context(viewport={"width": 1920, "height": 1080}, record_video_dir=work,
                                      record_video_size={"width": 1920, "height": 1080})
            t_page = time.monotonic()
            page = ctx.new_page()
            page.goto(f"http://localhost:{PORT}/static/promo.html")
            page.evaluate("document.fonts.ready.then(() => true)")
            page.wait_for_timeout(800)
            t_play = time.monotonic()
            page.evaluate("tl => play(tl)", {"bpm": 120, "scenes": SCENES})
            raw = page.video.path()
            ctx.close()
            browser.close()
        offset = t_play - t_page + 0.05
        silent = os.path.join(work, "silent.mp4")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{offset:.3f}", "-i", raw, "-t", str(TOTAL),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-r", "30", silent], check=True)
        # audio: voice lines placed on their scenes; music ducks under the voice; loudness to -14 LUFS
        inputs, filters, vo_labels = ["-i", silent, "-i", music], [], []
        n = 2
        for sc in SCENES:
            vo = sc.get("vo") and os.path.join(AUDIO, f"vo_{sc['vo']}.mp3")
            if vo and os.path.exists(vo):
                ms = int((sc["start"] + VO_AT) * 1000)
                inputs += ["-i", vo]
                filters.append(f"[{n}:a]aresample=44100,aformat=channel_layouts=stereo,adelay={ms}|{ms}[v{n}]")
                vo_labels.append(f"[v{n}]")
                n += 1
        music_chain = "[1:a]aresample=44100,aformat=channel_layouts=stereo,volume=0.9[m]"
        if vo_labels:
            filters.append("".join(vo_labels) + f"amix=inputs={len(vo_labels)}:normalize=0,volume=1.6,"
                           f"apad=whole_dur={TOTAL},asplit=2[vo][key]")
            filters.append(music_chain)
            filters.append("[m][key]sidechaincompress=threshold=0.03:ratio=9:attack=15:release=350:makeup=1[md]")
            filters.append("[md][vo]amix=inputs=2:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=9,"
                           f"afade=t=out:st={TOTAL - 1.2}:d=1.2,atrim=0:{TOTAL}[a]")
        else:
            filters.append(music_chain.replace("[m]", ",loudnorm=I=-14:TP=-1.5[a]"))
        out = os.path.join(HERE, "video", "pitch.mp4")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(filters),
                        "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", out],
                       check=True)
        print(f"Saved {out} ({duration(out):.1f}s)")
    finally:
        app.terminate()
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
