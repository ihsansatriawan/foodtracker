# MVP Scope: Telegram Calorie Tracker Bot

## Summary
Build a working Telegram bot with Gemini Vision integration for food analysis. Skip Google Sheets for now - bot will analyze and reply but not persist data.

## Files to Create

| File | Purpose |
|------|---------|
| `requirements.txt` | Python dependencies |
| `config.py` | Environment variables loader |
| `.env.example` | Template for credentials |
| `gemini_service.py` | Gemini API integration |
| `bot.py` | Main Telegram bot |

---

## Implementation Steps

### Phase 1: Setup & Configuration

#### Step 1: Create `requirements.txt`
```
python-telegram-bot==21.0
google-generativeai==0.8.0
python-dotenv==1.0.0
```

#### Step 2: Create `config.py`
- Load env vars via python-dotenv
- Export: `TELEGRAM_BOT_TOKEN`, `GEMINI_API_KEY`

#### Step 3: Create `.env.example`
```
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
GEMINI_API_KEY=your_gemini_api_key
```

---

### Phase 2: Gemini Vision Integration

#### Step 4: Create `gemini_service.py`

Two async functions:

**`analyze_food_image(image_bytes: bytes) -> dict`**
- Send image to Gemini Vision with Indonesian prompt
- Return: `{name, calories, protein, carbs, fat, portion}` or `{error: "..."}`

**`analyze_food_text(food_description: str) -> dict`**
- Send text to Gemini with Indonesian prompt
- Return: `{name, calories, protein, carbs, fat, portion}` or `{error: "..."}`

**Prompt template (Indonesian):**
```
Kamu adalah ahli nutrisi Indonesia. Analisis makanan berikut dan berikan estimasi nutrisi.

Berikan response dalam format JSON ONLY (tanpa markdown):
{
  "name": "nama makanan dalam Bahasa Indonesia",
  "calories": angka dalam kkal,
  "protein": angka dalam gram,
  "carbs": angka dalam gram,
  "fat": angka dalam gram,
  "portion": "deskripsi porsi, misal: 1 piring, 1 mangkok"
}

Jika bukan makanan/minuman, return:
{"error": "Tidak dapat mengenali makanan"}
```

---

### Phase 4: Telegram Bot (without Sheets)

#### Step 5: Create `bot.py`

**Commands:**
- `/start` - Welcome message with usage instructions
- `/help` - How to use the bot

**Handlers:**

**`handle_photo(update, context)`**
1. Download photo from Telegram
2. Send to Gemini for analysis
3. Reply with nutrition info (no Sheets saving)

**`handle_text(update, context)`**
1. Get text from user
2. Send to Gemini for analysis
3. Reply with nutrition info (no Sheets saving)

**Response format (Indonesian):**
```
✅ Hasil Analisis!

🍽️ Nasi Goreng
📊 Kalori: 450 kkal
🥩 Protein: 12g
🍞 Karbo: 55g
🧈 Lemak: 18g
📏 Porsi: 1 piring
```

**Error handling:**
- Gemini API error → "Maaf, terjadi kesalahan. Coba lagi nanti."
- Non-food image → "Tidak dapat mengenali makanan dari foto."
- Rate limit → "Bot sedang sibuk, coba lagi dalam beberapa menit."

---

## Scope

| Included | Excluded |
|----------|----------|
| Project setup | Google Sheets integration (Phase 3) |
| Gemini Vision integration | `/today` command |
| Telegram bot | Data persistence |
| Photo & text analysis | |
| `/start` & `/help` commands | |

---

## Verification

1. **Set up credentials:**
   - Get Telegram bot token from @BotFather
   - Get Gemini API key from https://aistudio.google.com/

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Fill in your credentials
   ```

3. **Run the bot:**
   ```bash
   pip install -r requirements.txt
   python bot.py
   ```

4. **Test in Telegram:**
   - Send `/start` → should receive welcome message
   - Send `/help` → should receive usage instructions
   - Send food photo → should receive nutrition estimate
   - Send food text (e.g., "nasi goreng 1 piring") → should receive nutrition estimate
   - Send non-food photo → should receive error message
