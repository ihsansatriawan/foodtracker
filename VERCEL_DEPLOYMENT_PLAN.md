# Plan Deployment Telegram Bot ke Vercel

## Ringkasan Situasi Saat Ini

| Aspek | Status Saat Ini | Status yang Dibutuhkan |
|-------|-----------------|------------------------|
| Mode Bot | Polling (`run_polling()`) | Webhook |
| Runtime | Python 3.10+ | Python 3.12 (Vercel) |
| Arsitektur | Long-running process | Serverless function |
| Dependencies | python-telegram-bot, google-generativeai | Sama + tambahan minor |

## Mengapa Perlu Perubahan?

**Masalah Utama:** Bot saat ini menggunakan **polling mode** yang tidak kompatibel dengan Vercel:
- Polling membutuhkan proses yang berjalan terus-menerus (infinite loop)
- Vercel Functions memiliki batas waktu eksekusi 10 detik (free tier)
- Polling akan timeout dan gagal di Vercel

**Solusi:** Mengubah ke **webhook mode**:
- Telegram mengirim update ke URL endpoint kita
- Vercel function hanya aktif saat ada request masuk
- Setiap request diproses dalam waktu singkat (<10 detik)

---

## Langkah-Langkah Deployment

### Step 1: Buat Struktur Folder untuk Vercel

```
foodtracker/
├── api/
│   └── webhook.py        # <-- Handler utama untuk Vercel
├── bot.py                # (tetap untuk local development)
├── config.py
├── gemini_service.py
├── requirements.txt
├── vercel.json           # <-- Konfigurasi Vercel
└── .env.example
```

### Step 2: Buat File `api/webhook.py`

File ini akan menjadi serverless function yang menerima webhook dari Telegram.

```python
"""
Vercel Serverless Function untuk Telegram Bot Webhook
"""
import json
import logging
from http.server import BaseHTTPRequestHandler
from telegram import Update, Bot
from telegram.ext import Application
import asyncio

from config import TELEGRAM_BOT_TOKEN, GEMINI_API_KEY
from gemini_service import analyze_food_image, analyze_food_text

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize bot
bot = Bot(token=TELEGRAM_BOT_TOKEN)

async def process_update(update_data: dict):
    """Process incoming Telegram update"""
    update = Update.de_json(update_data, bot)

    if update.message:
        chat_id = update.message.chat_id

        # Handle /start command
        if update.message.text and update.message.text.startswith('/start'):
            await bot.send_message(
                chat_id=chat_id,
                text="👋 Halo! Saya FoodTracker Bot...",  # Pesan welcome
                parse_mode='Markdown'
            )
            return

        # Handle photo
        if update.message.photo:
            await bot.send_message(chat_id=chat_id, text="🔍 Menganalisis foto makanan...")
            photo = update.message.photo[-1]
            file = await bot.get_file(photo.file_id)
            image_bytes = await file.download_as_bytearray()

            result = await analyze_food_image(bytes(image_bytes))
            await bot.send_message(chat_id=chat_id, text=result, parse_mode='Markdown')
            return

        # Handle text
        if update.message.text and not update.message.text.startswith('/'):
            await bot.send_message(chat_id=chat_id, text="🔍 Menganalisis...")
            result = await analyze_food_text(update.message.text)
            await bot.send_message(chat_id=chat_id, text=result, parse_mode='Markdown')
            return

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Handle incoming webhook POST request from Telegram"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            update_data = json.loads(body.decode('utf-8'))

            # Process the update
            asyncio.run(process_update(update_data))

            # Return success
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'ok': True}).encode())

        except Exception as e:
            logger.error(f"Error processing update: {e}")
            self.send_response(500)
            self.end_headers()

    def do_GET(self):
        """Health check endpoint"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'Bot is running'}).encode())
```

### Step 3: Buat File `vercel.json`

```json
{
  "version": 2,
  "builds": [
    {
      "src": "api/webhook.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/api/webhook",
      "dest": "/api/webhook.py"
    }
  ]
}
```

### Step 4: Update `requirements.txt`

```
python-telegram-bot==21.0
google-generativeai==0.8.0
python-dotenv==1.0.0
```

(Tidak perlu perubahan, sudah kompatibel)

### Step 5: Deploy ke Vercel

```bash
# 1. Install Vercel CLI
npm install -g vercel

# 2. Login ke Vercel
vercel login

# 3. Deploy
vercel

# 4. Set environment variables di Vercel Dashboard
#    - TELEGRAM_BOT_TOKEN
#    - GEMINI_API_KEY
```

### Step 6: Set Webhook di Telegram

Setelah deploy berhasil, daftarkan webhook URL ke Telegram:

```bash
# Ganti YOUR_VERCEL_URL dengan URL deployment Anda
curl -X POST "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://YOUR_VERCEL_URL.vercel.app/api/webhook"}'
```

**Response yang diharapkan:**
```json
{"ok": true, "result": true, "description": "Webhook was set"}
```

---

## Arsitektur Setelah Deploy

```
┌─────────────────┐     POST      ┌──────────────────┐
│  Telegram API   │ ─────────────▶│  Vercel Function │
│  (sends update) │               │  /api/webhook    │
└─────────────────┘               └────────┬─────────┘
                                           │
                                           ▼
                                  ┌──────────────────┐
                                  │  gemini_service  │
                                  │  (analyze food)  │
                                  └────────┬─────────┘
                                           │
                                           ▼
                                  ┌──────────────────┐
                                  │   Gemini API     │
                                  │   (AI response)  │
                                  └──────────────────┘
```

---

## Environment Variables di Vercel

Masuk ke **Vercel Dashboard > Project Settings > Environment Variables** dan tambahkan:

| Variable | Value | Environment |
|----------|-------|-------------|
| `TELEGRAM_BOT_TOKEN` | `your_bot_token_here` | Production, Preview, Development |
| `GEMINI_API_KEY` | `your_gemini_key_here` | Production, Preview, Development |

---

## Checklist Deployment

- [ ] Buat folder `api/` dan file `webhook.py`
- [ ] Buat file `vercel.json`
- [ ] Update `gemini_service.py` jika ada yang perlu disesuaikan
- [ ] Test locally menggunakan `vercel dev`
- [ ] Deploy ke Vercel dengan `vercel --prod`
- [ ] Set environment variables di Vercel Dashboard
- [ ] Register webhook URL ke Telegram API
- [ ] Test bot dengan mengirim foto makanan

---

## Troubleshooting

### Bot tidak merespon setelah deploy
1. Cek webhook sudah terdaftar:
   ```bash
   curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
   ```
2. Cek logs di Vercel Dashboard > Deployments > Functions logs

### Error "Timeout"
- Vercel free tier memiliki batas 10 detik
- Pastikan Gemini API response time < 10 detik
- Pertimbangkan upgrade ke Vercel Pro jika perlu

### Error "Module not found"
- Pastikan semua dependencies ada di `requirements.txt`
- Pastikan path import benar (relative vs absolute)

---

## Alternatif: Menggunakan Flask

Jika mau menggunakan Flask (lebih familiar bagi banyak developer):

```python
# api/webhook.py dengan Flask
from flask import Flask, request, jsonify
import asyncio
from telegram import Bot, Update

app = Flask(__name__)
bot = Bot(token=TELEGRAM_BOT_TOKEN)

@app.route('/api/webhook', methods=['POST'])
def webhook():
    update_data = request.get_json()
    asyncio.run(process_update(update_data))
    return jsonify({'ok': True})

# Untuk Vercel, export app
app = app
```

Tambahkan `flask` ke `requirements.txt` jika menggunakan opsi ini.

---

## Timeline Estimasi

| Task | Estimasi |
|------|----------|
| Setup struktur folder & files | 30 menit |
| Implementasi webhook handler | 1-2 jam |
| Testing lokal | 30 menit |
| Deploy & konfigurasi | 30 menit |
| Testing production | 30 menit |
| **Total** | **3-4 jam** |

---

## Referensi

- [Vercel Python Runtime](https://vercel.com/docs/functions/runtimes/python)
- [python-telegram-bot Webhook](https://docs.python-telegram-bot.org/en/stable/telegram.ext.application.html#telegram.ext.Application.run_webhook)
- [Telegram Bot API - setWebhook](https://core.telegram.org/bots/api#setwebhook)
