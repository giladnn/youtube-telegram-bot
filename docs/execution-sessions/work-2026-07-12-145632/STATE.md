---
source_type: plan
plan_file: docs/plans/2026-07-12-feat-youtube-telegram-summarizer-plan.md
ticket_file: null
tickets_ref: null
brainstorm_ref: docs/brainstorms/2026-07-12-youtube-telegram-summarizer-brainstorm.md
started: 2026-07-12T00:00:00Z
status: in_progress
execution_shape: vertical-slices
current_unit: 0
total_units: 4
session_id: work-2026-07-12-000000
---

## WHY Context

### Problem Narrative
You and your investment group consume Israeli market intelligence across fragmented sources: two YouTube channels with in-depth stock analysis (@Micha.Stocks, @guynatan9) and a Telegram channel (Hon Land) with live market updates. Watching full 30–90 minute videos consumes too much time, and updates across platforms are easy to miss. The group lacks a daily alignment point. You need a single consolidated digest delivered each morning so the group can absorb key actionable intel in minutes and stay coordinated.

### User Story
**As an** Israeli investor in a small trading/investment group,
**I need to** receive one daily digest by 8am combining summaries of new YouTube videos + latest Telegram channel posts,
**so that** I can stay informed on Israeli stock opportunities and market movements without spending hours across platforms,
**because currently** I'm either missing critical updates or wasting time watching full videos and monitoring channels,
**which causes** the group to misalign and me to miss potential trading opportunities.

### Architectural Context
- **Lives in:** A new standalone Python service (`youtube_telegram_bot/` directory)
- **Feature home:** The bot script and scheduler
- **Interacts with:** YouTube RSS, Gemini API, Telegram Bot API, Telethon, macOS launchd
- **Entry point:** Scheduled daily at 8am via LaunchAgent
- **Data:** YouTube RSS (input), Hebrew captions (via yt-dlp), Telegram channel posts (via Telethon), state.json (local persistence)
- **Dependencies:** yt-dlp, python-telegram-bot, telethon, google-generativeai
- **Conventions:** Plain Python, minimal deps, simple structure

### Success Criteria
- [ ] Digest arrives automatically at 8am in Telegram group every day
- [ ] Content is skimmable in 2–3 minutes (no walls of text)
- [ ] Summaries capture actionable Israeli stock tickers, recommendations, and market themes (Hebrew accuracy matters)
- [ ] All team members receive the same digest and stay aligned
- [ ] Zero manual intervention after initial setup (fully automated)
- [ ] $0 cost (free APIs only: Gemini free tier, YouTube RSS, Telegram Bot API, Telethon)

### TDD Contract
- Effective mode: Ralph-driven TDD
- Effective loop: Red-Green-Refactor with post-refactor rerun
- Required evidence: Unit + E2E evidence required
- Exceptions: None

### Constitution Context
No project constitution exists. This is a greenfield automation service. No approvals or waivers needed.

### Architecture Handoff
- Feature homes: `youtube_telegram_bot/` (main module) for all slices
- Shared / global: None (standalone service)
- Context tiers: Local only
- Deletion test: Keep simple; no premature abstraction
- Interfaces: RSS feed polling, transcript extraction, Gemini API wrapper, Telegram posting
- Seams: Error handling at each API boundary
- Review guidance: Ensure Hebrew prompting quality, deduplication logic, error resilience

## Work Status

| # | Unit | Kind | Serves / Unlocks | Status | Attempts | Session File |
|---|------|------|------------------|--------|----------|--------------|
| 1.1 | YouTube RSS Polling & State File | tracer-bullet | Proves core polling + deduplication | pending | -- | -- |
| 2.1 | yt-dlp Transcript Extraction | expansion | Enables summarization | pending | -- | -- |
| 2.2 | Gemini Summarization with Hebrew Prompt | expansion | Delivers concise Hebrew summaries | pending | -- | -- |
| 3.3 | Full Integration + LaunchAgent Scheduler | hardening | Delivers fully automated daily digest | pending | -- | -- |

## Learnings Brief
_No learnings yet._
