# Telegram Calorie Tracker Bot

## Project Overview

Telegram bot untuk tracking kalori dengan fitur:
- **Input foto makanan** → AI mengenali dan estimasi nutrisi otomatis
- **Input text** → AI estimasi nutrisi dari deskripsi makanan
- **Data logging** → Simpan ke Google Sheets

## Tech Stack

| Component | Technology | Biaya |
|-----------|------------|-------|
| Bot Framework | Python + python-telegram-bot v21 | Free |
| Food Recognition | Google Gemini Vision API | Free (15 RPM, 1500 req/day) |
| Database | Google Sheets via gspread | Free |
| Hosting | Railway / Render | Free tier |

## Project Structure

```
calorie-tracker-bot/
├── bot.py              # Main bot logic
├── gemini_service.py   # Gemini API integration
├── sheets_service.py   # Google Sheets integration
├── config.py           # Configuration & env variables
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variables template
└── README.md           # Setup instructions
```

## Implementation Tasks

### Phase 1: Setup & Configuration

#### 1.1 Create `requirements.txt`
```
python-telegram-bot==21.0
google-generativeai==0.8.0
gspread==6.0.0
google-auth==2.27.0
python-dotenv==1.0.0
```

#### 1.2 Create `config.py`
- Load environment variables using python-dotenv
- Required env vars:
  - `TELEGRAM_BOT_TOKEN` - dari BotFather
  - `GEMINI_API_KEY` - dari Google AI Studio
  - `GOOGLE_SHEETS_ID` - ID spreadsheet
  - `GOOGLE_CREDENTIALS_JSON` - path ke service account JSON

#### 1.3 Create `.env.example`
```
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
GEMINI_API_KEY=your_gemini_api_key
GOOGLE_SHEETS_ID=your_spreadsheet_id
GOOGLE_CREDENTIALS_JSON=credentials.json
```

---

### Phase 2: Gemini Vision Integration

#### 2.1 Create `gemini_service.py`

**Functions to implement:**

```python
async def analyze_food_image(image_bytes: bytes) -> dict:
    """
    Analyze food from image using Gemini Vision.
    Returns: {name, calories, protein, carbs, fat, portion}
    """
    pass

async def analyze_food_text(food_description: str) -> dict:
    """
    Analyze food from text description.
    Returns: {name, calories, protein, carbs, fat, portion}
    """
    pass
```

**Prompt template untuk Gemini:**
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

### Phase 3: Google Sheets Integration

#### 3.1 Create `sheets_service.py`

**Functions to implement:**

```python
def get_sheet_client():
    """Initialize gspread client with service account."""
    pass

def append_food_entry(data: dict) -> bool:
    """
    Append food entry to spreadsheet.
    Columns: Tanggal, Waktu, Nama Makanan, Kalori, Protein, Karbo, Lemak, Porsi
    """
    pass

def get_daily_total(date: str) -> dict:
    """Get total calories for a specific date."""
    pass
```

**Google Sheets Structure:**

| Column | Description |
|--------|-------------|
| A - Tanggal | Format: YYYY-MM-DD |
| B - Waktu | Format: HH:MM |
| C - Nama Makanan | String |
| D - Kalori | Integer (kkal) |
| E - Protein | Float (gram) |
| F - Karbo | Float (gram) |
| G - Lemak | Float (gram) |
| H - Porsi | String |

---

### Phase 4: Telegram Bot

#### 4.1 Create `bot.py`

**Commands:**
- `/start` - Welcome message dengan instruksi penggunaan
- `/help` - Cara menggunakan bot
- `/today` - (Optional) Ringkasan kalori hari ini

**Handlers:**

```python
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    1. Download photo dari Telegram
    2. Kirim ke Gemini untuk analisis
    3. Simpan hasil ke Google Sheets
    4. Reply dengan ringkasan nutrisi
    """
    pass

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    1. Ambil text dari user
    2. Kirim ke Gemini untuk analisis
    3. Simpan hasil ke Google Sheets
    4. Reply dengan ringkasan nutrisi
    """
    pass
```

**Response format ke user:**
```
✅ Tercatat!

🍽️ Nasi Goreng
📊 Kalori: 450 kkal
🥩 Protein: 12g
🍞 Karbo: 55g
🧈 Lemak: 18g
📏 Porsi: 1 piring

📈 Total hari ini: 1,250 kkal
```

---

## Setup Instructions

### 1. Buat Telegram Bot
1. Buka Telegram, cari @BotFather
2. Kirim `/newbot`
3. Ikuti instruksi, simpan token yang diberikan

### 2. Dapatkan Gemini API Key
1. Buka https://aistudio.google.com/
2. Klik "Get API Key"
3. Create new API key, simpan

### 3. Setup Google Sheets
1. Buka Google Cloud Console (https://console.cloud.google.com/)
2. Buat project baru atau pilih existing
3. Enable Google Sheets API
4. Buat Service Account:
   - IAM & Admin → Service Accounts → Create
   - Beri nama, klik Create
   - Download JSON key
5. Buat spreadsheet baru di Google Sheets
6. Share spreadsheet ke email service account (dari JSON, field `client_email`)
7. Copy spreadsheet ID dari URL

### 4. Run Locally
```bash
# Clone/navigate to project
cd calorie-tracker-bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# atau: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Copy .env.example to .env and fill values
cp .env.example .env

# Run bot
python bot.py
```

### 5. Deploy ke Railway (Opsional)
1. Push code ke GitHub
2. Buka https://railway.app/
3. New Project → Deploy from GitHub
4. Pilih repo
5. Add environment variables di Railway dashboard
6. Deploy

---

## Testing Checklist

- [ ] Bot responds to `/start` command
- [ ] Bot responds to `/help` command
- [ ] Send food photo → receives nutrition estimate
- [ ] Send food text → receives nutrition estimate
- [ ] Data appears in Google Sheets with correct format
- [ ] Non-food photo → graceful error message
- [ ] Invalid text → graceful error message

---

## Error Handling

Handle these edge cases:
1. **Gemini API error** → Reply: "Maaf, terjadi kesalahan. Coba lagi nanti."
2. **Non-food image** → Reply: "Tidak dapat mengenali makanan dari foto."
3. **Google Sheets error** → Log to console, still reply to user
4. **Rate limit exceeded** → Reply: "Bot sedang sibuk, coba lagi dalam beberapa menit."

---

## Future Enhancements (Post-MVP)

- `/summary` - Daily/weekly calorie summary
- `/target 2000` - Set daily calorie target
- `/undo` - Delete last entry
- Inline keyboard untuk koreksi estimasi AI
- Multi-language support
