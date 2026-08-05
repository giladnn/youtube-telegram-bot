"""One-time Telethon login — run this once in your terminal.

Sends a login code to your Telegram app, asks for it, and saves the session
so the bot never needs to ask again.

Usage:
    python3 telethon_login.py
"""

import os

from dotenv import load_dotenv
from telethon.sync import TelegramClient

load_dotenv()

API_ID = int(os.environ["TELEGRAM_API_ID"])
API_HASH = os.environ["TELEGRAM_API_HASH"]
PHONE = os.environ["TELEGRAM_PHONE"]
SESSION_FILE = os.getenv("TELETHON_SESSION_FILE", "telethon_session.session")
CHANNEL_ID = int(os.getenv("TELEGRAM_CHANNEL_ID", "-1002007708028"))

print("Connecting to Telegram — a login code will be sent to your Telegram app...")
with TelegramClient(SESSION_FILE, API_ID, API_HASH) as client:
    client.start(phone=PHONE)
    me = client.get_me()
    print(f"\n✓ Logged in as: {me.first_name} (+{me.phone})")
    print(f"✓ Session saved to: {SESSION_FILE}")

    # Verify we can read the Hon Land channel
    try:
        entity = client.get_entity(CHANNEL_ID)
        title = getattr(entity, "title", CHANNEL_ID)
        messages = client.get_messages(entity, limit=3)
        print(f"✓ Can read channel: {title}")
        for m in messages:
            if m.text:
                print(f"  • {m.text[:80]}...")
        print("\nAll set! The bot can now read Hon Land automatically.")
    except Exception as e:
        print(f"\n⚠ Logged in, but could not read the channel: {e}")
        print("Make sure you are a member of Hon Land with this account.")
