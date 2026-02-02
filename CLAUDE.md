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
cp .env.example .env  # Then add TELEGRAM_BOT_TOKEN and GEMINI_API_KEY

# Run the bot
python bot.py
```

No automated tests exist. Manual testing involves sending food photos/text to the Telegram bot.

## Architecture

Five-file modular design:

- **bot.py** - Telegram bot entry point using python-telegram-bot. Handles `/start`, `/help`, `/today`, `/history`, `/undo` commands and photo/text message handlers. Formats nutrition responses with emoji-rich Indonesian UI. Auto-logs to Google Sheets after successful analysis.

- **config.py** - Loads environment variables via python-dotenv:
  - `TELEGRAM_BOT_TOKEN`, `GEMINI_API_KEY` (required)
  - `GOOGLE_SHEETS_ID`, `GOOGLE_CREDENTIALS_FILE` (optional, for food logging)
  - `IMAGEKIT_PRIVATE_KEY`, `IMAGEKIT_URL_ENDPOINT` (optional, for image storage)

- **gemini_service.py** - Gemini AI integration with two analysis functions:
  - `analyze_food_image(image_bytes, weight_grams=None)` - Vision-based food analysis
  - `analyze_food_text(food_description, weight_grams=None)` - Text-based food analysis
  - `parse_weight_from_text(text)` - Extracts weight in grams from user input (supports "250g", "0.5 kg", etc.)
  - Uses `PROMPT_TEMPLATE` for estimation mode and `PROMPT_WITH_WEIGHT` for precise weight-based calculations

- **sheets_service.py** - Google Sheets integration for food logging:
  - `log_food_entry()` / `log_multiple_foods()` - Save entries with timestamp
  - `get_today_entries()` / `get_today_totals()` - Daily summary
  - `get_recent_entries()` - Paginated history
  - `delete_last_entry()` - Undo support
  - Schema: Tanggal, Waktu, User ID, Nama Makanan, Kalori, Protein, Karbo, Lemak, Porsi/Berat, Image URL

- **imagekit_service.py** - ImageKit integration for permanent image storage:
  - `upload_food_image(image_bytes, user_id, food_name)` - Upload with auto-naming
  - Returns permanent URL stored in Google Sheets for manual validation

**Data Flow:** User sends photo/text → Bot downloads/captures → Weight parsed from caption/message → Gemini API analyzes with appropriate prompt → JSON response normalized → Emoji-rich nutrition breakdown returned → Auto-logged to Google Sheets (with ImageKit URL if photo)

**Response Format:** All Gemini responses are normalized to `{foods: [...], total: {...}}` structure for consistent handling of single and multi-food detection.

## Tech Stack

- Python 3.10+
- python-telegram-bot 21.0
- google-generativeai 0.8.0 (Gemini 2.0 Flash model)
- gspread + google-auth (Google Sheets integration)
- imagekitio (ImageKit image storage)
- python-dotenv

## Documentation

- **ROADMAP.md** - Development roadmap with completed and planned features
  - Update when implementing new features (mark as ✅ completed)
  - Update when adding new planned features
  - Keep priority levels current

- **docs/WEIGHT_FEEDBACK_LOOP_PLAN.md** - Implementation plan for improving gram accuracy
  - 4-phase plan: Feedback UI → Schema Extension → Learning System → Analytics
  - Target: 20-30% improvement in weight estimation accuracy
