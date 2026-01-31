import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from config import TELEGRAM_BOT_TOKEN
from gemini_service import analyze_food_image, analyze_food_text, parse_weight_from_text

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

        # Pass weight to analyzer
        result = await analyze_food_image(bytes(photo_bytes), weight_grams=weight_grams)

        # Send response
        response = format_nutrition_response(result)
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
        await update.message.reply_text(response)

    except Exception as e:
        logger.error(f"Error handling text: {e}")
        await update.message.reply_text("❌ Maaf, terjadi kesalahan. Coba lagi nanti.")


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
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Start polling
    logger.info("Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
