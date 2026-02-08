# Food Tracker Bot 🍽️

A Telegram bot that analyzes food photos and text descriptions to provide nutritional estimates using Google's Gemini AI. Interface fully localized in Indonesian (Bahasa Indonesia).

## ✅ Current Capabilities

### Core Features (Implemented)

| Feature | Status | Description |
|---------|--------|-------------|
| **Photo Analysis** | ✅ Done | Send a food photo and get instant nutritional breakdown (supports food name hint in caption) |
| **Text Analysis** | ✅ Done | Describe your food (e.g., "nasi goreng 1 piring") to get estimates |
| **Weight-Based Calculation** | ✅ Done | Specify food weight in grams for precise nutrition estimates |
| **Multi-Food Detection** | ✅ Done | Automatically detects and analyzes multiple food items in a single image |
| **Indonesian Language** | ✅ Done | Bot interface fully optimized for Indonesian users |
| **Food Logging** | ✅ Done | Auto-save entries to Google Sheets with timestamp |
| **Image Storage** | ✅ Done | Food photos stored permanently on ImageKit for validation |
| **Daily Summary** | ✅ Done | `/today` command shows today's calorie totals |
| **History** | ✅ Done | `/history` command shows recent food entries |
| **Undo** | ✅ Done | `/undo` command deletes last entry |
| **Goal Tracking** | ✅ Done | `/target` command to set daily calorie goals |
| **Progress Bar** | ✅ Done | Visual emoji progress bar with color-coded status |
| **Calorie Warnings** | ✅ Done | Alerts when approaching or exceeding target |
| **Progress Updates** | ✅ Done | Real-time status messages during photo/text processing |

### Supported Input Formats

**Photo Input:**
- Send food photo without caption → AI estimates portion and nutrition
- Send food photo with weight caption → Precise nutrition calculation
  - Example: `250 gram`, `250g`, `0.5 kg`
- Send food photo with food name caption → AI uses name as hint for identification
  - Example: `nasi goreng`, `ayam bakar`
- Send food photo with food name + weight → Both name hint and precise calculation
  - Example: `nasi goreng 250g`, `ayam bakar 150 gram`

**Text Input:**
- With weight: `"nasi goreng 200 gram"`, `"ayam bakar 150g"`
- Without weight: `"nasi goreng 1 piring"`, `"ayam bakar setengah ekor"`

**Nutritional Data Returned:**
- 📊 Calories (kkal)
- 🥩 Protein (gram)
- 🍞 Carbohydrates (gram)
- 🧈 Fat (gram)
- ⚖️ Weight / 📏 Portion

## Tech Stack

| Component | Technology | Notes |
|-----------|------------|-------|
| Runtime | Python 3.10+ | |
| Bot Framework | python-telegram-bot v21 | Async Telegram API wrapper |
| AI Model | Google Gemini 2.0 Flash | Vision & text analysis |
| Data Storage | Google Sheets | Food logging via gspread |
| Image Storage | ImageKit | Permanent image hosting for validation |
| Config | python-dotenv | Environment variable management |

## Prerequisites

- Python 3.10 or higher
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Google Gemini API Key (from [Google AI Studio](https://aistudio.google.com/apikey))
- Google Sheets API credentials (optional, for food logging)
  - Create a Service Account in [Google Cloud Console](https://console.cloud.google.com/)
  - Enable Google Sheets API
  - Download `credentials.json`
  - Share your spreadsheet with the service account email
- ImageKit account (optional, for image storage)
  - Sign up at [ImageKit.io](https://imagekit.io/)
  - Get Private Key and URL Endpoint from dashboard

## Installation

1. **Clone the repository**
   ```bash
   git clone git@github.com:ihsansatriawan/foodtracker.git
   cd foodtracker
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add your credentials:
   ```env
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   GEMINI_API_KEY=your_gemini_api_key

   # Optional: Google Sheets for food logging
   GOOGLE_SHEETS_ID=your_spreadsheet_id
   GOOGLE_CREDENTIALS_FILE=credentials.json

   # Optional: ImageKit for image storage
   IMAGEKIT_PRIVATE_KEY=private_xxxxx
   IMAGEKIT_URL_ENDPOINT=https://ik.imagekit.io/your_id
   ```

## Usage

**Start the bot:**
```bash
python bot.py
```

**Bot Commands:**
| Command | Description |
|---------|-------------|
| `/start` | Welcome message and usage instructions |
| `/help` | Detailed usage guide |
| `/today` | Show today's food log and calorie summary with progress |
| `/history` | Show last 10 food entries |
| `/undo` | Delete the last logged entry |
| `/target` | View current calorie target and progress |
| `/target <kkal>` | Set daily calorie target (500-10000 kkal) |
| `/target <date>` | View progress for a specific date (e.g., 01/02/2024) |

**Interaction Examples:**

1. **Photo Analysis (with weight):**
   - Send a food photo with caption `250 gram` or `0.5 kg`
   - Bot calculates nutrition based on the specified weight
   - Displays: `⚖️ Berat: 250 gram`

2. **Photo Analysis (with food name):**
   - Send a food photo with caption `nasi goreng` or `nasi goreng 250g`
   - Bot uses the food name as a hint for more accurate identification
   - Progress: `📸 Foto nasi goreng (250 gram) diterima!` → `🔍 Menganalisis...` → `💾 Menyimpan...` → `✅ Selesai!`

3. **Photo Analysis (estimation):**
   - Send a food photo without caption
   - Bot estimates portion size and nutrition
   - Displays: `📏 Porsi: ~1 piring`

4. **Text Analysis:**
   - With weight: `"nasi goreng 200 gram"` or `"ayam bakar 150g"`
   - Without weight: `"nasi goreng 1 piring"` or `"ayam bakar setengah ekor"`
   - Progress: `✍️ Menerima pesanan "nasi goreng"!` → `💾 Menyimpan...` → `✅ Selesai!`

## Project Structure

```
food_tracker/
├── bot.py              # Main bot application and handlers
├── config.py           # Environment configuration
├── gemini_service.py   # Gemini AI integration
├── sheets_service.py   # Google Sheets integration (food logging)
├── imagekit_service.py # ImageKit integration (image storage)
├── requirements.txt    # Python dependencies
├── .env.example        # Environment template
├── .gitignore          # Git ignore rules
├── CLAUDE.md           # AI assistant guidelines
├── README.md           # This file
└── ROADMAP.md          # Development roadmap
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Telegram User                            │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                         bot.py                                  │
│  • /start, /help, /today, /history, /undo, /target commands     │
│  • Photo & text message handlers                                │
│  • Progressive status updates via message editing               │
│  • Weight & food name parsing from caption/text                  │
│  • Goal tracking with progress bar & calorie warnings           │
└───────────┬─────────────────────┬─────────────────────┬─────────┘
            │                     │                     │
            ▼                     ▼                     ▼
┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
│ gemini_service.py │ │ sheets_service.py │ │imagekit_service.py│
│ • analyze_image() │ │ • log_food_entry()│ │ • upload_image()  │
│ • analyze_text()  │ │ • get_today()     │ │ • Permanent URLs  │
│ • parse_weight()  │ │ • calorie_target()│ │                   │
└─────────┬─────────┘ └─────────┬─────────┘ └─────────┬─────────┘
          │                     │                     │
          ▼                     ▼                     ▼
┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
│  Gemini 2.0 Flash │ │  Google Sheets    │ │     ImageKit      │
│  • Vision AI      │ │  • Food logging   │ │  • Image storage  │
│  • Nutrition est. │ │  • User settings  │ │  • CDN delivery   │
└───────────────────┘ └───────────────────┘ └───────────────────┘
```

## Development

**Running in development:**
```bash
# Activate virtual environment
source venv/bin/activate

# Run the bot
python bot.py
```

**Code style:**
- Follow PEP 8 guidelines
- Use type hints where applicable
- Keep functions focused and documented

## Roadmap

See [ROADMAP.md](ROADMAP.md) for the full development roadmap including:
- ✅ Completed: MVP features, Data persistence, Goal tracking, Progressive status updates
- 🔜 Planned: Enhanced analysis, User experience improvements
- 🔧 Technical improvements

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [Google Generative AI](https://ai.google.dev/)
- [ImageKit](https://imagekit.io/) - Image storage and CDN
