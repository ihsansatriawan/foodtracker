import logging
from datetime import datetime
from typing import Optional
import os
import uuid
import re

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
    "Image URL",    # Telegram file URL for validation
    # New feedback columns
    "Entry ID",           # UUID untuk track individual entries
    "AI Estimate (g)",    # Berat estimasi dari AI
    "User Verified",      # TRUE jika user confirm benar
    "Actual Weight (g)",  # Berat sebenarnya dari user
    "Correction Ratio",   # actual/estimate (untuk learning)
    "Feedback Date"       # Kapan feedback diberikan
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


def generate_entry_id() -> str:
    """Generate unique entry ID."""
    return str(uuid.uuid4())[:8]


def extract_weight_from_portion(portion: str) -> Optional[int]:
    """Extract weight in grams from portion string."""
    if not portion:
        return None

    # Match patterns like "150 gram", "200g", etc.
    match = re.search(r'(\d+)\s*(?:gram|g)\b', portion, re.IGNORECASE)
    if match:
        return int(match.group(1))

    return None


def log_food_entry(user_id: int, food_data: dict, image_url: str = "") -> bool:
    """
    Log a food entry to Google Sheets (legacy function for backward compatibility).

    Args:
        user_id: Telegram user ID
        food_data: Dictionary containing food nutrition data
            Expected keys: name, calories, protein, carbs, fat, weight_grams/portion
        image_url: Optional URL to the food image for manual validation

    Returns:
        True if logged successfully, False otherwise
    """
    entry_id = log_food_with_tracking(user_id, food_data, image_url)
    return entry_id is not None


def log_food_with_tracking(user_id: int, food_data: dict, image_url: str = "") -> Optional[str]:
    """
    Log food entry dengan tracking ID untuk feedback.

    Args:
        user_id: Telegram user ID
        food_data: Dictionary containing food nutrition data
        image_url: Optional URL to the food image for manual validation

    Returns:
        Entry ID if successful, None otherwise
    """
    sheet = get_worksheet()
    if not sheet:
        return None

    entry_id = generate_entry_id()

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")

    # Get portion/weight info
    if food_data.get('weight_grams'):
        portion = f"{food_data['weight_grams']} gram"
    else:
        portion = food_data.get('portion', '-')

    # Extract AI estimate from food dict
    ai_estimate = food_data.get("weight_grams") or extract_weight_from_portion(portion)

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
        image_url,
        # Feedback columns
        entry_id,
        ai_estimate or "",
        "",  # User Verified (empty = pending)
        "",  # Actual Weight
        "",  # Correction Ratio
        "",  # Feedback Date
    ]

    try:
        sheet.append_row(row)
        logger.info(f"Logged food entry for user {user_id}: {food_data.get('name')} (ID: {entry_id})")
        return entry_id
    except Exception as e:
        logger.error(f"Failed to log food entry: {e}")
        return None


def log_multiple_foods(user_id: int, foods: list, image_url: str = "") -> list:
    """
    Log multiple food entries at once.

    Args:
        user_id: Telegram user ID
        foods: List of food dictionaries
        image_url: Optional URL to the food image for manual validation

    Returns:
        List of entry IDs for successfully logged entries
    """
    entry_ids = []
    for food in foods:
        entry_id = log_food_with_tracking(user_id, food, image_url)
        if entry_id:
            entry_ids.append(entry_id)
    return entry_ids


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


def update_entry_feedback(entry_id: str, user_id: int, verified: bool = None,
                          actual_weight: int = None) -> bool:
    """
    Update entry dengan feedback dari user.

    Args:
        entry_id: Entry ID to update
        user_id: Telegram user ID (for security check)
        verified: TRUE if user verified the estimate is correct
        actual_weight: Actual weight in grams from user correction

    Returns:
        True if updated successfully, False otherwise
    """
    sheet = get_worksheet()
    if not sheet:
        return False

    try:
        # Find row by entry_id
        all_values = sheet.get_all_values()

        for i, row in enumerate(all_values[1:], start=2):  # Skip header
            if len(row) > 10 and row[10] == entry_id and str(row[2]) == str(user_id):
                # Found the entry
                updates = {}

                # Column L: User Verified (index 12)
                if verified is not None:
                    sheet.update_cell(i, 13, "TRUE" if verified else "FALSE")

                # Column M: Actual Weight (index 13)
                if actual_weight is not None:
                    sheet.update_cell(i, 14, actual_weight)

                    # Column N: Calculate correction ratio (index 14)
                    ai_estimate = int(row[11]) if row[11] and row[11].isdigit() else None
                    if ai_estimate and ai_estimate > 0:
                        ratio = round(actual_weight / ai_estimate, 2)
                        sheet.update_cell(i, 15, ratio)

                # Column O: Feedback Date (index 15)
                sheet.update_cell(i, 16, datetime.now().strftime("%Y-%m-%d %H:%M"))

                logger.info(f"Updated feedback for entry {entry_id}")
                return True

        logger.warning(f"Entry {entry_id} not found for user {user_id}")
        return False
    except Exception as e:
        logger.error(f"Failed to update entry feedback: {e}")
        return False


def delete_entry_by_id(entry_id: str, user_id: int) -> bool:
    """
    Delete entry by entry ID.

    Args:
        entry_id: Entry ID to delete
        user_id: Telegram user ID (for security check)

    Returns:
        True if deleted successfully, False otherwise
    """
    sheet = get_worksheet()
    if not sheet:
        return False

    try:
        all_values = sheet.get_all_values()

        for i, row in enumerate(all_values[1:], start=2):  # Skip header
            if len(row) > 10 and row[10] == entry_id and str(row[2]) == str(user_id):
                sheet.delete_rows(i)
                logger.info(f"Deleted entry {entry_id} for user {user_id}")
                return True

        logger.warning(f"Entry {entry_id} not found for user {user_id}")
        return False
    except Exception as e:
        logger.error(f"Failed to delete entry: {e}")
        return False


def get_user_correction_history(user_id: int) -> list:
    """
    Get correction history untuk user tertentu.

    Args:
        user_id: Telegram user ID

    Returns:
        List of corrections with food name, estimates, ratios, etc.
    """
    sheet = get_worksheet()
    if not sheet:
        return []

    try:
        all_values = sheet.get_all_values()
        corrections = []

        for row in all_values[1:]:  # Skip header
            # Check if this row belongs to user and has actual weight (column 13)
            if len(row) > 13 and str(row[2]) == str(user_id) and row[13]:
                ai_estimate = int(row[11]) if row[11] and row[11].isdigit() else None
                actual_weight = int(row[13]) if row[13] and row[13].isdigit() else None
                correction_ratio = float(row[14]) if len(row) > 14 and row[14] else None

                corrections.append({
                    "food_name": row[3],
                    "ai_estimate": ai_estimate,
                    "actual_weight": actual_weight,
                    "correction_ratio": correction_ratio,
                    "date": row[0],
                })

        return corrections
    except Exception as e:
        logger.error(f"Failed to get correction history: {e}")
        return []


def get_average_correction_ratio(user_id: int, food_category: str = None) -> float:
    """
    Hitung rata-rata correction ratio untuk user.
    Bisa filtered by food category untuk accuracy yang lebih tinggi.

    Args:
        user_id: Telegram user ID
        food_category: Optional food category filter (not implemented yet)

    Returns:
        Average correction ratio (1.0 if no corrections)
    """
    corrections = get_user_correction_history(user_id)

    if not corrections:
        return 1.0  # No corrections, use 1:1 ratio

    # Filter valid ratios (between 0.5 and 2.0 to avoid outliers)
    ratios = [
        c["correction_ratio"]
        for c in corrections
        if c["correction_ratio"] and 0.5 <= c["correction_ratio"] <= 2.0
    ]

    if not ratios:
        return 1.0

    return sum(ratios) / len(ratios)


def is_sheets_configured() -> bool:
    """Check if Google Sheets is properly configured."""
    if not GOOGLE_SHEETS_ID:
        return False
    if not GOOGLE_CREDENTIALS_FILE or not os.path.exists(GOOGLE_CREDENTIALS_FILE):
        return False
    return True
