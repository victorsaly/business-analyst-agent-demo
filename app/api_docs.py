"""The API reference: descriptions, tags and examples for server.py's endpoints, kept here so the server stays short.

FastAPI turns these into an OpenAPI spec: browse it at http://localhost:8501/redoc (or /docs) while the app runs.
build_site.py also publishes it, with the online Ask chat's endpoints added (WORKER_PATHS), as site/api/.
"""

VERSION = "1.0"
WORKER_URL = "https://analyst-agent-ask.still-union-ef8a.workers.dev"

DESCRIPTION = """
**A course demonstration** (Capstone 2, Agentic AI Workshop 2026): an AI agent that answers plain-English
questions about sales on Microsoft's AdventureWorks sample data, and shows the query behind every number.

This is the API behind the demo app's screens. It runs **on your machine** (`cd app && ./demo.sh app`, then
`http://localhost:8501`); only the **Ask chat (online)** runs on the internet.

## Modes

Every run endpoint takes `mode`:

| Mode | Uses the AI? | What happens |
|---|---|---|
| `live` | Yes | The real agent. The run is recorded to `app/recordings/` for replay. |
| `replay` | No | Plays back a recorded live run, step by step. Errors if there's no recording yet. |
| `dry` | No | Real tool calls with scripted wording. For testing the screens only. |

## Streaming runs

`/api/run`, `/api/briefing` and `/api/scorecard` answer with **Server-Sent Events** (`text/event-stream`): one
`data: {json}` line per event, in this order. Lines starting with `:` are keep-alives; ignore them.

| `type` | When | Fields |
|---|---|---|
| `start` | first | the question or week, `mode` |
| `wait` | any time | `message`: e.g. waiting for a rate limit, switching AI service, stopping the previous run |
| `think` | before each AI round (live only) | `n` (round), `model` |
| `kpis` | briefing only, before the AI starts | `kpis` (the final KPI table), `query` (its SQL) |
| `step` | after each tool call | `n`, `tool`, `args`, `summary`, `error`, `body` (the SQL or code), `lang` |
| `result` | scorecard only, per question | `row`: `qid`, `question`, `passed`, `reasons`, `answer`, `seconds` |
| `done` | last | `result` (see each endpoint) |
| `error` | instead of `done` | `message` |

**One run at a time.** Starting a run stops the previous one, and a run stops when its browser goes away.

## Guardrails

The database file is opened **read-only**, and `run_sql` refuses anything but one `SELECT`. Answers list the
exact queries from the tool log. The agent says when the data can't answer, and never states a forecast as fact.
""".strip()

TAGS = [
    {"name": "App", "description": "What the screens need to start: data range, demo tracks, AI services, prompts."},
    {"name": "Agent runs", "description": "Ask the agent: a question, the weekly briefing or the scorecard. "
                                          "Streamed as Server-Sent Events; see **Streaming runs** above."},
    {"name": "Tools (no AI)", "description": "The agent's own read-only tools, called directly: no AI involved."},
    {"name": "Ask chat", "description": "The course students' chat, local version: answers about the task, its steps, "
                                        "the course material and how the project was built, citing its sources."},
    {"name": "Ask chat (online)", "description": f"The same chat, online, as a Cloudflare Worker at `{WORKER_URL}`. "
                                                 "It holds the AI key, answers only the demo site, and caps questions per "
                                                 "day: 300 in total and 25 per visitor."},
    {"name": "Competitor prices", "description": "Optional, for demos. AdventureWorks has no competitor data, so a "
                                                 "mock price list or your own CSV can be attached, read-only."},
]

MODE = {"description": "`live` (the AI), `replay` (a recorded live run) or `dry` (no AI, scripted).",
        "json_schema_extra": {"enum": ["live", "replay", "dry"], "example": "replay"}}
DELAY = {"description": "Seconds to pause after each step, so a replay or dry run is easy to follow (used by the video recorder)."}
SSE = {200: {"description": "A stream of Server-Sent Events: see **Streaming runs** above.",
             "content": {"text/event-stream": {"example": 'data: {"type": "start", "question": "...", "mode": "replay"}\n\n'
                                                          'data: {"type": "step", "n": 1, "tool": "run_sql", "summary": "10 rows back, saved as q1", "body": "SELECT ..."}\n\n'
                                                          'data: {"type": "done", "result": {"answer": "...", "queries": [...], "charts": [...]}}\n\n'}}}}


def json_body(example, description="", required=True):
    """Document a JSON request body that the endpoint reads itself (openapi_extra)."""
    return {"requestBody": {"required": required, "description": description,
                            "content": {"application/json": {"schema": {"type": "object"}, "example": example}}}}


ASK_BODY = json_body({"question": "How do I do Step 2?", "history": [{"role": "user", "content": "What does the brief ask for?"},
                                                                    {"role": "assistant", "content": "It asks for an agent that..."}]},
                     "`question` (up to 500 characters) and optional `history`: the last few turns, oldest first.")
ASK_ANSWER = {200: {"description": "The answer, and the passages it cited.", "content": {"application/json": {"example": {
    "answer": "The training guide says the free plan allows about 8,000 tokens a minute [1]...",
    "sources": [{"n": 1, "source": "Course training guide", "title": "Free-tier limits", "url": ""}],
    "model": "openai · gpt-5.4-mini"}}}}}

# The online chat's endpoints, added to the published spec by build_site.py (the Worker isn't a FastAPI app).
WORKER_PATHS = {
    "/ask": {"post": {
        "tags": ["Ask chat (online)"], "summary": "Ask the course chat (online)", "operationId": "worker_ask",
        "servers": [{"url": WORKER_URL, "description": "Cloudflare Worker"}],
        "description": "Same answers as `POST /api/story`, from the same knowledge base. Only requests from the demo "
                       "site are answered (checked by the `Origin` header).",
        **ASK_BODY,
        "responses": {**ASK_ANSWER,
                      "403": {"description": "Not from the demo site."},
                      "429": {"description": "Today's limit is reached (300 in total, or 25 for you)."},
                      "502": {"description": "The AI service didn't answer."}}}},
    "/health": {"get": {
        "tags": ["Ask chat (online)"], "summary": "Is the online chat up?", "operationId": "worker_health",
        "servers": [{"url": WORKER_URL, "description": "Cloudflare Worker"}],
        "responses": {"200": {"description": "Up, with the size of its knowledge base.",
                              "content": {"application/json": {"example": {"ok": True, "passages": 549, "model": "gpt-5.4-mini"}}}}}}},
}


def tidy(spec):
    """Streaming endpoints answer only with text/event-stream: drop the JSON FastAPI adds by default."""
    for ops in spec.get("paths", {}).values():
        for op in ops.values():
            content = op.get("responses", {}).get("200", {}).get("content", {})
            if "text/event-stream" in content:
                content.pop("application/json", None)
    return spec
