# Food Tracker Bot 🍽️

A Telegram bot that analyzes food photos and text descriptions to provide nutritional estimates using Google's Gemini AI. Interface fully localized in Indonesian (Bahasa Indonesia).

## ✅ Current Capabilities

### Core Features (Implemented)

| Feature | Status | Description |
|---------|--------|-------------|
| **Photo Analysis** | ✅ Done | Send a food photo and get instant nutritional breakdown |
| **Text Analysis** | ✅ Done | Describe your food (e.g., "nasi goreng 1 piring") to get estimates |
| **Weight-Based Calculation** | ✅ Done | Specify food weight in grams for precise nutrition estimates |
| **Multi-Food Detection** | ✅ Done | Automatically detects and analyzes multiple food items in a single image |
| **Indonesian Language** | ✅ Done | Bot interface fully optimized for Indonesian users |

### Supported Input Formats

**Photo Input:**
- Send food photo without caption → AI estimates portion and nutrition
- Send food photo with weight caption → Precise nutrition calculation
  - Example: `250 gram`, `250g`, `0.5 kg`

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
| Config | python-dotenv | Environment variable management |

## Prerequisites

- Python 3.10 or higher
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Google Gemini API Key (from [Google AI Studio](https://aistudio.google.com/apikey))

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

**Interaction Examples:**

1. **Photo Analysis (with weight):**
   - Send a food photo with caption `250 gram` or `0.5 kg`
   - Bot calculates nutrition based on the specified weight
   - Displays: `⚖️ Berat: 250 gram`

2. **Photo Analysis (estimation):**
   - Send a food photo without caption
   - Bot estimates portion size and nutrition
   - Displays: `📏 Porsi: ~1 piring`

3. **Text Analysis:**
   - With weight: `"nasi goreng 200 gram"` or `"ayam bakar 150g"`
   - Without weight: `"nasi goreng 1 piring"` or `"ayam bakar setengah ekor"`

## Project Structure

```
food_tracker/
├── bot.py              # Main bot application and handlers
├── config.py           # Environment configuration
├── gemini_service.py   # Gemini AI integration
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
│  • /start, /help commands                                       │
│  • Photo & text message handlers                                │
│  • Weight parsing from caption/text                             │
│  • Emoji-rich Indonesian response formatting                    │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                     gemini_service.py                           │
│  • analyze_food_image(image_bytes, weight_grams)                │
│  • analyze_food_text(description, weight_grams)                 │
│  • parse_weight_from_text(text)                                 │
│  • Response normalization: {foods: [...], total: {...}}         │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Google Gemini 2.0 Flash API                   │
│  • Vision-based food recognition                                 │
│  • Nutritional estimation                                        │
│  • Indonesian language understanding                             │
└─────────────────────────────────────────────────────────────────┘
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
- ✅ Completed MVP features
- 🔜 Planned features (Google Sheets, goal tracking, etc.)
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
