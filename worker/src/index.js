// The online Ask chat: a Cloudflare Worker between the demo site and OpenAI.
// It holds the API key (a Worker secret, never in the site), finds the knowledge-base passages that best
// match each question (BM25, the same way app/analyst/knowledge.py does), and asks the AI to answer from
// them only. It answers only the demo site, keeps answers short, and caps questions per day and per visitor.
// knowledge.json is built by app/scripts/make_knowledge.py (git-ignored: it holds course material).
import KB from "../knowledge.json";

const ALLOWED = ["https://victorsaly.github.io", "http://localhost:8501", "http://127.0.0.1:8501"];
const STOP = new Set(KB.stop);
const words = (t) => (String(t).toLowerCase().match(/[a-z0-9_]+/g) || []).filter((w) => w.length > 1 && !STOP.has(w));

// ---- the search index, built once per Worker instance
const K1 = 1.4, B = 0.75;
const DOCS = KB.passages.map((p) => {
  const counts = new Map();
  const add = (ws, n = 1) => ws.forEach((w) => counts.set(w, (counts.get(w) || 0) + n));
  add(words(p.text)); add(words(p.title), 2); add(words(`${p.source} ${KB.aliases[p.source] || ""}`));
  let len = 0; counts.forEach((c) => (len += c));
  return { counts, len };
});
const AVG = DOCS.reduce((a, d) => a + d.len, 0) / Math.max(1, DOCS.length);
const DF = new Map();
DOCS.forEach((d) => d.counts.forEach((_, w) => DF.set(w, (DF.get(w) || 0) + 1)));
const IDF = new Map([...DF].map(([w, f]) => [w, Math.log(1 + (DOCS.length - f + 0.5) / (f + 0.5))]));

function search(question, k) {
  const q = [...new Set(words(question))];
  const scored = [];
  DOCS.forEach((d, i) => {
    let s = 0;
    for (const w of q) {
      const tf = d.counts.get(w);
      if (tf) s += IDF.get(w) * tf * (K1 + 1) / (tf + K1 * (1 - B + B * d.len / AVG));
    }
    if (s > 0 && !KB.skip_sources.includes(KB.passages[i].source)) scored.push([s, i]);
  });
  scored.sort((a, b) => b[0] - a[0]);
  const out = []; let total = 0;
  for (const [, i] of scored) {
    const p = KB.passages[i];
    if (total + p.text.length > KB.max_chars) continue;
    out.push(p); total += p.text.length;
    if (out.length >= k) break;
  }
  return out;
}

const json = (obj, status, headers) => new Response(JSON.stringify(obj), { status, headers: { ...headers, "Content-Type": "application/json" } });

async function hash(text) {   // visitors are counted by a hash of their IP address, never the address itself
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].slice(0, 8).map((b) => b.toString(16).padStart(2, "0")).join("");
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    const cors = { "Access-Control-Allow-Origin": ALLOWED.includes(origin) ? origin : ALLOWED[0],
                   "Access-Control-Allow-Methods": "POST, OPTIONS", "Access-Control-Allow-Headers": "Content-Type", Vary: "Origin" };
    const url = new URL(request.url);
    if (request.method === "OPTIONS") return new Response(null, { headers: cors });
    if (request.method === "GET" && url.pathname === "/health") return json({ ok: true, passages: KB.passages.length, model: env.MODEL }, 200, cors);
    if (request.method !== "POST" || url.pathname !== "/ask") return json({ error: "Not found." }, 404, cors);
    if (!ALLOWED.includes(origin)) return json({ error: "This chat only answers questions from the demo site." }, 403, cors);

    let body;
    try { body = await request.json(); } catch { return json({ error: "Send JSON: {question, history}." }, 400, cors); }
    const question = String(body.question || "").trim().slice(0, 500);
    if (!question) return json({ error: "Ask a question about the course or the project." }, 400, cors);
    const history = (Array.isArray(body.history) ? body.history : []).slice(-4)
      .filter((m) => m && (m.role === "user" || m.role === "assistant"))
      .map((m) => ({ role: m.role, content: String(m.content || "").slice(0, 1500) }));

    // daily caps: for everyone, and per visitor
    const day = new Date().toISOString().slice(0, 10);
    const who = await hash(request.headers.get("CF-Connecting-IP") || "unknown");
    const [total, mine] = await Promise.all([env.LIMITS.get(`day:${day}`), env.LIMITS.get(`v:${day}:${who}`)]);
    if (+(total || 0) >= +env.DAILY_LIMIT) return json({ error: "The chat has reached its question limit for today. Please try again tomorrow, or run the app locally." }, 429, cors);
    if (+(mine || 0) >= +env.PER_VISITOR_LIMIT) return json({ error: `You've asked ${env.PER_VISITOR_LIMIT} questions today, the limit per visitor. Please come back tomorrow.` }, 429, cors);
    await Promise.all([env.LIMITS.put(`day:${day}`, String(+(total || 0) + 1), { expirationTtl: 172800 }),
                       env.LIMITS.put(`v:${day}:${who}`, String(+(mine || 0) + 1), { expirationTtl: 172800 })]);

    const asked = [...history.filter((m) => m.role === "user").map((m) => m.content), question].join(" ");
    const found = search(asked, KB.course_passages + 2);
    const passages = found.map((p, i) => `[${i + 1}] (${p.source} · ${p.title})\n${p.text}`).join("\n\n") || "(none matched)";
    const messages = [{ role: "system", content: KB.prompt.replace(KB.marker, passages) }, ...history, { role: "user", content: question }];

    const stream = body.stream === true;
    const r = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${env.OPENAI_API_KEY}` },
      body: JSON.stringify({ model: env.MODEL, messages, max_completion_tokens: 900, stream }),
    });
    if (!r.ok) return json({ error: `The AI service didn't answer (${r.status}). Please try again in a minute.` }, 502, cors);
    const finish = (text) => {
      const answer = text.replace(/^#+\s*/gm, "").trim() || "The course material and our notes don't cover that.";
      const nums = [...new Set((answer.match(/\[(\d+)\]/g) || []).map((m) => +m.slice(1, -1)))].filter((n) => n > 0 && n <= found.length).sort((a, b) => a - b);
      const sources = nums.map((n) => ({ n, source: found[n - 1].source, title: found[n - 1].title, url: found[n - 1].url || "" }));
      return { answer, sources, model: `openai · ${env.MODEL}` };
    };
    if (!stream) {
      const data = await r.json();
      return json(finish(data.choices?.[0]?.message?.content || ""), 200, cors);
    }
    // Streaming: OpenAI's chunks become {"type":"delta","text"} events, then one {"type":"done", answer, sources, model}.
    const enc = new TextEncoder(), dec = new TextDecoder();
    const { readable, writable } = new TransformStream();
    const out = writable.getWriter();
    const send = (ev) => out.write(enc.encode(`data: ${JSON.stringify(ev)}\n\n`));
    (async () => {
      let text = "", buf = "";
      try {
        const reader = r.body.getReader();
        for (;;) {
          const { done, value } = await reader.read();
          if (done) break;
          buf += dec.decode(value, { stream: true });
          const lines = buf.split("\n"); buf = lines.pop();
          for (const line of lines) {
            if (!line.startsWith("data: ") || line === "data: [DONE]") continue;
            const piece = JSON.parse(line.slice(6)).choices?.[0]?.delta?.content || "";
            if (piece) { text += piece; await send({ type: "delta", text: piece }); }
          }
        }
        await send({ type: "done", ...finish(text) });
      } catch (e) {
        await send({ type: "error", message: "The answer was cut off. Please try again." });
      } finally {
        await out.close();
      }
    })();
    return new Response(readable, { headers: { ...cors, "Content-Type": "text/event-stream", "Cache-Control": "no-cache" } });
  },
};
