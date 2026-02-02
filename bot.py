import logging
from datetime import datetime
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from config import TELEGRAM_BOT_TOKEN
from gemini_service import analyze_food_image, analyze_food_text, parse_weight_from_text
from sheets_service import (
    log_food_entry,
    log_multiple_foods,
    get_today_entries,
    get_today_totals,
    get_recent_entries,
    delete_last_entry,
    is_sheets_configured
)
from imagekit_service import upload_food_image, is_imagekit_configured

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

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

        await update.message.reply_text(response)

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

        await update.message.reply_text(response)

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

    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("today", today_command))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CommandHandler("undo", undo_command))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Start polling
    logger.info("Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
