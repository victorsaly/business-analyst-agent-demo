/* Business Performance Analyst Agent: demo front end (no framework).
   URL parameters: page, case, mode, aud (stakeholder | developer), autorun=1, presenter=1, delay, week.
   The video recorder waits for <body data-scene="done">. */

const params = new URLSearchParams(location.search);
const view = document.getElementById("view");
const PRESENTER = params.get("presenter") === "1";
const DELAY = params.get("delay") || (PRESENTER ? "0.6" : "0");
let META = null;
let MODE = null;
let AUD = "stakeholder";     // stakeholder: just the data · developer: every call, query and timing underneath
let SIDE = "A";
let CURRENT = null;          // id of the track playing / last played
let STREAM = null;
/* The online copy (GitHub Pages, built by build_site.py) has no server: it reads the recorded runs from
   data/*.json and plays them back. Live AI, dry runs and your own questions need the local app. */
const STATIC = !!window.STATIC_SITE;
const DEFAULT_SQL = `SELECT channel, year, ROUND(SUM(revenue)) AS revenue,
       ROUND(100.0 * SUM(margin) / SUM(revenue), 1) AS margin_pct
FROM sales_lines
GROUP BY channel, year
ORDER BY year, channel`;
// The online Ask chat: a Cloudflare Worker that holds the AI key and the knowledge base (see worker/).
const ASK_URL = "https://analyst-agent-ask.still-union-ef8a.workers.dev/ask";
const LOCAL_ONLY = "Runs in the local app only (./demo.sh app). This online copy replays recorded runs.";
function staticPath(url, body) {
  const u = new URL(url, location.origin), q = u.searchParams;
  switch (u.pathname) {
    case "/api/meta": return "data/meta.json";
    case "/api/changes": return "data/changes.json";
    case "/api/scorecard/key": return "data/scorecard_key.json";
    case "/api/scorecard": return "data/scorecard.json";
    case "/api/run": return q.get("case") ? `data/run/${q.get("case")}.json` : null;
    case "/api/briefing": return `data/briefing/${q.get("week")}.json`;
    case "/api/anomalies": return `data/anomalies/${q.get("metric")}-${q.get("by")}-${q.get("grain")}.json`;
    case "/api/sql": { const query = JSON.parse(body || "{}").query || "";
      return query.trim() === DEFAULT_SQL ? "data/sql/default.json" : /^\s*delete/i.test(query) ? "data/sql/delete.json" : null; }
    default: return null;
  }
}
async function getJSON(url, opts = {}) {
  if (!STATIC) return (await fetch(url, opts)).json();
  if (url === "/api/new-chat") return { ok: true };
  const path = staticPath(url, opts.body);
  if (!path) return { error: LOCAL_ONLY };
  const r = await fetch(path);
  return r.ok ? r.json() : { error: LOCAL_ONLY };
}
const asset = (path) => STATIC ? path.replace(/^\/static\//, "") : path;

const ICON = {
  play: '<svg class="icon" viewBox="0 0 24 24"><path d="M7 4.5v15l12-7.5z"/></svg>',
  flip: '<svg class="icon" viewBox="0 0 24 24"><path d="M4 9a8 8 0 0 1 14-3l2 2"/><path d="M20 4v4h-4"/><path d="M20 15a8 8 0 0 1-14 3l-2-2"/><path d="M4 20v-4h4"/></svg>',
  down: '<svg class="icon" viewBox="0 0 24 24"><path d="M12 4v11"/><path d="M7 10l5 5 5-5"/><path d="M5 20h14"/></svg>',
  tick: '<svg class="icon" viewBox="0 0 24 24"><path d="M4 12.5l5 5L20 6"/></svg>',
  cross: '<svg class="icon" viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18"/></svg>',
  plus: '<svg class="icon fold-ic" viewBox="0 0 24 24"><path d="M12 5v14" class="v"/><path d="M5 12h14"/></svg>',
  pen: '<svg class="icon" viewBox="0 0 24 24"><path d="M15 4l5 5L9 20H4v-5z"/><path d="M13 6l5 5"/></svg>',
};

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const mmss = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
const sum = (xs) => xs.reduce((a, b) => a + b, 0);

function inline(text) {
  return esc(text).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/`([^`]+)`/g, "<code>$1</code>");
}
function prose(text) {   // tiny markdown: paragraphs, "- " bullets, **bold**, `code`
  const out = []; let list = [];
  const flush = () => { if (list.length) { out.push(`<ul>${list.map((l) => `<li>${inline(l)}</li>`).join("")}</ul>`); list = []; } };
  for (const raw of String(text || "").split("\n")) {
    const line = raw.trim();
    if (/^[-*•]\s+/.test(line)) { list.push(line.replace(/^[-*•]\s+/, "")); continue; }
    flush();
    if (line) out.push(`<p${/^\**checked with/i.test(line) ? ' class="dev-only"' : ""}>${inline(line.replace(/^#+\s*/, ""))}</p>`);
  }
  flush();
  return out.join("");
}

function sceneDone() { document.body.dataset.scene = "done"; }
function sceneBusy() { document.body.dataset.scene = "busy"; }

function setURL(next, push = true) {
  const p = new URLSearchParams(location.search);
  for (const [k, v] of Object.entries(next)) (v === null || v === undefined) ? p.delete(k) : p.set(k, v);
  ["autorun"].forEach((k) => { if (!("autorun" in next)) p.delete(k); });
  const url = `${location.pathname}?${p}`;
  push ? history.pushState({}, "", url) : history.replaceState({}, "", url);
}

/* ---------------- mode ---------------- */
function defaultMode() {
  if (STATIC) return "replay";
  const asked = params.get("mode");
  if (asked) return asked;
  try { const saved = localStorage.getItem("mode"); if (saved) return saved; } catch (e) { /* storage blocked */ }
  return META.ai_ready ? "live" : META.any_recordings ? "replay" : "dry";
}
function setMode(m) {
  MODE = m;
  try { localStorage.setItem("mode", m); } catch (e) { /* storage blocked */ }
  document.querySelectorAll("[data-mode]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.mode === m)));
  if (currentPage() === "tracks") renderTracks(false);
}
function modeTag(mode, extra = "") {
  const label = { live: "Live AI", replay: "Replay of a recorded live run", dry: "Dry run · no AI" }[mode] || mode;
  return `<span class="tag ${mode === "dry" ? "red" : mode === "live" ? "solid" : ""}">${esc(label)}${extra}</span>`;
}
const DRY_NOTE = `<p class="dry-note">Dry run: the tool steps, queries and numbers are real, but the plan and wording are scripted by the team, not written by the AI. Switch to Live AI or Replay for the real agent.</p>`;

/* ---------------- audience ---------------- */
function defaultAud() {
  const asked = params.get("aud");
  if (asked === "developer" || asked === "stakeholder") return asked;
  try { const saved = localStorage.getItem("aud"); if (saved) return saved; } catch (e) { /* storage blocked */ }
  return "stakeholder";
}
function setAud(a) {
  if (EXPLAIN) explainStop();
  AUD = a;
  document.body.dataset.aud = a;
  try { localStorage.setItem("aud", a); } catch (e) { /* storage blocked */ }
  document.querySelectorAll("[data-aud]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.aud === a)));
}

/* ---------------- tape counter ---------------- */
const counter = { t0: 0, timer: null, budget: 0 };
function counterStart(budget) {
  counter.t0 = performance.now(); counter.budget = budget || 0;
  clearInterval(counter.timer);
  counter.timer = setInterval(counterTick, 250);
  counterTick();
}
function counterTick() {
  const s = (performance.now() - counter.t0) / 1000;
  const el = document.getElementById("counter");
  const over = counter.budget && s > counter.budget;
  el.classList.toggle("over", !!over);
  el.innerHTML = `${mmss(s)}<small>${counter.budget ? (over ? `over by ${mmss(s - counter.budget)}` : `of ${mmss(counter.budget)}`) : ""}</small>`;
  document.getElementById("position").style.transform = `scaleX(${counter.budget ? Math.min(1, s / counter.budget) : 0})`;
}
function counterStop() { clearInterval(counter.timer); counter.timer = null; }

/* ---------------- streaming runs ---------------- */
let PLAYBACK = 0;            // static playback generation: a newer run (or leaving the screen) stops the old one
async function streamStatic(url, handlers) {
  const me = ++PLAYBACK;
  const path = staticPath(url);
  let events = null;
  try { if (path) { const r = await fetch(path); if (r.ok) events = await r.json(); } } catch (e) { /* not exported */ }
  if (me !== PLAYBACK) return;
  if (!events) { (handlers.error || (() => {}))({ message: `This run isn't in the online replay. ${LOCAL_ONLY}` }); return; }
  const gap = Math.max(300, 1000 * Number(DELAY || 0));
  for (const ev of events) {
    if (["step", "result"].includes(ev.type)) await new Promise((r) => setTimeout(r, gap));
    if (me !== PLAYBACK) return;
    (handlers[ev.type] || (() => {}))(ev);
  }
}
function stopStream() {
  PLAYBACK++;
  if (STREAM) { STREAM.close(); STREAM = null; }
}
function stream(url, handlers) {
  if (STATIC) { stopStream(); streamStatic(url, handlers); return; }
  if (STREAM) STREAM.close();
  const es = new EventSource(url);
  STREAM = es;
  es.onmessage = (e) => {
    const ev = JSON.parse(e.data);
    (handlers[ev.type] || (() => {}))(ev);
    if (ev.type === "done" || ev.type === "error") { es.close(); STREAM = null; }
  };
  es.onerror = () => { if (STREAM === es) { es.close(); STREAM = null; (handlers.error || (() => {}))({ message: "Lost the connection to the local server." }); } };
}

const REFUSAL = /read-only|only reading|only select/i;
function plainStep(ev) {   // what a step means, for stakeholders
  const a = ev.args || {};
  if (ev.error) return REFUSAL.test(ev.error) ? `Refused: ${ev.error}` : "Hit a snag, so it corrected itself and tried again";
  const words = (x) => String(x || "").replace(/_pct$/, " %").replace(/_/g, " ");
  return {
    get_schema: "Read the data dictionary: which numbers exist, and for which dates",
    run_sql: "Pulled numbers from the sales database",
    run_python: "Did some extra maths on those numbers",
    make_chart: `Drew a chart${a.title ? `: ${a.title}` : ""}`,
    detect_anomalies: `Scanned ${words(a.metric) || "the numbers"}${a.by && a.by !== "total" ? ` by ${words(a.by)}` : ""} for anything unusual`,
    explain_change: "Split the change into volume, price and mix",
  }[ev.tool] || ev.summary;
}
function stepItem(ev, at = "") {
  const shown = (ev.args && Object.keys(ev.args).length) ? JSON.stringify(Object.fromEntries(Object.entries(ev.args).filter(([k]) => k !== "query" && k !== "code"))) : "";
  const args = shown && shown !== "{}" ? `<code class="args dev-only">${esc(shown)}</code>` : "";
  const body = ev.body ? `<details class="q dev-only" open><summary>show ${ev.lang === "python" ? "code" : "query"}</summary><pre class="typed">${esc(ev.body)}</pre></details>` : "";
  return `<li class="${ev.error ? "err" : ""}"><div class="line"><span class="num">${ev.n}</span>`
    + `<span class="tool dev-only">${esc(ev.tool)}</span><span class="sum dev-only">${esc(ev.error ? "Refused: " + ev.error : ev.summary)}</span>`
    + `<span class="sum sh-only">${esc(plainStep(ev))}</span><span class="at dev-only">${at}</span></div>${args}${body}</li>`;
}
function foldSteps(list) { list.querySelectorAll("details.q[open]").forEach((d) => d.removeAttribute("open")); }
function writingLine(text) { return `<li class="writing" id="writing">${esc(text)}</li>`; }

/* A run in progress: the steps list, a status line that ticks every second (so a slow AI never looks
   frozen), AI-round markers for developers, and an offer to switch to the recording if it runs long. */
function progress(steps, { budget = 0, onSlow } = {}) {
  const t0 = performance.now();
  const secs = () => (performance.now() - t0) / 1000;
  let status = "Starting", slow = false;
  const paint = () => {
    const w = document.getElementById("writing");
    if (w) w.textContent = `${status}… ${Math.floor(secs())}s`;
    if (!slow && onSlow && secs() > (budget || 60)) { slow = true; onSlow(); }
  };
  const timer = setInterval(paint, 500);
  const at = () => `+${secs().toFixed(1)}s`;
  paint();
  return {
    say(text) { status = text; paint(); },
    step(ev) {
      document.getElementById("writing")?.remove(); foldSteps(steps);
      steps.insertAdjacentHTML("beforeend", stepItem(ev, at()) + writingLine(""));
      status = "Working"; paint();
    },
    think(ev) {
      const w = document.getElementById("writing");
      const li = `<li class="think dev-only"><div class="line"><span class="num">·</span><span class="tool">AI round ${ev.n}</span><span class="sum">${esc(ev.model)}</span><span class="at">${at()}</span></div></li>`;
      w ? w.insertAdjacentHTML("beforebegin", li) : steps.insertAdjacentHTML("beforeend", li);
      status = ev.n === 1 ? "The AI is reading the question and planning" : "The AI is deciding what to check next";
      paint();
    },
    stop() { clearInterval(timer); document.getElementById("writing")?.remove(); document.getElementById("slow")?.remove(); },
  };
}
function slowSlip(where, budget, canReplay, onReplay) {
  where.insertAdjacentHTML("beforebegin", `<div class="slow" id="slow"><span>Taking longer than usual${budget ? ` (its slot is ${mmss(budget)})` : ""}. The AI service may be busy.</span>${canReplay ? `<button class="btn" type="button" id="toreplay">${ICON.play} Show the recorded run instead</button>` : ""}</div>`);
  document.getElementById("toreplay")?.addEventListener("click", onReplay);
}
const EXPECT = {
  live: "Live AI: each step appears as it happens. Usually 10 to 30 seconds.",
  replay: "Replay: a recorded live run, played back step by step.",
  dry: "",
};

function resultBlock(r) {
  const charts = (r.charts || []).map((c) => `<figure class="chart"><img alt="${esc(c.caption)}" src="data:image/png;base64,${c.png}"><figcaption>${esc(c.id)}: ${esc(c.caption)}</figcaption></figure>`).join("");
  const notes = (r.queries || []).length
    ? `<ol class="notes">${r.queries.map((q) => `<li><div class="lab">${esc(q.label)}</div><pre class="typed">${esc(q.text)}</pre></li>`).join("")}</ol>`
    : `<p class="note">No queries were run for this answer.</p>`;
  const when = r.recorded_at ? ` · recorded ${esc(r.recorded_at)}` : "";
  const n = (r.queries || []).length;
  return `<div class="section"><h2>Answer</h2></div><div class="answer">${prose(r.answer)}</div>${charts}
    <p class="foot sh-only">${n ? `Every number above comes from ${n} database quer${n === 1 ? "y" : "ies"}. Switch to Developer to see them.` : "No database queries were needed for this answer."}</p>
    <div class="dev-only"><div class="section"><h2>How I got this</h2></div>${notes}
    <p class="foot">${r.steps} tool call${r.steps === 1 ? "" : "s"} · ${Number(r.tokens || 0).toLocaleString()} tokens · ${r.seconds}s · ${esc(r.model || "")}${when}</p></div>`;
}

/* ---------------- pages ---------------- */
function currentPage() { return new URLSearchParams(location.search).get("page") || "home"; }

function render() {
  if (ZOOMED) zoomOut();
  if (EXPLAIN) explainStop();
  stopStream(); counterStop();   // leaving a screen stops its run (the server cancels it too)
  const go = () => renderNow();
  if (document.startViewTransition && !matchMedia("(prefers-reduced-motion: reduce)").matches && META) document.startViewTransition(go);
  else go();
}
function renderNow() {
  sceneBusy();
  const page = currentPage();
  menuClose();   // first: puts a phone's open list back inside the nav so the highlight below sees its links
  document.querySelectorAll(".masthead nav a").forEach((a) => { if (a.dataset.page === page) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current"); });
  document.querySelectorAll(".masthead .menu").forEach((m) => m.classList.toggle("current", !!m.querySelector('a[aria-current="page"]')));
  ({ home: renderHome, cover: renderCover, changes: renderChanges, tracks: () => renderTracks(true), tools: renderTools, briefing: renderBriefing, scorecard: renderScorecard, story: renderStory }[page] || (() => renderTracks(true)))();
}

function renderCover() {
  const sideA = META.tracks.filter((t) => t.side === "A");
  view.innerHTML = `
  <div class="cover">
    <div>
      <p class="course-badge"><img src="${asset("/static/logo.svg")}" alt="" width="40" height="40"> Course demonstration · Capstone 2 · Agentic AI Workshop 2026</p>
      <h1>Business Performance Analyst Agent</h1>
      <div class="underline"></div>
      <p class="lede">Ask the numbers a question in plain English. Get the answer, the chart, and the query behind it.</p>
      <div class="actions">
        <a class="btn primary" href="?page=tracks" data-nav>${ICON.play} Play side A</a>
        <a class="btn" href="?page=changes" data-nav>What changed</a>
      </div>
      <div class="facts">
        <p>Microsoft AdventureWorks: ${META.orders.toLocaleString()} orders, ${esc(fmtDate(META.data_from))} to ${esc(fmtDate(META.data_to))}, ten sales territories, US dollars. A local database the agent can only read.</p>
        <p class="typed">Margin = LineTotal &minus; (OrderQty &times; StandardCost)</p>
        <p class="typed dev-only">AI services, in order: ${META.providers.map(esc).join(" → ") || "none set"}<br>Tools: ${META.tools.map(esc).join(", ")}<br>Server: FastAPI, streaming tool calls as server-sent events</p>
      </div>
    </div>
    <div class="panel">
      <div class="rule-head"><h2>How it plays</h2></div>
      <ol class="list">
        ${["Plain-English question", "Plan the analysis", "Write SQL or pandas", "Run it, fix its own errors", "Chart and the reason why", "Weekly leadership briefing"]
          .map((t, i) => `<li><span class="n">${String(i + 1).padStart(2, "0")}</span><span class="t">${t}</span><span></span></li>`).join("")}
      </ol>
      <div class="rule-head"><h2>House rules</h2></div>
      <ul class="list">
        ${[["Read-only", "The database file is opened read-only; only SELECT queries run."],
           ["Show the working", "Every answer lists the exact queries, taken from the tool log."],
           ["Say when it can't", "No competitor, returns or satisfaction data: it says so."],
           ["No forecast as fact", "Projections are labelled estimates, or not made."]]
          .map(([t, d]) => `<li class="plain"><span class="t">${t}</span><span class="d">${d}</span></li>`).join("")}
      </ul>
    </div>
  </div>`;
  if (PRESENTER) view.insertAdjacentHTML("afterbegin", `<p class="margin-note"><b>Point out:</b> managers wait days for an analyst. This answers in about a minute, and every number can be checked.</p>`);
  sceneDone();
}

const REQS = [
  ["Use AdventureWorks", "New", "P1"], ["get_schema(): tables, columns, data dictionary", "New", "P1"],
  ["run_sql(query): read-only", "New", "P1"], ["run_python(code): pandas sandbox", "New", "P1"],
  ["make_chart(data, type): bar, line, breakdown", "Changed", "P1"], ["detect_anomalies(metric)", "Changed", "P1"],
  ["Margin = LineTotal − OrderQty × StandardCost", "Changed", "P1"], ["Guardrail: read-only access", "New", "P1"],
  ["Guardrail: always show the query", "Changed", "P1"], ["Guardrail: say when data can't answer", "Changed", "P1"],
  ["Guardrail: never present a forecast as fact", "New", "P1"], ["Explain what drove a result", "Changed", "P1"],
  ["Fix its own errors", "Changed", "P1"], ["The four 'Try these first' questions", "Changed", "P1"],
  ["One-page weekly briefing", "Changed", "P2"], ["Planted-anomaly demo moment", "New", "P2"],
  ["Stretch: follow-up drill-downs", "New", "P3"], ["Stretch: volume / price / mix breakdown", "New", "P3"],
];

async function renderChanges() {
  view.innerHTML = `
  <h1 class="page-title">What changed</h1>
  <p class="page-lede">We kept the agent's engine from the starting notebook and changed what it works on: real data, the five tools from the brief, and four guardrails.</p>
  ${PRESENTER ? `<p class="margin-note"><b>Point out:</b> same engine, real data, the brief's tools, and the guardrails built in.</p>` : ""}
  <div class="two">
    <div><div class="rule-head"><h2>Before</h2></div><ol class="list">
      ${["Made-up retailer: North, South, East, West, in £", "Tools only worked on the made-up data", "No SQL, no Python sandbox", "Answers showed tool steps, not the queries", "No rule about forecasts", "Exam questions about the made-up regions"].map((t) => `<li class="plain"><span class="t">${t}</span></li>`).join("")}
    </ol></div>
    <div><div class="rule-head"><h2>After</h2></div><ol class="list">
      ${["Microsoft AdventureWorks: ten territories, US $", "get_schema, run_sql, run_python, make_chart, detect_anomalies", "Read-only SQL that fixes its own errors", "Every answer lists its exact queries", "Forecasts are never stated as fact", "New scorecard, briefing and follow-ups"].map((t) => `<li class="plain"><span class="t">${t}</span></li>`).join("")}
    </ol></div>
  </div>
  <div class="rule-head" style="margin-top:1.5rem"><h2>The brief, line by line</h2><span class="total">${REQS.length} of ${REQS.length} done</span></div>
  <div class="req-wrap">${REQS.map(([t, c, p]) => `<div class="req">${ICON.tick}<span class="t">${esc(t)}</span><span class="c">${c}</span><span class="p">${p}</span></div>`).join("")}</div>
  <details class="fold dev-only"><summary>${ICON.plus}The agent's rulebook, before and after</summary><div class="two" id="prompts"><p class="note">Loading…</p></div></details>
  <details class="fold dev-only"><summary>${ICON.plus}The tool descriptions the AI reads</summary><ol class="list" id="toolcards"></ol></details>`;
  const ch = await getJSON("/api/changes");
  document.getElementById("prompts").innerHTML = `<div><div class="rule-head"><h2>Before</h2></div><pre class="typed">${esc(ch.old_prompt || "(starting notebook not found)")}</pre></div><div><div class="rule-head"><h2>After</h2></div><pre class="typed">${esc(ch.new_prompt)}</pre></div>`;
  document.getElementById("toolcards").innerHTML = ch.tools.map((t, i) => `<li><span class="n">${String(i + 1).padStart(2, "0")}</span><span class="t typed" style="font-size:1.05rem;font-weight:700">${esc(t.name)}</span><span></span><span class="d">${esc(t.description)}</span></li>`).join("");
  sceneDone();
}

/* ---------- tracks ---------- */
function trackRows(side) {
  const tracks = META.tracks.filter((t) => t.side === side);
  return tracks.map((t, i) => trackRow(t, i + 1)).join("");
}
function trackRow(t, n) {
  const needsRec = MODE === "replay" && !t.page && !t.recorded;
  const sub = needsRec ? `<span class="sub">No recording yet: play it once in Live AI.</span>` : t.page ? `<span class="sub">Opens the ${esc(t.page)} screen</span>` : "";
  const num = CURRENT === t.id ? ICON.play : typeof n === "number" ? String(n).padStart(2, "0") : n;
  return `<button class="track" type="button" data-track="${t.id}" ${CURRENT === t.id ? 'aria-current="true"' : ""} ${needsRec ? "disabled" : ""}>
    <span class="n">${num}</span><span class="t">${esc(t.title)}</span><span class="time">${mmss(t.budget)}</span>${sub}</button>`;
}
function sideTotal(side) { return sum(META.tracks.filter((t) => t.side === side).map((t) => t.budget)); }

function renderTracks(fresh) {
  const P = new URLSearchParams(location.search);
  const caseId = P.get("case");
  if (fresh && caseId) { const t = META.tracks.find((x) => x.id === caseId); if (t && t.side !== "bonus") SIDE = t.side; }
  const bonus = META.tracks.filter((t) => t.side === "bonus");
  const listHTML = `
    <div class="sides" role="group" aria-label="Tape side">
      <button type="button" data-side="A" aria-pressed="${SIDE === "A"}">Side A</button>
      <button type="button" data-side="B" aria-pressed="${SIDE === "B"}">Side B</button>
    </div>
    <div class="side-face" id="face">
      <div class="rule-head"><h2>Side ${SIDE}</h2><span class="total">${mmss(sideTotal(SIDE))}</span></div>
      ${trackRows(SIDE)}
      ${SIDE === "B" && bonus.length ? `<div class="hidden-track"><div class="gap">· · · hidden track${bonus.length > 1 ? "s" : ""} · · ·</div>${bonus.map((t) => trackRow(t, "+")).join("")}</div>` : ""}
    </div>
    <div class="budget"><span>Both sides</span><span>${mmss(sideTotal("A") + sideTotal("B"))} of 6:00</span></div>
    <div class="ask">
      <form id="askform"><input id="askq" placeholder="${STATIC ? "Your own questions: local app only" : "Write your own question…"}" aria-label="Your own question" autocomplete="off" ${STATIC ? "disabled" : ""}><button class="btn primary" type="submit" ${STATIC ? "disabled" : ""}>${ICON.pen} Ask</button></form>
      ${compNote()}
      <div class="memory">${META.history.length ? `Follow-ups remember: ${META.history.map((h) => `“${esc(h)}”`).join(", then ")}` : "Follow-up questions remember the last two answers."} <button type="button" class="linkish" id="newchat">New conversation</button></div>
    </div>`;
  const existing = document.getElementById("tapelist");
  if (existing && !fresh) { existing.innerHTML = listHTML; bindTracklist(); return; }
  view.innerHTML = `<div class="deck"><div class="tapelist" id="tapelist">${listHTML}</div><section class="playing" id="playing" aria-live="polite"></section></div>`;
  bindTracklist();
  const playing = document.getElementById("playing");
  if (fresh && caseId && P.get("autorun") === "1") { playTrack(caseId); return; }
  if (fresh && P.get("ask") && !STATIC) { const q = P.get("ask"); setURL({ ask: null }, false); playQuestion(q); return; }
  playing.innerHTML = `<div class="empty"><h1>Pick a track.</h1><p>Side A plays the brief's four questions and a follow-up. Side B shows the guardrails, the weekly briefing and the scorecard. Or write your own question.</p>${MODE === "dry" ? DRY_NOTE : ""}</div>`;
  sceneDone();
}

function bindTracklist() {
  document.querySelectorAll("[data-side]").forEach((b) => b.onclick = () => flipTo(b.dataset.side));
  document.querySelectorAll("[data-track]").forEach((b) => b.onclick = () => playTrack(b.dataset.track));
  document.getElementById("askform").onsubmit = (e) => { e.preventDefault(); const q = document.getElementById("askq").value.trim(); if (q) playQuestion(q); };
  document.getElementById("newchat").onclick = async () => { await getJSON("/api/new-chat", { method: "POST" }); META.history = []; renderTracks(false); };
}

function flipTo(side) {
  if (side === SIDE) return;
  const face = document.getElementById("face");
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduce || !face) { SIDE = side; renderTracks(false); return; }
  face.classList.add("turning");
  setTimeout(() => { SIDE = side; renderTracks(false); const f = document.getElementById("face"); f.classList.add("turning"); requestAnimationFrame(() => requestAnimationFrame(() => f.classList.remove("turning"))); }, 220);
}

function playTrack(id) {
  const t = META.tracks.find((x) => x.id === id);
  if (!t) return;
  if (t.page) { setURL({ page: t.page, case: null }); render(); return; }
  CURRENT = id;
  setURL({ page: "tracks", case: id }, false);
  renderTracks(false);
  runQuestion({ caseId: id, question: t.question, budget: t.budget, point: t.point, planted: t.db === "planted", title: t.title, side: t.side, competitors: t.competitors || null });
}
function playQuestion(q) {
  CURRENT = null;
  renderTracks(false);
  runQuestion({ question: q, budget: 0, competitors: META.competitors?.selected || null });
}

/* On a phone the answer sits below the tracklist: bring it into view, or a tap looks like it did nothing. */
function showOnPhone(el) {
  if (!el || !matchMedia("(max-width: 1100px)").matches) return;
  el.scrollIntoView({ block: "start", behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
}

function runQuestion({ caseId, question, budget, point, planted, side, competitors }) {
  sceneBusy();
  const playing = document.getElementById("playing");
  const where = side === "bonus" ? "Hidden track" : side ? `Side ${side}` : "Your question";
  playing.innerHTML = `
    ${PRESENTER && point ? `<p class="margin-note"><b>Point out:</b> ${esc(point)}</p>` : ""}
    <h1>${esc(question)}</h1><div class="rule3"></div>
    <div class="meta">${modeTag(MODE)}${planted ? ' <span class="tag red">Rehearsal data: planted anomaly</span>' : ""}${competitors ? ` <span class="tag${competitors === "mock" ? " red" : ""}">${competitors === "mock" ? "Mock competitor prices" : "Your competitor prices"}</span>` : ""}<span>${where}${budget ? ` · budget ${mmss(budget)}` : ""}</span></div>
    ${MODE === "dry" ? DRY_NOTE : ""}
    ${EXPECT[MODE] ? `<p class="expect">${EXPECT[MODE]}</p>` : ""}
    <ol class="steps" id="steps">${writingLine("Reading the question…")}</ol>
    <div id="result"></div>`;
  showOnPhone(playing);
  counterStart(budget);
  const steps = document.getElementById("steps");
  const track = caseId && META.tracks.find((x) => x.id === caseId);
  const prog = progress(steps, {
    budget, onSlow: MODE === "live" ? () => slowSlip(steps, budget, !!(track && track.recorded), () => { setMode("replay"); playTrack(caseId); }) : null,
  });
  const q = new URLSearchParams({ mode: MODE, delay: DELAY });
  caseId ? q.set("case", caseId) : q.set("question", question);
  stream(`/api/run?${q}`, {
    step: (ev) => prog.step(ev),
    think: (ev) => prog.think(ev),
    wait: (ev) => prog.say(ev.message),
    done: (ev) => {
      prog.stop(); counterStop(); foldSteps(steps);
      document.getElementById("result").innerHTML = resultBlock(ev.result);
      if (caseId) { const t = META.tracks.find((x) => x.id === caseId); if (t && ev.result.mode === "live") t.recorded = true; }
      META.history = [...META.history, question].slice(-2);
      sceneDone();
    },
    error: (ev) => {
      prog.stop(); counterStop();
      document.getElementById("result").innerHTML = `<div class="slip"><b>Stopped.</b> ${esc(ev.message)}</div>`;
      sceneDone();
    },
  });
}

/* ---------- tools (no AI) ---------- */
function renderTools() {
  const opt = (xs, sel) => xs.map((x) => `<option ${x === sel ? "selected" : ""}>${x}</option>`).join("");
  view.innerHTML = `
  <h1 class="page-title">Tools, no AI</h1>
  <p class="page-lede">The same read-only tools the agent presses, used by hand.</p>
  ${PRESENTER ? `<p class="margin-note"><b>Point out:</b> try to delete data and the tool refuses; the database file is read-only too.</p>` : ""}
  <div class="two">
    <section>
      <div class="rule-head"><h2>Anomaly scan</h2></div>
      <form class="controls" id="anform">
        <div class="field"><label for="am">Metric</label><select id="am">${opt(["revenue", "margin", "cost", "margin_pct", "units", "orders", "avg_discount_pct"], "revenue")}</select></div>
        <div class="field"><label for="ab">By</label><select id="ab">${opt(["total", "channel", "territory", "category", "country", "territory_group", "subcategory"], "channel")}</select></div>
        <div class="field"><label for="ag">Grain</label><select id="ag">${opt(["month", "week"], "month")}</select></div>
        <div class="field"><label for="ap">Period</label><input id="ap" size="8" value="${esc(META.periods.latest_quarter)}" ${STATIC ? `readonly title="${esc(LOCAL_ONLY)}"` : ""}></div>
        <button class="btn primary" type="submit">Scan</button>
      </form>
      <div id="anout"></div>
    </section>
    <section>
      <div class="rule-head"><h2>Read-only SQL</h2></div>
      <p class="note sh-only" style="margin-top:0.8rem">Revenue and margin by channel and year, read straight from the database. Then try to delete orders: the request is refused.</p>
      <div class="field dev-only" style="margin-top:0.8rem"><label for="sq">Query</label><textarea id="sq" rows="7" ${STATIC ? `readonly title="${esc(LOCAL_ONLY)}"` : ""}>${DEFAULT_SQL}</textarea></div>
      <div class="controls"><button class="btn primary" id="sqlrun" type="button"><span class="dev-only">Run query</span><span class="sh-only">Show the numbers</span></button><button class="btn warn" id="sqldel" type="button">Try: delete the orders</button></div>
      <div id="sqlout"></div>
    </section>
  </div>
  <section class="comp">
    <div class="rule-head"><h2>Competitor prices</h2><span class="total" id="compstate"></span></div>
    <p class="note">AdventureWorks has no competitor prices, so the agent says so (side B, track 1). For a demo, attach a price list: the mock one (three fictional shops), or your own CSV in the template's format. Your own questions then see it; the guardrail track never does.</p>
    <div class="controls">
      <button class="btn primary" type="button" data-comp="mock" ${STATIC ? `disabled title="${esc(LOCAL_ONLY)}"` : ""}>Use the mock price list</button>
      <a class="btn" ${STATIC ? `aria-disabled="true" title="${esc(LOCAL_ONLY)}"` : 'href="/api/competitors/template.csv" download'}>${ICON.down} Download the template (CSV)</a>
      <label class="btn" for="compfile" ${STATIC ? `aria-disabled="true" title="${esc(LOCAL_ONLY)}"` : ""}>${ICON.pen} Attach your CSV…</label>
      <input type="file" id="compfile" accept=".csv,text/csv" hidden ${STATIC ? "disabled" : ""}>
      <button class="btn" type="button" data-comp="off" ${STATIC ? "disabled" : ""}>Detach</button>
    </div>
    <p class="note dev-only">Columns: <code>product, competitor, competitor_price, observed_date</code> (date optional, prices in $). Product names must match AdventureWorks names, e.g. <code>Road-150 Red, 62</code>. The agent reads it as the <code>price_comparison</code> view, attached read-only.</p>
    <div id="compout"></div>
  </section>`;
  const scan = async () => {
    const q = new URLSearchParams({ metric: am.value, by: ab.value, grain: ag.value, period: ap.value });
    const r = await getJSON(`/api/anomalies?${q}`);
    if (r.error) { anout.innerHTML = `<div class="slip"><b>Can't scan.</b> ${esc(r.error)}</div>`; return; }
    const maxz = Math.max(1, ...r.runs.map((x) => Math.abs(x.z)));
    const fmt = (v) => /pct/.test(r.metric) ? `${Number(v).toFixed(1)}%` : /revenue|margin|cost/.test(r.metric) ? `$${Math.round(v).toLocaleString()}` : Math.round(v).toLocaleString();
    anout.innerHTML = `<p style="font-size:1.25rem">${esc(r.summary)}</p>
      ${r.runs.length ? `<ul class="runs">${r.runs.map((x) => { const d = 0.8 + 2.4 * Math.min(1, Math.abs(x.z) / Math.min(maxz, 20)); return `<li><span class="mag ${x.direction}" style="width:${d}rem" aria-hidden="true"></span><span><b>${esc(x.segment)}</b>, ${esc(x.periods)}: ${x.direction === "high" ? "high" : "low"}, peak ${fmt(x.value)} vs about ${fmt(x.expected)} expected</span></li>`; }).join("")}</ul>` : ""}
      <pre class="typed dev-only">${esc(r.query)}</pre>`;
  };
  const runSQL = async (query) => {
    const r = await getJSON("/api/sql", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query }) });
    if (r.error) { sqlout.innerHTML = `<div class="slip"><b>Refused.</b> ${esc(r.error)}${r.hint ? `<br>${esc(r.hint)}` : ""}</div>`; return; }
    const cols = r.columns;
    sqlout.innerHTML = `<table class="ruled"><thead><tr>${cols.map((c) => `<th>${esc(c)}</th>`).join("")}</tr></thead><tbody>${r.rows.map((row) => `<tr>${cols.map((c) => typeof row[c] === "number" ? `<td class="num">${/year|id$|week|month/i.test(c) ? row[c] : row[c].toLocaleString()}</td>` : `<td>${esc(row[c])}</td>`).join("")}</tr>`).join("")}</tbody></table><p class="foot dev-only">${esc(r.summary)}</p>`;
  };
  const [am, ab, ag, ap, anout, sqlout] = ["am", "ab", "ag", "ap", "anout", "sqlout"].map((id) => document.getElementById(id));
  document.getElementById("anform").onsubmit = (e) => { e.preventDefault(); scan(); };
  document.getElementById("sqlrun").onclick = () => runSQL(document.getElementById("sq").value);
  document.getElementById("sqldel").onclick = () => runSQL("DELETE FROM SalesOrderHeader WHERE OrderDate < '2023-01-01'");
  bindCompetitors();
  Promise.all([scan(), runSQL(document.getElementById("sq").value), showCompetitors()]).then(sceneDone);
}

/* ---------- competitor prices (optional demo data) ---------- */
const COMP_QUESTION = "How do our bike prices compare with our competitors' prices?";
function compNote() {
  const c = META.competitors, sel = c && c.selected && c[c.selected];
  return sel ? `<div class="memory"><span>Competitor prices attached: <b>${esc(c.selected === "mock" ? "mock list" : sel.filename)}</b>. Your questions can use them.</span> <a class="linkish" href="?page=tools" data-nav>Change</a></div>` : "";
}
async function showCompetitors(msg = "") {
  const out = document.getElementById("compout"), state = document.getElementById("compstate");
  if (!out) return;
  const c = META.competitors || {}, sel = c.selected && c[c.selected];
  state.textContent = sel ? (c.selected === "mock" ? "Mock list attached" : "Your list attached") : "Not attached";
  if (!sel) { out.innerHTML = msg || `<p class="note">Nothing attached: the agent will say it has no competitor data.</p>`; return; }
  const skipped = (sel.skipped_rows ? `${sel.skipped_rows} row${sel.skipped_rows === 1 ? "" : "s"} skipped (no price). ` : "")
    + (sel.unmatched_count ? `${sel.unmatched_count} product name${sel.unmatched_count === 1 ? "" : "s"} didn't match AdventureWorks, e.g. ${sel.unmatched.slice(0, 3).map((u) => `“${esc(u)}”`).join(", ")}.` : "");
  const r = await getJSON("/api/sql", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query:
    "SELECT category, competitor, COUNT(*) AS products, ROUND(AVG(list_gap_pct), 1) AS our_price_vs_theirs_pct\nFROM price_comparison\nWHERE category NOT LIKE '(%'\nGROUP BY category, competitor ORDER BY category, competitor" }) });
  const gap = (v) => v == null ? "" : `${v > 0 ? "+" : ""}${v}%`;
  out.innerHTML = `${msg}<p style="font-size:1.15rem">${c.selected === "mock" ? '<span class="tag red">Mock data</span> ' : ""}${esc(sel.label)}: ${sel.rows.toLocaleString()} prices, ${sel.products} products, ${sel.competitors.map(esc).join(", ")}.</p>
    ${skipped ? `<p class="note">${skipped}</p>` : ""}
    ${r.error ? `<div class="slip">${esc(r.error)}</div>` : `<table class="ruled"><thead><tr><th>Category</th><th>Competitor</th><th class="num">Products</th><th class="num">Our list price vs theirs</th></tr></thead>
      <tbody>${r.rows.map((x) => `<tr><td>${esc(x.category)}</td><td>${esc(x.competitor)}</td><td class="num">${x.products}</td><td class="num">${gap(x.our_price_vs_theirs_pct)}</td></tr>`).join("")}</tbody></table>
      <p class="foot">Above 0 means we are dearer. Read straight from the database, no AI.</p>`}
    <p style="margin-top:1rem"><a class="btn primary" href="?page=tracks&ask=${encodeURIComponent(COMP_QUESTION)}" data-ask>${ICON.play} Ask the agent: “${esc(COMP_QUESTION)}”</a></p>`;
}
function bindCompetitors() {
  const out = document.getElementById("compout");
  const apply = async (res, done = "") => {
    if (res.error) { out.insertAdjacentHTML("afterbegin", `<div class="slip"><b>Not attached.</b> ${esc(res.error)}</div>`); return; }
    META.competitors = res;
    await showCompetitors(done);
  };
  document.querySelectorAll("[data-comp]").forEach((b) => b.onclick = async () => {
    const source = b.dataset.comp === "off" ? null : b.dataset.comp;
    apply(await getJSON("/api/competitors/use", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ source }) }));
  });
  document.getElementById("compfile").onchange = async (e) => {
    const file = e.target.files[0];
    e.target.value = "";
    if (!file) return;
    out.innerHTML = `<p class="note">Reading ${esc(file.name)}…</p>`;
    apply(await getJSON("/api/competitors/upload", { method: "POST", headers: { "Content-Type": "text/csv", "X-Filename": file.name }, body: file }));
  };
}

/* ---------- briefing ---------- */
function renderBriefing() {
  const P = new URLSearchParams(location.search);
  const week = P.get("week") || META.latest_week;
  view.innerHTML = `
  <h1 class="page-title">Weekly leadership briefing</h1>
  <p class="page-lede">One page: the KPI table straight from SQL, the agent's commentary and charts, and every query it used.</p>
  ${PRESENTER ? `<p class="margin-note"><b>Point out:</b> the KPI numbers come straight from SQL, so the AI can't mistype them.</p>` : ""}
  <div class="controls">
    <div class="field"><label for="wk">Week starting</label><select id="wk">${META.weeks.map((w) => `<option ${w === week ? "selected" : ""}>${w}</option>`).join("")}</select></div>
    <button class="btn primary" id="build" type="button">${ICON.pen} Write the briefing</button>
  </div>
  <p class="note">AdventureWorks books Reseller orders about once a month, so weekly numbers swing a lot. The briefing says so.</p>
  <div id="bout"></div>`;
  const BUDGET = 40;
  const build = () => {
    sceneBusy();
    const wk = document.getElementById("wk").value;
    const bout = document.getElementById("bout");
    const expect = { live: "The KPI table appears first, straight from SQL. Then the AI investigates and writes the commentary: usually about 20 seconds.",
                     replay: "Replay: a recorded live briefing, played back step by step.", dry: "" }[MODE];
    bout.innerHTML = `<div class="meta">${modeTag(MODE)}</div>${MODE === "dry" ? DRY_NOTE : ""}${expect ? `<p class="expect">${expect}</p>` : ""}
      <div id="bkpis"></div><ol class="steps" id="bsteps">${writingLine("Looking up the KPI table…")}</ol><div id="bsheet"></div>`;
    counterStart(BUDGET);
    const steps = document.getElementById("bsteps");
    const recorded = (META.briefing_recorded || []).includes(wk);
    const prog = progress(steps, {
      budget: BUDGET, onSlow: MODE === "live" ? () => slowSlip(steps, BUDGET, recorded, () => { setMode("replay"); build(); }) : null,
    });
    prog.say("Looking up the KPI table");
    stream(`/api/briefing?${new URLSearchParams({ mode: MODE, week: wk, delay: DELAY })}`, {
      kpis: (ev) => {
        document.getElementById("bkpis").innerHTML = `<div class="kpi-early"><div class="section"><h2>Key numbers, week of ${esc(fmtDate(wk))}</h2></div>${kpiTable(ev.kpis)}
          <p class="note">Final already: these come straight from SQL. The commentary below is being written.</p></div>`;
        prog.say(MODE === "live" ? "Asking the AI to investigate" : "Investigating");
      },
      step: (ev) => prog.step(ev),
      think: (ev) => prog.think(ev),
      wait: (ev) => prog.say(ev.message),
      done: (ev) => {
        prog.stop(); counterStop();
        if (ev.result.mode === "live" && !recorded) META.briefing_recorded = [...(META.briefing_recorded || []), wk];
        document.getElementById("bout").innerHTML = sheet(ev.result); sceneDone();
      },
      error: (ev) => { prog.stop(); counterStop(); document.getElementById("bsheet").innerHTML = `<div class="slip"><b>Stopped.</b> ${esc(ev.message)}</div>`; sceneDone(); },
    });
  };
  document.getElementById("build").onclick = build;
  if (P.get("autorun") === "1") build(); else sceneDone();
}
function kpiTable(kpis) {
  return `<table class="ruled"><thead><tr><th>KPI</th><th class="num">This week</th><th class="num">Last week</th><th class="num">vs last week</th><th class="num">4-week avg</th><th class="num">vs 4-week avg</th></tr></thead>
      <tbody>${kpis.map((k) => `<tr><td>${esc(k.label)}</td><td class="num"><b>${esc(k.now)}</b></td><td class="num">${esc(k.last)}</td><td class="num">${esc(k.vs_last)}</td><td class="num">${esc(k.avg4)}</td><td class="num">${esc(k.vs_avg4)}</td></tr>`).join("")}</tbody></table>`;
}
function sheet(b) {
  const p = b.parts;
  const ul = (xs) => xs.length ? `<ul>${xs.map((x) => `<li>${inline(x)}</li>`).join("")}</ul>` : `<p class="note">None.</p>`;
  const blob = URL.createObjectURL(new Blob([`<!doctype html><html><head><meta charset="utf-8"><title>Weekly briefing ${b.week}</title></head><body style="margin:0;padding:24px;background:#fcfbf7">${b.html}</body></html>`], { type: "text/html" }));
  return `<article class="sheet">
    <div class="meta">${modeTag(b.mode)}<span>Week of ${esc(fmtDate(b.week))}</span></div>${b.mode === "dry" ? DRY_NOTE : ""}
    <h1>${inline(p.headline || "Weekly briefing")}</h1>
    ${kpiTable(b.kpis)}
    <div class="section"><h2>What changed and why</h2></div><div class="answer">${ul(p.changed)}</div>
    <div class="section"><h2>Watch list</h2></div><div class="answer">${ul(p.watch)}</div>
    ${(b.charts || []).map((c) => `<figure class="chart"><img alt="${esc(c.caption)}" src="data:image/png;base64,${c.png}"><figcaption>${esc(c.caption)}</figcaption></figure>`).join("")}
    <div class="section"><h2>Recommended follow-ups</h2></div><div class="answer">${ul(p.followups)}</div>
    <p class="foot sh-only">Every number comes from ${b.queries.length} read-only database queries. Switch to Developer to see them. Nothing here is a forecast.</p>
    <div class="dev-only"><div class="section"><h2>How these numbers were produced</h2></div>
    <ol class="notes">${b.queries.map((q) => `<li><div class="lab">${esc(q.label)}</div><pre class="typed">${esc(q.text)}</pre></li>`).join("")}</ol>
    ${b.mode !== "dry" ? `<p class="foot">${b.steps} tool calls · ${Number(b.tokens || 0).toLocaleString()} tokens · ${b.seconds}s · ${esc(b.model || "")}</p>` : ""}</div>
    <p style="margin-top:1.5rem"><a class="btn" download="weekly_briefing_${esc(b.week)}.html" href="${blob}">${ICON.down} Download the page</a></p>
  </article>`;
}

/* ---------- story: how we got here (timeline + chat about the project) ----------
   Locally the chat asks the AI, which answers only from our notes in docs/ (the brief, the step-by-step guide
   and the history). The online copy has no AI, so it
   matches the question to answers the AI wrote ahead of time (make_story_answers.py). */
const STOP = new Set("a an and are as at be but by can did do does for from how i in is it its of on or our so that the this to was we what when where which who why with you your".split(" "));
const SAME = { cheap: "cost", cheaper: "cost", expensive: "cost", price: "cost", token: "cost", money: "cost", save: "cost",
  begin: "start", began: "start", first: "start", history: "timeline", progress: "timeline", journey: "timeline", steps: "step", brief: "task", job: "task", assignment: "task",
  wrong: "problem", mistake: "problem", fail: "problem", learn: "lesson", learned: "lesson", missing: "done", left: "done", todo: "done",
  safe: "guardrail", safety: "guardrail", rules: "guardrail", accurate: "right", correct: "right", trust: "right", design: "cassette", look: "cassette" };
const words = (t) => String(t).toLowerCase().replace(/[^a-z0-9 ]/g, " ").split(/\s+/).filter((w) => w && !STOP.has(w))
  .map((w) => SAME[w] || w.replace(/(ing|ed|es|s)$/, "")).map((w) => SAME[w] || w);
function closest(q, prepared) {
  const qa = new Set(words(q));
  let best = null, score = 0;
  for (const p of prepared) {
    const pa = new Set(words(p.q));
    const hit = [...qa].filter((w) => pa.has(w)).length;
    const sc = hit / Math.sqrt(Math.max(1, qa.size) * Math.max(1, pa.size));
    if (sc > score) { score = sc; best = p; }
  }
  return score >= 0.3 ? best : null;
}
const SITE = "https://victorsaly.github.io/business-analyst-agent-demo/";   // the public website: blog, API, pitch, deck
// Where the other services are: next to the demo online; served by this app locally (blog, API reference, presentation).
const LINKS = STATIC
  ? { blog: "../blog/", api: "../api/", pitch: "../pitch/", deck: "../deck/", start: "../" }
  : { blog: "/blog/", api: "/redoc", pitch: "/pitch/", deck: "/deck/", start: "/" };
LINKS.code = "https://github.com/victorsaly/business-analyst-agent-demo";
const BLOG = {   // the blog's page titles (docs/<name>.md), for "Read more in the blog" links
  index: "How this was made", history: "Timeline, step by step", requirements: "Every requirement, with evidence",
  "build-guide": "The 13 build steps", "getting-started": "Run it on your laptop", "running-the-app": "Running the demo",
  product: "Who it's for", design: "How it looks", "prompt-optimization": "Cutting the AI cost", "audio-sources": "Audio sources" };
const loadJSON = (path, empty) => fetch(asset(path)).then((r) => r.ok ? r.json() : empty).catch(() => empty);

/* The Ask chat: one floating panel on every screen ("Ask", bottom right), so the conversation follows you around.
   Locally it asks this app's server, online the Cloudflare Worker; both answer only from the course material and
   our notes, stream the answer as it's written, and number their sources. Suggested questions have prepared answers. */
const CHAT = { prepared: [], history: [], ready: null, open: false };
const RESOURCES = [   // extra reading, picked from the question's words
  [/\bapi\b|endpoint|redoc|openapi|stream|sse|json|request/i, () => ["API reference", LINKS.api]],
  [/present|slide|deck/i, () => ["The presentation", LINKS.deck]],
  [/pitch|video/i, () => ["The pitch video", LINKS.pitch]],
  [/install|set ?up|laptop|windows|\bmac\b|run (it|the app)|start the app/i, () => ["Run it on your laptop", `${LINKS.blog}getting-started.html`]],
  [/requirement|brief|scorecard|\bmet\b/i, () => ["Every requirement, with evidence", `${LINKS.blog}requirements.html`]],
  [/\bsteps?\b|guide|how do i/i, () => ["The 13 build steps", `${LINKS.blog}build-guide.html`]],
  [/cost|token|cheap|groq|rate limit/i, () => ["Cutting the AI cost", `${LINKS.blog}prompt-optimization.html`]],
  [/design|look|cassette|font|colou?r/i, () => ["How it looks", `${LINKS.blog}design.html`]],
  [/code|before|after|changed|diff/i, () => ["Before and after, in code", `${LINKS.blog}#before-and-after-in-code`]],
];
function resourcesFor(question, sources = []) {
  const out = new Map();
  for (const x of sources) {            // the blog pages and code files behind the answer's sources
    const page = (x.url || "").match(/\/blog\/([\w-]+)\.html/)?.[1];
    if (page) out.set(`${LINKS.blog}${page}.html`, BLOG[page] || page);
    else if (/github\.com/.test(x.url || "")) out.set(x.url, `${x.source} (code)`);
  }
  for (const [re, link] of RESOURCES) if (re.test(question)) { const [label, url] = link(); out.set(url, label); }
  if (!out.size) out.set(LINKS.blog, "How this was made");
  return `<div class="resources"><span>Resources</span>${[...out].slice(0, 5).map(([url, label]) =>
    `<a href="${esc(url)}" target="_blank" rel="noopener">${esc(label)} <span aria-hidden="true">↗</span></a>`).join("")}</div>`;
}
const sourcesHTML = (sources) => (sources || []).length
  ? `<ol class="sources">${sources.map((x) => `<li value="${x.n}">${x.url ? `<a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.source)}</a>` : esc(x.source)} · ${esc(x.title)}</li>`).join("")}</ol>` : "";

async function streamChat(question, onDelta, onStatus, signal) {   // POST, then read the Server-Sent Events as they arrive
  const body = JSON.stringify({ question, history: CHAT.history, stream: true });
  const r = await fetch(STATIC ? ASK_URL : "/api/story/stream", { method: "POST", headers: { "Content-Type": "application/json" }, body, signal });
  if (!r.ok) { const d = await r.json().catch(() => ({})); return { error: d.error || `The chat service answered ${r.status}.` }; }
  const reader = r.body.getReader(), dec = new TextDecoder();
  let buf = "", done = null;
  for (;;) {
    const { done: end, value } = await reader.read();
    if (end) break;
    buf += dec.decode(value, { stream: true });
    const parts = buf.split("\n\n"); buf = parts.pop();
    for (const part of parts) {
      const line = part.split("\n").find((l) => l.startsWith("data: "));
      if (!line) continue;
      const ev = JSON.parse(line.slice(6));
      if (ev.type === "delta") onDelta(ev.text);
      else if (ev.type === "status") onStatus?.(ev);
      else if (ev.type === "done") done = ev;
      else if (ev.type === "error") return { error: ev.message };
    }
  }
  return done || { error: "The answer was cut off. Please try again." };
}

function chatSay(who, html, foot = "") {
  const log = document.getElementById("chatlog");
  log.insertAdjacentHTML("beforeend", `<div class="msg ${who}"><span class="who">${who === "me" ? "You" : "Guide"}</span><div class="body">${html}</div>${foot ? `<p class="foot">${foot}</p>` : ""}</div>`);
  log.scrollTop = log.scrollHeight;
  return log.lastElementChild;
}
const REDUCED = matchMedia("(prefers-reduced-motion: reduce)").matches;
const sleep = (ms) => new Promise((res) => setTimeout(res, ms));
const statusHTML = (text, extra = "") => `<div class="status"><span class="dots" aria-hidden="true"><i></i><i></i><i></i></span><span class="stage">${text}</span>${extra}</div>`;

function makeWriter(body, log) {   // shows the answer as it's written: pieces arrive in bursts, the text catches up smoothly
  let target = "", shown = 0, raf = 0, waiting = null;
  const tick = () => {
    raf = 0;
    const backlog = target.length - shown;
    if (backlog > 0) {
      shown = REDUCED ? target.length : Math.min(target.length, shown + Math.max(2, Math.ceil(backlog / 14)));
      const stick = log.scrollHeight - log.scrollTop - log.clientHeight < 90;   // don't yank the page if they scrolled up to read
      body.innerHTML = prose(target.slice(0, shown)) + '<span class="caret" aria-hidden="true"></span>';
      if (stick) log.scrollTop = log.scrollHeight;
    }
    if (shown < target.length) raf = requestAnimationFrame(tick);
    else if (waiting) { waiting(); waiting = null; }
  };
  return {
    set(text) { target = text; if (!raf) raf = requestAnimationFrame(tick); },
    drain: () => (shown >= target.length ? Promise.resolve() : new Promise((res) => { waiting = res; })),
    stop() { cancelAnimationFrame(raf); raf = 0; waiting?.(); waiting = null; },
  };
}
function chatBusy(on) {
  const form = document.getElementById("chatform");
  form.classList.toggle("busy", on); CHAT.busy = on;
  document.getElementById("chatlog").setAttribute("aria-busy", on);
}
function finishAnswer(msg, q, answer, sources, foot) {
  const body = msg.querySelector(".body"), log = document.getElementById("chatlog");
  body.innerHTML = prose(answer) + sourcesHTML(sources) + resourcesFor(q, sources);
  msg.insertAdjacentHTML("beforeend", `<p class="foot">${foot}</p>`);
  log.scrollTop = log.scrollHeight;
}
async function sayPrepared(q) {
  const hit = CHAT.prepared.find((x) => x.q.toLowerCase() === q.toLowerCase()) || closest(q, CHAT.prepared);
  if (!hit) return false;
  const msg = chatSay("ai", statusHTML("Found a prepared answer…")), log = document.getElementById("chatlog");
  chatBusy(true);
  await sleep(REDUCED ? 0 : 450);
  const writer = makeWriter(msg.querySelector(".body"), log);
  writer.set(hit.a); await writer.drain();
  chatBusy(false);
  finishAnswer(msg, q, hit.a, [], `Prepared answer, written by the AI from our notes${hit.q.toLowerCase() !== q.toLowerCase() ? ` · closest question: “${esc(hit.q)}”` : ""}`);
  return true;
}
async function askChat(q) {
  q = String(q || "").trim(); if (!q || CHAT.busy) return;
  openChat();
  chatSay("me", esc(q));
  if (CHAT.prepared.some((x) => x.q.toLowerCase() === q.toLowerCase())) { await sayPrepared(q); return; }   // prepared: no AI call, no cost
  const msg = chatSay("ai", statusHTML("Reading our notes…")), body = msg.querySelector(".body"), log = document.getElementById("chatlog");
  const writer = makeWriter(body, log), ctl = new AbortController();
  let text = "", started = false, stopped = false;
  const stage = (t, extra = "") => { if (!started) body.innerHTML = statusHTML(t, extra); };
  const timers = [setTimeout(() => stage("Searching the course material…"), 1500),
                  setTimeout(() => stage("Still working. The AI service can be slow, hang on…"), 7000)];
  CHAT.stop = () => { stopped = true; ctl.abort(); };
  chatBusy(true);
  const r = await streamChat(q, (piece) => {
    if (!started) { started = true; timers.forEach(clearTimeout); }
    text += piece; writer.set(text);
  }, (ev) => {
    if (ev.stage === "found") {
      timers.forEach(clearTimeout);
      const names = (ev.passages || []).map((p) => `<li>${esc(p.source)} · ${esc(p.title)}</li>`).join("");
      stage(ev.passages.length ? `Found ${ev.passages.length} passage${ev.passages.length === 1 ? "" : "s"} in the course material. Writing the answer…` : "Using our notes. Writing the answer…", names ? `<ul class="found">${names}</ul>` : "");
    }
  }, ctl.signal).catch((e) => ({ error: String(e) }));
  timers.forEach(clearTimeout);
  CHAT.stop = null;
  if (stopped) {   // they pressed Stop: keep what was written so far
    writer.stop(); chatBusy(false);
    if (text) { body.innerHTML = prose(text); msg.insertAdjacentHTML("beforeend", `<p class="foot">Stopped. Ask again for the full answer.</p>`); } else msg.remove();
    return;
  }
  if (r.error) {
    writer.stop(); chatBusy(false); msg.remove();
    if (!(await sayPrepared(q))) chatSay("ai", `<p>The AI isn't available right now (${esc(String(r.error).slice(0, 180))}). Try a suggested question.</p>` + resourcesFor(q));
    return;
  }
  await writer.drain();   // let the last words finish appearing before the final version replaces them
  chatBusy(false);
  CHAT.history.push({ role: "user", content: q }, { role: "assistant", content: r.answer });
  CHAT.history = CHAT.history.slice(-8);
  finishAnswer(msg, q, r.answer, r.sources, `Live answer from ${esc(r.model)}, using only the course material and our notes`);
}
function openChat() {
  const panel = document.getElementById("askpanel");
  if (!CHAT.open) {
    CHAT.open = true; panel.hidden = false;
    document.getElementById("askfab").setAttribute("aria-expanded", "true");
    document.body.classList.add("asking");
    setTimeout(() => document.getElementById("chatq")?.focus({ preventScroll: true }), 50);
  }
}
function closeChat() {
  CHAT.open = false;
  document.getElementById("askpanel").hidden = true;
  document.getElementById("askfab").setAttribute("aria-expanded", "false");
  document.body.classList.remove("asking");
  document.getElementById("askfab").focus({ preventScroll: true });
}
function suggestions(list) {   // question buttons that open the chat and ask
  return list.map((x) => `<button type="button" class="chip" data-ask="${esc(x.q)}">${esc(x.q)}</button>`).join("");
}
document.addEventListener("click", (e) => { const b = e.target.closest("[data-ask]"); if (b) askChat(b.dataset.ask); });
function setupChat() {
  document.body.insertAdjacentHTML("beforeend", `
  <button type="button" class="ask-fab" id="askfab" aria-expanded="false" aria-controls="askpanel" title="Ask about the project">
    <svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5h16v11H9l-5 4z"/><path d="M8 9.5h8M8 12.5h5"/></svg><span>Ask</span></button>
  <section class="ask-panel" id="askpanel" role="dialog" aria-labelledby="askh" hidden>
    <header><div><h2 id="askh">Ask about the project</h2><p>How we built it, the task and its steps, the course material</p></div>
      <button type="button" class="ask-x" id="askx" aria-label="Close the chat"><svg class="icon" viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18"/></svg></button></header>
    <div class="ask-log" id="chatlog" aria-live="polite"></div>
    <div class="chips ask-chips" id="chatchips"></div>
    <form class="chat-form" id="chatform"><input id="chatq" placeholder="Ask anything about the project…" autocomplete="off" aria-label="Your question"><button class="btn primary send" type="submit">${ICON.pen}<span class="sr">Ask</span></button><button class="btn stop" type="button" id="chatstop" title="Stop the answer"><span aria-hidden="true">■</span><span class="sr">Stop</span></button></form>
    <p class="ask-note">${STATIC ? "Live AI through a small server with a daily limit." : "Live AI from the service in .env."} It answers only from the course's training guide and starting notebook, our notebook and our notes, and numbers its sources.</p>
  </section>`);
  document.getElementById("askfab").onclick = () => (CHAT.open ? closeChat() : openChat());
  document.getElementById("askx").onclick = closeChat;
  document.getElementById("chatstop").onclick = () => CHAT.stop?.();
  document.getElementById("chatform").onsubmit = (e) => { e.preventDefault(); const i = document.getElementById("chatq"); const q = i.value; i.value = ""; askChat(q); };
  addEventListener("keydown", (e) => { if (e.key === "Escape" && CHAT.open && !ZOOMED && !EXPLAIN) closeChat(); });
  CHAT.ready = loadJSON("/static/story/answers.json", { answers: [] }).then((prep) => {
    CHAT.prepared = prep.answers || [];
    document.getElementById("chatchips").innerHTML = suggestions(CHAT.prepared.slice(0, 4));
    chatSay("ai", `<p>Hi! Ask me how this project was built, what the brief asks for, any of its steps, or what the course material says. I answer from our notes and point you to the blog, the API reference and the code.</p>`);
  });
}

/* ---------- home: every area of the project, and the chat about how it was built ---------- */
const AREAS = [
  ["tracks", "Tracks", "The live demo: the brief's questions on side A, the guardrails on side B. Each answer with its chart and the query behind it."],
  ["briefing", "Briefing", "The one-page weekly leadership briefing. The KPI table comes straight from SQL."],
  ["scorecard", "Scorecard", "Seven test questions marked against the database: 7 of 7 on the recordings."],
  ["tools", "Tools", "The agent's own read-only tools, by hand, with no AI. Try deleting the orders."],
  ["changes", "What changed", "From the course notebook to this agent: every line of the brief, the rulebook before and after."],
  ["story", "Story", "The timeline of the day, step by step, and the full course chat."],
  ["cover", "Cover", "The problem in one slide, how it works, and the house rules."],
];
const ELSEWHERE = [
  ["blog", "Blog: How this was made", "From the course's question to this agent, requirement by requirement, and every improvement."],
  ["api", "API reference", "Every endpoint behind these screens and the chat, with examples."],
  ["pitch", "Sales pitch", "The 60-second pitch video, with voiceover."],
  ["deck", "Presentation", "Twelve slides with speaker notes, or the PDF."],
];
async function renderHome() {
  view.innerHTML = `
  <div class="home">
    <section class="home-hero">
      <p class="course-badge"><img src="${asset("/static/logo.svg")}" alt="" width="40" height="40"> Course demonstration · Capstone 2 · Agentic AI Workshop 2026</p>
      <h1 class="page-title">Business Performance Analyst Agent</h1>
      <p class="page-lede">Ask the numbers a question in plain English, and get the answer, the chart and the query behind every number. Pick an area below, or ask the chat how we built it.</p>
    </section>
    <div class="home-grid">
      <section aria-labelledby="h-areas">
        <div class="rule-head"><h2 id="h-areas">In the app</h2><span class="total">${AREAS.length} screens</span></div>
        <div class="area-grid">${AREAS.map(([page, title, text], i) => `<a class="area" href="?page=${page}" data-page="${page}"><span class="n">${String(i + 1).padStart(2, "0")}</span><b>${title}</b><span class="d">${text}</span></a>`).join("")}</div>
        <div class="rule-head" style="margin-top:1.6rem"><h2>Read and watch</h2><span class="total">${STATIC ? "online" : "new tab"}</span></div>
        <div class="area-grid">${ELSEWHERE.map(([key, title, text]) => `<a class="area out" href="${LINKS[key]}" target="_blank" rel="noopener"><span class="n">↗</span><b>${title}</b><span class="d">${text}</span></a>`).join("")}</div>
      </section>
      <section class="ask-card" aria-labelledby="h-ask">
        <div class="rule-head"><h2 id="h-ask">Ask how we built it</h2></div>
        <p>A chat that knows the project: how it started, each step, what went wrong, what the course material says. Answers stream in, cite their sources, and link to the blog, the API reference and the code.</p>
        <p><button type="button" class="btn primary" id="homeask">${ICON.pen} Open the chat</button></p>
        <div class="chips" id="homechips"></div>
        <p class="blog-ref">The long version is the blog: <a href="${LINKS.blog}" target="_blank" rel="noopener">How this was made</a> ·
          <a href="${LINKS.blog}history.html" target="_blank" rel="noopener">the timeline</a> ·
          <a href="${LINKS.blog}requirements.html" target="_blank" rel="noopener">every requirement</a>.</p>
      </section>
    </div>
  </div>`;
  document.getElementById("homeask").onclick = openChat;
  await CHAT.ready;
  const chips = document.getElementById("homechips");
  if (!chips) return;   // left the screen meanwhile
  const about = /project|built|start|timeline|wrong|learn|cost|cheap|cassette|replay|real|not done|still|rewrite/i;   // "how we built it"
  chips.innerHTML = suggestions(CHAT.prepared.filter((x) => about.test(x.q)).slice(0, 6));
  sceneDone();
}

async function renderStory() {
  view.innerHTML = `
  <h1 class="page-title">How we got here</h1>
  <p class="page-lede">A course project, start to finish: Capstone 2 of the Agentic AI Workshop 2026, built on 1 October 2026, with final touches on 2 October. Follow the timeline, or ask the chat about the task, any of its steps, the course material, or how we built it. The full write-up, from the original notebook to this app: <a href="${LINKS.blog}">How this was made</a>.</p>
  <div class="story">
    <section><div class="rule-head"><h2>Timeline</h2><span class="total">1 Oct 2026</span></div><ol class="timeline" id="tl"></ol></section>
    <section class="ask-card"><div class="rule-head"><h2>Ask about the course, the task and its steps</h2></div>
      <p>The chat (bottom right, on every screen) answers from the brief, the build guide, the course's training guide and starting notebook, and our notes.</p>
      <p><button type="button" class="btn primary" id="storyask">${ICON.pen} Open the chat</button></p>
      <div class="chips" id="storychips"></div></section>
  </div>`;
  const [tl, prep] = await Promise.all([loadJSON("/static/story/timeline.json", { steps: [] }), loadJSON("/static/story/answers.json", { answers: [] })]);
  if (!document.getElementById("tl")) return;     // left the screen meanwhile
  document.getElementById("tl").innerHTML = tl.steps.map((st, i) => `<li><span class="when">${esc(st.time)}</span><span class="dot">${String(i + 1).padStart(2, "0")}</span><div><b>${esc(st.title)}</b><p>${esc(st.text)}</p></div></li>`).join("");
  document.getElementById("storyask").onclick = openChat;
  await CHAT.ready;
  if (document.getElementById("storychips")) document.getElementById("storychips").innerHTML = suggestions((prep.answers || []).slice(0, 8));
  sceneDone();
}

/* ---------- scorecard ---------- */
async function renderScorecard() {
  const P = new URLSearchParams(location.search);
  const key = await getJSON("/api/scorecard/key");
  view.innerHTML = `
  <h1 class="page-title">Scorecard</h1>
  <p class="page-lede">The brief's four questions plus three guardrail traps, marked against answers worked out from the database every time.</p>
  ${PRESENTER ? `<p class="margin-note"><b>Point out:</b> the exam is computed from the data, so it can't be gamed by typing answers in.</p>` : ""}
  <div class="controls"><button class="btn primary" id="mark" type="button">${ICON.pen} Mark the answers</button><span id="smode"></span></div>
  <div class="rule-head"><h2>Questions</h2><span class="total" id="stotal">${key.length} to mark</span></div>
  <div id="rows">${key.map((k) => `<div class="score-row" id="row-${k.qid}"><span class="id">${k.qid}</span><span class="q">${esc(k.question)}</span><span class="mark"></span><span class="needs">${esc(k.needs)}</span></div>`).join("")}</div>`;
  const mark = () => {
    sceneBusy();
    document.getElementById("smode").innerHTML = modeTag(MODE) + (MODE === "dry" ? `<p class="dry-note" style="margin:0.5rem 0 0">A dry-run score only proves the screens, tools and examiner work together. It says nothing about the AI.</p>` : "");
    let passed = 0, done = 0;
    counterStart(30);
    stream(`/api/scorecard?${new URLSearchParams({ mode: MODE })}`, {
      result: (ev) => {
        const r = ev.row; done += 1; if (r.passed) passed += 1;
        const row = document.getElementById(`row-${r.qid}`);
        row.querySelector(".mark").outerHTML = `<span class="mark ${r.passed ? "pass" : "fail"}">${r.passed ? ICON.tick + "Pass" : ICON.cross + "Fail"}</span>`;
        row.insertAdjacentHTML("beforeend", `<span class="why">${esc(r.reasons)}</span>`);
        document.getElementById("stotal").textContent = `${passed} of ${done} passed`;
      },
      done: () => { counterStop(); sceneDone(); },
      error: (ev) => { counterStop(); document.getElementById("rows").insertAdjacentHTML("beforebegin", `<div class="slip"><b>Stopped.</b> ${esc(ev.message)}</div>`); sceneDone(); },
    });
  };
  document.getElementById("mark").onclick = mark;
  if (P.get("autorun") === "1") mark(); else sceneDone();
}

function fmtDate(iso) {
  const d = new Date(iso + "T00:00:00");
  return isNaN(d) ? iso : d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

/* ---------------- presenter zoom ----------------
   Press Z to zoom into whatever the mouse is over (a chart, the answer, a query, a panel);
   press Z or Esc again to zoom out. window.__zoom(selector) does the same for the video recorder. */
let ZOOMED = false;
let POINTER = { x: innerWidth / 2, y: innerHeight / 2 };
const ZOOMABLE = "figure.chart, .notes li, .answer, .steps li, .sheet table, .score-row, .req, .list li, .panel, .two > div, .two > section, .tapelist, .playing h1, .playing, .cover h1, main";
addEventListener("pointermove", (e) => { POINTER = { x: e.clientX, y: e.clientY }; }, { passive: true });
function zoomTo(el) {
  if (!el) return;
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  view.style.transition = "none";           // measure the page un-zoomed, not mid-animation
  view.style.transform = "none";
  void view.offsetWidth;
  const vr = view.getBoundingClientRect(), r = el.getBoundingClientRect();
  void view.offsetWidth;
  view.style.transition = reduce ? "none" : "transform 520ms var(--ease)";
  const s = Math.max(1, Math.min(2.4, (0.86 * innerWidth) / r.width, (0.78 * (innerHeight - 80)) / r.height));
  const tx = innerWidth / 2 - (vr.left + (r.left - vr.left + r.width / 2) * s);
  const ty = 80 + (innerHeight - 80) / 2 - (vr.top + (r.top - vr.top + r.height / 2) * s);
  view.style.transformOrigin = "0 0";
  view.style.transform = `translate(${tx}px, ${ty}px) scale(${s})`;
  document.body.classList.add("zoomed");
  ZOOMED = true;
}
function zoomOut() {
  view.style.transform = "none";
  document.body.classList.remove("zoomed");
  ZOOMED = false;
}
window.__zoom = (selector) => {
  const el = typeof selector === "string" ? document.querySelector(selector) : selector;
  if (!el) return false;
  if (ZOOMED) zoomOut();
  el.scrollIntoView({ block: "center" });
  requestAnimationFrame(() => zoomTo(el));
  return true;
};
window.__zoomOut = zoomOut;
addEventListener("keydown", (e) => {
  if (e.target.closest("input, textarea, select") || e.metaKey || e.ctrlKey || e.altKey) return;
  if (e.key === "Escape" && ZOOMED) { zoomOut(); return; }
  if (e.key.toLowerCase() !== "z") return;
  if (ZOOMED) { zoomOut(); return; }
  const under = document.elementFromPoint(POINTER.x, POINTER.y);
  zoomTo(under && under.closest(ZOOMABLE));
});

/* ---------------- Explain this page: ElevenLabs narration with live captions ----------------
   Text: web/explain/scripts.json, one line per screen and audience. Audio: web/explain/<page>-<audience>.mp3.
   Word timings: web/explain/timings.json (make_explain_timings.py measures each clip's pauses), so the
   highlighted word keeps pace with the voice. With no mp3, the browser's own voice reads the text. */
let SCRIPTS = null;
let TIMINGS = null;
let EXPLAIN = null;
const PAGE_NAME = { home: "Home", cover: "Cover", changes: "What changed", tracks: "Tracks", tools: "Tools", briefing: "Briefing", scorecard: "Scorecard", story: "Story" };
function explainStop() {
  if (!EXPLAIN) return;
  EXPLAIN.audio?.pause();
  if (EXPLAIN.speech) speechSynthesis.cancel();
  cancelAnimationFrame(EXPLAIN.raf);
  EXPLAIN = null;
  document.getElementById("explainer").hidden = true;
  document.getElementById("explain").setAttribute("aria-pressed", "false");
}
async function explainPage() {
  if (EXPLAIN) { explainStop(); return; }
  const page = PAGE_NAME[currentPage()] ? currentPage() : "tracks";
  try { SCRIPTS = SCRIPTS || await (await fetch(asset("/static/explain/scripts.json"))).json(); } catch (e) { return; }
  try { TIMINGS = TIMINGS || await (await fetch(asset("/static/explain/timings.json"))).json(); } catch (e) { TIMINGS = {}; }
  const text = SCRIPTS[page]?.[AUD];
  if (!text) return;
  const tokens = text.split(/\s+/);
  const weight = tokens.map((w) => w.length + 1 + (/[,;]$/.test(w) ? 4 : /[.:?!]$/.test(w) ? 8 : 0));   // pauses after punctuation
  const ends = []; weight.reduce((a, w, i) => (ends[i] = a + w), 0);
  const total = ends[ends.length - 1];
  const starts = []; tokens.reduce((a, w, i) => { starts[i] = a; return a + w.length + 1; }, 0);   // char offsets, for the browser voice
  document.getElementById("ex-text").innerHTML = tokens.map((w, i) => `<span class="w" data-i="${i}">${esc(w)}</span>`).join(" ");
  document.getElementById("ex-who").textContent = `${PAGE_NAME[page]}, in plain English · for ${AUD === "developer" ? "developers" : "stakeholders"}`;
  document.getElementById("ex-time").textContent = "";
  document.getElementById("explainer").hidden = false;
  document.getElementById("explain").setAttribute("aria-pressed", "true");
  const spans = [...document.querySelectorAll("#ex-text .w")];
  const mark = (k, lit = true) => spans.forEach((sp, i) => { sp.classList.toggle("said", i < k); sp.classList.toggle("now", lit && i === k); });
  const toggle = document.getElementById("ex-toggle");
  toggle.classList.remove("paused");
  const me = (EXPLAIN = { audio: null, speech: false, raf: 0 });

  const speakInstead = () => {     // no mp3 (or it won't play): the browser's own voice
    if (EXPLAIN !== me || me.speech || !("speechSynthesis" in window)) return;
    me.audio = null; me.speech = true;
    const u = new SpeechSynthesisUtterance(text);
    u.rate = 1.02;
    u.onboundary = (e) => { let k = starts.findIndex((st, i) => e.charIndex < st + tokens[i].length + 1); mark(k < 0 ? spans.length - 1 : k); };
    u.onend = () => { if (EXPLAIN === me) { mark(spans.length); setTimeout(() => EXPLAIN === me && explainStop(), 1500); } };
    speechSynthesis.cancel(); speechSynthesis.speak(u);
    document.getElementById("ex-time").textContent = "browser voice";
  };
  const audio = new Audio(asset(`/static/explain/${page}-${AUD}.mp3`));
  me.audio = audio;
  const timed = TIMINGS[`${page}-${AUD}`];
  const useTimed = timed && timed.start.length === tokens.length;
  const tick = () => {
    if (EXPLAIN !== me || !me.audio) return;
    const d = audio.duration || 0, t = audio.currentTime;
    if (d) {
      if (t >= d - 0.05) mark(spans.length);
      else if (useTimed) {      // measured: light the word being said; in a pause, light nothing
        const n = timed.start.filter((st) => st <= t).length;          // words started so far
        const k = Math.max(0, n - 1);
        mark(t > timed.end[k] + 0.05 ? k + 1 : k, t <= timed.end[k] + 0.05);
      } else {                  // no timings: share the clip by word length
        const lead = 0.15, tail = 0.35;
        const f = Math.min(1, Math.max(0, (t - lead) / Math.max(0.5, d - lead - tail)));
        mark(Math.max(0, ends.findIndex((e) => e >= f * total)));
      }
      document.getElementById("ex-time").textContent = `${mmss(t)} / ${mmss(d)}`;
    }
    me.raf = requestAnimationFrame(tick);
  };
  audio.addEventListener("error", speakInstead);
  audio.addEventListener("ended", () => { if (EXPLAIN === me) { mark(spans.length); setTimeout(() => EXPLAIN === me && explainStop(), 1500); } });
  audio.play().then(() => { me.raf = requestAnimationFrame(tick); }).catch(speakInstead);
}
document.getElementById("explain").onclick = explainPage;
document.getElementById("ex-close").onclick = explainStop;
document.getElementById("ex-toggle").onclick = (e) => {
  if (!EXPLAIN) return;
  const btn = e.currentTarget;
  if (EXPLAIN.speech) { speechSynthesis.paused ? speechSynthesis.resume() : speechSynthesis.pause(); btn.classList.toggle("paused", speechSynthesis.paused); }
  else if (EXPLAIN.audio) { EXPLAIN.audio.paused ? EXPLAIN.audio.play() : EXPLAIN.audio.pause(); btn.classList.toggle("paused", EXPLAIN.audio.paused); }
  btn.setAttribute("aria-label", btn.classList.contains("paused") ? "Play" : "Pause");
};
addEventListener("keydown", (e) => { if (e.key === "Escape" && EXPLAIN && !ZOOMED) explainStop(); });

/* ---------------- menu ----------------
   Demo, Blog, Present, More: each opens a list. Click (or tap) to open, click outside or Escape to close;
   on a computer with a mouse they also open on hover (app.css). */
function menuClose(except) {
  document.querySelectorAll(".masthead .menu.open").forEach((m) => {
    if (m === except) return;
    m.classList.remove("open");
    m.querySelector(".menu-btn").setAttribute("aria-expanded", "false");
    if (m._sub) { m.appendChild(m._sub); m._sub = null; }
  });
}
document.querySelectorAll(".masthead .menu-btn").forEach((btn) => btn.addEventListener("click", () => {
  const m = btn.closest(".menu"), open = !m.classList.contains("open");
  menuClose(m);
  m.classList.toggle("open", open);
  btn.setAttribute("aria-expanded", String(open));
  if (open && matchMedia("(max-width: 700px)").matches) {
    // On a phone the list is pinned under the nav bar. iOS Safari clips a fixed list inside the nav's sideways
    // scroller, so while open it lives on <body> (app.css: body > .sub) and goes back home on close.
    const sub = m.querySelector(".sub"), r = btn.closest("nav").getBoundingClientRect();
    sub.style.setProperty("--nav-bottom", `${r.bottom}px`);
    document.body.appendChild(sub);
    m._sub = sub;
  }
}));
document.addEventListener("click", (e) => { if (!e.target.closest(".masthead .menu, body > .sub")) menuClose(); });
addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  const m = document.querySelector(".masthead .menu.open");
  if (m) { menuClose(); m.querySelector(".menu-btn").focus(); }
});
document.querySelectorAll(".masthead [data-link]").forEach((a) => (a.href = LINKS[a.dataset.link] + (a.dataset.path || "")));

/* ---------------- boot ---------------- */
document.addEventListener("click", (e) => {
  const a = e.target.closest("a[data-page], a[data-nav], a[data-ask]");
  if (!a || e.metaKey || e.ctrlKey) return;
  e.preventDefault();
  const p = new URLSearchParams(a.getAttribute("href").slice(1));
  setURL({ page: p.get("page"), case: null, ask: p.get("ask") });
  render();
  view.focus({ preventScroll: true });
  window.scrollTo(0, 0);
});
window.addEventListener("popstate", render);
document.querySelectorAll("[data-mode]").forEach((b) => b.onclick = () => setMode(b.dataset.mode));
document.querySelectorAll("[data-aud]").forEach((b) => b.onclick = () => setAud(b.dataset.aud));
setAud(defaultAud());

(async () => {
  document.querySelectorAll("a[data-blog]").forEach((a) => (a.href = LINKS.blog));
  setupChat();
  META = await getJSON("/api/meta");
  if (!META.ai_ready) document.querySelector('[data-mode="live"]').title = "No AI key: put GROQ_API_KEY in app/.env";
  if (STATIC) {
    document.querySelectorAll('[data-mode="live"], [data-mode="dry"]').forEach((b) => { b.disabled = true; b.title = LOCAL_ONLY; });
    document.getElementById("explain").insertAdjacentHTML("beforebegin", `<span class="tag online-tag" title="${esc(LOCAL_ONLY)}">Online replay · Live AI runs locally</span>`);
  }
  MODE = defaultMode();
  document.querySelectorAll("[data-mode]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.mode === MODE)));
  render();
})();
