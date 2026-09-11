# 🎭 Telegram Emoji → Sticker Userbot

A personal Telegram **userbot** (self-bot) that monitors your **Saved Messages** chat and converts premium animated custom emoji into proper Telegram stickers — on demand, with a single reply.

Built with [Telethon](https://github.com/LonamiWebs/Telethon) and deployable on [Railway](https://railway.app) with zero interactive login required.

---

## ✨ Features

| Feature | Detail |
|---|---|
| **Self-bot / userbot** | Runs under your personal Telegram account via MTProto — no Bot API, no bot account needed |
| **Saved Messages monitor** | Watches only your private Saved Messages chat — no other chats are affected |
| **Trigger-phrase conversion** | Reply `convert to sticker` (configurable) to any emoji message to convert it |
| **Lottie TGS support** | Animated emoji backed by Lottie/TGS are passed through with zero re-encoding |
| **WebM video support** | Video-animated emoji (VP9 WebM) are passed through at original quality |
| **Static WebP/PNG support** | Static emoji are resized to 512×512 lossless WebP (Telegram sticker requirement) |
| **Rich error feedback** | Every error sends a descriptive message back to you in Saved Messages |
| **StringSession auth** | Session is generated once locally and stored as an env var — no interactive login on Railway |
| **Auto-reconnect** | Telethon reconnects indefinitely if the connection drops |
| **Fully configurable** | Trigger phrase, log level via environment variables |

---

## 🗂️ Project Structure

```
telegram-emoji-sticker-bot/
├── src/
│   ├── __init__.py           # Package marker
│   ├── config.py             # Environment variable loading & validation
│   ├── logger.py             # Logging configuration
│   ├── emoji_extractor.py    # Detect & fetch custom emoji documents
│   ├── sticker_converter.py  # Convert emoji document to sticker file
│   ├── sender.py             # Send sticker / feedback to Saved Messages
│   └── handler.py            # Telethon event handlers (the brain)
├── main.py                   # Entry point
├── generate_session.py       # One-time local script to generate SESSION_STRING
├── requirements.txt          # Pinned Python dependencies
├── .env.example              # Template for environment variables
├── .gitignore                # Excludes secrets & cache files
├── Procfile                  # For Railway / Heroku worker process
├── railway.json              # Railway deployment config
├── LICENSE                   # MIT License
└── README.md                 # This file
```

---

## 🔑 Step 1 — Get Your Telegram API ID & Hash

1. Go to **[https://my.telegram.org/apps](https://my.telegram.org/apps)** and log in with your phone number.
2. Click **"Create new application"** (or use an existing one).
3. Fill in any name/short name — they don't matter for a private userbot.
4. Copy the **`App api_id`** (a number, e.g. `1234567`) and **`App api_hash`** (a hex string).

> ⚠️ **Never share these values.** They're tied to your Telegram account and grant API-level access.

---

## ⚙️ Step 2 — Local Setup

### 2.1 Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/telegram-emoji-sticker-bot.git
cd telegram-emoji-sticker-bot
```

### 2.2 Create a virtual environment & install dependencies

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

### 2.3 Create your `.env` file

```bash
cp .env.example .env
```

Open `.env` and fill in `API_ID` and `API_HASH` from Step 1. Leave `SESSION_STRING` blank for now.

---

## 🔐 Step 3 — Generate Your Session String

Run the helper script **once** on your local machine:

```bash
python generate_session.py
```

It will:
1. Ask for your phone number (e.g. `+1234567890`)
2. Send a Telegram login code to your account
3. Ask for the code (and 2FA password if you have one)
4. Print your `SESSION_STRING`

Copy the printed string and paste it into your `.env` file:

```
SESSION_STRING=1BVtsOKABu....(very long string)....==
```

> ⚠️ **This string = full access to your Telegram account.** Treat it like a password. Never commit it to git (`.gitignore` already excludes `.env` and `*.session` files).

---

## ▶️ Step 4 — Run Locally

```bash
python main.py
```

You should see:
```
[2024-01-01 12:00:00] INFO     __main__ — Starting telegram-emoji-sticker-bot…
[2024-01-01 12:00:02] INFO     __main__ — ✅ Logged in as YourName (id=123456789). Monitoring Saved Messages…
[2024-01-01 12:00:02] INFO     __main__ — Trigger phrase: 'convert to sticker'
```

### Usage

1. **Send** a message with a 💎 premium animated emoji into your **Saved Messages** chat.
2. **Reply** to that message with the text: `convert to sticker`
3. The bot will send the sticker back to you as a reply.

---

## 🚀 Step 5 — Deploy to Railway

### 5.1 Push to GitHub

```bash
git add .
git commit -m "Initial commit"
git push origin main
```

> Make sure `.env` is **not** committed (it's in `.gitignore`).

### 5.2 Create a Railway project

1. Go to **[https://railway.app](https://railway.app)** and sign in.
2. Click **"New Project"** → **"Deploy from GitHub repo"**.
3. Select your `telegram-emoji-sticker-bot` repository.
4. Railway will auto-detect the `railway.json` configuration.

### 5.3 Set environment variables on Railway

In your Railway project dashboard:

1. Click your service → **"Variables"** tab.
2. Add the following variables:

| Variable | Value |
|---|---|
| `API_ID` | Your Telegram API ID (number) |
| `API_HASH` | Your Telegram API hash (hex string) |
| `SESSION_STRING` | The string from `generate_session.py` |
| `TRIGGER_PHRASE` | *(optional)* default: `convert to sticker` |
| `LOG_LEVEL` | *(optional)* default: `INFO` |

### 5.4 Deploy

Railway will automatically deploy once variables are set. Check the **Logs** tab to confirm:

```
✅ Logged in as YourName (id=123456789). Monitoring Saved Messages…
```

### 5.5 Worker vs Web service

The `railway.json` and `Procfile` both declare this as a **worker** process (no HTTP port binding). This is correct — the bot is a persistent TCP connection to Telegram, not a web server. Railway keeps it running continuously and restarts it on failure (up to 10 times per `railway.json`).

---

## 🛠️ Configuration Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `API_ID` | ✅ | — | Telegram App API ID from my.telegram.org |
| `API_HASH` | ✅ | — | Telegram App API Hash |
| `SESSION_STRING` | ✅ | — | Telethon StringSession from generate_session.py |
| `TRIGGER_PHRASE` | ❌ | `convert to sticker` | Case-insensitive phrase to trigger conversion |
| `LOG_LEVEL` | ❌ | `INFO` | Python logging level: DEBUG, INFO, WARNING, ERROR |

---

## 🔄 How It Works (Architecture)

```
Your message with emoji          Your "convert to sticker" reply
         │                                    │
         ▼                                    ▼
   handler.py                          handler.py
  (tracks msg ID)              (detects trigger phrase)
                                            │
                                            ▼
                                  emoji_extractor.py
                              (fetches Document via MTProto
                               GetCustomEmojiDocuments)
                                            │
                              ┌─────────────┴──────────────┐
                              │                             │
                         Lottie TGS                  WebM / Static
                         (pass-thru)            (pass-thru / resize)
                              │                             │
                              └─────────────┬──────────────┘
                                            │
                                  sticker_converter.py
                                  (produces temp file)
                                            │
                                            ▼
                                       sender.py
                              (uploads to Saved Messages as reply)
```

---

## 📋 Emoji Format Support

| Emoji type | Telegram MIME | Output | Re-encoded? |
|---|---|---|---|
| Lottie animated | `application/x-tgsticker` | `.tgs` | ❌ No — zero-copy |
| Video animated | `video/webm` | `.webm` | ❌ No — zero-copy |
| Static | `image/webp` or `image/png` | `.webp` (512×512 lossless) | ✅ Resized only |

---

## 🐛 Troubleshooting

**`SESSION_STRING` is invalid / expired**  
→ Re-run `python generate_session.py` and update the environment variable.

**`API_ID must be a valid integer`**  
→ Make sure `API_ID` contains only digits, no spaces or quotes.

**Bot doesn't respond to trigger phrase**  
→ Check that `TRIGGER_PHRASE` matches exactly (it's case-insensitive but must be the entire message text, not a substring).

**`FloodWaitError`**  
→ Telegram is rate-limiting you. The bot auto-sleeps for up to 60 seconds. For longer waits, it will log the error and retry.

**Railway container keeps restarting**  
→ Check Railway logs. Common causes: wrong `SESSION_STRING`, bad `API_ID`/`API_HASH`, or a Telegram account ban.

---

## ⚖️ Legal & Ethical Notes

- This is a **self-bot** — it operates on your own account and only monitors your **Saved Messages** (a private chat with yourself). It does not interact with other users, groups, or channels.
- Telegram's Terms of Service technically prohibit automated account usage. Use at your own risk, as with any userbot.
- The session string gives full account access — never share it.

---

## 📄 License

MIT — see [LICENSE](LICENSE).
