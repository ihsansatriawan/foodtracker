# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Telegram bot that analyzes food photos and text descriptions to provide nutritional estimates using Google's Gemini AI. The bot interface is fully localized in Indonesian.

## Commands

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Then add required API keys

# Run the bot
python bot.py
```

No automated tests exist. Manual testing involves sending food photos/text to the Telegram bot.

## Architecture

Five-file modular design:

- **bot.py** - Telegram bot entry point using python-telegram-bot. Handles commands and message handlers. Features:
  - `/start` - Welcome message with usage overview
  - `/help` - Detailed usage guide with examples
  - `/today` - Daily food log and calorie summary with progress bar (if target set)
  - `/history` - Last 10 food entries grouped by date
  - `/undo` - Delete the most recent food entry
  - `/target <kkal>` - Set daily calorie target (500-10000 kkal range)
  - `/target <date>` - View progress for a specific date (supports DD/MM/YYYY, YYYY-MM-DD)
  - Photo handler with caption weight and food name hint support
  - Text handler with inline weight parsing
  - Calorie warning system - alerts at 80%, 90%, and 100%+ of target
  - Slash command menu via `set_my_commands()` - commands appear when user types "/"

- **config.py** - Loads environment variables via python-dotenv:
  - `TELEGRAM_BOT_TOKEN` - Telegram Bot API token
  - `GEMINI_API_KEY` - Google Gemini API key
  - `GOOGLE_SHEETS_CREDENTIALS` - Service account JSON for Sheets
  - `GOOGLE_SHEETS_ID` - Target spreadsheet ID
  - `IMAGEKIT_*` - ImageKit credentials for image storage

- **gemini_service.py** - Gemini AI integration:
  - `analyze_food_image(image_bytes, weight_grams=None, food_name=None)` - Vision-based food analysis with optional food name hint from caption
  - `analyze_food_text(food_description, weight_grams=None)` - Text-based food analysis
  - `parse_weight_from_text(text)` - Extracts weight in grams from user input (supports "250g", "0.5 kg", etc.)
  - Uses `PROMPT_TEMPLATE` for estimation, `PROMPT_WITH_WEIGHT` for weight-based, `PROMPT_WITH_FOOD_HINT` for caption food name, and `PROMPT_WITH_WEIGHT_AND_FOOD_HINT` for both

- **sheets_service.py** - Google Sheets integration for data persistence:
  - `log_food_entry()` / `log_multiple_foods()` - Save food entries with timestamp
  - `get_today_entries()` / `get_today_totals()` - Daily summary
  - `get_entries_by_date()` / `get_totals_by_date()` - Query entries by specific date
  - `get_recent_entries()` - Paginated history
  - `delete_last_entry()` - Undo support
  - `is_sheets_configured()` - Check if Sheets is set up
  - `set_calorie_target()` / `get_calorie_target()` - User calorie target management
  - `get_daily_progress(user_id, date_str=None)` - Returns target progress with status (safe/warning/approaching/over)

- **imagekit_service.py** - ImageKit integration for permanent image storage:
  - `upload_food_image()` - Upload photos with user/food metadata
  - `is_imagekit_configured()` - Check if ImageKit is set up
  - Generates permanent URLs stored in Google Sheets for manual validation

**Data Flow:** User sends photo/text → Bot downloads/captures → Weight and food name parsed from caption/message → Gemini API analyzes with appropriate prompt (food name hint forwarded for photos) → JSON response normalized → Food logged to Google Sheets (with image URL if photo) → Emoji-rich nutrition breakdown returned → Calorie warning shown if target exceeded

**Response Format:** All Gemini responses are normalized to `{foods: [...], total: {...}}` structure for consistent handling of single and multi-food detection.

**Google Sheets Structure:**
- "Food Log" worksheet - Stores food entries with timestamp, nutrition data, and image URLs
- "User Settings" worksheet - Stores user calorie targets (User ID, Kalori Target, Created At, Updated At)

## Tech Stack

- Python 3.10+
- python-telegram-bot 21.0
- google-generativeai 0.8.0 (Gemini 2.0 Flash model)
- gspread + google-auth (Google Sheets API)
- imagekitio (ImageKit SDK)
- python-dotenv

## Documentation

- **ROADMAP.md** - Development roadmap with completed and planned features
  - Update when implementing new features (mark as completed)
  - Update when adding new planned features
  - Keep priority levels current
