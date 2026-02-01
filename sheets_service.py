import logging
from datetime import datetime
from typing import Optional
import os

import gspread
from google.oauth2.service_account import Credentials

from config import GOOGLE_SHEETS_ID, GOOGLE_CREDENTIALS_FILE

logger = logging.getLogger(__name__)

# Google Sheets API scopes
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Sheet header row
HEADERS = [
    "Tanggal",      # Date (YYYY-MM-DD)
    "Waktu",        # Time (HH:MM)
    "User ID",      # Telegram user ID
    "Nama Makanan", # Food name
    "Kalori",       # Calories (kkal)
    "Protein",      # Protein (gram)
    "Karbo",        # Carbs (gram)
    "Lemak",        # Fat (gram)
    "Porsi/Berat",  # Portion or weight
    "Image URL"     # Telegram file URL for validation
]

# Cache for the sheets client
_client: Optional[gspread.Client] = None
_sheet: Optional[gspread.Worksheet] = None


def get_sheet_client() -> Optional[gspread.Client]:
    """Get authenticated Google Sheets client."""
    global _client

    if _client is not None:
        return _client

    if not GOOGLE_CREDENTIALS_FILE or not os.path.exists(GOOGLE_CREDENTIALS_FILE):
        logger.warning(f"Google credentials file not found: {GOOGLE_CREDENTIALS_FILE}")
        return None

    try:
        credentials = Credentials.from_service_account_file(
            GOOGLE_CREDENTIALS_FILE,
            scopes=SCOPES
        )
        _client = gspread.authorize(credentials)
        logger.info("Google Sheets client authenticated successfully")
        return _client
    except Exception as e:
        logger.error(f"Failed to authenticate with Google Sheets: {e}")
        return None


def get_worksheet() -> Optional[gspread.Worksheet]:
    """Get the food log worksheet, creating it if necessary."""
    global _sheet

    if _sheet is not None:
        return _sheet

    if not GOOGLE_SHEETS_ID:
        logger.warning("GOOGLE_SHEETS_ID not configured")
        return None

    client = get_sheet_client()
    if not client:
        return None

    try:
        spreadsheet = client.open_by_key(GOOGLE_SHEETS_ID)

        # Try to get "Food Log" sheet, or create it
        try:
            _sheet = spreadsheet.worksheet("Food Log")
        except gspread.WorksheetNotFound:
            _sheet = spreadsheet.add_worksheet(title="Food Log", rows=1000, cols=len(HEADERS))
            _sheet.append_row(HEADERS)
            logger.info("Created 'Food Log' worksheet with headers")

        return _sheet
    except Exception as e:
        logger.error(f"Failed to get worksheet: {e}")
        return None


def log_food_entry(user_id: int, food_data: dict, image_url: str = "") -> bool:
    """
    Log a food entry to Google Sheets.

    Args:
        user_id: Telegram user ID
        food_data: Dictionary containing food nutrition data
            Expected keys: name, calories, protein, carbs, fat, weight_grams/portion
        image_url: Optional URL to the food image for manual validation

    Returns:
        True if logged successfully, False otherwise
    """
    sheet = get_worksheet()
    if not sheet:
        return False

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")

    # Get portion/weight info
    if food_data.get('weight_grams'):
        portion = f"{food_data['weight_grams']} gram"
    else:
        portion = food_data.get('portion', '-')

    row = [
        date_str,
        time_str,
        str(user_id),
        food_data.get('name', 'Unknown'),
        food_data.get('calories', 0),
        food_data.get('protein', 0),
        food_data.get('carbs', 0),
        food_data.get('fat', 0),
        portion,
        image_url
    ]

    try:
        sheet.append_row(row)
        logger.info(f"Logged food entry for user {user_id}: {food_data.get('name')}")
        return True
    except Exception as e:
        logger.error(f"Failed to log food entry: {e}")
        return False


def log_multiple_foods(user_id: int, foods: list, image_url: str = "") -> int:
    """
    Log multiple food entries at once.

    Args:
        user_id: Telegram user ID
        foods: List of food dictionaries
        image_url: Optional URL to the food image for manual validation

    Returns:
        Number of entries logged successfully
    """
    count = 0
    for food in foods:
        if log_food_entry(user_id, food, image_url):
            count += 1
    return count


def get_today_entries(user_id: int) -> list:
    """
    Get all food entries for a user from today.

    Args:
        user_id: Telegram user ID

    Returns:
        List of food entries (each as a dict)
    """
    sheet = get_worksheet()
    if not sheet:
        return []

    today = datetime.now().strftime("%Y-%m-%d")
    user_id_str = str(user_id)

    try:
        all_records = sheet.get_all_records()

        entries = []
        for record in all_records:
            if record.get("Tanggal") == today and str(record.get("User ID")) == user_id_str:
                entries.append({
                    "time": record.get("Waktu", ""),
                    "name": record.get("Nama Makanan", ""),
                    "calories": record.get("Kalori", 0),
                    "protein": record.get("Protein", 0),
                    "carbs": record.get("Karbo", 0),
                    "fat": record.get("Lemak", 0),
                    "portion": record.get("Porsi/Berat", "")
                })

        return entries
    except Exception as e:
        logger.error(f"Failed to get today's entries: {e}")
        return []


def get_today_totals(user_id: int) -> dict:
    """
    Get total nutrition for today.

    Args:
        user_id: Telegram user ID

    Returns:
        Dictionary with total calories, protein, carbs, fat
    """
    entries = get_today_entries(user_id)

    totals = {
        "calories": 0,
        "protein": 0,
        "carbs": 0,
        "fat": 0,
        "count": len(entries)
    }

    for entry in entries:
        totals["calories"] += entry.get("calories", 0) or 0
        totals["protein"] += entry.get("protein", 0) or 0
        totals["carbs"] += entry.get("carbs", 0) or 0
        totals["fat"] += entry.get("fat", 0) or 0

    return totals


def get_recent_entries(user_id: int, limit: int = 10) -> list:
    """
    Get recent food entries for a user.

    Args:
        user_id: Telegram user ID
        limit: Maximum number of entries to return

    Returns:
        List of recent food entries (newest first)
    """
    sheet = get_worksheet()
    if not sheet:
        return []

    user_id_str = str(user_id)

    try:
        all_records = sheet.get_all_records()

        # Filter by user and collect entries
        entries = []
        for record in all_records:
            if str(record.get("User ID")) == user_id_str:
                entries.append({
                    "date": record.get("Tanggal", ""),
                    "time": record.get("Waktu", ""),
                    "name": record.get("Nama Makanan", ""),
                    "calories": record.get("Kalori", 0),
                    "protein": record.get("Protein", 0),
                    "carbs": record.get("Karbo", 0),
                    "fat": record.get("Lemak", 0),
                    "portion": record.get("Porsi/Berat", "")
                })

        # Return newest first (reverse order), limited
        return entries[::-1][:limit]
    except Exception as e:
        logger.error(f"Failed to get recent entries: {e}")
        return []


def delete_last_entry(user_id: int) -> Optional[dict]:
    """
    Delete the last food entry for a user.

    Args:
        user_id: Telegram user ID

    Returns:
        The deleted entry as a dict, or None if no entry found
    """
    sheet = get_worksheet()
    if not sheet:
        return None

    user_id_str = str(user_id)

    try:
        all_values = sheet.get_all_values()

        # Find the last row for this user (search from bottom)
        last_row_index = None
        last_entry = None

        for i in range(len(all_values) - 1, 0, -1):  # Skip header row (index 0)
            row = all_values[i]
            if len(row) >= 3 and str(row[2]) == user_id_str:  # Column 2 is User ID
                last_row_index = i + 1  # gspread uses 1-based indexing
                last_entry = {
                    "date": row[0],
                    "time": row[1],
                    "name": row[3] if len(row) > 3 else "",
                    "calories": row[4] if len(row) > 4 else 0,
                    "protein": row[5] if len(row) > 5 else 0,
                    "carbs": row[6] if len(row) > 6 else 0,
                    "fat": row[7] if len(row) > 7 else 0,
                    "portion": row[8] if len(row) > 8 else ""
                }
                break

        if last_row_index:
            sheet.delete_rows(last_row_index)
            logger.info(f"Deleted entry for user {user_id}: {last_entry.get('name')}")
            return last_entry

        return None
    except Exception as e:
        logger.error(f"Failed to delete last entry: {e}")
        return None


def is_sheets_configured() -> bool:
    """Check if Google Sheets is properly configured."""
    if not GOOGLE_SHEETS_ID:
        return False
    if not GOOGLE_CREDENTIALS_FILE or not os.path.exists(GOOGLE_CREDENTIALS_FILE):
        return False
    return True
