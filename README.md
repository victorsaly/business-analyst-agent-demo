<p align="center"><img src="app/web/logo.svg" width="96" alt="Logo: a cassette with a rising bar chart"></p>

<h1 align="center">Business Performance Analyst Agent</h1>

<p align="center"><b>A course demonstration</b>: Capstone 2 of the Agentic AI Workshop 2026.<br>
Ask a question about sales in plain English. Get the answer, the chart, and the exact query behind every number.</p>

<p align="center"><a href="https://victorsaly.github.io/business-analyst-agent-demo/"><b>Open the online demo</b></a> ·
<a href="https://victorsaly.github.io/business-analyst-agent-demo/media/pitch.mp4">60-second pitch video</a> · <a href="docs/history.md">How we got here</a> · <a href="docs/README.md">All documentation</a></p>

> [!IMPORTANT]
> **This is a learning project, not a product.** It was built in one day for a course. "AdventureWorks" is
> [Microsoft's public sample database](https://github.com/microsoft/sql-server-samples/tree/master/samples/databases/adventure-works)
> about a made-up bicycle company: no real business or personal data is used anywhere.

---

## What it does

A manager types a question, for example *"Why did margin drop in the Northwest in Q2 2023?"*. The agent:

1. **plans** the analysis;
2. **writes and runs read-only SQL** (or pandas) on the AdventureWorks sales data, fixing its own errors;
3. **draws a chart** and **explains what drove** the result;
4. **shows the exact queries** it used, taken from the tool log, not from the AI's own words;
5. **says so** when the data can't answer, and **never states a forecast as fact**;
6. writes a **one-page weekly leadership briefing**.

It is checked by a **scorecard** (the brief's 4 questions plus 3 guardrail traps), marked against answers
worked out from the database.

## Try it

| | What you get | What you need |
|---|---|---|
| **Online** ([link](https://victorsaly.github.io/business-analyst-agent-demo/)) | Every screen, replaying **recorded live AI runs** step by step. Stakeholder / Developer views, spoken explanations, the Story chat. | A browser |
| **Locally** | All of the above, plus **Live AI**, your own questions, the hand-run tools, and the Story chat answering anything live. | macOS or Linux, Python 3, an OpenAI or Groq API key |

```bash
cd app
./demo.sh setup          # Python environment + downloads AdventureWorks (17 MB) into a read-only SQLite file
cp .env.example .env     # then add GROQ_API_KEY=... and/or OPENAI_API_KEY=...
./demo.sh app            # opens http://localhost:8501
```

The online copy can't run the AI: that would need a server holding an API key that anyone could spend.

## The screens

| Screen | What it shows |
|---|---|
| **Cover** | The problem, how it works, the house rules (guardrails) |
| **What changed** | Before and after, every line of the brief, the old and new rulebook |
| **Tracks** | The demo as a cassette tracklist. Side A: the brief's questions. Side B: guardrails, briefing, scorecard |
| **Tools** | The agent's tools used by hand, with no AI. Try "delete the orders": it's refused |
| **Briefing** | The weekly leadership briefing. The KPI table comes straight from SQL and appears first |
| **Scorecard** | 7 test questions, marked Pass or Fail against the database |
| **Story** | The project timeline, and a chat that answers questions about how we built it |

On every screen:
- **View for: Stakeholder / Developer.** Stakeholders see answers, numbers and charts, with each step in plain
  English. Developers also see every tool call, its arguments, the SQL, timings, AI rounds and tokens.
- **Explain this page.** A spoken explanation of the screen, written for the chosen audience (voice:
  ElevenLabs), with captions that light up word by word in time with the voice.
- **Modes: Live AI / Replay / Dry run.** Replay plays back a recorded live run. Dry run has no AI and is for
  testing the screens only. Both are always labelled on screen.

## How we got here

The full story, with times, is in **[docs/history.md](docs/history.md)**. In short, on 1 October 2026:

| # | Step | What we did | Where |
|---|---|---|---|
| 0 | **Starting point** | The course's notebook had a working agent engine, but on made-up data (a pretend retailer, in pounds). | course repo |
| 1 | **Cut the AI cost** | Measured the tokens: a shorter rulebook and tool menu cut the fixed cost per round by 32% on the free Groq plan. | [prompt-optimization](docs/prompt-optimization.md) |
| 2 | **Plan** | Turned the brief into 18 requirements and 13 steps anyone can follow. Decision: keep the engine, add a new Section 6. | [build guide](docs/build-guide.md) |
| 3 | **Build Section 6** | Real AdventureWorks data opened read-only; 5 tools; 4 guardrails; "show the query"; new scorecard; weekly briefing; a planted anomaly to rehearse. | [notebook](notebooks/capstone2_business_analyst_adventureworks.ipynb) |
| 4 | **Demo app** | The same agent behind a small FastAPI server and a hand-built web page, with Live, Replay and Dry run modes, and 27 automatic checks. | [running the app](docs/running-the-app.md) |
| 5 | **Product and design** | Who it's for and what success means; the look of a hand-lettered cassette J-card. | [product](docs/product.md), [design](docs/design.md) |
| 6 | **Real AI, recorded** | Groq's free daily allowance ran out, so OpenAI takes over automatically. Every demo question recorded live. Pitch video with ElevenLabs audio. | [app/recordings/](app/recordings) |
| 7 | **Clear for every audience** | Fixed a stalled briefing screen; Stakeholder and Developer views; spoken explanations; this online copy; the Story chat. | this repo |

**Results:** on the recorded runs, the scorecard passes **6 of 7**. The miss, kept visible on purpose: asked for
a return rate, the agent said "0.00%" instead of saying the data has no returns.

## How it works

```
question ──► AI model (OpenAI or Groq) ──► picks a tool ──► tool runs on a READ-ONLY SQLite file
              ▲                                                    │
              └──────────── result (numbers, never invented) ◄────┘
                    … repeats up to 8 rounds, then writes the answer
answer + chart + the exact queries, taken from the tool log
```

- **Tools:** `get_schema`, `run_sql` (SELECT only), `run_python` (pandas sandbox), `make_chart`,
  `detect_anomalies`, plus `explain_change` (volume / price / mix).
- **Guardrails:** every number comes from a tool result; the database file is opened read-only and the
  tool refuses anything but SELECT; it says "the data does not include …"; projections are labelled
  "ESTIMATE, not a fact" or not made.
- **AI services:** Groq first, falling back to OpenAI automatically when an allowance runs out (`app/.env`).

## Repository layout

```
app/                    the demo app (run it from here)
  analyst/              the agent: data, tools, rulebook + tool loop, demo cases, briefing, scorecard, story chat
  web/                  the screens (HTML, CSS, JS, fonts, logo)
    explain/            Explain narration: text, ElevenLabs audio, word timings
    story/              Story timeline and the prepared chat answers
  recordings/           recorded live AI runs, used by Replay and the online copy
  promo/audio/          pitch-video music and voiceover (ElevenLabs)
  server.py             local web server
  demo.sh               every command: setup, app, test, prepare, video, pitch, timings, story, site
  build_site.py         builds the online copy into ../site
  make_explain_timings.py, make_story_answers.py, prepare_recordings.py, record_video.py, make_promo.py
  test_demo.py          27 checks, no AI key needed
docs/                   all the documentation; start at docs/README.md
  history.md            how we got here (also what the Story chat answers from)
  running-the-app.md    setup, modes, screens, presenting, recording
  build-guide.md        the brief as 13 steps: every notebook cell we added, and why
  prompt-optimization.md, product.md, design.md, audio-sources.md
notebooks/              our finished notebook (Section 6 = this project)
site/                   the online copy, built by app/build_site.py; site/media has the pitch video
.github/workflows/      publishes site/ to GitHub Pages on every push
```

## Updating the online copy

```bash
cd app
./demo.sh prepare        # optional: re-record live runs (uses the AI)
./demo.sh story          # optional: refresh the Story chat's prepared answers (uses the AI)
./demo.sh site           # rebuild ../site, then commit and push: GitHub Pages updates itself
```

## Credits

- Course: Agentic AI Workshop 2026, Capstone 2. The starting notebook and training guide belong to the course
  and are not included here.
- Data: Microsoft AdventureWorks sample database (MIT licence).
- Fonts: Patrick Hand, Patrick Hand SC, Courier Prime (SIL Open Font Licence, `app/web/fonts/OFL.txt`).
- Voice and music: ElevenLabs (voice "Emma"); see [docs/audio-sources.md](docs/audio-sources.md).
