<p align="center"><img src="app/web/logo.svg" width="96" alt="Logo: a cassette with a rising bar chart"></p>

<h1 align="center">Business Performance Analyst Agent</h1>

<p align="center"><b>A course demonstration</b>: Capstone 2 of the Agentic AI Workshop 2026.<br>
Ask a question about sales in plain English. Get the answer, the chart, and the exact query behind every number.</p>

<p align="center"><a href="https://victorsaly.github.io/business-analyst-agent-demo/"><b>Home: the 60-second pitch</b></a> · <a href="https://victorsaly.github.io/business-analyst-agent-demo/demo/"><b>Online demo</b></a> · <a href="https://victorsaly.github.io/business-analyst-agent-demo/demo/?page=story">Ask the course chat</a> ·
<a href="https://victorsaly.github.io/business-analyst-agent-demo/pitch/">60-second pitch video</a> · <a href="https://victorsaly.github.io/business-analyst-agent-demo/deck/"><b>Presentation</b></a> · <a href="https://victorsaly.github.io/business-analyst-agent-demo/api/">API reference</a> · <a href="https://victorsaly.github.io/business-analyst-agent-demo/blog/"><b>How this was made</b> (blog)</a> · <a href="docs/history.md">History</a></p>

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
| **Online** ([link](https://victorsaly.github.io/business-analyst-agent-demo/demo/)) | Every screen, replaying **recorded live AI runs** step by step. Stakeholder / Developer views, spoken explanations, the Story chat. | A browser |
| **On your laptop** | All of the above, plus **Live AI**, your own questions, the hand-run tools, and the Story chat answering anything live. | A Mac or Windows laptop. Optional: a free Groq key |

### Run it on your laptop: step by step (Mac and Windows)

No programming needed. The full guide, with what you should see after each step and fixes for common problems,
is **[docs/getting-started.md](docs/getting-started.md)**. In short:

1. **Download:** on this page, click the green **Code** button, then **Download ZIP**, and unzip it.
2. **Install Python 3.10 or newer** from [python.org](https://www.python.org/downloads/), once.
   On Windows, tick **"Add python.exe to PATH"** in the installer.
3. **Optional:** get a free AI key at [console.groq.com](https://console.groq.com) → **API Keys** → **Create API Key**.
4. **Set up, once:** double-click **`Mac - 1 Setup.command`** or **`Windows - 1 Setup.bat`**. When the
   `.env` file opens, paste your key after `GROQ_API_KEY=` and save.
5. **Start:** double-click **`Mac - 2 Start.command`** or **`Windows - 2 Start.bat`**. The cover page opens at
   <http://localhost:8501>; click **Try the live demo**. Keep that window open; close it to stop.

<details><summary>For developers: the same thing from a terminal</summary>

```bash
cd app
./demo.sh setup          # Python environment + downloads AdventureWorks (17 MB) into a read-only SQLite file
# add GROQ_API_KEY=... and/or OPENAI_API_KEY=... to app/.env
./demo.sh app            # opens http://localhost:8501
```

On Windows (PowerShell, in `app`): `py -3 -m venv .venv`, `.venv\Scripts\pip install -r requirements.txt`,
`copy .env.example .env`, then `.venv\Scripts\python server.py`.
</details>

The online copy can't run the AI: that would need a server holding an API key that anyone could spend.

## The screens

| Screen | What it shows |
|---|---|
| **Home** | The front door: every screen, the blog, the API reference, the pitch and the presentation |
| **Cover** | The problem, how it works, the house rules (guardrails) |
| **What changed** | Before and after, every line of the brief, the old and new rulebook |
| **Tracks** | The demo as a cassette tracklist. Side A: the brief's questions. Side B: guardrails, briefing, scorecard |
| **Tools** | The agent's tools used by hand, with no AI. Try "delete the orders": it's refused |
| **Briefing** | The weekly leadership briefing. The KPI table comes straight from SQL and appears first |
| **Scorecard** | 7 test questions, marked Pass or Fail against the database |
| **Story** | The project timeline, step by step |

On every screen:
- **The Ask chat** (bottom right). Ask anything about the project, the task, its steps or the course material.
  Answers stream in, number their sources, and link to the matching blog pages, the API reference and the code.
  The conversation stays open while you move between screens.
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
| 8 | **Checked against the brief** | Every line of the brief, with evidence. Fixed three gaps: a returns answer, the cost metric, the planted-anomaly recording. | [requirements](docs/requirements.md) |
| 9 | **A finished product** | A Home screen with every area; a floating Ask chat that streams answers and links the blog, API and code; the blog and API reference; every track re-recorded live. | [blog](https://victorsaly.github.io/business-analyst-agent-demo/blog/) |

**Results:** every requirement in the brief is met; see **[docs/requirements.md](docs/requirements.md)** for the
evidence. On the recorded runs the scorecard passes **7 of 7**. It first scored 6 of 7: asked for a return rate,
the AI invented a stand-in instead of saying the data has no returns, so we tightened the rule and re-recorded it.

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
docs/                   all the documentation (lower-case names); also published as the blog at site/blog/
  index.md              the blog post "How this was made": the brief, before and after, every improvement
  history.md            how we got here (also what the Story chat answers from)
  requirements.md       every line of the brief, and the evidence it's met
  running-the-app.md    setup, modes, screens, presenting, recording
  build-guide.md        the brief as 13 steps: every notebook cell we added, and why
  prompt-optimization.md, product.md, design.md, audio-sources.md
notebooks/              our finished notebook (Section 6 = this project)
site/                   the website, built by app/build_site.py: the front page with the pitch video, the demo (demo/),
                        the blog (blog/), the API reference (api/), the pitch (pitch/), the presentation (deck/)
worker/                 the online Ask chat (a Cloudflare Worker); its knowledge base is built locally, never committed
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

<!-- team:start (written by app/build_site.py from app/web/team.json) -->
<!-- team:end -->

- Course: Agentic AI Workshop 2026, Capstone 2. The starting notebook and training guide belong to the course
  and are not included here.
- Data: Microsoft AdventureWorks sample database (MIT licence).
- Fonts: Patrick Hand, Patrick Hand SC, Courier Prime (SIL Open Font Licence, `app/web/fonts/OFL.txt`).
- Voice and music: ElevenLabs (voice "Emma"); see [docs/audio-sources.md](docs/audio-sources.md).
