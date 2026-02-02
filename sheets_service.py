import logging
import json
import uuid
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

# Headers for Favorites worksheet
FAVORITES_HEADERS = [
    "User ID",      # Telegram user ID
    "Food Name",    # Normalized food name
    "Calories",     # Calories (kkal)
    "Protein",      # Protein (gram)
    "Carbs",        # Carbs (gram)
    "Fat",          # Fat (gram)
    "Portion",      # Default portion
    "Use Count",    # Times logged via favorites
    "Last Used"     # Timestamp
]

# Headers for Templates worksheet
TEMPLATES_HEADERS = [
    "Template ID",    # UUID
    "User ID",        # Telegram user ID
    "Name",           # Template name
    "Foods JSON",     # JSON array of food items
    "Total Calories", # Pre-calculated total
    "Total Protein",  # Pre-calculated total
    "Total Carbs",    # Pre-calculated total
    "Total Fat",      # Pre-calculated total
    "Use Count",      # Times used
    "Created At"      # Timestamp
]

# Cache for the sheets client
_client: Optional[gspread.Client] = None
_sheet: Optional[gspread.Worksheet] = None
_favorites_sheet: Optional[gspread.Worksheet] = None
_templates_sheet: Optional[gspread.Worksheet] = None


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


# ============================================================
# FAVORITES FUNCTIONS
# ============================================================

def get_favorites_sheet() -> Optional[gspread.Worksheet]:
    """Get the favorites worksheet, creating it if necessary."""
    global _favorites_sheet

    if _favorites_sheet is not None:
        return _favorites_sheet

    if not GOOGLE_SHEETS_ID:
        return None

    client = get_sheet_client()
    if not client:
        return None

    try:
        spreadsheet = client.open_by_key(GOOGLE_SHEETS_ID)

        try:
            _favorites_sheet = spreadsheet.worksheet("Favorites")
        except gspread.WorksheetNotFound:
            _favorites_sheet = spreadsheet.add_worksheet(
                title="Favorites", rows=500, cols=len(FAVORITES_HEADERS)
            )
            _favorites_sheet.append_row(FAVORITES_HEADERS)
            logger.info("Created 'Favorites' worksheet with headers")

        return _favorites_sheet
    except Exception as e:
        logger.error(f"Failed to get favorites worksheet: {e}")
        return None


def get_user_favorites(user_id: int, limit: int = 10) -> list:
    """
    Get user's favorite foods sorted by use count.

    Args:
        user_id: Telegram user ID
        limit: Maximum number of favorites to return

    Returns:
        List of favorite food dicts
    """
    sheet = get_favorites_sheet()
    if not sheet:
        return []

    user_id_str = str(user_id)

    try:
        all_records = sheet.get_all_records()

        favorites = []
        for record in all_records:
            if str(record.get("User ID")) == user_id_str:
                favorites.append({
                    "id": record.get("Food Name", ""),
                    "name": record.get("Food Name", ""),
                    "calories": record.get("Calories", 0),
                    "protein": record.get("Protein", 0),
                    "carbs": record.get("Carbs", 0),
                    "fat": record.get("Fat", 0),
                    "portion": record.get("Portion", ""),
                    "use_count": record.get("Use Count", 0),
                    "last_used": record.get("Last Used", "")
                })

        # Sort by use count (descending)
        favorites.sort(key=lambda x: x.get("use_count", 0), reverse=True)

        return favorites[:limit]
    except Exception as e:
        logger.error(f"Failed to get favorites: {e}")
        return []


def add_to_favorites(user_id: int, food_data: dict) -> bool:
    """
    Add or update a food in user's favorites.

    Args:
        user_id: Telegram user ID
        food_data: Dict with name, calories, protein, carbs, fat, portion

    Returns:
        True if successful
    """
    sheet = get_favorites_sheet()
    if not sheet:
        return False

    user_id_str = str(user_id)
    food_name = food_data.get("name", "").strip()

    if not food_name:
        return False

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    try:
        all_values = sheet.get_all_values()

        # Check if already exists
        for i, row in enumerate(all_values[1:], start=2):  # Skip header
            if len(row) >= 2 and str(row[0]) == user_id_str and row[1] == food_name:
                # Update existing favorite
                sheet.update_cell(i, 8, int(row[7] or 0) + 1)  # Increment use count
                sheet.update_cell(i, 9, now)  # Update last used
                logger.info(f"Updated favorite for user {user_id}: {food_name}")
                return True

        # Add new favorite
        row = [
            user_id_str,
            food_name,
            food_data.get("calories", 0),
            food_data.get("protein", 0),
            food_data.get("carbs", 0),
            food_data.get("fat", 0),
            food_data.get("portion", "1 porsi"),
            1,  # Use count
            now
        ]
        sheet.append_row(row)
        logger.info(f"Added favorite for user {user_id}: {food_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to add favorite: {e}")
        return False


def remove_from_favorites(user_id: int, food_name: str) -> bool:
    """
    Remove a food from user's favorites.

    Args:
        user_id: Telegram user ID
        food_name: Name of the food to remove

    Returns:
        True if deleted successfully
    """
    sheet = get_favorites_sheet()
    if not sheet:
        return False

    user_id_str = str(user_id)

    try:
        all_values = sheet.get_all_values()

        for i, row in enumerate(all_values[1:], start=2):  # Skip header
            if len(row) >= 2 and str(row[0]) == user_id_str and row[1] == food_name:
                sheet.delete_rows(i)
                logger.info(f"Removed favorite for user {user_id}: {food_name}")
                return True

        return False
    except Exception as e:
        logger.error(f"Failed to remove favorite: {e}")
        return False


def increment_favorite_usage(user_id: int, food_name: str) -> bool:
    """
    Increment use count for a favorite.

    Args:
        user_id: Telegram user ID
        food_name: Name of the food

    Returns:
        True if updated successfully
    """
    sheet = get_favorites_sheet()
    if not sheet:
        return False

    user_id_str = str(user_id)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    try:
        all_values = sheet.get_all_values()

        for i, row in enumerate(all_values[1:], start=2):
            if len(row) >= 2 and str(row[0]) == user_id_str and row[1] == food_name:
                current_count = int(row[7]) if len(row) > 7 and row[7] else 0
                sheet.update_cell(i, 8, current_count + 1)
                sheet.update_cell(i, 9, now)
                logger.info(f"Incremented favorite usage for user {user_id}: {food_name}")
                return True

        return False
    except Exception as e:
        logger.error(f"Failed to increment favorite usage: {e}")
        return False


def get_favorite_by_name(user_id: int, food_name: str) -> Optional[dict]:
    """
    Get a specific favorite by name.

    Args:
        user_id: Telegram user ID
        food_name: Name of the food

    Returns:
        Favorite dict or None
    """
    favorites = get_user_favorites(user_id, limit=100)
    for fav in favorites:
        if fav.get("name") == food_name:
            return fav
    return None


def suggest_favorites_from_history(user_id: int, min_count: int = 3) -> list:
    """
    Find frequently logged foods not yet in favorites.

    Args:
        user_id: Telegram user ID
        min_count: Minimum times a food must be logged to be suggested

    Returns:
        List of suggested food dicts
    """
    sheet = get_worksheet()
    favorites_sheet = get_favorites_sheet()
    if not sheet or not favorites_sheet:
        return []

    user_id_str = str(user_id)

    try:
        # Get existing favorites
        fav_records = favorites_sheet.get_all_records()
        existing_favorites = set()
        for record in fav_records:
            if str(record.get("User ID")) == user_id_str:
                existing_favorites.add(record.get("Food Name", "").lower())

        # Count food occurrences in history
        all_records = sheet.get_all_records()
        food_counts = {}
        food_data = {}

        for record in all_records:
            if str(record.get("User ID")) == user_id_str:
                name = record.get("Nama Makanan", "")
                if name and name.lower() not in existing_favorites:
                    food_counts[name] = food_counts.get(name, 0) + 1
                    if name not in food_data:
                        food_data[name] = {
                            "name": name,
                            "calories": record.get("Kalori", 0),
                            "protein": record.get("Protein", 0),
                            "carbs": record.get("Karbo", 0),
                            "fat": record.get("Lemak", 0),
                            "portion": record.get("Porsi/Berat", "1 porsi")
                        }

        # Filter by min_count and sort by frequency
        suggestions = []
        for name, count in food_counts.items():
            if count >= min_count:
                data = food_data[name]
                data["count"] = count
                suggestions.append(data)

        suggestions.sort(key=lambda x: x.get("count", 0), reverse=True)
        return suggestions[:5]
    except Exception as e:
        logger.error(f"Failed to suggest favorites: {e}")
        return []


# ============================================================
# TEMPLATES FUNCTIONS
# ============================================================

def get_templates_sheet() -> Optional[gspread.Worksheet]:
    """Get the templates worksheet, creating it if necessary."""
    global _templates_sheet

    if _templates_sheet is not None:
        return _templates_sheet

    if not GOOGLE_SHEETS_ID:
        return None

    client = get_sheet_client()
    if not client:
        return None

    try:
        spreadsheet = client.open_by_key(GOOGLE_SHEETS_ID)

        try:
            _templates_sheet = spreadsheet.worksheet("Templates")
        except gspread.WorksheetNotFound:
            _templates_sheet = spreadsheet.add_worksheet(
                title="Templates", rows=500, cols=len(TEMPLATES_HEADERS)
            )
            _templates_sheet.append_row(TEMPLATES_HEADERS)
            logger.info("Created 'Templates' worksheet with headers")

        return _templates_sheet
    except Exception as e:
        logger.error(f"Failed to get templates worksheet: {e}")
        return None


def get_user_templates(user_id: int) -> list:
    """
    Get user's meal templates.

    Args:
        user_id: Telegram user ID

    Returns:
        List of template dicts
    """
    sheet = get_templates_sheet()
    if not sheet:
        return []

    user_id_str = str(user_id)

    try:
        all_records = sheet.get_all_records()

        templates = []
        for record in all_records:
            if str(record.get("User ID")) == user_id_str:
                foods_json = record.get("Foods JSON", "[]")
                try:
                    foods = json.loads(foods_json)
                except json.JSONDecodeError:
                    foods = []

                templates.append({
                    "id": record.get("Template ID", ""),
                    "name": record.get("Name", ""),
                    "foods": foods,
                    "total_calories": record.get("Total Calories", 0),
                    "total_protein": record.get("Total Protein", 0),
                    "total_carbs": record.get("Total Carbs", 0),
                    "total_fat": record.get("Total Fat", 0),
                    "use_count": record.get("Use Count", 0),
                    "created_at": record.get("Created At", "")
                })

        # Sort by use count (descending)
        templates.sort(key=lambda x: x.get("use_count", 0), reverse=True)

        return templates
    except Exception as e:
        logger.error(f"Failed to get templates: {e}")
        return []


def create_template(user_id: int, name: str, foods: list) -> Optional[str]:
    """
    Create a new meal template.

    Args:
        user_id: Telegram user ID
        name: Template name
        foods: List of food dicts

    Returns:
        Template ID if successful, None otherwise
    """
    sheet = get_templates_sheet()
    if not sheet:
        return None

    template_id = str(uuid.uuid4())[:8]
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Calculate totals
    total_calories = sum(f.get("calories", 0) for f in foods)
    total_protein = sum(f.get("protein", 0) for f in foods)
    total_carbs = sum(f.get("carbs", 0) for f in foods)
    total_fat = sum(f.get("fat", 0) for f in foods)

    try:
        row = [
            template_id,
            str(user_id),
            name,
            json.dumps(foods),
            total_calories,
            total_protein,
            total_carbs,
            total_fat,
            0,  # Use count
            now
        ]
        sheet.append_row(row)
        logger.info(f"Created template '{name}' for user {user_id}")
        return template_id
    except Exception as e:
        logger.error(f"Failed to create template: {e}")
        return None


def get_template_by_id(user_id: int, template_id: str) -> Optional[dict]:
    """
    Get a specific template by ID.

    Args:
        user_id: Telegram user ID
        template_id: Template ID

    Returns:
        Template dict or None
    """
    templates = get_user_templates(user_id)
    for template in templates:
        if template.get("id") == template_id:
            return template
    return None


def delete_template(user_id: int, template_id: str) -> bool:
    """
    Delete a meal template.

    Args:
        user_id: Telegram user ID
        template_id: Template ID to delete

    Returns:
        True if deleted successfully
    """
    sheet = get_templates_sheet()
    if not sheet:
        return False

    user_id_str = str(user_id)

    try:
        all_values = sheet.get_all_values()

        for i, row in enumerate(all_values[1:], start=2):  # Skip header
            if (len(row) >= 2 and
                row[0] == template_id and
                str(row[1]) == user_id_str):
                sheet.delete_rows(i)
                logger.info(f"Deleted template {template_id} for user {user_id}")
                return True

        return False
    except Exception as e:
        logger.error(f"Failed to delete template: {e}")
        return False


def log_template(user_id: int, template_id: str) -> int:
    """
    Log all foods from a template and increment its use count.

    Args:
        user_id: Telegram user ID
        template_id: Template ID to log

    Returns:
        Number of foods logged (0 if failed)
    """
    template = get_template_by_id(user_id, template_id)
    if not template:
        return 0

    foods = template.get("foods", [])
    if not foods:
        return 0

    # Log all foods
    logged_count = log_multiple_foods(user_id, foods)

    # Increment template use count
    if logged_count > 0:
        _increment_template_usage(user_id, template_id)

    return logged_count


def _increment_template_usage(user_id: int, template_id: str) -> bool:
    """Increment use count for a template."""
    sheet = get_templates_sheet()
    if not sheet:
        return False

    user_id_str = str(user_id)

    try:
        all_values = sheet.get_all_values()

        for i, row in enumerate(all_values[1:], start=2):
            if (len(row) >= 2 and
                row[0] == template_id and
                str(row[1]) == user_id_str):
                current_count = int(row[8]) if len(row) > 8 and row[8] else 0
                sheet.update_cell(i, 9, current_count + 1)
                return True

        return False
    except Exception as e:
        logger.error(f"Failed to increment template usage: {e}")
        return False
