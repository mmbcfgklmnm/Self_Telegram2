"""
generate_session.py — One-time helper to generate a Telethon StringSession.

Run this script locally (NOT on Railway) to authenticate once and print the
session string that you'll paste into your Railway environment variables.

Usage:
    python generate_session.py

You will be prompted for:
  • Your phone number (with country code, e.g. +1234567890)
  • The login code Telegram sends you
  • Your 2FA password (if enabled)

The resulting session string is printed to stdout. Copy it and set it as the
SESSION_STRING environment variable in Railway (or your .env file for local
development).

⚠️  Keep the session string SECRET — it grants full access to your account.
"""

import asyncio
import os
import sys

try:
    from telethon import TelegramClient
    from telethon.sessions import StringSession
except ImportError:
    print("Telethon is not installed. Run: pip install telethon")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional here


def _get_credentials() -> tuple[int, str]:
    api_id_str = os.getenv("API_ID", "").strip()
    api_hash = os.getenv("API_HASH", "").strip()

    if not api_id_str:
        api_id_str = input("Enter your API_ID (from https://my.telegram.org): ").strip()
    if not api_hash:
        api_hash = input("Enter your API_HASH: ").strip()

    try:
        api_id = int(api_id_str)
    except ValueError:
        print("API_ID must be a number.", file=sys.stderr)
        sys.exit(1)

    return api_id, api_hash


async def generate() -> None:
    api_id, api_hash = _get_credentials()

    print("\nConnecting to Telegram…")
    async with TelegramClient(StringSession(), api_id, api_hash) as client:
        me = await client.get_me()
        session_string = client.session.save()

    print("\n" + "=" * 70)
    print("✅ Authenticated as:", me.first_name, f"(id={me.id})")
    print("=" * 70)
    print("\nYour SESSION_STRING (keep this SECRET):\n")
    print(session_string)
    print("\n" + "=" * 70)
    print("Next steps:")
    print("  1. Copy the string above.")
    print("  2. Set it as SESSION_STRING in your Railway environment variables,")
    print("     or paste it into your local .env file.")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(generate())
