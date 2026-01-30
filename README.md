# Food Tracker Bot

A Telegram bot that analyzes food photos and text descriptions to provide nutritional estimates using Google's Gemini AI.

## Features

- **Photo Analysis**: Send a food photo and get instant nutritional breakdown
- **Text Analysis**: Describe your food (e.g., "nasi goreng 1 piring") to get estimates
- **Nutritional Data**: Returns calories, protein, carbohydrates, and fat content
- **Indonesian Language**: Bot interface optimized for Indonesian users

## Tech Stack

- **Python 3.10+**
- **python-telegram-bot** - Telegram Bot API wrapper
- **Google Generative AI (Gemini 2.0 Flash)** - Food image and text analysis
- **python-dotenv** - Environment variable management

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
   ```
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

**Interaction:**
- Send a photo of your food to get nutritional analysis
- Send a text description (e.g., "ayam bakar setengah ekor") to get estimates

## Project Structure

```
food_tracker/
├── bot.py              # Main bot application and handlers
├── config.py           # Environment configuration
├── gemini_service.py   # Gemini AI integration
├── requirements.txt    # Python dependencies
├── .env.example        # Environment template
├── .gitignore          # Git ignore rules
└── README.md           # Documentation
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

- [ ] Daily calorie tracking and history
- [ ] User meal logging with database storage
- [ ] Daily/weekly nutrition reports
- [ ] Calorie goal setting and reminders
- [ ] Support for multiple languages
- [ ] Barcode scanning for packaged foods
- [ ] Integration with fitness apps
- [ ] Group chat support for family tracking

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
