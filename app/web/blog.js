/* The blog's small helpers: the search box, copy buttons on code, the "On this page" highlight, the mobile page list.
   The search index is blog/search.json (blog.search_index()): one entry per section, loaded the first time it's needed. */
(() => {
  const input = document.getElementById("q");
  const box = document.getElementById("hits");
  let index = null, loading = null, hits = [], active = -1;

  const esc = (s) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const terms = (q) => q.toLowerCase().split(/\s+/).filter((t) => t.length > 1 || /\d/.test(t));

  function load() {
    loading = loading || fetch("search.json").then((r) => r.json()).then((d) => {
      index = d.map((e) => ({ ...e, hl: e.h.toLowerCase(), tl: e.t.toLowerCase(), xl: e.x.toLowerCase() }));
    }).catch(() => { index = []; });
    return loading;
  }

  // Every word must appear somewhere in the section; words in the heading count most, then the page title, then the text.
  function search(q) {
    const ts = terms(q), phrase = q.trim().toLowerCase();
    if (!ts.length) return [];
    const out = [];
    for (const e of index) {
      let score = 0;
      for (const t of ts) {
        const inH = e.hl.includes(t), inT = e.tl.includes(t), inX = e.xl.includes(t);
        if (!inH && !inT && !inX) { score = 0; break; }
        score += (inH ? 10 : 0) + (inT ? 3 : 0) + (inX ? 1 + Math.min(e.xl.split(t).length - 2, 4) : 0);
      }
      if (score && ts.length > 1 && (e.hl.includes(phrase) || e.xl.includes(phrase))) score += 8;
      if (score) out.push({ e, score });
    }
    return out.sort((a, b) => b.score - a.score).slice(0, 8).map((h) => h.e);
  }

  // A short piece of the text around the first word found, with the words marked.
  function snippet(e, ts) {
    const at = Math.max(0, Math.min(...ts.map((t) => e.xl.indexOf(t)).filter((i) => i >= 0), Infinity) - 50);
    let s = e.x.slice(at === Infinity ? 0 : at, (at === Infinity ? 0 : at) + 150);
    if (at > 0 && at !== Infinity) s = "…" + s;
    s = esc(s);
    for (const t of ts) s = s.replace(new RegExp(t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi"), (m) => `<mark>${m}</mark>`);
    return s;
  }

  function show(q) {
    const ts = terms(q);
    hits = index ? search(q) : [];
    active = hits.length ? 0 : -1;
    if (!q.trim()) { close(); return; }
    box.innerHTML = hits.length
      ? hits.map((e, i) => `<a role="option" id="hit${i}" href="${e.p}.html${e.id ? "#" + e.id : ""}"${i === active ? ' aria-selected="true"' : ""}>`
          + `<span class="where">${esc(e.t)}</span><span class="what">${esc(e.h)}</span><span class="text">${snippet(e, ts)}</span></a>`).join("")
      : `<p class="none">No matches for “${esc(q.trim())}”. Try fewer or shorter words.</p>`;
    box.hidden = false;
    input.setAttribute("aria-expanded", "true");
    input.setAttribute("aria-activedescendant", active >= 0 ? "hit0" : "");
  }

  function move(step) {
    if (!hits.length) return;
    box.querySelector(`#hit${active}`)?.removeAttribute("aria-selected");
    active = (active + step + hits.length) % hits.length;
    const el = box.querySelector(`#hit${active}`);
    el.setAttribute("aria-selected", "true");
    el.scrollIntoView({ block: "nearest" });
    input.setAttribute("aria-activedescendant", el.id);
  }

  function close() {
    box.hidden = true;
    input.setAttribute("aria-expanded", "false");
    input.removeAttribute("aria-activedescendant");
  }

  if (input) {
    input.addEventListener("focus", load);
    input.addEventListener("input", () => load().then(() => show(input.value)));
    input.addEventListener("keydown", (ev) => {
      if (ev.key === "ArrowDown") { ev.preventDefault(); move(1); }
      else if (ev.key === "ArrowUp") { ev.preventDefault(); move(-1); }
      else if (ev.key === "Enter" && active >= 0) { ev.preventDefault(); box.querySelector(`#hit${active}`).click(); close(); }
      else if (ev.key === "Escape") { if (box.hidden) input.blur(); else close(); }
    });
    box.addEventListener("click", (ev) => { if (ev.target.closest("a")) close(); });
    document.addEventListener("click", (ev) => { if (!ev.target.closest(".search")) close(); });
    // "/" or Ctrl+K / Cmd+K jumps to the search box from anywhere on the page.
    document.addEventListener("keydown", (ev) => {
      const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName);
      if ((ev.key === "/" && !typing) || (ev.key.toLowerCase() === "k" && (ev.metaKey || ev.ctrlKey))) {
        ev.preventDefault();
        input.focus();
        input.select();
      }
    });
  }

  // A "Copy" button on every code block, so commands can be pasted into Terminal or PowerShell without retyping.
  for (const pre of document.querySelectorAll("main pre:not(.mermaid)")) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "copy";
    btn.textContent = "Copy";
    btn.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(pre.querySelector("code")?.innerText ?? pre.innerText);
        btn.textContent = "Copied";
      } catch { btn.textContent = "Select and copy"; }
      setTimeout(() => { btn.textContent = "Copy"; }, 1600);
    });
    pre.append(btn);
  }

  // "On this page": mark the section being read.
  const links = [...document.querySelectorAll(".toc a")];
  if (links.length) {
    const byId = new Map(links.map((a) => [decodeURIComponent(a.hash.slice(1)), a]));
    const heads = [...byId.keys()].map((id) => document.getElementById(id)).filter(Boolean);
    let queued = false;
    const mark = () => {
      queued = false;
      let cur = heads[0];
      for (const h of heads) if (h.getBoundingClientRect().top < 120) cur = h;
      links.forEach((a) => a.classList.toggle("here", a === byId.get(cur?.id)));
    };
    addEventListener("scroll", () => { if (!queued) { queued = true; requestAnimationFrame(mark); } }, { passive: true });
    mark();
  }

  // On a phone the page list sits above the article, folded so it doesn't push the text down.
  const list = document.querySelector(".areas details");
  if (list && matchMedia("(max-width: 900px)").matches) list.open = false;
})();
