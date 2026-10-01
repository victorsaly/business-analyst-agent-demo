"""The one-page weekly leadership briefing (same logic as notebook Section 6H).

KPI table: looked up directly with SQL, so the AI cannot mistype it.
Commentary: the agent investigates with its tools (live), or plays a recording (replay), or runs a
scripted plan through the real tools (dry run, no AI).
"""
import base64
import html
import os
import re
import time

import pandas as pd

from . import tools as T
from .agent import queries_used, run_agent
from .cases import load_recording, run_dry_plan, save_recording
from .data import AW_END, connect


def _q(sql):
    with connect() as con:
        return pd.read_sql_query(sql, con)


AW_BRIEFING_KPIS = [("revenue", "Revenue", "SUM(revenue)"), ("margin", "Margin", "SUM(margin)"),
                    ("margin_pct", "Margin %", "100.0 * SUM(margin) / SUM(revenue)"),
                    ("units", "Units sold", "SUM(qty)"), ("orders", "Orders", "COUNT(DISTINCT order_id)")]


def _aw_latest_full_week():
    end = pd.Timestamp(AW_END)
    return (end - pd.Timedelta(days=6 if end.weekday() == 6 else end.weekday() + 7)).strftime("%Y-%m-%d")


def _aw_fmt(metric, v):
    if v is None or pd.isna(v):
        return "n/a"
    return f"{v:.1f}%" if metric == "margin_pct" else (f"${v:,.0f}" if metric in ("revenue", "margin") else f"{v:,.0f}")


def _aw_change(metric, now, before):
    if any(x is None or pd.isna(x) for x in (now, before)) or (metric != "margin_pct" and before == 0):
        return "n/a"
    return f"{now - before:+.1f} pts" if metric == "margin_pct" else f"{(now / before - 1) * 100:+.1f}%"


def _aw_kpis(week):
    w = pd.Timestamp(week)
    weeks = [(w - pd.Timedelta(weeks=k)).strftime("%Y-%m-%d") for k in range(5)]   # this week + 4 before
    sql = (f"SELECT week_start, " + ", ".join(f"{expr} AS {m}" for m, _, expr in AW_BRIEFING_KPIS) +
           f"\nFROM sales_lines\nWHERE week_start IN ({', '.join(repr(x) for x in weeks)})\nGROUP BY week_start")
    df = _q(sql).set_index("week_start").reindex(weeks)
    rows = []
    for m, label, _ in AW_BRIEFING_KPIS:
        now, last, avg4 = df.at[weeks[0], m], df.at[weeks[1], m], df.loc[weeks[1:], m].mean()
        rows.append({"metric": m, "label": label, "now": now, "last": last, "avg4": avg4,
                     "vs_last": _aw_change(m, now, last), "vs_avg4": _aw_change(m, now, avg4)})
    return rows, sql


AW_BRIEFING_INSTRUCTIONS = """Write the weekly leadership briefing for the week starting {week}.
The KPI table was already looked up for you (do not re-query it):
{kpi_text}

Investigate with your tools:
1. detect_anomalies for revenue and margin_pct with period "{quarter}": grain "week" with by "total",
   and grain "month" with by "channel" and by "territory" (reseller orders arrive about once a
   month, so weekly checks by channel or territory raise false alarms).
2. run_sql to find out WHY the biggest change happened (channel, territory, category, discount).
3. make_chart once or twice (e.g. weekly revenue by channel for the last 13 weeks as a bar chart;
   Reseller orders arrive about monthly, so a line would mislead).

Only give a reason if a tool result shows it; otherwise say it needs checking. No forecasts.
Reply in EXACTLY this format (every number from a tool result or the table):
HEADLINE: <one sentence>
WHAT CHANGED AND WHY:
- <2-3 bullets>
WATCH LIST:
- <1-3 bullets, one per unusual run found, with dates and numbers>
FOLLOW-UPS:
- <2-3 recommended actions or questions for the team>
"""


def _parse_briefing(text):
    """Split the agent's reply into its sections (falls back gracefully if the format drifts)."""
    keys = {"HEADLINE": "headline", "WHAT CHANGED AND WHY": "changed", "WATCH LIST": "watch",
            "FOLLOW-UPS": "followups", "FOLLOW UPS": "followups"}
    parts, current = {"headline": "", "changed": [], "watch": [], "followups": []}, None
    for line in text.splitlines():
        clean = line.strip().strip("*#").strip()
        head = next((k for k in keys if clean.upper().startswith(k)), None)
        if head:
            current = keys[head]
            rest = clean[len(head):].lstrip(":* ").strip()
            if current == "headline":
                parts["headline"] = rest
            elif rest:
                parts[current].append(rest)
            continue
        if not clean or current is None:
            continue
        item = re.sub(r"^(?:[-*\u2022]|\d+[.)])\s+", "", line.strip()).strip()
        if current == "headline":
            parts["headline"] = (parts["headline"] + " " + item).strip()
        elif item:
            parts[current].append(item)
    if not parts["headline"] and not parts["changed"]:
        parts["changed"] = [l for l in text.splitlines() if l.strip()][:6]
    return parts


def _inline_md(text):
    """Tiny markdown -> HTML for one line: **bold** and `code`."""
    t = html.escape(text)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    return re.sub(r"`(.+?)`", r"<code>\1</code>", t)


_FONTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "fonts")


def _font(name):
    path = os.path.join(_FONTS, name)
    return base64.b64encode(open(path, "rb").read()).decode("ascii") if os.path.exists(path) else ""


def _page_css():
    """The downloadable page carries its own fonts, so it looks the same when emailed or printed."""
    return (f"@font-face{{font-family:'PHSC';src:url(data:font/ttf;base64,{_font('PatrickHandSC-Regular.ttf')})}}"
            f"@font-face{{font-family:'PH';src:url(data:font/ttf;base64,{_font('PatrickHand-Regular.ttf')})}}"
            f"@font-face{{font-family:'CP';src:url(data:font/ttf;base64,{_font('CourierPrime-Regular.ttf')})}}" + """
.bp{display:grid;grid-template-columns:64px 1fr;max-width:1000px;margin:0 auto;background:#fcfbf7;color:#1e3a8a;
 border:2px solid #1e3a8a;font-family:'PH',cursive;font-size:17px;line-height:1.45;
 background-image:linear-gradient(to bottom,transparent 27px,#dbe2f1 27px,#dbe2f1 28px,transparent 28px);background-size:100% 28px}
.bp ::selection{background:#1e3a8a;color:#fcfbf7}
.sp{border-right:2px solid #1e3a8a;display:flex;flex-direction:column;align-items:center;padding:16px 0;gap:14px}
.st{display:grid;gap:3px;width:38px}.st i{height:4px;background:#c62828}
.vt{writing-mode:vertical-rl;transform:rotate(180deg);font-family:'PHSC';font-size:24px;white-space:nowrap}
.body{padding:22px 30px 30px}
.meta{font-family:'CP',monospace;font-size:12px;color:#3f5a9e;margin:0 0 6px}
h1{font-family:'PHSC';font-weight:400;font-size:32px;line-height:1.1;margin:4px 0 16px;border-bottom:3px solid #1e3a8a;padding-bottom:8px}
h2{font-family:'PHSC';font-weight:400;font-size:22px;margin:22px 0 6px;border-bottom:2px solid #1e3a8a}
table{border-collapse:collapse;width:100%}th{font-family:'PHSC';font-weight:400;text-align:left;border-bottom:2px solid #1e3a8a;padding:4px 6px}
td{border-bottom:1px solid #a9b8dc;padding:4px 6px}.n{text-align:right;font-family:'CP',monospace;font-size:14px;white-space:nowrap}
ul{margin:0;padding-left:20px}li::marker{color:#c62828}
.charts{display:flex;gap:10px;flex-wrap:wrap;margin-top:14px}figure{flex:1 1 45%;margin:0}
figure img{width:100%;border:1px solid #a9b8dc}figcaption{font-size:13px;color:#3f5a9e}
.notes{padding-left:24px}.notes li{margin-bottom:10px}.notes span{font-family:'CP',monospace;font-size:12px}
.notes pre{font-family:'CP',monospace;font-size:12px;white-space:pre-wrap;background:#fff;border:1px solid #a9b8dc;padding:8px;margin:4px 0 0}
body{background:#fcfbf7}@media print{.bp{border:0}}""")


def latest_full_week():
    return _aw_latest_full_week()


def _dry_commentary(call, week, quarter, kpis):
    """Scripted (no AI) plan: real tool calls, templated wording driven by the results."""
    call("detect_anomalies", metric="revenue", by="total", grain="week", period=quarter)
    an = call("detect_anomalies", metric="revenue", by="channel", grain="month", period=quarter)
    r = call("run_sql", query="SELECT week_start, channel, ROUND(SUM(revenue), 0) AS revenue,\n"
                              "       ROUND(100.0 * SUM(margin) / SUM(revenue), 1) AS margin_pct\nFROM sales_lines\n"
                              f"WHERE week_start > date('{week}', '-91 days') AND week_start <= '{week}'\n"
                              "GROUP BY week_start, channel ORDER BY week_start")
    call("make_chart", data=r["result_id"], chart_type="bar", x="week_start", y="revenue", series="channel",
         title="Weekly revenue by channel, last 13 weeks")
    k = {x["metric"]: x for x in kpis}
    now = {x["channel"]: x for x in r["rows"] if x["week_start"] == week}
    res_now = now.get("Reseller", {}).get("revenue", 0)
    res_weeks = [x["week_start"] for x in r["rows"] if x["channel"] == "Reseller"]
    reason = ""
    if not res_now and res_weeks:
        reason = f", with no Reseller orders this week (last Reseller week: {res_weeks[-1]})"
    elif res_now:
        reason = f"; Reseller brought ${res_now:,.0f} of it"
    changed = [f"Revenue {_aw_fmt('revenue', k['revenue']['now'])}: {k['revenue']['vs_last']} vs last week, "
               f"{k['revenue']['vs_avg4']} vs the 4-week average{reason}."]
    online = now.get("Online")
    if online:
        changed.append(f"Online: ${online['revenue']:,.0f} at {online['margin_pct']}% margin"
                       + (f"; Reseller: ${res_now:,.0f} at {now['Reseller']['margin_pct']}% margin." if res_now else
                          ". Margin % moves mostly with the Online / Reseller mix, so read it together with the channel split."))
    changed.append(f"Margin % {_aw_fmt('margin_pct', k['margin_pct']['now'])} ({k['margin_pct']['vs_avg4']} vs the 4-week average).")
    return ("HEADLINE: Revenue " + k["revenue"]["vs_avg4"] + " vs the 4-week average" + reason + ".\n"
            "WHAT CHANGED AND WHY:\n" + "\n".join(f"- {c}" for c in changed) + "\n"
            "WATCH LIST:\n- " + an["summary"][:300] + "\n"
            "FOLLOW-UPS:\n- Ask Sales Ops to confirm the Reseller order pattern for this period.\n"
            "- Confirm the latest weeks of data are complete before sharing externally.")


def build(week=None, mode="live", on_step=None, on_wait=None, step_delay=0.0, on_kpis=None, on_think=None):
    """Returns {"html", "answer", "trace", "charts", "kpis", "queries", "mode"}."""
    week = week or _aw_latest_full_week()
    w = pd.Timestamp(week)
    quarter = f"{w.year}-Q{(w.month - 1) // 3 + 1}"
    kpis, kpi_sql = _aw_kpis(week)
    if on_kpis:   # the table is final already: show it while the agent writes the commentary
        on_kpis(kpis, kpi_sql)
    kpi_text = "\n".join(f"- {k['label']}: {_aw_fmt(k['metric'], k['now'])}, vs last week {k['vs_last']}, "
                         f"vs 4-week average {k['vs_avg4']}" for k in kpis)
    key = f"briefing:{week}"
    if mode == "replay":
        res = load_recording(key)
        if res is None:
            raise LookupError("No recorded briefing for this week. Build it once in Live mode first.")
        for i, t in enumerate(res["trace"], 1):
            if on_step:
                on_step(i, t["tool"], t["args"], t["result"])
            time.sleep(step_delay)
    elif mode == "dry":
        res = run_dry_plan(lambda call: _dry_commentary(call, week, quarter, kpis), on_step=on_step, step_delay=step_delay)
    else:
        res = run_agent(AW_BRIEFING_INSTRUCTIONS.format(week=week, kpi_text=kpi_text, quarter=quarter),
                        on_step=on_step, on_wait=on_wait, on_think=on_think, max_iterations=12, max_tokens=2500)
        save_recording(key, res)
    parts = _parse_briefing(res["answer"])
    queries = [{"label": "KPI table", "lang": "sql", "text": kpi_sql}] + queries_used(res["trace"])
    ul = lambda items: "<ul>" + "".join(f"<li>{_inline_md(i)}</li>" for i in items) + "</ul>" if items else "<p><i>None.</i></p>"
    kpi_rows = "".join(f"<tr><td>{k['label']}</td><td class='n'><b>{_aw_fmt(k['metric'], k['now'])}</b></td>"
                       f"<td class='n'>{_aw_fmt(k['metric'], k['last'])}</td><td class='n'>{k['vs_last']}</td>"
                       f"<td class='n'>{_aw_fmt(k['metric'], k['avg4'])}</td><td class='n'>{k['vs_avg4']}</td></tr>" for k in kpis)
    charts = "".join(f"<figure><img src='data:image/png;base64,{c['png_base64']}' alt='{html.escape(c['caption'])}'>"
                     f"<figcaption>{html.escape(c['caption'])}</figcaption></figure>" for c in res["charts"][:3])
    working = "<ol class='notes'>" + "".join(f"<li><span>{html.escape(q['label'])}</span><pre>{html.escape(q['text'])}</pre></li>"
                                             for q in queries) + "</ol>"
    badge = {"dry": "Dry run: scripted plan through the real tools, wording not written by the AI",
             "replay": f"Replay of a live run recorded {res.get('recorded_at', '')}",
             "live": f"Live run, {res.get('model', '')}"}[mode]
    page = f"""<style>{_page_css()}</style>
<div class="bp">
<aside class="sp"><div class="st"><i></i><i></i><i></i></div><div class="vt">Weekly leadership briefing</div></aside>
<div class="body">
<p class="meta">AdventureWorks · week of {w:%d %b %Y} · {html.escape(badge)}</p>
<h1>{_inline_md(parts['headline'] or 'Weekly briefing')}</h1>
<table><tr><th>KPI</th><th class="n">This week</th><th class="n">Last week</th><th class="n">vs last week</th>
<th class="n">4-week avg</th><th class="n">vs 4-week avg</th></tr>{kpi_rows}</table>
<h2>What changed and why</h2>{ul(parts['changed'])}
<h2>Watch list</h2>{ul(parts['watch'])}
<div class="charts">{charts}</div>
<h2>Recommended follow-ups</h2>{ul(parts['followups'])}
<h2>How these numbers were produced</h2>{working}
<p class="meta">Every number comes from a read-only query on the AdventureWorks database. Nothing here is a forecast.</p>
</div></div>"""
    return {"html": page, "answer": res["answer"], "trace": res["trace"], "charts": res["charts"], "kpis": kpis,
            "queries": queries, "mode": mode, "week": week, "tokens": res.get("tokens", 0),
            "seconds": res.get("seconds", 0), "model": res.get("model", ""), "recorded_at": res.get("recorded_at")}
