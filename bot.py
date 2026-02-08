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
    get_entries_by_date,
    get_totals_by_date,
    get_recent_entries,
    delete_last_entry,
    is_sheets_configured,
    set_calorie_target,
    get_calorie_target,
    get_daily_progress
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
/target - Atur target kalori harian

🎯 Contoh Target:
/target 2000 - Set target 2000 kkal/hari
/target - Lihat progress target hari ini
/target 01/02/2024 - Lihat progress tanggal tertentu

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


def format_progress_bar(percentage: float, width: int = 10) -> str:
    """
    Format a progress bar with emoji.

    Args:
        percentage: Progress percentage (0-100+)
        width: Number of blocks in the bar

    Returns:
        Emoji progress bar string
    """
    filled = min(int(percentage / 100 * width), width)
    empty = width - filled

    # Choose color based on percentage threshold
    if percentage >= 100:
        block = "🟥"
    elif percentage >= 90:
        block = "🟧"
    elif percentage >= 80:
        block = "🟨"
    else:
        block = "🟩"

    bar = block * filled + "⬜" * empty

    # Add warning indicator if over limit
    if percentage >= 100:
        return f"{bar} ⚠️"
    return f"{bar} {percentage:.0f}%"


def get_warning_message(status: str, percentage: float, remaining: int) -> str:
    """
    Get warning message based on calorie status.

    Args:
        status: Status string (safe, warning, approaching, over)
        percentage: Current percentage of target
        remaining: Remaining calories (can be negative if over)

    Returns:
        Warning message string, or empty string if no warning needed
    """
    if status == "over":
        over_amount = abs(remaining)
        return f"\n⚠️ Kamu sudah melebihi target sebanyak {over_amount} kkal!"
    elif status == "approaching":
        return f"\n⚡ Hampir mencapai target! Sisa {remaining} kkal lagi."
    elif status == "warning":
        return f"\n📊 Sudah {percentage:.0f}% dari target. Sisa {remaining} kkal."
    return ""


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

    # Parse weight and food name from caption
    food_name_hint, weight_grams = parse_weight_from_text(caption)
    food_name_hint = food_name_hint.strip() or None

    # Step 1: Foto diterima, mengunduh gambar
    food_label = food_name_hint or "makanan"
    if weight_grams:
        status_text = f"📸 Foto {food_label} ({weight_grams} gram) diterima! Mengunduh gambar..."
    else:
        status_text = f"📸 Foto {food_label} diterima! Mengunduh gambar..."
    status_msg = await update.message.reply_text(status_text)

    try:
        # Get the largest photo
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)

        # Download photo as bytes
        photo_bytes = await file.download_as_bytearray()
        photo_bytes_raw = bytes(photo_bytes)

        # Step 2: Menganalisis nutrisi
        await status_msg.edit_text("🔍 Foto berhasil diunduh! Sedang menganalisis nutrisi makanan...")

        # Pass weight to analyzer
        result = await analyze_food_image(photo_bytes_raw, weight_grams=weight_grams, food_name=food_name_hint)

        # Send response
        response = format_nutrition_response(result)

        # Log to Google Sheets if configured and successful
        logged = False
        if "error" not in result and is_sheets_configured():
            # Step 3: Menyimpan ke catatan
            await status_msg.edit_text("💾 Analisis selesai! Menyimpan ke catatan...")

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

            # Add calorie warning if target is set
            progress = get_daily_progress(user_id)
            if progress["target"] is not None and progress["status"] != "safe":
                warning = get_warning_message(
                    progress["status"],
                    progress["percentage"],
                    progress["remaining"]
                )
                if warning:
                    response += warning

        # Step 4: Final status
        await status_msg.edit_text("✅ Selesai!")
        await update.message.reply_text(response)

    except Exception as e:
        logger.error(f"Error handling photo: {e}")
        await status_msg.edit_text("❌ Maaf, terjadi kesalahan saat memproses foto. Coba kirim ulang ya!")


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

    # Step 1: Menerima pesanan
    if weight_grams:
        status_text = f'✍️ Menerima pesanan "{food_description}" ({weight_grams} gram)! Sedang menganalisis nutrisi...'
    else:
        status_text = f'✍️ Menerima pesanan "{text}"! Sedang menganalisis nutrisi...'
    status_msg = await update.message.reply_text(status_text)

    try:
        # Pass weight to analyzer
        result = await analyze_food_text(food_description, weight_grams=weight_grams)

        # Send response
        response = format_nutrition_response(result)

        # Log to Google Sheets if configured and successful
        logged = False
        if "error" not in result and is_sheets_configured():
            # Step 2: Menyimpan ke catatan
            await status_msg.edit_text("💾 Analisis selesai! Menyimpan ke catatan...")

            user_id = update.effective_user.id
            foods = result.get("foods", [])
            if foods:
                logged_count = log_multiple_foods(user_id, foods)
                if logged_count > 0:
                    logged = True

        if logged:
            response += "\n\n✅ Tersimpan ke log"

            # Add calorie warning if target is set
            progress = get_daily_progress(user_id)
            if progress["target"] is not None and progress["status"] != "safe":
                warning = get_warning_message(
                    progress["status"],
                    progress["percentage"],
                    progress["remaining"]
                )
                if warning:
                    response += warning

        # Step 3: Final status
        await status_msg.edit_text("✅ Selesai!")
        await update.message.reply_text(response)

    except Exception as e:
        logger.error(f"Error handling text: {e}")
        await status_msg.edit_text("❌ Maaf, terjadi kesalahan saat menganalisis. Coba kirim ulang ya!")


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
    progress = get_daily_progress(user_id)

    today_str = datetime.now().strftime("%d %b %Y")

    if not entries:
        message = (
            f"📅 Makanan Hari Ini ({today_str})\n\n"
            "Belum ada makanan yang dicatat hari ini.\n"
            "Kirim foto atau ketik nama makanan untuk mulai tracking!"
        )
        # Suggest setting target if not set
        if progress["target"] is None:
            message += "\n\n💡 Tip: Gunakan /target untuk mengatur target kalori harian."
        await update.message.reply_text(message)
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

    # Add progress bar section if target is set
    if progress["target"] is not None:
        bar = format_progress_bar(progress["percentage"])
        lines.append("\n━━━━━━━━━━━━━━━━━━")
        lines.append("🎯 Progress Target:")
        lines.append(f"Target: {progress['target']} kkal")
        lines.append(f"Sisa: {max(0, progress['remaining'])} kkal")
        lines.append(f"\n{bar}")

        # Add warning if applicable
        warning = get_warning_message(
            progress["status"],
            progress["percentage"],
            progress["remaining"]
        )
        if warning:
            lines.append(warning)
    else:
        lines.append("\n💡 Tip: Gunakan /target untuk mengatur target kalori harian.")

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


def parse_date_arg(date_arg: str) -> tuple[str, str]:
    """
    Parse date argument into YYYY-MM-DD format.

    Args:
        date_arg: Date string in various formats

    Returns:
        Tuple of (date_str in YYYY-MM-DD, display_str for user)
        Returns (None, None) if parsing fails
    """
    # Try different date formats
    formats = [
        ("%Y-%m-%d", None),      # 2024-02-01
        ("%d/%m/%Y", None),      # 01/02/2024
        ("%d-%m-%Y", None),      # 01-02-2024
        ("%d/%m/%y", None),      # 01/02/24
        ("%d-%m-%y", None),      # 01-02-24
    ]

    for fmt, _ in formats:
        try:
            parsed = datetime.strptime(date_arg, fmt)
            date_str = parsed.strftime("%Y-%m-%d")
            display_str = parsed.strftime("%d %b %Y")
            return date_str, display_str
        except ValueError:
            continue

    return None, None


async def target_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /target command - set or view daily calorie target."""
    if not is_sheets_configured():
        await update.message.reply_text(
            "⚠️ Fitur tracking belum dikonfigurasi.\n"
            "Hubungi admin untuk setup Google Sheets."
        )
        return

    user_id = update.effective_user.id
    args = context.args

    # If no arguments, show current target with today's progress
    if not args:
        progress = get_daily_progress(user_id)

        if progress["target"] is None:
            await update.message.reply_text(
                "🎯 Target Kalori Harian\n\n"
                "Kamu belum mengatur target kalori.\n\n"
                "Gunakan: /target <jumlah>\n"
                "Contoh: /target 2000"
            )
            return

        # Show current progress
        bar = format_progress_bar(progress["percentage"])
        lines = [
            "🎯 Target Kalori Harian\n",
            f"Target: {progress['target']} kkal",
            f"Tercapai: {progress['current']} kkal",
            f"Sisa: {max(0, progress['remaining'])} kkal\n",
            f"Progress: {bar}"
        ]

        # Add warning if applicable
        warning = get_warning_message(
            progress["status"],
            progress["percentage"],
            progress["remaining"]
        )
        if warning:
            lines.append(warning)

        await update.message.reply_text("\n".join(lines))
        return

    arg = args[0]

    # Check if argument is a date
    date_str, display_str = parse_date_arg(arg)
    if date_str:
        # Show progress for specific date
        progress = get_daily_progress(user_id, date_str)

        if progress["target"] is None:
            await update.message.reply_text(
                f"🎯 Progress Kalori ({display_str})\n\n"
                "Kamu belum mengatur target kalori.\n\n"
                "Gunakan: /target <jumlah>\n"
                "Contoh: /target 2000"
            )
            return

        if progress["current"] == 0:
            await update.message.reply_text(
                f"📅 Progress Kalori ({display_str})\n\n"
                f"Target: {progress['target']} kkal\n"
                "Tidak ada makanan yang dicatat pada tanggal ini."
            )
            return

        bar = format_progress_bar(progress["percentage"])
        lines = [
            f"📅 Progress Kalori ({display_str})\n",
            f"Target: {progress['target']} kkal",
            f"Tercapai: {progress['current']} kkal",
            f"Sisa: {max(0, progress['remaining'])} kkal\n",
            f"Progress: {bar}"
        ]

        # Add status message
        if progress["status"] == "over":
            over_amount = abs(progress["remaining"])
            lines.append(f"\n⚠️ Melebihi target sebanyak {over_amount} kkal")
        elif progress["status"] == "safe":
            lines.append(f"\n✅ Dalam batas target")

        await update.message.reply_text("\n".join(lines))
        return

    # Try to parse as target value (number)
    try:
        target = int(arg)
    except ValueError:
        await update.message.reply_text(
            "❌ Format tidak valid.\n\n"
            "Gunakan:\n"
            "• /target <angka> - Set target kalori\n"
            "• /target <tanggal> - Lihat progress tanggal tertentu\n\n"
            "Contoh:\n"
            "• /target 2000\n"
            "• /target 01/02/2024\n"
            "• /target 2024-02-01"
        )
        return

    # Validate range (500-10000 kkal)
    if target < 500 or target > 10000:
        await update.message.reply_text(
            "❌ Target harus antara 500 - 10000 kkal.\n\n"
            "Contoh: /target 2000"
        )
        return

    # Save target
    if set_calorie_target(user_id, target):
        progress = get_daily_progress(user_id)
        bar = format_progress_bar(progress["percentage"])

        await update.message.reply_text(
            f"✅ Target kalori harian diatur: {target} kkal\n\n"
            f"Progress hari ini:\n"
            f"Tercapai: {progress['current']} kkal\n"
            f"Sisa: {max(0, progress['remaining'])} kkal\n\n"
            f"{bar}"
        )
    else:
        await update.message.reply_text(
            "❌ Gagal menyimpan target. Coba lagi nanti."
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
        BotCommand("target", "Atur target kalori harian"),
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
    application.add_handler(CommandHandler("target", target_command))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Start polling
    logger.info("Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
