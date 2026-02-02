"""
Inline keyboard builders for Telegram bot.

Provides reusable keyboard layouts for:
- Post-analysis quick actions
- Favorites management
- Meal templates
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_post_analysis_keyboard() -> InlineKeyboardMarkup:
    """
    Get keyboard shown after food analysis.

    Buttons:
    - Log lagi: Prompt user to log another food
    - Hari ini: Show today's summary
    - Batalkan: Undo the last entry
    """
    keyboard = [
        [
            InlineKeyboardButton("📝 Log lagi", callback_data="action:log_again"),
            InlineKeyboardButton("📊 Hari ini", callback_data="action:today"),
        ],
        [
            InlineKeyboardButton("↩️ Batalkan", callback_data="action:undo_last"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_confirmation_keyboard(confirm_action: str) -> InlineKeyboardMarkup:
    """
    Get yes/no confirmation keyboard.

    Args:
        confirm_action: The action to confirm (used in callback data)
    """
    keyboard = [
        [
            InlineKeyboardButton("✅ Ya", callback_data=f"confirm:{confirm_action}"),
            InlineKeyboardButton("❌ Tidak", callback_data="confirm:cancel"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_favorites_keyboard(favorites: list) -> InlineKeyboardMarkup:
    """
    Get keyboard grid of favorite foods for quick logging.

    Args:
        favorites: List of favorite food dicts with 'name' key

    Returns:
        Keyboard with favorites as buttons (2 per row)
    """
    keyboard = []
    row = []

    for fav in favorites:
        food_name = fav.get('name', '')[:20]  # Truncate long names
        btn = InlineKeyboardButton(
            f"🍽️ {food_name}",
            callback_data=f"fav:{fav.get('id', food_name[:30])}"
        )
        row.append(btn)

        if len(row) == 2:
            keyboard.append(row)
            row = []

    # Add remaining button if odd number
    if row:
        keyboard.append(row)

    # Add management button
    keyboard.append([
        InlineKeyboardButton("➕ Tambah favorit", callback_data="fav:add_new"),
    ])

    return InlineKeyboardMarkup(keyboard)


def get_favorites_delete_keyboard(favorites: list) -> InlineKeyboardMarkup:
    """
    Get keyboard for deleting favorites.

    Args:
        favorites: List of favorite food dicts

    Returns:
        Keyboard with delete buttons (1 per row)
    """
    keyboard = []

    for fav in favorites:
        food_name = fav.get('name', '')[:25]
        btn = InlineKeyboardButton(
            f"🗑️ {food_name}",
            callback_data=f"delfav:{fav.get('id', food_name[:30])}"
        )
        keyboard.append([btn])

    # Add cancel button
    keyboard.append([
        InlineKeyboardButton("❌ Batal", callback_data="action:cancel"),
    ])

    return InlineKeyboardMarkup(keyboard)


def get_templates_keyboard(templates: list) -> InlineKeyboardMarkup:
    """
    Get keyboard grid of meal templates for quick logging.

    Args:
        templates: List of template dicts with 'name' and 'id' keys

    Returns:
        Keyboard with templates as buttons
    """
    keyboard = []

    for template in templates:
        name = template.get('name', '')[:20]
        total_cal = template.get('total_calories', 0)
        btn = InlineKeyboardButton(
            f"🍱 {name} ({total_cal} kkal)",
            callback_data=f"template:{template.get('id', '')}"
        )
        keyboard.append([btn])

    # Add create new button
    keyboard.append([
        InlineKeyboardButton("➕ Buat template baru", callback_data="template:create_new"),
    ])

    return InlineKeyboardMarkup(keyboard)


def get_templates_delete_keyboard(templates: list) -> InlineKeyboardMarkup:
    """
    Get keyboard for deleting templates.

    Args:
        templates: List of template dicts

    Returns:
        Keyboard with delete buttons
    """
    keyboard = []

    for template in templates:
        name = template.get('name', '')[:25]
        btn = InlineKeyboardButton(
            f"🗑️ {name}",
            callback_data=f"deltemplate:{template.get('id', '')}"
        )
        keyboard.append([btn])

    # Add cancel button
    keyboard.append([
        InlineKeyboardButton("❌ Batal", callback_data="action:cancel"),
    ])

    return InlineKeyboardMarkup(keyboard)


def get_recent_foods_keyboard(recent_foods: list) -> InlineKeyboardMarkup:
    """
    Get keyboard showing recent foods to add to favorites.

    Args:
        recent_foods: List of recent food entries

    Returns:
        Keyboard with recent foods as buttons
    """
    keyboard = []

    for food in recent_foods[:5]:  # Max 5 recent foods
        name = food.get('name', '')[:25]
        btn = InlineKeyboardButton(
            f"⭐ {name}",
            callback_data=f"addfav:{name[:30]}"
        )
        keyboard.append([btn])

    # Add cancel button
    keyboard.append([
        InlineKeyboardButton("❌ Batal", callback_data="action:cancel"),
    ])

    return InlineKeyboardMarkup(keyboard)


def get_template_creation_keyboard() -> InlineKeyboardMarkup:
    """
    Get keyboard shown during template creation.

    Shows options to finish or cancel template creation.
    """
    keyboard = [
        [
            InlineKeyboardButton("✅ Selesai", callback_data="template:done"),
            InlineKeyboardButton("❌ Batal", callback_data="template:cancel"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
