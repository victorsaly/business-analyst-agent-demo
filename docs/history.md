# How we got here: project history

A course project, not a product. This is the **Capstone 2** project from the **Agentic AI Workshop 2026**:
build a "Business Performance Analyst Agent" that answers managers' questions about sales data. The
company, AdventureWorks, is Microsoft's public sample database of a made-up bicycle maker. No real
business data is used anywhere.

Everything happened on **1 October 2026**. Times are UK time, taken from file timestamps and the git
history, so they are approximate.

## The starting point (15:15)

The course gave us a starter notebook and a training guide. The notebook already had a working agent
"engine": a loop that lets an AI model pick tools, retry logic for the free Groq AI plan, a scorecard
and a weekly briefing. But it ran on **made-up data**: a pretend retailer with North, South, East and West
regions, prices in pounds, and four planted "stories" to find.

The brief asked for something different:
- use **Microsoft AdventureWorks**, real sample data, not made-up data;
- build **five tools**: `get_schema`, `run_sql`, `run_python`, `make_chart`, `detect_anomalies`;
- enforce **four guardrails**: read-only access, always show the query, say when the data can't answer,
  never present a forecast as a fact;
- produce a **one-page weekly leadership briefing**, and demo it all in **six minutes**.

## Step 1: Cut the AI cost (about 16:00 to 16:50)

The free Groq plan allows about 8,000 tokens a minute and 200,000 a day. We measured where the tokens
went: every round of the agent loop re-sends the rulebook and the whole tool menu. Shortening both cut
the fixed cost per round by **32%** (about 2,650 to 1,810 tokens), and one anomaly scan of five metrics
went from five rounds to one. Notes: [prompt-optimization.md](prompt-optimization.md).

## Step 2: Turn the brief into a plan (afternoon)

We wrote the brief out requirement by requirement (18 items, P1 must-have to P3 stretch) and turned it
into 13 steps a non-programmer can follow: where to click, what to paste, why, and how to check it
worked. The key decision: **keep the engine, swap what's underneath.** Sections 1 to 5 of the notebook
stay as they were; a new Section 6 is added at the bottom. Guide: [build-guide.md](build-guide.md).

## Step 3: Build Section 6 in the notebook (afternoon, finished 20:49)

In a copy of the notebook, [notebooks/capstone2_business_analyst_adventureworks.ipynb](../notebooks/capstone2_business_analyst_adventureworks.ipynb):
- **6A** downloads AdventureWorks (31,465 orders, May 2022 to June 2025) into a SQLite file that is
  opened **read-only**, with one easy view, `sales_lines`. Margin = LineTotal - OrderQty x StandardCost.
- **6B** the five tools. `run_sql` refuses anything but a single SELECT. `detect_anomalies` flags months
  or weeks far off their own recent trend.
- **6C** (stretch) `explain_change` splits a change into volume, price and mix.
- **6D** the tool "menu cards" the AI reads; **6E** the new rulebook with the four guardrails.
- **6F** switches the agent over, shows the exact queries from the tool log (never from the AI's own
  words), and lets follow-up questions remember earlier answers.
- **6G** a new scorecard: the brief's four questions plus three guardrail traps, with expected answers
  worked out from the database every time.
- **6H** the weekly briefing: the KPI table comes straight from SQL, so the AI can't mistype it.
- A **planted anomaly** (a fake 25% bike discount in Northwest, May 2024), in a separate copy of the
  database, for rehearsing.

## Step 4: A demo app around the same agent (from 19:48)

A notebook is hard to present. We moved the same code into a small Python package (`app/analyst`)
behind a FastAPI server, with a hand-built web page and **three modes**: **Live AI**, **Replay** (plays
back a recorded live run, step by step, as a backup if the wifi or AI fails) and **Dry run** (no AI,
for testing the screens only). 27 automatic checks run without any AI key.

## Step 5: Product brief and design (20:08 to 20:33)

We wrote down who it's for (judges and a "leadership team" watching a projector) and what success
looks like ([product.md](product.md)). For the look we chose a hand-lettered **cassette J-card**: the
six-minute demo as a mixtape, with side A for the brief's questions and side B for the guardrails, over the
usual dark AI dashboard ([design.md](design.md)).

## Step 6: Real AI runs, recorded (20:36 to 20:58)

The free Groq plan ran out of its daily allowance during testing, so the agent now **falls back to
OpenAI automatically** (gpt-5.4-mini). We ran every demo question live once and **recorded** it for
Replay. On those recordings the scorecard passes **6 of 7**. The miss: asked for a return rate, one run
stated "0.00%" instead of saying the data has no returns, and we left that visible. We also made a 60-second pitch video
with music and a voiceover from ElevenLabs.

## Step 7: Make it clear for every audience (21:00 onwards)

- **Fixed a stall** on the briefing screen: an earlier run left behind on another screen could hold the
  server's one-run-at-a-time lock. A new run now stops the old one, the KPI table appears at once,
  and a status line ticks every second, so a slow AI never looks frozen.
- **Stakeholder and Developer views**: stakeholders see only the answers, numbers and charts, with every
  step in plain English. Developers see every tool call, its arguments, the SQL, timings and tokens.
- **Explain this page**: a spoken explanation of every screen for each audience (ElevenLabs), with
  captions that light up word by word in time with the voice.
- **An online copy** on GitHub Pages that replays the recorded runs, plus this history and a Story chat.

## What we learned

- **Keep the engine, change the inputs.** Adding Section 6 instead of rewriting meant nothing that
  worked before broke.
- **Never trust the model with numbers it can look up.** KPI tables and "show the query" come from
  code and the tool log, not from the AI's words.
- **Measure the tokens.** On a free plan, the fixed text sent each round is the real cost.
- **Have a fallback for live demos.** Recorded replays, clearly labelled, saved the day when the AI
  allowance ran out.
- **Mark honestly.** The scorecard checks numbers against the database, so a pass means something, and
  we show the one that fails.

## What's not done

- The planted-anomaly rehearsal track has no recording yet, so it isn't in the online copy.
- The return-rate guardrail answer should be re-recorded live.
- Live AI needs a server and an API key, so the online copy is replay-only.
