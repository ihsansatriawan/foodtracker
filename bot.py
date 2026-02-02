import logging
from datetime import datetime
from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes
)

from config import TELEGRAM_BOT_TOKEN
from gemini_service import analyze_food_image, analyze_food_text, parse_weight_from_text
from sheets_service import (
    log_food_entry,
    log_multiple_foods,
    get_today_entries,
    get_today_totals,
    get_recent_entries,
    delete_last_entry,
    is_sheets_configured,
    # Favorites
    get_user_favorites,
    add_to_favorites,
    remove_from_favorites,
    increment_favorite_usage,
    get_favorite_by_name,
    suggest_favorites_from_history,
    # Templates
    get_user_templates,
    create_template,
    get_template_by_id,
    delete_template,
    log_template
)
from imagekit_service import upload_food_image, is_imagekit_configured
from keyboards import (
    get_post_analysis_keyboard,
    get_favorites_keyboard,
    get_favorites_delete_keyboard,
    get_templates_keyboard,
    get_templates_delete_keyboard,
    get_recent_foods_keyboard,
    get_template_creation_keyboard
)

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ConversationHandler states
ADDING_FOODS = 1

WELCOME_MESSAGE = """🍽️ Selamat datang di Calorie Tracker Bot!

Saya bisa membantu kamu menghitung estimasi kalori dan nutrisi makanan.

Cara menggunakan:
📸 Kirim foto makanan - Saya akan menganalisis dan memberikan estimasi nutrisi
✍️ Ketik nama makanan - Contoh: "nasi goreng 1 piring"

Kirim /help untuk bantuan lebih lanjut."""

HELP_MESSAGE = """📖 Panduan Penggunaan

🔹 Kirim Foto Makanan
Ambil foto makanan kamu dan kirim ke bot.

💡 Tips: Tambahkan caption dengan berat untuk hasil lebih akurat!
Contoh: Kirim foto dengan caption "250 gram"

🔹 Kirim Deskripsi Makanan
Ketik nama dan porsi makanan, contoh:
- "nasi goreng 1 piring"
- "ayam bakar 150 gram"
- "es teh manis 1 gelas"

⚖️ Format Berat yang Didukung:
- 250 gram / 250g / 250 gr
- 0.5 kg / 500 gram

📊 Perintah Tracking:
/today - Lihat ringkasan kalori hari ini
/history - Lihat riwayat makanan terakhir
/undo - Hapus entri makanan terakhir

⭐ Favorit & Template:
/favorites - Lihat dan log makanan favorit
/addfav - Tambah makanan ke favorit
/delfav - Hapus makanan dari favorit
/templates - Lihat dan log template makanan
/newtemplate <nama> - Buat template baru
/deltemplate - Hapus template

❓ Ada pertanyaan? Langsung kirim pesan!"""


def format_nutrition_response(data: dict) -> str:
    """Format nutrition data into a nice response message."""
    if "error" in data:
        return f"❌ {data['error']}"

    foods = data.get("foods", [])
    total = data.get("total", {})

    if not foods:
        return "❌ Tidak ada makanan yang terdeteksi"

    lines = ["✅ Hasil Analisis!"]

    # Format each food item
    for i, food in enumerate(foods, 1):
        if len(foods) > 1:
            lines.append(f"\n📍 Item {i}:")
        lines.append(f"🍽️ {food.get('name', 'Makanan')}")
        lines.append(f"📊 Kalori: {food.get('calories', 0)} kkal")
        lines.append(f"🥩 Protein: {food.get('protein', 0)}g")
        lines.append(f"🍞 Karbo: {food.get('carbs', 0)}g")
        lines.append(f"🧈 Lemak: {food.get('fat', 0)}g")

        # Show weight if available, otherwise show portion
        if food.get('weight_grams'):
            lines.append(f"⚖️ Berat: {food.get('weight_grams')} gram")
        else:
            lines.append(f"📏 Porsi: {food.get('portion', '-')}")

    # Add total section if multiple foods
    if len(foods) > 1:
        lines.append("\n━━━━━━━━━━━━━━━━━━")
        lines.append("📊 TOTAL:")
        lines.append(f"📊 Kalori: {total.get('calories', 0)} kkal")
        lines.append(f"🥩 Protein: {total.get('protein', 0)}g")
        lines.append(f"🍞 Karbo: {total.get('carbs', 0)}g")
        lines.append(f"🧈 Lemak: {total.get('fat', 0)}g")
        if total.get('weight_grams'):
            lines.append(f"⚖️ Berat: {total.get('weight_grams')} gram")

    return "\n".join(lines)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    await update.message.reply_text(WELCOME_MESSAGE)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    await update.message.reply_text(HELP_MESSAGE)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle photo messages - analyze food from image."""

    # Get caption if exists (may contain weight)
    caption = update.message.caption or ""

    # Parse weight from caption
    _, weight_grams = parse_weight_from_text(caption)

    if weight_grams:
        await update.message.reply_text(f"🔄 Menganalisis foto makanan ({weight_grams} gram)...")
    else:
        await update.message.reply_text("🔄 Menganalisis foto makanan...")

    try:
        # Get the largest photo
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)

        # Download photo as bytes
        photo_bytes = await file.download_as_bytearray()
        photo_bytes_raw = bytes(photo_bytes)

        # Pass weight to analyzer
        result = await analyze_food_image(photo_bytes_raw, weight_grams=weight_grams)

        # Send response
        response = format_nutrition_response(result)

        # Log to Google Sheets if configured and successful
        logged = False
        if "error" not in result and is_sheets_configured():
            user_id = update.effective_user.id
            foods = result.get("foods", [])
            if foods:
                # Upload image to ImageKit for permanent storage
                image_url = ""
                if is_imagekit_configured():
                    food_name = foods[0].get('name', 'food') if foods else 'food'
                    image_url = upload_food_image(photo_bytes_raw, user_id, food_name) or ""

                logged_count = log_multiple_foods(user_id, foods, image_url)
                if logged_count > 0:
                    logged = True

        if logged:
            response += "\n\n✅ Tersimpan ke log"

        # Include quick action keyboard
        await update.message.reply_text(
            response,
            reply_markup=get_post_analysis_keyboard()
        )

    except Exception as e:
        logger.error(f"Error handling photo: {e}")
        await update.message.reply_text("❌ Maaf, terjadi kesalahan. Coba lagi nanti.")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages - analyze food from description."""
    text = update.message.text

    # Skip if it's a command
    if text.startswith("/"):
        return

    # Parse weight from text
    food_description, weight_grams = parse_weight_from_text(text)

    # If only weight was provided (empty description), use original text
    if not food_description.strip():
        food_description = text

    if weight_grams:
        await update.message.reply_text(f"🔄 Menganalisis makanan ({weight_grams} gram)...")
    else:
        await update.message.reply_text("🔄 Menganalisis makanan...")

    try:
        # Pass weight to analyzer
        result = await analyze_food_text(food_description, weight_grams=weight_grams)

        # Send response
        response = format_nutrition_response(result)

        # Log to Google Sheets if configured and successful
        logged = False
        if "error" not in result and is_sheets_configured():
            user_id = update.effective_user.id
            foods = result.get("foods", [])
            if foods:
                logged_count = log_multiple_foods(user_id, foods)
                if logged_count > 0:
                    logged = True

        if logged:
            response += "\n\n✅ Tersimpan ke log"

        # Include quick action keyboard
        await update.message.reply_text(
            response,
            reply_markup=get_post_analysis_keyboard()
        )

    except Exception as e:
        logger.error(f"Error handling text: {e}")
        await update.message.reply_text("❌ Maaf, terjadi kesalahan. Coba lagi nanti.")


async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /today command - show today's food summary."""
    if not is_sheets_configured():
        await update.message.reply_text(
            "⚠️ Fitur tracking belum dikonfigurasi.\n"
            "Hubungi admin untuk setup Google Sheets."
        )
        return

    user_id = update.effective_user.id
    entries = get_today_entries(user_id)
    totals = get_today_totals(user_id)

    today_str = datetime.now().strftime("%d %b %Y")

    if not entries:
        await update.message.reply_text(
            f"📅 Makanan Hari Ini ({today_str})\n\n"
            "Belum ada makanan yang dicatat hari ini.\n"
            "Kirim foto atau ketik nama makanan untuk mulai tracking!"
        )
        return

    lines = [f"📅 Makanan Hari Ini ({today_str})\n"]

    for i, entry in enumerate(entries, 1):
        lines.append(f"{i}. {entry['name']} - {entry['calories']} kkal")

    lines.append("\n━━━━━━━━━━━━━━━━━━")
    lines.append("📊 Total Hari Ini:")
    lines.append(f"🔥 Kalori: {totals['calories']} kkal")
    lines.append(f"🥩 Protein: {totals['protein']}g")
    lines.append(f"🍚 Karbo: {totals['carbs']}g")
    lines.append(f"🧈 Lemak: {totals['fat']}g")

    await update.message.reply_text("\n".join(lines))


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /history command - show recent food entries."""
    if not is_sheets_configured():
        await update.message.reply_text(
            "⚠️ Fitur tracking belum dikonfigurasi.\n"
            "Hubungi admin untuk setup Google Sheets."
        )
        return

    user_id = update.effective_user.id
    entries = get_recent_entries(user_id, limit=10)

    if not entries:
        await update.message.reply_text(
            "📜 Riwayat Makanan\n\n"
            "Belum ada riwayat makanan.\n"
            "Kirim foto atau ketik nama makanan untuk mulai tracking!"
        )
        return

    lines = ["📜 Riwayat Makanan (10 terakhir)\n"]

    current_date = None
    for entry in entries:
        # Add date header if date changes
        if entry['date'] != current_date:
            current_date = entry['date']
            lines.append(f"\n📅 {current_date}")

        lines.append(f"  • {entry['time']} - {entry['name']} ({entry['calories']} kkal)")

    await update.message.reply_text("\n".join(lines))


async def undo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /undo command - delete last food entry."""
    if not is_sheets_configured():
        await update.message.reply_text(
            "⚠️ Fitur tracking belum dikonfigurasi.\n"
            "Hubungi admin untuk setup Google Sheets."
        )
        return

    user_id = update.effective_user.id
    deleted = delete_last_entry(user_id)

    if deleted:
        await update.message.reply_text(
            f"🗑️ Dihapus: {deleted['name']} ({deleted['calories']} kkal)\n"
            f"📅 {deleted['date']} {deleted['time']}"
        )
    else:
        await update.message.reply_text(
            "❌ Tidak ada entri yang bisa dihapus."
        )


# ============================================================
# CALLBACK HANDLER
# ============================================================

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline keyboard button callbacks."""
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = update.effective_user.id

    # Route callbacks by prefix
    if data.startswith("action:"):
        await handle_action_callback(query, user_id, data[7:])
    elif data.startswith("fav:"):
        await handle_favorite_callback(query, user_id, data[4:], context)
    elif data.startswith("delfav:"):
        await handle_delete_favorite_callback(query, user_id, data[7:])
    elif data.startswith("addfav:"):
        await handle_add_favorite_callback(query, user_id, data[7:])
    elif data.startswith("template:"):
        await handle_template_callback(query, user_id, data[9:], context)
    elif data.startswith("deltemplate:"):
        await handle_delete_template_callback(query, user_id, data[12:])
    elif data.startswith("confirm:"):
        await handle_confirm_callback(query, user_id, data[8:])


async def handle_action_callback(query, user_id: int, action: str) -> None:
    """Handle action: callbacks."""
    if action == "today":
        # Show today's summary
        entries = get_today_entries(user_id)
        totals = get_today_totals(user_id)
        today_str = datetime.now().strftime("%d %b %Y")

        if not entries:
            await query.edit_message_text(
                f"📅 Makanan Hari Ini ({today_str})\n\n"
                "Belum ada makanan yang dicatat hari ini."
            )
            return

        lines = [f"📅 Makanan Hari Ini ({today_str})\n"]
        for i, entry in enumerate(entries, 1):
            lines.append(f"{i}. {entry['name']} - {entry['calories']} kkal")

        lines.append("\n━━━━━━━━━━━━━━━━━━")
        lines.append("📊 Total Hari Ini:")
        lines.append(f"🔥 Kalori: {totals['calories']} kkal")
        lines.append(f"🥩 Protein: {totals['protein']}g")
        lines.append(f"🍚 Karbo: {totals['carbs']}g")
        lines.append(f"🧈 Lemak: {totals['fat']}g")

        await query.edit_message_text("\n".join(lines))

    elif action == "undo_last":
        # Undo last entry
        deleted = delete_last_entry(user_id)
        if deleted:
            await query.edit_message_text(
                f"🗑️ Dihapus: {deleted['name']} ({deleted['calories']} kkal)\n"
                f"📅 {deleted['date']} {deleted['time']}"
            )
        else:
            await query.edit_message_text("❌ Tidak ada entri yang bisa dihapus.")

    elif action == "log_again":
        await query.edit_message_text(
            "📝 Kirim foto atau ketik nama makanan berikutnya!"
        )

    elif action == "cancel":
        await query.edit_message_text("❌ Dibatalkan.")


# ============================================================
# FAVORITES COMMANDS & CALLBACKS
# ============================================================

async def favorites_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /favorites command - show and log favorite foods."""
    if not is_sheets_configured():
        await update.message.reply_text(
            "⚠️ Fitur tracking belum dikonfigurasi.\n"
            "Hubungi admin untuk setup Google Sheets."
        )
        return

    user_id = update.effective_user.id
    favorites = get_user_favorites(user_id)

    if not favorites:
        # Check for suggestions from history
        suggestions = suggest_favorites_from_history(user_id)
        if suggestions:
            lines = ["⭐ Belum ada makanan favorit.\n"]
            lines.append("💡 Berdasarkan riwayat, mungkin kamu mau menambahkan:")
            for food in suggestions:
                lines.append(f"  • {food['name']} ({food['count']}x dicatat)")
            lines.append("\nGunakan /addfav untuk menambahkan favorit.")
            await update.message.reply_text("\n".join(lines))
        else:
            await update.message.reply_text(
                "⭐ Belum ada makanan favorit.\n\n"
                "Gunakan /addfav untuk menambahkan makanan favorit,\n"
                "atau log makanan beberapa kali agar muncul saran!"
            )
        return

    lines = ["⭐ Makanan Favorit\n"]
    lines.append("Tekan tombol untuk langsung log makanan:\n")

    await update.message.reply_text(
        "\n".join(lines),
        reply_markup=get_favorites_keyboard(favorites)
    )


async def addfav_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /addfav command - add food to favorites."""
    if not is_sheets_configured():
        await update.message.reply_text(
            "⚠️ Fitur tracking belum dikonfigurasi.\n"
            "Hubungi admin untuk setup Google Sheets."
        )
        return

    user_id = update.effective_user.id

    # Get recent entries to pick from
    recent = get_recent_entries(user_id, limit=5)

    if not recent:
        await update.message.reply_text(
            "⚠️ Belum ada makanan yang dicatat.\n"
            "Log makanan dulu, baru bisa ditambahkan ke favorit."
        )
        return

    await update.message.reply_text(
        "⭐ Pilih makanan untuk ditambahkan ke favorit:",
        reply_markup=get_recent_foods_keyboard(recent)
    )


async def delfav_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /delfav command - delete a favorite."""
    if not is_sheets_configured():
        await update.message.reply_text(
            "⚠️ Fitur tracking belum dikonfigurasi.\n"
            "Hubungi admin untuk setup Google Sheets."
        )
        return

    user_id = update.effective_user.id
    favorites = get_user_favorites(user_id)

    if not favorites:
        await update.message.reply_text("⭐ Belum ada makanan favorit.")
        return

    await update.message.reply_text(
        "🗑️ Pilih favorit yang mau dihapus:",
        reply_markup=get_favorites_delete_keyboard(favorites)
    )


async def handle_favorite_callback(query, user_id: int, action: str, context) -> None:
    """Handle fav: callbacks."""
    if action == "add_new":
        # Show recent foods to add
        recent = get_recent_entries(user_id, limit=5)
        if not recent:
            await query.edit_message_text(
                "⚠️ Belum ada makanan yang dicatat.\n"
                "Log makanan dulu, baru bisa ditambahkan ke favorit."
            )
            return

        await query.edit_message_text(
            "⭐ Pilih makanan untuk ditambahkan ke favorit:",
            reply_markup=get_recent_foods_keyboard(recent)
        )
        return

    # Log the favorite
    food_name = action
    favorite = get_favorite_by_name(user_id, food_name)

    if not favorite:
        await query.edit_message_text(f"❌ Favorit '{food_name}' tidak ditemukan.")
        return

    # Log the food
    food_data = {
        "name": favorite["name"],
        "calories": favorite["calories"],
        "protein": favorite["protein"],
        "carbs": favorite["carbs"],
        "fat": favorite["fat"],
        "portion": favorite["portion"]
    }

    if log_food_entry(user_id, food_data):
        increment_favorite_usage(user_id, food_name)
        await query.edit_message_text(
            f"✅ Dicatat: {favorite['name']}\n"
            f"📊 {favorite['calories']} kkal | "
            f"P: {favorite['protein']}g | "
            f"K: {favorite['carbs']}g | "
            f"L: {favorite['fat']}g",
            reply_markup=get_post_analysis_keyboard()
        )
    else:
        await query.edit_message_text("❌ Gagal mencatat makanan.")


async def handle_add_favorite_callback(query, user_id: int, food_name: str) -> None:
    """Handle addfav: callbacks."""
    # Get the food data from recent entries
    recent = get_recent_entries(user_id, limit=10)
    food_data = None
    for entry in recent:
        if entry.get("name") == food_name:
            food_data = {
                "name": entry["name"],
                "calories": entry["calories"],
                "protein": entry["protein"],
                "carbs": entry["carbs"],
                "fat": entry["fat"],
                "portion": entry.get("portion", "1 porsi")
            }
            break

    if not food_data:
        await query.edit_message_text(f"❌ Makanan '{food_name}' tidak ditemukan.")
        return

    if add_to_favorites(user_id, food_data):
        await query.edit_message_text(
            f"⭐ Ditambahkan ke favorit: {food_name}\n\n"
            "Gunakan /favorites untuk melihat dan log favorit."
        )
    else:
        await query.edit_message_text("❌ Gagal menambahkan ke favorit.")


async def handle_delete_favorite_callback(query, user_id: int, food_name: str) -> None:
    """Handle delfav: callbacks."""
    if remove_from_favorites(user_id, food_name):
        await query.edit_message_text(f"🗑️ Dihapus dari favorit: {food_name}")
    else:
        await query.edit_message_text(f"❌ Gagal menghapus favorit.")


# ============================================================
# TEMPLATES COMMANDS & CALLBACKS
# ============================================================

async def templates_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /templates command - show and log meal templates."""
    if not is_sheets_configured():
        await update.message.reply_text(
            "⚠️ Fitur tracking belum dikonfigurasi.\n"
            "Hubungi admin untuk setup Google Sheets."
        )
        return

    user_id = update.effective_user.id
    templates = get_user_templates(user_id)

    if not templates:
        await update.message.reply_text(
            "🍱 Belum ada template makanan.\n\n"
            "Template adalah kombinasi makanan yang sering kamu makan bersama.\n"
            "Contoh: 'Sarapan' = nasi goreng + telur + teh manis\n\n"
            "Gunakan /newtemplate <nama> untuk membuat template baru.\n"
            "Contoh: /newtemplate Sarapan"
        )
        return

    lines = ["🍱 Template Makanan\n"]
    lines.append("Tekan tombol untuk langsung log semua makanan:\n")

    await update.message.reply_text(
        "\n".join(lines),
        reply_markup=get_templates_keyboard(templates)
    )


async def newtemplate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /newtemplate command - start template creation."""
    if not is_sheets_configured():
        await update.message.reply_text(
            "⚠️ Fitur tracking belum dikonfigurasi.\n"
            "Hubungi admin untuk setup Google Sheets."
        )
        return ConversationHandler.END

    # Get template name from args
    if not context.args:
        await update.message.reply_text(
            "⚠️ Mohon berikan nama template.\n"
            "Contoh: /newtemplate Sarapan"
        )
        return ConversationHandler.END

    template_name = " ".join(context.args)
    context.user_data["template_name"] = template_name
    context.user_data["template_foods"] = []

    await update.message.reply_text(
        f"🍱 Membuat template: {template_name}\n\n"
        "Kirim nama makanan satu per satu.\n"
        "Contoh: nasi goreng\n\n"
        "Ketik /done jika sudah selesai.\n"
        "Ketik /cancel untuk membatalkan.",
        reply_markup=get_template_creation_keyboard()
    )

    return ADDING_FOODS


async def template_add_food(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle food input during template creation."""
    text = update.message.text

    if text.startswith("/"):
        return ADDING_FOODS

    # Analyze the food to get nutrition data
    await update.message.reply_text("🔄 Menganalisis makanan...")

    try:
        food_description, weight_grams = parse_weight_from_text(text)
        if not food_description.strip():
            food_description = text

        result = await analyze_food_text(food_description, weight_grams=weight_grams)

        if "error" in result:
            await update.message.reply_text(
                f"❌ {result['error']}\n"
                "Coba ketik makanan lain atau /done untuk selesai."
            )
            return ADDING_FOODS

        foods = result.get("foods", [])
        if not foods:
            await update.message.reply_text(
                "❌ Tidak bisa mengenali makanan.\n"
                "Coba ketik lebih spesifik."
            )
            return ADDING_FOODS

        # Add to template foods
        for food in foods:
            context.user_data["template_foods"].append(food)

        # Show confirmation
        food_names = [f.get("name", "") for f in foods]
        total_foods = len(context.user_data["template_foods"])

        await update.message.reply_text(
            f"✅ Ditambahkan: {', '.join(food_names)}\n"
            f"📝 Total makanan di template: {total_foods}\n\n"
            "Kirim makanan lagi atau /done untuk selesai.",
            reply_markup=get_template_creation_keyboard()
        )

        return ADDING_FOODS

    except Exception as e:
        logger.error(f"Error adding food to template: {e}")
        await update.message.reply_text(
            "❌ Terjadi kesalahan. Coba lagi."
        )
        return ADDING_FOODS


async def template_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /done command - finish template creation."""
    user_id = update.effective_user.id
    template_name = context.user_data.get("template_name", "Template")
    template_foods = context.user_data.get("template_foods", [])

    if not template_foods:
        await update.message.reply_text(
            "⚠️ Template kosong. Tambahkan minimal 1 makanan.\n"
            "Ketik /cancel untuk membatalkan."
        )
        return ADDING_FOODS

    # Create the template
    template_id = create_template(user_id, template_name, template_foods)

    if template_id:
        # Calculate totals for display
        total_cal = sum(f.get("calories", 0) for f in template_foods)
        total_protein = sum(f.get("protein", 0) for f in template_foods)
        total_carbs = sum(f.get("carbs", 0) for f in template_foods)
        total_fat = sum(f.get("fat", 0) for f in template_foods)

        lines = [f"✅ Template '{template_name}' berhasil dibuat!\n"]
        lines.append("📋 Isi template:")
        for food in template_foods:
            lines.append(f"  • {food.get('name', '')} ({food.get('calories', 0)} kkal)")
        lines.append(f"\n📊 Total: {total_cal} kkal | P: {total_protein}g | K: {total_carbs}g | L: {total_fat}g")
        lines.append("\nGunakan /templates untuk melihat dan log template.")

        await update.message.reply_text("\n".join(lines))
    else:
        await update.message.reply_text("❌ Gagal membuat template.")

    # Clear user data
    context.user_data.pop("template_name", None)
    context.user_data.pop("template_foods", None)

    return ConversationHandler.END


async def template_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /cancel command - cancel template creation."""
    context.user_data.pop("template_name", None)
    context.user_data.pop("template_foods", None)

    await update.message.reply_text("❌ Pembuatan template dibatalkan.")
    return ConversationHandler.END


async def deltemplate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /deltemplate command - delete a template."""
    if not is_sheets_configured():
        await update.message.reply_text(
            "⚠️ Fitur tracking belum dikonfigurasi.\n"
            "Hubungi admin untuk setup Google Sheets."
        )
        return

    user_id = update.effective_user.id
    templates = get_user_templates(user_id)

    if not templates:
        await update.message.reply_text("🍱 Belum ada template makanan.")
        return

    await update.message.reply_text(
        "🗑️ Pilih template yang mau dihapus:",
        reply_markup=get_templates_delete_keyboard(templates)
    )


async def handle_template_callback(query, user_id: int, action: str, context) -> None:
    """Handle template: callbacks."""
    if action == "create_new":
        await query.edit_message_text(
            "🍱 Untuk membuat template baru, gunakan:\n"
            "/newtemplate <nama template>\n\n"
            "Contoh: /newtemplate Sarapan"
        )
        return

    if action == "done":
        # Trigger done command logic
        template_name = context.user_data.get("template_name", "Template")
        template_foods = context.user_data.get("template_foods", [])

        if not template_foods:
            await query.edit_message_text(
                "⚠️ Template kosong. Tambahkan minimal 1 makanan."
            )
            return

        template_id = create_template(user_id, template_name, template_foods)

        if template_id:
            total_cal = sum(f.get("calories", 0) for f in template_foods)
            lines = [f"✅ Template '{template_name}' berhasil dibuat!\n"]
            lines.append("📋 Isi template:")
            for food in template_foods:
                lines.append(f"  • {food.get('name', '')} ({food.get('calories', 0)} kkal)")
            lines.append(f"\n📊 Total: {total_cal} kkal")

            await query.edit_message_text("\n".join(lines))
        else:
            await query.edit_message_text("❌ Gagal membuat template.")

        context.user_data.pop("template_name", None)
        context.user_data.pop("template_foods", None)
        return

    if action == "cancel":
        context.user_data.pop("template_name", None)
        context.user_data.pop("template_foods", None)
        await query.edit_message_text("❌ Pembuatan template dibatalkan.")
        return

    # Log the template
    template_id = action
    template = get_template_by_id(user_id, template_id)

    if not template:
        await query.edit_message_text("❌ Template tidak ditemukan.")
        return

    # Log all foods from template
    logged_count = log_template(user_id, template_id)

    if logged_count > 0:
        foods = template.get("foods", [])
        lines = [f"✅ Template '{template['name']}' dicatat!\n"]
        lines.append("📋 Makanan yang dicatat:")
        for food in foods:
            lines.append(f"  • {food.get('name', '')} ({food.get('calories', 0)} kkal)")
        lines.append(f"\n📊 Total: {template['total_calories']} kkal")

        await query.edit_message_text(
            "\n".join(lines),
            reply_markup=get_post_analysis_keyboard()
        )
    else:
        await query.edit_message_text("❌ Gagal mencatat template.")


async def handle_delete_template_callback(query, user_id: int, template_id: str) -> None:
    """Handle deltemplate: callbacks."""
    template = get_template_by_id(user_id, template_id)
    template_name = template.get("name", "Template") if template else "Template"

    if delete_template(user_id, template_id):
        await query.edit_message_text(f"🗑️ Dihapus: template '{template_name}'")
    else:
        await query.edit_message_text("❌ Gagal menghapus template.")


async def handle_confirm_callback(query, user_id: int, action: str) -> None:
    """Handle confirm: callbacks."""
    if action == "cancel":
        await query.edit_message_text("❌ Dibatalkan.")


async def setup_bot_commands(application) -> None:
    """Set up bot commands for Telegram menu.

    This registers commands with Telegram so they appear
    when users type '/' in the chat.
    """
    commands = [
        BotCommand("start", "Mulai bot dan lihat cara penggunaan"),
        BotCommand("help", "Panduan lengkap penggunaan bot"),
        BotCommand("today", "Lihat ringkasan kalori hari ini"),
        BotCommand("history", "Lihat riwayat 10 makanan terakhir"),
        BotCommand("undo", "Hapus entri makanan terakhir"),
        BotCommand("favorites", "Lihat dan log makanan favorit"),
        BotCommand("addfav", "Tambah makanan ke favorit"),
        BotCommand("delfav", "Hapus makanan dari favorit"),
        BotCommand("templates", "Lihat dan log template makanan"),
        BotCommand("newtemplate", "Buat template makanan baru"),
        BotCommand("deltemplate", "Hapus template makanan"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Bot commands registered successfully")


def main() -> None:
    """Start the bot."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        return

    # Create application with post_init to register commands
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(setup_bot_commands).build()

    # Template creation conversation handler
    template_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("newtemplate", newtemplate_command)],
        states={
            ADDING_FOODS: [
                CommandHandler("done", template_done),
                CommandHandler("cancel", template_cancel),
                MessageHandler(filters.TEXT & ~filters.COMMAND, template_add_food),
            ],
        },
        fallbacks=[CommandHandler("cancel", template_cancel)],
    )

    # Add handlers (order matters - more specific handlers first)
    application.add_handler(template_conv_handler)
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("today", today_command))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CommandHandler("undo", undo_command))
    # Favorites handlers
    application.add_handler(CommandHandler("favorites", favorites_command))
    application.add_handler(CommandHandler("addfav", addfav_command))
    application.add_handler(CommandHandler("delfav", delfav_command))
    # Templates handlers
    application.add_handler(CommandHandler("templates", templates_command))
    application.add_handler(CommandHandler("deltemplate", deltemplate_command))
    # Callback handler for inline keyboards
    application.add_handler(CallbackQueryHandler(handle_callback))
    # Message handlers
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Start polling
    logger.info("Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
