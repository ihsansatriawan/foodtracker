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

Six-file modular design:

- **bot.py** - Telegram bot entry point using python-telegram-bot. Handles commands and message handlers. Features:
  - `/start` - Welcome message with usage overview
  - `/help` - Detailed usage guide with examples
  - `/today` - Daily food log and calorie summary
  - `/history` - Last 10 food entries grouped by date
  - `/undo` - Delete the most recent food entry
  - `/favorites` - View and quick-log favorite foods
  - `/addfav` - Add food to favorites from recent entries
  - `/delfav` - Remove food from favorites
  - `/templates` - View and log meal templates
  - `/newtemplate <name>` - Create new meal template (ConversationHandler)
  - `/deltemplate` - Delete meal templates
  - Photo handler with caption weight support
  - Text handler with inline weight parsing
  - Callback handler for inline keyboard buttons
  - Slash command menu via `set_my_commands()` - commands appear when user types "/"

- **keyboards.py** - Inline keyboard builders for Telegram:
  - `get_post_analysis_keyboard()` - Quick actions after food analysis (Log lagi, Hari ini, Batalkan)
  - `get_favorites_keyboard()` / `get_favorites_delete_keyboard()` - Favorites management
  - `get_templates_keyboard()` / `get_templates_delete_keyboard()` - Templates management
  - `get_recent_foods_keyboard()` - Select recent foods to add to favorites
  - `get_template_creation_keyboard()` - Done/Cancel during template creation

- **config.py** - Loads environment variables via python-dotenv:
  - `TELEGRAM_BOT_TOKEN` - Telegram Bot API token
  - `GEMINI_API_KEY` - Google Gemini API key
  - `GOOGLE_SHEETS_CREDENTIALS` - Service account JSON for Sheets
  - `GOOGLE_SHEETS_ID` - Target spreadsheet ID
  - `IMAGEKIT_*` - ImageKit credentials for image storage

- **gemini_service.py** - Gemini AI integration:
  - `analyze_food_image(image_bytes, weight_grams=None)` - Vision-based food analysis
  - `analyze_food_text(food_description, weight_grams=None)` - Text-based food analysis
  - `parse_weight_from_text(text)` - Extracts weight in grams from user input (supports "250g", "0.5 kg", etc.)
  - Uses `PROMPT_TEMPLATE` for estimation mode and `PROMPT_WITH_WEIGHT` for precise weight-based calculations

- **sheets_service.py** - Google Sheets integration for data persistence:
  - `log_food_entry()` / `log_multiple_foods()` - Save food entries with timestamp
  - `get_today_entries()` / `get_today_totals()` - Daily summary
  - `get_recent_entries()` - Paginated history
  - `delete_last_entry()` - Undo support
  - `is_sheets_configured()` - Check if Sheets is set up
  - Favorites functions: `get_user_favorites()`, `add_to_favorites()`, `remove_from_favorites()`, `suggest_favorites_from_history()`
  - Templates functions: `get_user_templates()`, `create_template()`, `delete_template()`, `log_template()`

- **imagekit_service.py** - ImageKit integration for permanent image storage:
  - `upload_food_image()` - Upload photos with user/food metadata
  - `is_imagekit_configured()` - Check if ImageKit is set up
  - Generates permanent URLs stored in Google Sheets for manual validation

**Data Flow:** User sends photo/text → Bot downloads/captures → Weight parsed from caption/message → Gemini API analyzes with appropriate prompt → JSON response normalized → Food logged to Google Sheets (with image URL if photo) → Emoji-rich nutrition breakdown returned

**Response Format:** All Gemini responses are normalized to `{foods: [...], total: {...}}` structure for consistent handling of single and multi-food detection.

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
