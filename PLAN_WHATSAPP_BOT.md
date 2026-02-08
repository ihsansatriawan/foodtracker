# Plan: WhatsApp Bot Integration

Rencana implementasi WhatsApp bot untuk Food Tracker dengan fungsionalitas yang sama seperti Telegram bot.

---

## 1. Analisis Gap: Telegram vs WhatsApp

### Perbedaan Fundamental

| Aspek | Telegram | WhatsApp |
|-------|----------|----------|
| **Koneksi** | Long polling (`run_polling()`) | Webhook (HTTP server wajib) |
| **Command menu** | Slash commands (`/start`, `/help`) | Tidak ada — harus parse manual dari teks |
| **Photo handling** | `update.message.photo[-1]` API | Media URL dari webhook payload, harus download manual |
| **Bot identity** | BotFather token | WhatsApp Business API / Cloud API |
| **Message format** | Plain text + Markdown | Plain text (limited formatting: bold `*text*`, italic `_text_`) |
| **Session** | Persistent per-chat | Stateless webhook per-message |
| **Rate limiting** | Generous | Strict (template messages, 24h window) |
| **Deployment** | Bisa lokal (polling) | Butuh public HTTPS URL (webhook) |

### Fitur yang Harus Di-port

| Fitur | Telegram Implementation | WhatsApp Adaptation |
|-------|------------------------|---------------------|
| `/start` | CommandHandler | Trigger: user kirim "start", "mulai", atau pesan pertama |
| `/help` | CommandHandler | Trigger: user kirim "help", "bantuan" |
| `/today` | CommandHandler | Trigger: user kirim "today", "hari ini" |
| `/history` | CommandHandler | Trigger: user kirim "history", "riwayat" |
| `/undo` | CommandHandler | Trigger: user kirim "undo", "hapus" |
| `/target <N>` | CommandHandler + args | Trigger: user kirim "target 2000" |
| Photo + caption | PHOTO filter + caption | Image message type + caption field |
| Text food input | TEXT filter | Default: teks yang bukan command keyword |
| Progress bar emoji | Direct send | Sama (emoji supported di WhatsApp) |

---

## 2. Pilihan Teknologi WhatsApp API

### Option A: WhatsApp Cloud API (Meta Official) — **Recommended**

```
Pros:
+ Official API dari Meta
+ Gratis untuk 1000 conversations/bulan
+ Reliable dan well-documented
+ Webhook-based (standard)
+ Support media download/upload

Cons:
- Butuh Meta Business account
- Butuh Facebook App setup
- Butuh public HTTPS URL untuk webhook
- Template messages untuk outbound (di luar 24h window)
```

**Library:** `httpx` atau `requests` untuk API calls (REST API langsung, tidak perlu SDK khusus)

### Option B: Twilio WhatsApp API

```
Pros:
+ Easier setup (sandbox mode untuk development)
+ Well-documented Python SDK
+ Handle webhook routing

Cons:
- Berbayar (per message)
- Extra abstraction layer
- Vendor lock-in
```

### Option C: Baileys (Unofficial, Node.js)

```
Cons:
- Unofficial, bisa di-ban oleh WhatsApp
- Node.js (beda ecosystem dari project ini)
- Tidak untuk production
```

**Keputusan: Option A (WhatsApp Cloud API)** — gratis, official, dan sesuai untuk production.

---

## 3. Architecture Refactoring

### Current Architecture (Telegram-only)

```
bot.py (Telegram handlers + business logic + formatting)
  ├── gemini_service.py
  ├── sheets_service.py
  ├── imagekit_service.py
  └── config.py
```

### Proposed Architecture (Multi-platform)

```
├── config.py                    # Shared config (+ WA env vars)
├── gemini_service.py            # Unchanged
├── sheets_service.py            # Unchanged
├── imagekit_service.py          # Unchanged
│
├── core/
│   ├── __init__.py
│   ├── messages.py              # Shared message templates (Indonesian)
│   ├── formatter.py             # format_nutrition_response, format_progress_bar, etc.
│   └── handlers.py              # Platform-agnostic business logic
│
├── telegram_bot.py              # Telegram-specific adapter (renamed from bot.py)
│
├── whatsapp_bot.py              # WhatsApp-specific adapter
│   ├── Flask/FastAPI webhook server
│   ├── Message routing (text commands, photos)
│   ├── WhatsApp Cloud API client
│   └── Media download handling
│
└── main.py                      # Entry point: run Telegram, WhatsApp, atau keduanya
```

### Detail Refactoring

#### 3a. Extract `core/messages.py` — Shared Message Templates

Pindahkan dari `bot.py`:
- `WELCOME_MESSAGE`
- `HELP_MESSAGE`
- Semua string template bahasa Indonesia

#### 3b. Extract `core/formatter.py` — Shared Formatting

Pindahkan dari `bot.py`:
- `format_nutrition_response(data)` → string
- `format_progress_bar(percentage, width)` → string
- `get_warning_message(status, percentage, remaining)` → string

#### 3c. Extract `core/handlers.py` — Platform-Agnostic Business Logic

Buat handler functions yang return data/string, tanpa dependency ke platform:

```python
# core/handlers.py

async def process_photo(user_id: int, photo_bytes: bytes, caption: str = "") -> dict:
    """Process food photo and return result dict.

    Returns:
        {
            "status_messages": ["📸 ...", "🔍 ...", "💾 ...", "✅ ..."],
            "result_message": "formatted nutrition response",
            "success": bool
        }
    """

async def process_text(user_id: int, text: str) -> dict:
    """Process food text description and return result dict."""

async def get_today_summary(user_id: int) -> str:
    """Get today's food summary as formatted string."""

async def get_history(user_id: int) -> str:
    """Get recent food history as formatted string."""

async def do_undo(user_id: int) -> str:
    """Undo last entry and return confirmation string."""

async def handle_target(user_id: int, arg: str = None) -> str:
    """Handle target command and return response string."""
```

#### 3d. Platform Adapters

**`telegram_bot.py`** — Thin wrapper:
- Maps Telegram Update objects → calls `core/handlers.py`
- Sends progressive status messages via Telegram API
- Handles Telegram-specific features (slash commands, file download)

**`whatsapp_bot.py`** — WhatsApp adapter:
- Flask/FastAPI webhook endpoint
- Maps WhatsApp webhook payload → calls `core/handlers.py`
- Sends messages via WhatsApp Cloud API
- Handles WhatsApp-specific features (command keyword parsing, media download)

---

## 4. WhatsApp Bot Implementation Detail

### 4a. Config Changes (`config.py`)

```python
# WhatsApp Cloud API
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")      # Webhook verification
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")      # API access token
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID") # Bot phone number ID
WHATSAPP_API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v21.0")
```

### 4b. WhatsApp Webhook Server (`whatsapp_bot.py`)

```python
# Framework: Flask (lightweight) atau FastAPI (async-native)
# Recommendation: FastAPI karena project sudah async-heavy

from fastapi import FastAPI, Request, Response

app = FastAPI()

@app.get("/webhook")
async def verify_webhook(hub_mode, hub_verify_token, hub_challenge):
    """WhatsApp webhook verification (GET request)."""
    if hub_verify_token == WHATSAPP_VERIFY_TOKEN:
        return int(hub_challenge)
    return Response(status_code=403)

@app.post("/webhook")
async def handle_webhook(request: Request):
    """Handle incoming WhatsApp messages (POST request)."""
    body = await request.json()
    # Parse message → route to handler → send response
    ...
    return {"status": "ok"}
```

### 4c. WhatsApp Message Router

```python
# Keyword-based command routing (karena WA tidak punya slash commands)

COMMAND_KEYWORDS = {
    "start": ["start", "mulai", "halo", "hi"],
    "help": ["help", "bantuan", "cara"],
    "today": ["today", "hari ini", "hari_ini"],
    "history": ["history", "riwayat", "histori"],
    "undo": ["undo", "hapus", "batal"],
    "target": ["target"],  # "target 2000" → parse angka setelahnya
}

def route_message(message_text: str) -> tuple[str, str]:
    """Route text message to appropriate command.

    Returns:
        (command_name, remaining_args) atau ("food_text", original_text)
    """
```

### 4d. WhatsApp Cloud API Client

```python
class WhatsAppClient:
    """Client for WhatsApp Cloud API."""

    BASE_URL = "https://graph.facebook.com/{version}/{phone_number_id}/messages"

    async def send_text(self, to: str, text: str):
        """Send text message to user."""

    async def send_reply(self, to: str, message_id: str, text: str):
        """Send reply to specific message."""

    async def download_media(self, media_id: str) -> bytes:
        """Download media (photo) from WhatsApp servers.

        Two-step process:
        1. GET media URL: /v21.0/{media_id}
        2. GET download: fetch the URL with auth header
        """

    async def mark_as_read(self, message_id: str):
        """Mark message as read (blue ticks)."""
```

### 4e. WhatsApp Webhook Payload Parsing

```python
def parse_webhook(body: dict) -> dict:
    """Parse WhatsApp webhook payload into normalized message.

    Returns:
        {
            "type": "text" | "image" | "unknown",
            "from": "628xxxx",          # Phone number (= user_id)
            "message_id": "wamid.xxx",
            "text": "nasi goreng 200g", # For text messages
            "caption": "250 gram",      # For image messages
            "media_id": "xxx",          # For image messages
            "timestamp": "1234567890"
        }
    """
```

### 4f. Progressive Status Messages

Di WhatsApp, progressive messages dikirim sebagai pesan terpisah (sama seperti Telegram):

```
User: [kirim foto nasi goreng]

Bot: 📸 Foto makanan diterima! Mengunduh gambar...
Bot: 🔍 Foto berhasil diunduh! Sedang menganalisis nutrisi makanan...
Bot: 💾 Analisis selesai! Menyimpan ke catatan...
Bot: ✅ Selesai!
Bot: [Hasil analisis nutrisi]
```

### 4g. User ID Strategy

| Platform | User ID |
|----------|---------|
| Telegram | `update.effective_user.id` (integer) |
| WhatsApp | Phone number `628xxxxxxxxx` (string) |

**Approach:** Prefix user ID di Google Sheets:
- Telegram: `tg_123456789`
- WhatsApp: `wa_628xxxxxxxxx`

Atau, simpan as-is karena Telegram IDs (angka) dan WhatsApp IDs (nomor telepon) sudah secara natural tidak overlap.

**Recommendation:** Simpan as-is — lebih simple, tidak perlu migration.

---

## 5. Deployment Considerations

### WhatsApp butuh HTTPS Webhook

| Option | Description | Cost |
|--------|-------------|------|
| **ngrok** | Tunnel lokal ke public URL | Free (dev only) |
| **Railway** | Cloud deployment | ~$5/mo |
| **Render** | Cloud deployment | Free tier available |
| **VPS + Caddy** | Self-hosted | ~$5/mo |

### Architecture: Satu Server, Dua Bot

```python
# main.py
import asyncio
import threading

def run_telegram():
    """Run Telegram bot (polling mode)."""
    telegram_bot.main()

def run_whatsapp():
    """Run WhatsApp webhook server (FastAPI/uvicorn)."""
    import uvicorn
    uvicorn.run(whatsapp_bot.app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    mode = os.getenv("BOT_MODE", "all")  # "telegram", "whatsapp", "all"

    if mode == "telegram":
        run_telegram()
    elif mode == "whatsapp":
        run_whatsapp()
    else:
        # Run both
        threading.Thread(target=run_whatsapp, daemon=True).start()
        run_telegram()
```

---

## 6. Implementation Phases

### Phase WA-1: Refactor Core Logic (Prerequisite)
**Goal:** Extract shared logic agar bisa dipakai Telegram dan WhatsApp.

Tasks:
1. Buat folder `core/`
2. Extract `core/messages.py` — semua message templates
3. Extract `core/formatter.py` — `format_nutrition_response`, `format_progress_bar`, `get_warning_message`
4. Extract `core/handlers.py` — platform-agnostic business logic
5. Refactor `bot.py` → `telegram_bot.py` — thin wrapper yang call core handlers
6. Verify Telegram bot masih berfungsi sama persis

### Phase WA-2: WhatsApp Foundation
**Goal:** WhatsApp bot bisa menerima dan membalas pesan teks.

Tasks:
1. Tambah WhatsApp env vars ke `config.py` dan `.env.example`
2. Buat `whatsapp_bot.py` dengan FastAPI webhook server
3. Implement webhook verification (`GET /webhook`)
4. Implement message receiving (`POST /webhook`)
5. Implement `WhatsAppClient.send_text()`
6. Implement keyword-based command routing
7. Implement `/start` dan `/help` equivalents
8. Tambah `fastapi` dan `uvicorn` ke `requirements.txt`

### Phase WA-3: Food Analysis via WhatsApp
**Goal:** Analisis makanan dari teks dan foto.

Tasks:
1. Implement text food analysis (kirim teks → analisis → response)
2. Implement `WhatsAppClient.download_media()` untuk foto
3. Implement photo food analysis (kirim foto → download → analisis → response)
4. Implement progressive status messages
5. Implement caption parsing (weight + food name hint)
6. Test dengan berbagai format teks dan foto

### Phase WA-4: Data Tracking via WhatsApp
**Goal:** Semua fitur tracking berfungsi di WhatsApp.

Tasks:
1. Implement "hari ini" / "today" command
2. Implement "riwayat" / "history" command
3. Implement "hapus" / "undo" command
4. Implement "target" command (set + view + date)
5. Implement calorie warnings setelah logging
6. Implement progress bar di semua responses
7. Verify data di Google Sheets konsisten antara Telegram dan WhatsApp

### Phase WA-5: Entry Point & Deployment
**Goal:** Bisa menjalankan kedua bot dari satu entry point.

Tasks:
1. Buat `main.py` — unified entry point
2. Support `BOT_MODE` env var (telegram/whatsapp/all)
3. Update documentation (`README.md`, `CLAUDE.md`)
4. Update `ROADMAP.md`
5. Setup guide untuk WhatsApp Business API

---

## 7. File Changes Summary

### New Files
| File | Description |
|------|-------------|
| `core/__init__.py` | Package init |
| `core/messages.py` | Shared message templates (Indonesian) |
| `core/formatter.py` | Shared formatting functions |
| `core/handlers.py` | Platform-agnostic business logic |
| `whatsapp_bot.py` | WhatsApp webhook server + adapter |
| `main.py` | Unified entry point |

### Modified Files
| File | Changes |
|------|---------|
| `bot.py` → `telegram_bot.py` | Refactor to thin wrapper calling core/ |
| `config.py` | Add WhatsApp env vars |
| `.env.example` | Add WhatsApp env vars |
| `requirements.txt` | Add `fastapi`, `uvicorn`, `httpx` |
| `ROADMAP.md` | Add WhatsApp phases |
| `CLAUDE.md` | Update architecture docs |

### Unchanged Files
| File | Reason |
|------|--------|
| `gemini_service.py` | Already platform-agnostic |
| `sheets_service.py` | Already platform-agnostic |
| `imagekit_service.py` | Already platform-agnostic |

---

## 8. Dependencies Baru

```
fastapi>=0.104.0       # Webhook server
uvicorn>=0.24.0        # ASGI server for FastAPI
httpx>=0.25.0          # Async HTTP client for WhatsApp Cloud API
```

---

## 9. Environment Variables Baru

```bash
# WhatsApp Cloud API
WHATSAPP_VERIFY_TOKEN=your_webhook_verify_token
WHATSAPP_ACCESS_TOKEN=your_cloud_api_access_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_API_VERSION=v21.0

# Bot mode
BOT_MODE=all  # "telegram", "whatsapp", "all"
```

---

## 10. WhatsApp Business API Setup Guide

### Prerequisites
1. Facebook Business account
2. Meta Developer account (developers.facebook.com)
3. Public HTTPS URL untuk webhook

### Setup Steps
1. Buat Facebook App di Meta for Developers
2. Tambahkan WhatsApp product ke app
3. Setup WhatsApp Business phone number (test number gratis tersedia)
4. Generate permanent access token
5. Configure webhook URL: `https://yourdomain.com/webhook`
6. Subscribe ke webhook events: `messages`
7. Set verify token (sama dengan `WHATSAPP_VERIFY_TOKEN`)

---

## 11. Risiko & Mitigasi

| Risk | Impact | Mitigation |
|------|--------|------------|
| WhatsApp rate limits | Messages delayed/rejected | Implement queue + retry logic |
| 24h messaging window | Can't send proactive messages | All responses within window (reactive only) |
| Media download latency | Slow photo analysis | Show progress messages, async processing |
| Phone number as user ID | Privacy concern | Don't expose in logs, hash if needed |
| Webhook downtime | Missed messages | Health check endpoint, auto-restart |
| Cloud API token expiration | Bot stops working | Use system user token (non-expiring) |

---

*Created: February 2026*
