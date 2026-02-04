"""
Dashboard Service - Google Sheets operations for the dashboard.
"""

import logging
import sys
from pathlib import Path
from typing import Optional
import math

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sheets_service import get_worksheet, HEADERS

logger = logging.getLogger(__name__)


def get_all_entries() -> list:
    """
    Get all food entries from the sheet.

    Returns:
        List of all entries with row index for editing.
    """
    sheet = get_worksheet()
    if not sheet:
        return []

    try:
        all_values = sheet.get_all_values()

        entries = []
        for i, row in enumerate(all_values):
            if i == 0:  # Skip header
                continue

            if len(row) < 10:
                row.extend([''] * (10 - len(row)))

            entries.append({
                "row_index": i + 1,  # gspread uses 1-based indexing
                "date": row[0],
                "time": row[1],
                "user_id": row[2],
                "name": row[3],
                "calories": safe_float(row[4]),
                "protein": safe_float(row[5]),
                "carbs": safe_float(row[6]),
                "fat": safe_float(row[7]),
                "portion": row[8],
                "image_url": row[9] if len(row) > 9 else ""
            })

        # Return newest first
        return entries[::-1]

    except Exception as e:
        logger.error(f"Failed to get all entries: {e}")
        return []


def get_entries_paginated(page: int = 1, per_page: int = 20) -> dict:
    """
    Get paginated food entries.

    Args:
        page: Page number (1-based)
        per_page: Number of entries per page

    Returns:
        Dictionary with entries and pagination info.
    """
    all_entries = get_all_entries()
    total = len(all_entries)
    total_pages = math.ceil(total / per_page) if total > 0 else 1

    # Clamp page number
    page = max(1, min(page, total_pages))

    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page

    entries = all_entries[start_idx:end_idx]

    return {
        "entries": entries,
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
        "has_prev": page > 1,
        "has_next": page < total_pages
    }


def update_entry(row_index: int, data: dict) -> bool:
    """
    Update a food entry in the sheet.

    Args:
        row_index: Row index in the sheet (1-based)
        data: Dictionary with fields to update

    Returns:
        True if successful, False otherwise.
    """
    sheet = get_worksheet()
    if not sheet:
        return False

    # Map field names to column indices (1-based for gspread)
    field_to_col = {
        "name": 4,       # Nama Makanan
        "calories": 5,   # Kalori
        "protein": 6,    # Protein
        "carbs": 7,      # Karbo
        "fat": 8,        # Lemak
        "portion": 9     # Porsi/Berat
    }

    try:
        for field, value in data.items():
            if field in field_to_col:
                col = field_to_col[field]
                sheet.update_cell(row_index, col, value)
                logger.info(f"Updated row {row_index}, column {field}: {value}")

        return True

    except Exception as e:
        logger.error(f"Failed to update entry at row {row_index}: {e}")
        return False


def delete_entry(row_index: int) -> bool:
    """
    Delete a food entry from the sheet.

    Args:
        row_index: Row index in the sheet (1-based)

    Returns:
        True if successful, False otherwise.
    """
    sheet = get_worksheet()
    if not sheet:
        return False

    try:
        sheet.delete_rows(row_index)
        logger.info(f"Deleted row {row_index}")
        return True

    except Exception as e:
        logger.error(f"Failed to delete entry at row {row_index}: {e}")
        return False


def safe_float(value) -> float:
    """Safely convert a value to float."""
    try:
        if value == '' or value is None:
            return 0.0
        return float(value)
    except (ValueError, TypeError):
        return 0.0
