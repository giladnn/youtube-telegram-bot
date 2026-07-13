---
name: telegram
description: >-
  Interact with this project's Telegram setup: post messages to channels via
  @Gilad_sidekick_bot, read channel posts (including Hon Land) via the
  authorized Telethon user session, discover chat IDs, and run or verify the
  YouTube→Telegram digest bot. Use this skill whenever the user mentions
  Telegram, posting/reading channel messages, the digest bot, Hon Land,
  the Morning digest channel, chat IDs, or asks to test/run/debug the
  8am summarizer pipeline — even if they don't say "telegram" explicitly.
---

# Telegram Connector

All credentials live in `.env` at the project root (`/Users/victorianeiman/weekly-spending-dashboard`).
It is loaded automatically when any `youtube_telegram_bot` module is imported.
Never print secret values; never commit `.env` or `*.session` files (both gitignored — keep it that way).

## Known chats

| Chat | ID | Access |
|------|----|--------|
| "Morning digest" channel (digest destination) | `-1003772028678` | Bot is admin — post via Bot API |
| "Hon Land \| סקירות והחזקות" (read-only source) | `-1002007708028` | Read via Telethon user session only. The bot is NOT a member — do not try to post there or suggest adding the bot; the user explicitly declined |

The bot is **@Gilad_sidekick_bot** (id `8667217372`), token in `TELEGRAM_BOT_TOKEN`.

## Posting a message (Bot API)

```bash
source .env
curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  -d chat_id="${TELEGRAM_CHAT_ID}" \
  --data-urlencode text="your message" \
  -d parse_mode=Markdown
```

Or in Python: `from youtube_telegram_bot.telegram_posting import post_digest; post_digest("text")`.
Telegram messages cap at 4096 chars. Markdown parse mode fails the whole message on
unbalanced `*`/`_`/`` ` `` — if a post returns `can't parse entities`, retry without parse_mode.
Posting to a real channel is user-visible: don't post test messages unless the user asked for a test.

## Reading channel posts (Telethon)

The Telethon session (`telethon_session.session`, path in `TELETHON_SESSION_FILE`) is
already authorized as the user's personal account. Reuse it — never trigger a new login:
each `send_code_request` sends the user a login code (to their Telegram app, NOT SMS) and
repeated requests can flood-limit the account. If the session is ever unauthorized, tell the
user to run `python3 telethon_login.py` themselves in their own terminal (the login code is
their account credential — Claude must not handle it).

```python
from youtube_telegram_bot.telegram_reading import read_channel_posts
posts = read_channel_posts(limit=5)  # Hon Land by default, newest first, "[dd.mm] text" format
```

Always import `TelegramClient` from `telethon.sync` (the plain `telethon` client returns
coroutines that break sync code). Numeric channel IDs must be passed as `int`.

## Discovering a chat ID

After the user adds the bot to a chat (or posts a message there):

```bash
source .env
curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getUpdates" | python3 -m json.tool
```

Look for `chat.id` in `my_chat_member` / `channel_post` / `message` entries.
Channel IDs start with `-100`. If empty, ask the user to post any message in the chat first.

## Running / verifying the digest bot

```bash
python3 -m youtube_telegram_bot.bot        # full pipeline; POSTS a real digest at the end
python3 -m pytest tests/ -q               # 75 unit/integration tests, no network side effects
```

The pipeline: poll YouTube RSS → extract transcripts → Gemini summaries (+ tips, 150-day MA)
→ read Hon Land → format → post to Morning digest → update `summaries.html` + `summaries/*.md`.

- **Dedup**: `state.json` maps seen video IDs. To force reprocessing a video, delete its key
  from `state.json` and rerun. A full run posts to the real channel — warn the user first
  if they didn't explicitly ask for a run.
- **Quota**: Gemini free tier is per-model per-day; the summarizer falls back through
  `gemini-flash-latest → gemini-flash-lite-latest → gemini-2.0-flash` automatically.
  Failed videos are un-marked in state and retried next run.
- **Schedule**: LaunchAgent `com.youtube-telegram-summarizer.bot` at
  `~/Library/LaunchAgents/`, runs daily 08:00 via `/usr/bin/python3`, logs to
  `~/logs/youtube-telegram-bot*.log`. After editing the plist, `launchctl unload` then
  `load` it. Verify a scheduled run by checking the log, not by rerunning the bot.

## Quick health check (read-only, safe anytime)

```bash
source .env
curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe"   # bot token valid?
python3 - <<'EOF'
import os
from dotenv import load_dotenv; load_dotenv(".env")
from telethon.sync import TelegramClient
c = TelegramClient(os.getenv("TELETHON_SESSION_FILE", "telethon_session.session"),
                   int(os.environ["TELEGRAM_API_ID"]), os.environ["TELEGRAM_API_HASH"])
c.connect(); print("telethon authorized:", c.is_user_authorized()); c.disconnect()
EOF
```
