import json
import google.generativeai as genai
from config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)

PROMPT_TEMPLATE = """Kamu adalah ahli nutrisi Indonesia. Analisis makanan berikut dan berikan estimasi nutrisi.

Berikan response dalam format JSON ONLY (tanpa markdown):
{
  "name": "nama makanan dalam Bahasa Indonesia",
  "calories": angka dalam kkal,
  "protein": angka dalam gram,
  "carbs": angka dalam gram,
  "fat": angka dalam gram,
  "portion": "deskripsi porsi, misal: 1 piring, 1 mangkok"
}

Jika bukan makanan/minuman, return:
{"error": "Tidak dapat mengenali makanan"}"""


async def analyze_food_image(image_bytes: bytes) -> dict:
    """
    Analyze food from image using Gemini Vision.
    Returns: {name, calories, protein, carbs, fat, portion} or {error: "..."}
    """
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")

        image_part = {
            "mime_type": "image/jpeg",
            "data": image_bytes
        }

        response = model.generate_content([PROMPT_TEMPLATE, image_part])
        result_text = response.text.strip()

        # Clean up response if wrapped in markdown code blocks
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
            result_text = result_text.strip()

        return json.loads(result_text)
    except json.JSONDecodeError:
        return {"error": "Tidak dapat memproses respons dari AI"}
    except Exception as e:
        return {"error": f"Terjadi kesalahan: {str(e)}"}


async def analyze_food_text(food_description: str) -> dict:
    """
    Analyze food from text description using Gemini.
    Returns: {name, calories, protein, carbs, fat, portion} or {error: "..."}
    """
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")

        prompt = f"{PROMPT_TEMPLATE}\n\nMakanan: {food_description}"

        response = model.generate_content(prompt)
        result_text = response.text.strip()

        # Clean up response if wrapped in markdown code blocks
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
            result_text = result_text.strip()

        return json.loads(result_text)
    except json.JSONDecodeError:
        return {"error": "Tidak dapat memproses respons dari AI"}
    except Exception as e:
        return {"error": f"Terjadi kesalahan: {str(e)}"}
