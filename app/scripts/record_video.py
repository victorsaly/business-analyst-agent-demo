"""Record a demo video of the app: drives a real browser through every scene and saves an MP4.

  .venv/bin/python -m scripts.record_video --mode replay      # recommended: replays your recorded LIVE runs
  .venv/bin/python -m scripts.record_video --mode dry         # test video without any AI (clearly labelled DRY RUN)
  .venv/bin/python -m scripts.record_video --mode live        # runs the AI live while recording (slow on free tier)

Options: --no-voice (no narration), --rehearsal (add the planted-anomaly scene), --out video/demo.mp4
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # app/ (this script lives in app/scripts/)
PORT = 8611

# (url parameters, narration). Narration is read by the Mac's built-in voice if --voice is on.
SCENES = [
    ("page=cover", "This is our Business Performance Analyst Agent. Managers ask the numbers a question in plain "
                      "English, and get the answer, a chart, the reason why, and the exact query behind it."),
    ("page=changes", "We kept the agent's engine and changed what it works on: Microsoft AdventureWorks data, "
                          "the five tools from the brief, and four guardrails."),
    ("page=tracks&case=sales_territory", "Question one: total sales by territory last year. The agent works out "
                                            "that last year means 2024, writes the SQL, draws a chart, and shows its query."),
    ("page=tracks&case=followup_category", "A follow-up: and by product category? It remembers the previous question."),
    ("page=tracks&case=northwest_margin", "Question two: why did margin drop in the Northwest in Q2? The agent "
                                             "picks the year, compares the quarters, and finds the drivers."),
    ("page=tracks&case=growing_fastest", "Question three: which category is growing fastest? Year-on-year growth, "
                                            "with a warning about the small base."),
    ("page=tracks&case=unusual_last_quarter", "Question four: is anything unusual last quarter? The anomaly tool "
                                                 "finds that reseller sales stopped, and the agent explains the margin jump as a mix effect."),
    ("page=tracks&case=guard_competitors", "Guardrail: competitor prices are not in the data, so the agent says so "
                                              "instead of guessing."),
    ("page=tracks&case=guard_forecast", "Guardrail: it never presents a forecast as a fact."),
    ("page=tracks&case=guard_write", "Guardrail: the database is read-only. Asking it to delete data is refused."),
    ("page=briefing", "Every week it writes a one-page leadership briefing: KPIs straight from SQL, commentary, "
                             "charts, and every query used."),
    ("page=scorecard", "Finally, the scorecard: the brief's questions plus guardrail traps, marked against answers "
                       "worked out from the database."),
]
REHEARSAL = ("page=tracks&case=planted_anomaly", "Rehearsal: we planted a discount anomaly in a copy of the data. "
                                                    "The agent finds it and explains it.")

SCROLL_JS = """(dy) => {
  const el = document.scrollingElement;
  const before = el.scrollTop; el.scrollBy({top: dy, behavior: 'smooth'}); return before;
}"""
AT_BOTTOM_JS = """() => {
  const el = document.scrollingElement;
  return el.scrollTop + el.clientHeight >= el.scrollHeight - 5;
}"""


def wait_for_server(url, seconds=60):
    for _ in range(seconds):
        try:
            urllib.request.urlopen(url + "/api/meta", timeout=5)
            return
        except Exception:
            time.sleep(1)
    raise RuntimeError("The app did not start.")


def narrate(text, path, voice):
    subprocess.run(["say", "-v", voice, "-o", path, text], check=True)
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True)
    return float(out.stdout.strip() or 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["replay", "dry", "live"], default="replay")
    ap.add_argument("--out", default=os.path.join(HERE, "video", "demo.mp4"))
    ap.add_argument("--no-voice", action="store_true")
    ap.add_argument("--voice", default="Samantha", help="macOS voice for the narration (see: say -v '?')")
    ap.add_argument("--rehearsal", action="store_true", help="include the planted-anomaly rehearsal scene")
    ap.add_argument("--delay", default="0.8", help="seconds between replayed steps")
    args = ap.parse_args()

    use_voice = not args.no_voice and shutil.which("say") and shutil.which("ffprobe")
    scenes = SCENES[:-2] + ([REHEARSAL] if args.rehearsal else []) + SCENES[-2:]
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    work = tempfile.mkdtemp(prefix="demo_video_")
    app = subprocess.Popen([os.path.join(HERE, ".venv", "bin", "python"), os.path.join(HERE, "server.py")],
                           env=dict(os.environ, PORT=str(PORT)), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=HERE)
    marks = []   # (seconds into the video, narration file)
    try:
        wait_for_server(f"http://localhost:{PORT}")
        with sync_playwright() as p:
            browser = p.chromium.launch()
            ctx = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1,
                                      record_video_dir=work, record_video_size={"width": 1440, "height": 900})
            page = ctx.new_page()
            t0 = time.monotonic()
            for i, (params, text) in enumerate(scenes, 1):
                print(f"[{i}/{len(scenes)}] {params}")
                audio, length = None, 0.0
                if use_voice:
                    audio = os.path.join(work, f"scene{i}.aiff")
                    length = narrate(text, audio, args.voice)
                page.goto(f"http://localhost:{PORT}/?{params}&mode={args.mode}&presenter=1&autorun=1&delay={args.delay}")
                marks.append((time.monotonic() - t0 + 1.0, audio))
                page.wait_for_selector("body[data-scene=done]", timeout=600_000)
                if page.locator(".slip").count():
                    print("   ! the app showed an error slip on this scene")
                page.wait_for_timeout(1500)
                started = time.monotonic()
                while not page.evaluate(AT_BOTTOM_JS) and time.monotonic() - started < 40:
                    page.evaluate(SCROLL_JS, 260)
                    page.wait_for_timeout(700)
                spoken = time.monotonic() - marks[-1][0] - t0
                page.wait_for_timeout(int(max(2.0, length - spoken + 1.0) * 1000))
            video_path = page.video.path()
            ctx.close()
            browser.close()
        silent = os.path.join(work, "silent.mp4")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", video_path, "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "-crf", "23", "-r", "25", silent], check=True)
        if use_voice and marks:
            cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", silent]
            filters, labels = [], []
            for n, (at, audio) in enumerate(marks, 1):
                cmd += ["-i", audio]
                ms = int(at * 1000)
                filters.append(f"[{n}:a]aresample=44100,adelay={ms}|{ms}[a{n}]")
                labels.append(f"[a{n}]")
            filters.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0[aout]")
            cmd += ["-filter_complex", ";".join(filters), "-map", "0:v", "-map", "[aout]", "-c:v", "copy",
                    "-c:a", "aac", args.out]
            subprocess.run(cmd, check=True)
        else:
            shutil.copy(silent, args.out)
        print(f"Saved {args.out}")
    finally:
        app.terminate()
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
