import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from config import TELEGRAM_BOT_TOKEN
from gemini_service import analyze_food_image, analyze_food_text

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
Ambil foto makanan kamu dan kirim ke bot. Saya akan menganalisis dan memberikan estimasi:
- Nama makanan
- Kalori (kkal)
- Protein (gram)
- Karbohidrat (gram)
- Lemak (gram)
- Porsi

🔹 Kirim Deskripsi Makanan
Ketik nama dan porsi makanan, contoh:
- "nasi goreng 1 piring"
- "ayam bakar setengah ekor"
- "es teh manis 1 gelas"

❓ Ada pertanyaan? Langsung kirim pesan!"""


def format_nutrition_response(data: dict) -> str:
    """Format nutrition data into a nice response message."""
    if "error" in data:
        return f"❌ {data['error']}"

    return f"""✅ Hasil Analisis!

🍽️ {data.get('name', 'Makanan')}
📊 Kalori: {data.get('calories', 0)} kkal
🥩 Protein: {data.get('protein', 0)}g
🍞 Karbo: {data.get('carbs', 0)}g
🧈 Lemak: {data.get('fat', 0)}g
📏 Porsi: {data.get('portion', '-')}"""


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    await update.message.reply_text(WELCOME_MESSAGE)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    await update.message.reply_text(HELP_MESSAGE)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle photo messages - analyze food from image."""
    await update.message.reply_text("🔄 Menganalisis foto makanan...")

    try:
        # Get the largest photo
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)

        # Download photo as bytes
        photo_bytes = await file.download_as_bytearray()

        # Analyze with Gemini
        result = await analyze_food_image(bytes(photo_bytes))

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

    await update.message.reply_text("🔄 Menganalisis makanan...")

    try:
        # Analyze with Gemini
        result = await analyze_food_text(text)

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
