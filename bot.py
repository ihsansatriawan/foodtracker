import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

from config import TELEGRAM_BOT_TOKEN
from gemini_service import (
    analyze_food_image,
    analyze_food_text,
    analyze_food_image_with_learning,
    analyze_food_text_with_learning,
    parse_weight_from_text
)
from sheets_service import (
    log_food_entry,
    log_multiple_foods,
    get_today_entries,
    get_today_totals,
    get_recent_entries,
    delete_last_entry,
    delete_entry_by_id,
    update_entry_feedback,
    get_user_correction_history,
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
/accuracy - Lihat statistik akurasi estimasi

🎯 Feedback Loop:
Setelah mencatat makanan, gunakan tombol feedback untuk:
✅ Benar - Konfirmasi estimasi akurat
🔧 Koreksi Berat - Berikan berat sebenarnya
❌ Salah - Hapus dan kirim ulang

Semakin banyak feedback, semakin akurat estimasi untuk kamu!

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


def build_feedback_keyboard(entry_ids: list) -> InlineKeyboardMarkup:
    """Build inline keyboard untuk feedback setelah food logging."""
    # If multiple entries, use first entry ID for simplicity
    # In production, might want to handle multiple entries differently
    entry_id = entry_ids[0] if entry_ids else "unknown"

    keyboard = [
        [
            InlineKeyboardButton("✅ Benar", callback_data=f"feedback:correct:{entry_id}"),
            InlineKeyboardButton("🔧 Koreksi Berat", callback_data=f"feedback:adjust:{entry_id}"),
            InlineKeyboardButton("❌ Salah", callback_data=f"feedback:wrong:{entry_id}"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


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

        # Pass weight to analyzer with learning
        user_id = update.effective_user.id
        result = await analyze_food_image_with_learning(
            photo_bytes_raw,
            weight_grams=weight_grams,
            user_id=user_id
        )

        # Send response
        response = format_nutrition_response(result)

        # Add adjustment note if applied
        if "_adjustment_applied" in result:
            adj = result["_adjustment_applied"]
            corrections_count = len(get_user_correction_history(user_id))
            response += f"\n\n💡 Estimasi disesuaikan berdasarkan {corrections_count} koreksi sebelumnya"

        # Log to Google Sheets if configured and successful
        entry_ids = []
        if "error" not in result and is_sheets_configured():
            foods = result.get("foods", [])
            if foods:
                # Upload image to ImageKit for permanent storage
                image_url = ""
                if is_imagekit_configured():
                    food_name = foods[0].get('name', 'food') if foods else 'food'
                    image_url = upload_food_image(photo_bytes_raw, user_id, food_name) or ""

                entry_ids = log_multiple_foods(user_id, foods, image_url)

        if entry_ids:
            response += "\n\n✅ Tersimpan ke log"
            # Send response with feedback keyboard
            await update.message.reply_text(
                response,
                reply_markup=build_feedback_keyboard(entry_ids)
            )
        else:
            await update.message.reply_text(response)

    except Exception as e:
        logger.error(f"Error handling photo: {e}")
        await update.message.reply_text("❌ Maaf, terjadi kesalahan. Coba lagi nanti.")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages - analyze food from description or handle weight correction."""
    text = update.message.text
    user_id = update.effective_user.id

    # Skip if it's a command
    if text.startswith("/"):
        return

    # Check if awaiting weight correction
    if context.user_data.get("awaiting_weight"):
        weight_text = text.strip()
        _, weight = parse_weight_from_text(weight_text + " gram")

        if weight:
            entry_id = context.user_data.get("pending_correction")
            success = update_entry_feedback(entry_id, user_id, actual_weight=weight)

            context.user_data["awaiting_weight"] = False
            context.user_data["pending_correction"] = None

            if success:
                await update.message.reply_text(
                    f"✅ Berat diupdate menjadi {weight}g\n"
                    "Terima kasih atas koreksinya! Ini akan membantu meningkatkan akurasi estimasi."
                )
            else:
                await update.message.reply_text(
                    "❌ Gagal mengupdate berat. Silakan coba lagi."
                )
            return
        else:
            await update.message.reply_text(
                "❌ Format berat tidak valid. Contoh: 200 atau 200g\n"
                "Silakan coba lagi:"
            )
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
        # Pass weight to analyzer with learning
        result = await analyze_food_text_with_learning(
            food_description,
            weight_grams=weight_grams,
            user_id=user_id
        )

        # Send response
        response = format_nutrition_response(result)

        # Add adjustment note if applied
        if "_adjustment_applied" in result:
            adj = result["_adjustment_applied"]
            corrections_count = len(get_user_correction_history(user_id))
            response += f"\n\n💡 Estimasi disesuaikan berdasarkan {corrections_count} koreksi sebelumnya"

        # Log to Google Sheets if configured and successful
        entry_ids = []
        if "error" not in result and is_sheets_configured():
            foods = result.get("foods", [])
            if foods:
                entry_ids = log_multiple_foods(user_id, foods)

        if entry_ids:
            response += "\n\n✅ Tersimpan ke log"
            # Send response with feedback keyboard
            await update.message.reply_text(
                response,
                reply_markup=build_feedback_keyboard(entry_ids)
            )
        else:
            await update.message.reply_text(response)

    except Exception as e:
        logger.error(f"Error handling text: {e}")
        await update.message.reply_text("❌ Maaf, terjadi kesalahan. Coba lagi nanti.")


async def handle_feedback_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback from feedback buttons."""
    query = update.callback_query
    await query.answer()

    data = query.data  # format: "feedback:{action}:{entry_id}"
    parts = data.split(":")
    if len(parts) != 3:
        await query.message.reply_text("❌ Data callback tidak valid.")
        return

    _, action, entry_id = parts
    user_id = query.from_user.id

    if action == "correct":
        # Mark entry as verified
        success = update_entry_feedback(entry_id, user_id, verified=True)
        await query.edit_message_reply_markup(reply_markup=None)
        if success:
            await query.message.reply_text("✅ Terima kasih! Data telah diverifikasi.")
        else:
            await query.message.reply_text("❌ Gagal memverifikasi data.")

    elif action == "adjust":
        # Store entry_id in context for weight correction flow
        context.user_data["pending_correction"] = entry_id
        context.user_data["awaiting_weight"] = True
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            "📏 Berapa berat sebenarnya? (dalam gram)\n"
            "Contoh: 200 atau 200g"
        )

    elif action == "wrong":
        # Delete entry and ask for re-submission
        success = delete_entry_by_id(entry_id, user_id)
        await query.edit_message_reply_markup(reply_markup=None)
        if success:
            await query.message.reply_text(
                "❌ Entry dihapus.\n"
                "Silakan kirim ulang foto/deskripsi yang benar."
            )
        else:
            await query.message.reply_text("❌ Gagal menghapus entry.")


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


async def accuracy_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /accuracy command - show user's correction statistics."""
    if not is_sheets_configured():
        await update.message.reply_text(
            "⚠️ Fitur tracking belum dikonfigurasi.\n"
            "Hubungi admin untuk setup Google Sheets."
        )
        return

    user_id = update.effective_user.id
    corrections = get_user_correction_history(user_id)

    if not corrections:
        await update.message.reply_text(
            "📊 Belum ada data koreksi.\n"
            "Gunakan tombol 'Koreksi Berat' untuk membantu meningkatkan akurasi."
        )
        return

    # Calculate stats
    total_corrections = len(corrections)
    valid_ratios = [c["correction_ratio"] for c in corrections if c["correction_ratio"]]

    if not valid_ratios:
        await update.message.reply_text(
            "📊 Data koreksi ditemukan tapi belum lengkap.\n"
            "Terus berikan feedback untuk meningkatkan akurasi!"
        )
        return

    avg_ratio = sum(valid_ratios) / len(valid_ratios)

    # Determine trend
    if avg_ratio > 1.1:
        trend = "📈 AI cenderung underestimate (terlalu rendah)"
        tip = "Sistem akan mulai mengestimasi lebih tinggi untuk Anda"
    elif avg_ratio < 0.9:
        trend = "📉 AI cenderung overestimate (terlalu tinggi)"
        tip = "Sistem akan mulai mengestimasi lebih rendah untuk Anda"
    else:
        trend = "✅ Estimasi sudah cukup akurat"
        tip = "Terus berikan feedback untuk menjaga akurasi"

    message = f"""📊 *Statistik Akurasi Anda*

Total koreksi: {total_corrections}
Rata-rata rasio: {avg_ratio:.2f}x

{trend}

💡 {tip}

_Koreksi terakhir:_
"""

    for c in corrections[-3:]:
        if c["ai_estimate"] and c["actual_weight"]:
            message += f"\n• {c['food_name']}: {c['ai_estimate']}g → {c['actual_weight']}g"

    await update.message.reply_text(message, parse_mode="Markdown")


def main() -> None:
    """Start the bot."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        return

    # Create application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("today", today_command))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CommandHandler("undo", undo_command))
    application.add_handler(CommandHandler("accuracy", accuracy_command))
    application.add_handler(CallbackQueryHandler(handle_feedback_callback, pattern="^feedback:"))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Start polling
    logger.info("Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
