import json
import google.generativeai as genai
from config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)

PROMPT_TEMPLATE = """Kamu adalah ahli nutrisi Indonesia. Analisis SEMUA makanan yang ada dalam gambar.
PENTING: Pisahkan setiap jenis makanan yang berbeda dengan estimasi nutrisi masing-masing.

Berikan response dalam format JSON ONLY (tanpa markdown):
{
  "foods": [
    {
      "name": "nama makanan 1 dalam Bahasa Indonesia",
      "calories": angka dalam kkal,
      "protein": angka dalam gram,
      "carbs": angka dalam gram,
      "fat": angka dalam gram,
      "portion": "deskripsi porsi, misal: 150 gram, 1 potong"
    },
    {
      "name": "nama makanan 2",
      "calories": angka dalam kkal,
      "protein": angka dalam gram,
      "carbs": angka dalam gram,
      "fat": angka dalam gram,
      "portion": "deskripsi porsi"
    }
  ],
  "total": {
    "calories": total semua kkal,
    "protein": total semua gram,
    "carbs": total semua gram,
    "fat": total semua gram
  }
}

Jika hanya ada 1 makanan, tetap gunakan format array dengan 1 item.
Jika bukan makanan/minuman, return:
{"error": "Tidak dapat mengenali makanan"}"""


def normalize_response(data: dict) -> dict:
    """
    Normalize response to ensure consistent format.
    Converts old single-food format to new multi-food format for backward compatibility.
    """
    if "error" in data:
        return data

    if "foods" in data:
        return data  # Already in new format

    # Convert old format (single food) to new format
    if "name" in data:
        return {
            "foods": [data],
            "total": {
                "calories": data.get("calories", 0),
                "protein": data.get("protein", 0),
                "carbs": data.get("carbs", 0),
                "fat": data.get("fat", 0)
            }
        }

    return {"error": "Format respons tidak valid"}


async def analyze_food_image(image_bytes: bytes) -> dict:
    """
    Analyze food from image using Gemini Vision.
    Returns: {foods: [...], total: {...}} or {error: "..."}
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

        return normalize_response(json.loads(result_text))
    except json.JSONDecodeError:
        return {"error": "Tidak dapat memproses respons dari AI"}
    except Exception as e:
        return {"error": f"Terjadi kesalahan: {str(e)}"}


async def analyze_food_text(food_description: str) -> dict:
    """
    Analyze food from text description using Gemini.
    Returns: {foods: [...], total: {...}} or {error: "..."}
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

        return normalize_response(json.loads(result_text))
    except json.JSONDecodeError:
        return {"error": "Tidak dapat memproses respons dari AI"}
    except Exception as e:
        return {"error": f"Terjadi kesalahan: {str(e)}"}
