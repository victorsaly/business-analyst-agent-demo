# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Python back end (the existing `app/analyst` package: tools, agent loop, replay, scorecard, briefing) served
locally by FastAPI; a hand-built HTML/CSS/JS front end with no framework. Runs entirely on the presenter's
machine. Chosen by the user over restyling Streamlit, for full design control.

## Users

- **Judges and the "leadership team"** at the Agentic AI Workshop 2026 capstone presentations: they watch a
  6-minute live demo projected in a lit workshop room, read from a few metres away, then ask questions live
  (including one that leads to a planted anomaly). They also see a recorded video.
- **The presenting team** (mixed, many not Python users) drive the demo: click prepared cases, type live
  questions, fall back to replays if the AI or wifi fails.
- In the story the product tells: managers who ask simple questions about the numbers and today wait days
  for an analyst.

## Product Purpose

A Business Performance Analyst Agent: a manager asks a plain-English question about sales, and the agent
plans the analysis, writes and runs read-only SQL or pandas, corrects its own errors, draws a chart, explains
what drove the result, flags anomalies, and writes a one-page weekly leadership briefing. Success at the
presentation means judges see a working demo they can trust, and score it on business value, agent design,
working demo, trust & safety, and pitch.

## Positioning

Every number is traceable: the exact queries that produced an answer are shown from the tool log, not from
the AI's own words, against a read-only database. The agent says when the data cannot answer and never
presents a forecast or guess as a fact.

## Operating Context

- Live presentation: 13:45-15:30 sprint, 15:45-16:30 presentations; each a 6-minute demo plus 2-minute Q&A.
- Projector in a lit room; also a recorded, narrated video produced by `app/record_video.py`.
- Modes: Live AI (Groq free tier, rate-limited, with automatic fallback to OpenAI gpt-5.4-mini when the
  daily allowance runs out), Replay of a recorded live run, Dry run (no AI, scripted, for testing only).
  Replay and dry run are always labelled as such on screen.

## Capabilities and Constraints

- Data: Microsoft AdventureWorks (MIT), 30 May 2022 to 29 Jun 2025, 31,465 orders, US dollars, 10 sales
  territories, Online and Reseller channels, 4 categories. Local read-only SQLite.
- Tools: get_schema, run_sql, run_python, make_chart, detect_anomalies, explain_change.
- Margin = LineTotal - (OrderQty x StandardCost).
- Screens: overview, what changed (before/after vs the starting notebook), demo cases, tools without AI,
  weekly briefing, scorecard.
- The video recorder drives the UI by URL parameters and waits for a scene-complete signal
  ([record_video.py](../app/record_video.py)):

```python
page.goto(f"http://localhost:{PORT}/?{params}&mode={args.mode}&presenter=1&autorun=1&delay={args.delay}")
page.wait_for_selector("body[data-scene=done]", timeout=600_000)
```

## Brand Commitments

Name: "Business Performance Analyst Agent" for AdventureWorks. No team branding. No workshop or organiser
(sensiwise.ai) branding, and nothing that impersonates Microsoft.

## Evidence on Hand

Real query results from AdventureWorks; recorded live runs in `app/recordings/`; the
scorecard. No customer testimonials, benchmarks or business results exist; none may be invented.

## Product Principles

1. Show the working: the exact queries sit under every answer ("How I got this", in Developer view).
2. Honest about limits: "the data does not include…" is a feature, shown with the same weight as an answer.
3. Never blur modes: live, replay and dry run are always distinguishable.
4. Readable from the back of the room.

## Accessibility & Inclusion

Projected display: large type, high contrast that survives a washed-out projector, no meaning carried by
colour alone.
