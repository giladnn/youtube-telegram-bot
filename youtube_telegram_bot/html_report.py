"""Persist summaries to a JSON archive and render them as a browsable HTML page."""

import html
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Archive and report locations (project root by default)
SUMMARIES_FILE = os.getenv("SUMMARIES_FILE", "summaries.json")
HTML_REPORT_FILE = os.getenv("HTML_REPORT_FILE", "summaries.html")
MARKDOWN_DIR = os.getenv("MARKDOWN_DIR", "summaries")

CHANNEL_LABELS = {
    "Micha.Stocks": "מיכה סטוקס",
    "guynatan9": "גיא נתן",
}


def _load_archive(path: str) -> List[Dict[str, Any]]:
    """Load the summaries archive, returning an empty list if missing/corrupt."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def archive_summaries(videos: List[Dict[str, Any]], path: str = None) -> int:
    """
    Append newly processed videos to the summaries archive (deduplicated by id).

    Args:
        videos: Processed video dicts (id, title, tickers, claim, recommendation,
                risk_flag, hebrew_summary)
        path: Archive file path (defaults to SUMMARIES_FILE)

    Returns:
        Number of videos newly added to the archive
    """
    path = path or SUMMARIES_FILE
    archive = _load_archive(path)
    seen_ids = {entry.get("id") for entry in archive}

    added = 0
    today = datetime.now().strftime("%Y-%m-%d")
    for video in videos:
        if video.get("id") in seen_ids:
            continue
        entry = dict(video)
        entry["date"] = today
        archive.append(entry)
        added += 1

    if added:
        tmp_path = f"{path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(archive, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
        logger.info(f"Archived {added} new summarie(s) to {path}")

    return added


def generate_markdown_files(archive_path: str = None, output_dir: str = None) -> int:
    """
    Write one markdown file per archived summary — a browsable knowledge base.

    Files are named <date>-<video_id>.md and include YAML frontmatter
    (date, channel, tickers) plus the full structured analysis, so they can
    be searched, grepped, or fed to other tools for deeper analysis.

    Args:
        archive_path: Path of the JSON archive (defaults to SUMMARIES_FILE)
        output_dir: Directory for the .md files (defaults to MARKDOWN_DIR)

    Returns:
        Number of markdown files newly written (existing files are skipped)
    """
    archive_path = archive_path or SUMMARIES_FILE
    output_dir = Path(output_dir or MARKDOWN_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    archive = _load_archive(archive_path)
    written = 0

    for entry in archive:
        video_id = entry.get("id", "unknown")
        date = entry.get("date", "unknown")
        md_path = output_dir / f"{date}-{video_id}.md"
        if md_path.exists():
            continue

        channel = entry.get("channel", "")
        source = CHANNEL_LABELS.get(channel, channel)
        tickers = entry.get("tickers", [])
        url = f"https://www.youtube.com/watch?v={video_id}"

        lines = [
            "---",
            f"date: {date}",
            f"channel: {channel}",
            f"source: {source}",
            f"video_id: {video_id}",
            f"url: {url}",
            f"tickers: [{', '.join(tickers)}]",
            "---",
            "",
            f"# {entry.get('title', '')}",
            "",
            f"**מקור:** {source} · **תאריך:** {date} · [צפייה בסרטון]({url})",
            "",
        ]

        if tickers:
            lines += ["## 🎫 טיקרים", "", " · ".join(f"`{t}`" for t in tickers), ""]
        ticker_stats = entry.get("ticker_stats", {})
        if ticker_stats:
            lines += ["## 📊 נתוני שוק", ""]
            for ticker, stats in ticker_stats.items():
                arrow = "🟢 מעל" if stats.get("above_ma") else "🔴 מתחת"
                line = (
                    f"- **{ticker}**: מחיר {stats['price']:,} · "
                    f"ממוצע 150 ימים: {stats['ma150']:,} ({arrow})"
                )
                analyst = stats.get("analyst")
                if analyst:
                    line += (
                        f" · 🎯 {analyst['rating']}, יעד {analyst['target_mean']:,} "
                        f"({analyst['analysts']} אנליסטים)"
                    )
                lines.append(line)
            lines.append("")
        if entry.get("claim"):
            lines += ["## 💬 טענה מרכזית", "", entry["claim"], ""]
        if entry.get("recommendation"):
            lines += ["## 📈 המלצה", "", entry["recommendation"], ""]
        tips = entry.get("tips", [])
        if tips:
            lines += ["## 💡 טיפים מהסרטון", ""]
            lines += [f"- {tip}" for tip in tips]
            lines.append("")
        risk = entry.get("risk_flag", "")
        if risk and risk.lower() not in ("ללא", "none", ""):
            lines += ["## ⚠️ סיכונים", "", risk, ""]
        if entry.get("hebrew_summary"):
            lines += ["## 📋 סיכום מלא", "", entry["hebrew_summary"], ""]

        md_path.write_text("\n".join(lines), encoding="utf-8")
        written += 1

    if written:
        logger.info(f"Wrote {written} markdown file(s) to {output_dir}/")
    return written


def _render_video_card(video: Dict[str, Any]) -> str:
    """Render one video summary as an HTML card."""
    video_id = html.escape(video.get("id", ""))
    channel = video.get("channel", "")
    source = html.escape(CHANNEL_LABELS.get(channel, channel))
    title = html.escape(video.get("title", ""))
    if source:
        title = f"{source} | {title}"
    tickers = video.get("tickers", [])
    claim = html.escape(video.get("claim", ""))
    recommendation = html.escape(video.get("recommendation", ""))
    risk_flag = video.get("risk_flag", "")
    summary = html.escape(video.get("hebrew_summary", ""))
    url = f"https://www.youtube.com/watch?v={video_id}"

    ticker_badges = "".join(
        f'<span class="ticker">{html.escape(t)}</span>' for t in tickers
    )

    rows = []
    for ticker, stats in video.get("ticker_stats", {}).items():
        cls = "rec" if stats.get("above_ma") else "risk"
        arrow = "מעל" if stats.get("above_ma") else "מתחת"
        line = (
            f'📊 {html.escape(ticker)}: {stats["price"]:,} · '
            f'ממוצע 150: {stats["ma150"]:,} ({arrow})'
        )
        analyst = stats.get("analyst")
        if analyst:
            line += (
                f' · 🎯 {html.escape(analyst["rating"])} · '
                f'יעד {analyst["target_mean"]:,} ({analyst["analysts"]} אנליסטים)'
            )
        rows.append(f'<p class="{cls}">{line}</p>')
    if recommendation:
        rows.append(f'<p class="rec">📈 {recommendation}</p>')
    if claim:
        rows.append(f'<p class="claim">💬 {claim}</p>')
    tips = video.get("tips", [])
    if tips:
        tip_items = "".join(f"<li>{html.escape(t)}</li>" for t in tips)
        rows.append(f'<ul class="tips">{tip_items}</ul>')
    if risk_flag and risk_flag.lower() not in ("ללא", "none", ""):
        rows.append(f'<p class="risk">⚠️ {html.escape(risk_flag)}</p>')
    if summary:
        rows.append(f'<p class="summary">{summary}</p>')

    return f"""
    <article class="card">
      <h3><a href="{url}" target="_blank" rel="noopener">{title}</a></h3>
      <div class="tickers">{ticker_badges}</div>
      {"".join(rows)}
    </article>"""


def generate_html(archive_path: str = None, output_path: str = None) -> str:
    """
    Render the full summaries archive as a standalone RTL HTML page.

    Summaries are grouped by date, newest first.

    Args:
        archive_path: Path of the JSON archive (defaults to SUMMARIES_FILE)
        output_path: Where to write the HTML file (defaults to HTML_REPORT_FILE)

    Returns:
        Path of the written HTML file, or empty string if archive is empty
    """
    archive_path = archive_path or SUMMARIES_FILE
    output_path = output_path or HTML_REPORT_FILE

    archive = _load_archive(archive_path)
    if not archive:
        logger.info("No summaries archived yet — skipping HTML report")
        return ""

    # Group by date, newest first
    by_date: Dict[str, List[Dict[str, Any]]] = {}
    for entry in archive:
        by_date.setdefault(entry.get("date", "לא ידוע"), []).append(entry)

    sections = []
    for date in sorted(by_date.keys(), reverse=True):
        cards = "".join(_render_video_card(v) for v in by_date[date])
        display_date = date
        try:
            display_date = datetime.strptime(date, "%Y-%m-%d").strftime("%d.%m.%Y")
        except ValueError:
            pass
        sections.append(f'<section><h2>📅 {display_date}</h2>{cards}</section>')

    generated_at = datetime.now().strftime("%d.%m.%Y %H:%M")
    page = f"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>דייג'סט השקעות — ארכיון סיכומים</title>
<style>
  :root {{
    --bg: #f6f7f9; --card: #ffffff; --text: #1a1a2e; --muted: #6b7280;
    --accent: #2563eb; --risk: #dc2626; --rec: #059669; --border: #e5e7eb;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #111318; --card: #1c1f26; --text: #e5e7eb; --muted: #9ca3af;
      --accent: #60a5fa; --risk: #f87171; --rec: #34d399; --border: #2d3138;
    }}
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 24px 16px; background: var(--bg); color: var(--text);
    font-family: -apple-system, "Segoe UI", Roboto, "Heebo", sans-serif; line-height: 1.6;
  }}
  main {{ max-width: 720px; margin: 0 auto; }}
  h1 {{ font-size: 1.5rem; margin-bottom: 4px; }}
  .sub {{ color: var(--muted); font-size: 0.85rem; margin-bottom: 24px; }}
  h2 {{ font-size: 1.1rem; border-bottom: 1px solid var(--border); padding-bottom: 6px; margin-top: 32px; }}
  .card {{
    background: var(--card); border: 1px solid var(--border); border-radius: 12px;
    padding: 16px; margin: 12px 0;
  }}
  .card h3 {{ margin: 0 0 8px; font-size: 1rem; }}
  .card a {{ color: var(--accent); text-decoration: none; }}
  .card a:hover {{ text-decoration: underline; }}
  .tickers {{ margin-bottom: 8px; }}
  .ticker {{
    display: inline-block; background: var(--accent); color: #fff; border-radius: 6px;
    padding: 1px 8px; font-size: 0.75rem; font-weight: 600; margin-inline-end: 6px;
    font-family: ui-monospace, monospace;
  }}
  .rec {{ color: var(--rec); margin: 4px 0; }}
  .tips {{ margin: 8px 0; padding-inline-start: 20px; list-style: none; }}
  .tips li {{ margin: 4px 0; }}
  .tips li::before {{ content: "💡 "; }}
  .risk {{ color: var(--risk); margin: 4px 0; }}
  .claim {{ margin: 4px 0; }}
  .summary {{ color: var(--muted); font-size: 0.9rem; margin: 8px 0 0; }}
</style>
</head>
<body>
<main>
  <h1>📺 דייג'סט השקעות — ארכיון סיכומים</h1>
  <p class="sub">עודכן: {generated_at} · {len(archive)} סיכומים</p>
  {"".join(sections)}
</main>
</body>
</html>
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(page)
    logger.info(f"HTML report written to {output_path} ({len(archive)} summaries)")
    return output_path
