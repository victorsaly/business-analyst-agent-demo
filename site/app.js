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
function currentPage() { return new URLSearchParams(location.search).get("page") || "tracks"; }

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
  document.querySelectorAll(".masthead nav a").forEach((a) => { if (a.dataset.page === page) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current"); });
  ({ cover: renderCover, changes: renderChanges, tracks: () => renderTracks(true), tools: renderTools, briefing: renderBriefing, scorecard: renderScorecard, story: renderStory }[page] || (() => renderTracks(true)))();
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
  const bonus = META.tracks.find((t) => t.side === "bonus");
  const listHTML = `
    <div class="sides" role="group" aria-label="Tape side">
      <button type="button" data-side="A" aria-pressed="${SIDE === "A"}">Side A</button>
      <button type="button" data-side="B" aria-pressed="${SIDE === "B"}">Side B</button>
    </div>
    <div class="side-face" id="face">
      <div class="rule-head"><h2>Side ${SIDE}</h2><span class="total">${mmss(sideTotal(SIDE))}</span></div>
      ${trackRows(SIDE)}
      ${SIDE === "B" && bonus ? `<div class="hidden-track"><div class="gap">· · · hidden track · · ·</div>${trackRow(bonus, "+")}</div>` : ""}
    </div>
    <div class="budget"><span>Both sides</span><span>${mmss(sideTotal("A") + sideTotal("B"))} of 6:00</span></div>
    <div class="ask">
      <form id="askform"><input id="askq" placeholder="${STATIC ? "Your own questions: local app only" : "Write your own question…"}" aria-label="Your own question" autocomplete="off" ${STATIC ? "disabled" : ""}><button class="btn primary" type="submit" ${STATIC ? "disabled" : ""}>${ICON.pen} Ask</button></form>
      <div class="memory">${META.history.length ? `Follow-ups remember: ${META.history.map((h) => `“${esc(h)}”`).join(", then ")}` : "Follow-up questions remember the last two answers."} <button type="button" class="linkish" id="newchat">New conversation</button></div>
    </div>`;
  const existing = document.getElementById("tapelist");
  if (existing && !fresh) { existing.innerHTML = listHTML; bindTracklist(); return; }
  view.innerHTML = `<div class="deck"><div class="tapelist" id="tapelist">${listHTML}</div><section class="playing" id="playing" aria-live="polite"></section></div>`;
  bindTracklist();
  const playing = document.getElementById("playing");
  if (fresh && caseId && P.get("autorun") === "1") { playTrack(caseId); return; }
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
  runQuestion({ caseId: id, question: t.question, budget: t.budget, point: t.point, planted: t.db === "planted", title: t.title, side: t.side });
}
function playQuestion(q) {
  CURRENT = null;
  renderTracks(false);
  runQuestion({ question: q, budget: 0 });
}

function runQuestion({ caseId, question, budget, point, planted, side }) {
  sceneBusy();
  const playing = document.getElementById("playing");
  const where = side === "bonus" ? "Hidden track" : side ? `Side ${side}` : "Your question";
  playing.innerHTML = `
    ${PRESENTER && point ? `<p class="margin-note"><b>Point out:</b> ${esc(point)}</p>` : ""}
    <h1>${esc(question)}</h1><div class="rule3"></div>
    <div class="meta">${modeTag(MODE)}${planted ? ' <span class="tag red">Rehearsal data: planted anomaly</span>' : ""}<span>${where}${budget ? ` · budget ${mmss(budget)}` : ""}</span></div>
    ${MODE === "dry" ? DRY_NOTE : ""}
    ${EXPECT[MODE] ? `<p class="expect">${EXPECT[MODE]}</p>` : ""}
    <ol class="steps" id="steps">${writingLine("Reading the question…")}</ol>
    <div id="result"></div>`;
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
        <div class="field"><label for="am">Metric</label><select id="am">${opt(["revenue", "margin", "margin_pct", "units", "orders", "avg_discount_pct"], "revenue")}</select></div>
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
  </div>`;
  const scan = async () => {
    const q = new URLSearchParams({ metric: am.value, by: ab.value, grain: ag.value, period: ap.value });
    const r = await getJSON(`/api/anomalies?${q}`);
    if (r.error) { anout.innerHTML = `<div class="slip"><b>Can't scan.</b> ${esc(r.error)}</div>`; return; }
    const maxz = Math.max(1, ...r.runs.map((x) => Math.abs(x.z)));
    const fmt = (v) => /pct/.test(r.metric) ? `${Number(v).toFixed(1)}%` : /revenue|margin/.test(r.metric) ? `$${Math.round(v).toLocaleString()}` : Math.round(v).toLocaleString();
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
  Promise.all([scan(), runSQL(document.getElementById("sq").value)]).then(sceneDone);
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
   Locally the chat asks the AI, which answers only from docs/history.md. The online copy has no AI, so it
   matches the question to answers the AI wrote ahead of time (make_story_answers.py). */
const STOP = new Set("a an and are as at be but by can did do does for from how i in is it its of on or our so that the this to was we what when where which who why with you your".split(" "));
const SAME = { cheap: "cost", cheaper: "cost", expensive: "cost", price: "cost", token: "cost", money: "cost", save: "cost",
  begin: "start", began: "start", first: "start", history: "timeline", steps: "timeline", progress: "timeline", journey: "timeline",
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
async function renderStory() {
  view.innerHTML = `
  <h1 class="page-title">How we got here</h1>
  <p class="page-lede">A course project, start to finish: Capstone 2 of the Agentic AI Workshop 2026, built on 1 October 2026. Follow the timeline, or ask the chat about any step.</p>
  <div class="story">
    <section><div class="rule-head"><h2>Timeline</h2><span class="total">1 Oct 2026</span></div><ol class="timeline" id="tl"></ol></section>
    <section class="chat"><div class="rule-head"><h2>Ask about the project</h2></div>
      <div class="chat-log" id="chatlog" aria-live="polite"></div>
      <div class="chips" id="chips"></div>
      <form id="chatform" class="chat-form"><input id="chatq" placeholder="Ask how we built it…" autocomplete="off" aria-label="Your question about the project"><button class="btn primary" type="submit">${ICON.pen} Ask</button></form>
      <p class="note" id="chatnote"></p>
    </section>
  </div>`;
  const load = (path, empty) => fetch(asset(path)).then((r) => r.ok ? r.json() : empty).catch(() => empty);
  const [tl, prep] = await Promise.all([load("/static/story/timeline.json", { steps: [] }), load("/static/story/answers.json", { answers: [] })]);
  if (!document.getElementById("tl")) return;     // left the screen meanwhile
  document.getElementById("tl").innerHTML = tl.steps.map((st, i) => `<li><span class="when">${esc(st.time)}</span><span class="dot">${String(i + 1).padStart(2, "0")}</span><div><b>${esc(st.title)}</b><p>${esc(st.text)}</p></div></li>`).join("");
  const prepared = prep.answers || [];
  const log = document.getElementById("chatlog");
  const history = [];
  const say = (who, html, foot = "") => { log.insertAdjacentHTML("beforeend", `<div class="msg ${who}"><span class="who">${who === "me" ? "You" : "Story"}</span><div class="body">${html}</div>${foot ? `<p class="foot">${foot}</p>` : ""}</div>`); log.scrollTop = log.scrollHeight; };
  const chips = (list) => { document.getElementById("chips").innerHTML = list.map((p) => `<button type="button" class="chip">${esc(p.q)}</button>`).join(""); };
  const fromPrepared = (q) => {
    const hit = prepared.find((p) => p.q.toLowerCase() === q.toLowerCase()) || closest(q, prepared);
    if (hit) { say("ai", prose(hit.a), `Prepared answer, written by the AI from our project notes${hit.q.toLowerCase() !== q.toLowerCase() ? ` · closest question: “${esc(hit.q)}”` : ""}`); return true; }
    return false;
  };
  const ask = async (q) => {
    q = q.trim(); if (!q) return;
    say("me", esc(q));
    if (prepared.some((p) => p.q.toLowerCase() === q.toLowerCase()) || STATIC) {   // prepared questions answer at once, at no cost
      if (!fromPrepared(q)) say("ai", `<p>That one isn't in the prepared answers for the online copy. Try a question below, or run the local app (<code>./demo.sh app</code>) to ask anything.</p>`);
      return;
    }
    log.insertAdjacentHTML("beforeend", `<div class="msg ai pending" id="pending"><span class="who">Story</span><div class="body"><p>Reading our notes…</p></div></div>`);
    const r = await getJSON("/api/story", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: q, history }) }).catch((e) => ({ error: String(e) }));
    document.getElementById("pending")?.remove();
    if (r.error) { if (!fromPrepared(q)) say("ai", `<p>The AI isn't available right now (${esc(r.error.slice(0, 160))}).</p>`); return; }
    history.push({ role: "user", content: q }, { role: "assistant", content: r.answer });
    say("ai", prose(r.answer), `Live answer from ${esc(r.model)}, using only our project notes`);
  };
  chips(prepared.slice(0, 8));
  document.getElementById("chips").onclick = (e) => { const b = e.target.closest(".chip"); if (b) ask(b.textContent); };
  document.getElementById("chatform").onsubmit = (e) => { e.preventDefault(); const i = document.getElementById("chatq"); ask(i.value); i.value = ""; };
  document.getElementById("chatnote").textContent = STATIC
    ? "Online copy: the AI wrote these answers ahead of time from our project notes. The local app answers any question live."
    : "Answers come from the AI service in .env, using only our project notes (docs/history.md).";
  say("ai", `<p>Hi! I can tell you how this course project was built: where it started, each step, what went wrong and what we learned. Pick a question or type your own.</p>`);
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
const PAGE_NAME = { cover: "Cover", changes: "What changed", tracks: "Tracks", tools: "Tools", briefing: "Briefing", scorecard: "Scorecard", story: "Story" };
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

/* ---------------- boot ---------------- */
document.addEventListener("click", (e) => {
  const a = e.target.closest("a[data-page], a[data-nav]");
  if (!a || e.metaKey || e.ctrlKey) return;
  e.preventDefault();
  const p = new URLSearchParams(a.getAttribute("href").slice(1));
  setURL({ page: p.get("page"), case: null });
  render();
  view.focus({ preventScroll: true });
  window.scrollTo(0, 0);
});
window.addEventListener("popstate", render);
document.querySelectorAll("[data-mode]").forEach((b) => b.onclick = () => setMode(b.dataset.mode));
document.querySelectorAll("[data-aud]").forEach((b) => b.onclick = () => setAud(b.dataset.aud));
setAud(defaultAud());

(async () => {
  META = await getJSON("/api/meta");
  document.getElementById("spine-dates").textContent = `${META.data_from.slice(2, 4)}–${META.data_to.slice(2, 4)}`;
  if (!META.ai_ready) document.querySelector('[data-mode="live"]').title = "No AI key: put GROQ_API_KEY in app/.env";
  if (STATIC) {
    document.querySelectorAll('[data-mode="live"], [data-mode="dry"]').forEach((b) => { b.disabled = true; b.title = LOCAL_ONLY; });
    document.getElementById("explain").insertAdjacentHTML("beforebegin", `<span class="tag online-tag" title="${esc(LOCAL_ONLY)}">Online replay · Live AI runs locally</span>`);
  }
  MODE = defaultMode();
  document.querySelectorAll("[data-mode]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.mode === MODE)));
  render();
})();
