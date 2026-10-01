# The demo app: Business Performance Analyst Agent

> Course demonstration (Capstone 2, Agentic AI Workshop 2026). See the [main README](../README.md) for the
> project overview and [history.md](history.md) for how we got here. Commands below run from the `app/` folder.

A local app that runs the AdventureWorks agent from [build-guide.md](build-guide.md) on your own machine.
It has a screen per demo case, records live AI runs so you can replay them safely, and records a
narrated demo video.

## Quick start (macOS)

```bash
cd app
./demo.sh setup        # one-off: local Python environment, browser for the video, database (downloads 17 MB)
# put your key in app/.env:    GROQ_API_KEY=gsk_...  and/or  OPENAI_API_KEY=sk-...
./demo.sh app          # starts the app and opens http://localhost:8501
```

## The three modes (top right)

| Mode | Uses the AI? | When to use it |
|---|---|---|
| **Live AI** | Yes | The real thing. Every run is saved to `recordings/` automatically. |
| **Replay** | No (plays back a real AI run, step by step) | Backup for the live demo if the wifi or the free plan fails. Labelled "Replay". |
| **Dry run** | No | Only to test the screens and the video. The steps and numbers are real tool results, but the plan and wording are scripted. Labelled in red. |

## The screens

The app is designed as a hand-lettered cassette J-card: the demo is a six-minute mixtape.

| Screen | What it shows | Judging point |
|---|---|---|
| Cover | The problem, how it works, the house rules (guardrails) | Pitch, business value |
| What changed | Before / after, every brief requirement, old vs new rulebook, the tool descriptions | Agent design |
| Tracks | The demo as a tracklist. Side A has the brief's questions, side B the guardrails, briefing and scorecard, plus a hidden rehearsal track. Each track shows its time budget; both sides add up to 6:00. Your own questions go in the box below. | Working demo, trust |
| Tools | Anomaly scan and read-only SQL by hand. "Try: delete the orders" is refused | Trust & safety |
| Briefing | The one-page leadership briefing, downloadable as a standalone HTML page | Business value |
| Scorecard | The brief's 4 questions plus 3 guardrail traps, marked Pass / Fail | Evaluation |
| Story | The project timeline, and a chat that answers questions about how we built it (from `docs/history.md`) | Pitch |

**View for: Stakeholder / Developer** (under the header) switches between just the answers, numbers and charts,
and everything underneath: each tool call, its arguments, SQL, timings, AI rounds and tokens.
**Explain this page** plays a spoken explanation for the chosen audience with word-by-word captions
(`web/explain/`: edit `scripts.json`, regenerate the mp3, then `./demo.sh timings`).

A run left behind on another screen no longer blocks the next one: starting a run stops the previous one.
On the briefing screen the KPI table appears at once, and a status line ticks every second while the AI works.
If a live run goes past its time slot, a button offers the recorded run instead.

While a track plays, the counter top right shows time used against the track's budget. The red bar
under the header fills as you go, and the counter turns red if you run over.

## The 60-second pitch video

`video/pitch.mp4` is a launch-style trailer:
- a hand-lettered hook and problem card;
- the app revealed on the music's drop;
- real AI runs, replayed, with zooms into the chart, the answer and the SQL;
- a three-shot trust montage;
- an end card on the final hit.

It runs on a 120 BPM music bed, with a professional voiceover and the music dipping under the voice. Audio is
from ElevenLabs; see [audio-sources.md](audio-sources.md).

```bash
./demo.sh pitch        # re-render from the current recordings (about 1 minute)
```

Live runs re-record their tracks. So before rendering, `make_promo.py` checks that each recording still
supports what the voiceover says (for example, that the anomaly answer still mentions the Reseller channel).
If one doesn't, it stops and tells you which track to re-record. The scenes, captions and timings are in
`SCENES` at the top of `make_promo.py`.

## Making the video

```bash
./demo.sh prepare      # runs every case LIVE once and records it (~120-160k tokens: most of a day's free allowance)
./demo.sh video        # replays those recordings in a browser and saves video/demo.mp4 with narration
```

- `./demo.sh video --no-voice` records without narration. `--voice Daniel` picks another macOS voice
  (`say -v '?'` lists them). `--rehearsal` adds the planted-anomaly scene.
- `./demo.sh video-dry` makes a test video with no AI at all. It is clearly labelled DRY RUN, so don't
  present it as the agent.
- To re-record just a few cases: `./demo.sh prepare northwest_margin guard_forecast`.

## Presenting live

1. Start `./demo.sh app` before the session and choose **Live AI** (top right).
2. Play side A, then side B, track by track. The counters keep you inside the 6-minute slot.
3. If the AI is slow or rate-limited, switch to **Replay**. The same track shows the recorded
   live run, labelled as a replay.
4. For the organisers' planted-anomaly question, type it into "Write your own question" in Live AI mode.

`?presenter=1` in the URL adds a red margin note with the talking point for each screen (used by the video).

## Presenter zoom

While presenting, point at anything (a chart, the answer, a query, a panel) and press **Z** to zoom into it.
Press **Z** or **Esc** to zoom out. Screens change with a short transition.

## AI services: Groq, then OpenAI

The agent tries the services in `.env` in order: Groq (`GROQ_API_KEY`) first, then OpenAI (`OPENAI_API_KEY`,
model `gpt-5.4-mini`, change it with `OPENAI_MODEL`). If Groq runs out of its daily allowance or credit, the
agent switches to OpenAI automatically and keeps going, and the footer of each answer shows which model
answered. To make OpenAI the first choice, set `LLM_PROVIDER=openai`; the current recordings were made this
way, because it follows the rules more reliably than the free model.

## Running without Groq

Any OpenAI-compatible API works. For a fully local AI, install [Ollama](https://ollama.com), run
`ollama pull qwen2.5:14b`, and set in `.env`:

```
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=qwen2.5:14b
```

This setup is untested; small local models make more mistakes, so check the scorecard.

## Checks

`./demo.sh test` runs 27 checks without any AI key:
- the guardrails;
- every case in dry run;
- the briefing;
- the examiner;
- the live AI loop against a fake AI server (tool calls, a rate-limit retry, recording and replay);
- adapting to OpenAI's settings, and falling back to the next service when one runs out.

## Files

| File | Purpose |
|---|---|
| `server.py` | Local web server: the analyst package behind a small streaming API |
| `web/` | The screens: `index.html`, `app.css`, `app.js`, and the fonts (OFL licence) |
| `analyst/data.py` | Builds the read-only AdventureWorks SQLite file |
| `analyst/tools.py` | The tools and their menu cards (same code as notebook Section 6) |
| `analyst/agent.py` | The rulebook and the AI tool loop |
| `analyst/cases.py` | Demo cases, dry-run scripts, recordings / replay |
| `analyst/briefing.py` | Weekly leadership briefing |
| `analyst/evals.py` | Scorecard (examiner copied from the notebook) |
| `prepare_recordings.py` | Records every case live |
| `record_video.py` | Records the narrated walkthrough video |
| `make_promo.py`, `web/promo.html` | Renders the 60-second pitch video |
| `promo/audio/` | Pitch-video music and voiceover lines (sources: [audio-sources.md](audio-sources.md)) |
| `test_demo.py` | Automated checks |
| `analyst/story.py`, `make_story_answers.py` | The Story chat, and its prepared answers for the online copy |
| `make_explain_timings.py` | Word timings for the Explain captions, measured from each clip's pauses |
| `build_site.py` | Builds the online copy (GitHub Pages) into `../site` |
