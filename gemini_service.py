import json
import re
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
      "portion": "deskripsi porsi, misal: 150 gram, 1 potong",
      "reference_source": "nama database referensi",
      "reference_url": "URL ke sumber data"
    },
    {
      "name": "nama makanan 2",
      "calories": angka dalam kkal,
      "protein": angka dalam gram,
      "carbs": angka dalam gram,
      "fat": angka dalam gram,
      "portion": "deskripsi porsi",
      "reference_source": "nama database referensi",
      "reference_url": "URL ke sumber data"
    }
  ],
  "total": {
    "calories": total semua kkal,
    "protein": total semua gram,
    "carbs": total semua gram,
    "fat": total semua gram
  }
}

Sertakan sumber referensi nutrisi yang digunakan:
- reference_source: nama database (contoh: "TKPI Indonesia", "USDA FoodData", "FatSecret Indonesia")
- reference_url: URL valid ke sumber data

Prioritas sumber referensi:
1. TKPI (Tabel Komposisi Pangan Indonesia) - https://www.panganku.org/id-ID/view
2. USDA FoodData Central - https://fdc.nal.usda.gov
3. FatSecret Indonesia - https://www.fatsecret.co.id

Jika hanya ada 1 makanan, tetap gunakan format array dengan 1 item.
Jika bukan makanan/minuman, return:
{"error": "Tidak dapat mengenali makanan"}"""

PROMPT_WITH_WEIGHT = """Kamu adalah ahli nutrisi Indonesia. Analisis makanan dalam gambar.
PENTING: User sudah menimbang makanan ini dengan berat {weight} gram.
Hitung kandungan nutrisi berdasarkan berat {weight} gram tersebut.

Berikan response dalam format JSON ONLY (tanpa markdown):
{{
  "foods": [
    {{
      "name": "nama makanan dalam Bahasa Indonesia",
      "calories": angka dalam kkal untuk {weight} gram,
      "protein": angka dalam gram,
      "carbs": angka dalam gram,
      "fat": angka dalam gram,
      "weight_grams": {weight},
      "reference_source": "nama database referensi",
      "reference_url": "URL ke sumber data"
    }}
  ],
  "total": {{
    "calories": total kkal,
    "protein": total gram,
    "carbs": total gram,
    "fat": total gram,
    "weight_grams": {weight}
  }}
}}

Sertakan sumber referensi nutrisi yang digunakan:
- reference_source: nama database (contoh: "TKPI Indonesia", "USDA FoodData", "FatSecret Indonesia")
- reference_url: URL valid ke sumber data

Prioritas sumber referensi:
1. TKPI (Tabel Komposisi Pangan Indonesia) - https://www.panganku.org/id-ID/view
2. USDA FoodData Central - https://fdc.nal.usda.gov
3. FatSecret Indonesia - https://www.fatsecret.co.id

Jika bukan makanan/minuman, return:
{{"error": "Tidak dapat mengenali makanan"}}"""


def parse_weight_from_text(text: str) -> tuple[str, int | None]:
    """
    Parse weight (gram) from text input.
    Returns: (cleaned_text, weight_in_grams)

    Examples:
        "250 gram" -> ("", 250)
        "250g" -> ("", 250)
        "nasi goreng 200 gram" -> ("nasi goreng", 200)
        "0.5 kg" -> ("", 500)
        "nasi goreng 1 piring" -> ("nasi goreng 1 piring", None)
    """
    if not text:
        return (text, None)

    patterns = [
        r'(\d+(?:\.\d+)?)\s*(?:gram|gr|g)\b',  # 250 gram, 250g, 250 gr
        r'(\d+(?:\.\d+)?)\s*(?:kilogram|kg)\b', # 0.5 kg, 1 kilogram
    ]

    weight = None
    cleaned_text = text

    # Match gram patterns
    match = re.search(patterns[0], text, re.IGNORECASE)
    if match:
        weight = int(float(match.group(1)))
        cleaned_text = re.sub(patterns[0], '', text, flags=re.IGNORECASE).strip()

    # Match kg patterns (convert to gram)
    if weight is None:
        match = re.search(patterns[1], text, re.IGNORECASE)
        if match:
            weight = int(float(match.group(1)) * 1000)
            cleaned_text = re.sub(patterns[1], '', text, flags=re.IGNORECASE).strip()

    # Validate weight (must be positive and reasonable)
    if weight is not None and (weight <= 0 or weight > 10000):
        weight = None
        cleaned_text = text

    return (cleaned_text, weight)


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


async def analyze_food_image(image_bytes: bytes, weight_grams: int | None = None) -> dict:
    """
    Analyze food from image using Gemini Vision.

    Args:
        image_bytes: Raw image data
        weight_grams: Optional weight in grams for precise calculation

    Returns: {foods: [...], total: {...}} or {error: "..."}
    """
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")

        # Use weight-specific prompt if weight is provided
        if weight_grams:
            prompt = PROMPT_WITH_WEIGHT.format(weight=weight_grams)
        else:
            prompt = PROMPT_TEMPLATE

        image_part = {
            "mime_type": "image/jpeg",
            "data": image_bytes
        }

        response = model.generate_content([prompt, image_part])
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


async def analyze_food_text(food_description: str, weight_grams: int | None = None) -> dict:
    """
    Analyze food from text description using Gemini.

    Args:
        food_description: Food description text
        weight_grams: Optional weight in grams for precise calculation

    Returns: {foods: [...], total: {...}} or {error: "..."}
    """
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")

        if weight_grams:
            prompt = f"{PROMPT_WITH_WEIGHT.format(weight=weight_grams)}\n\nMakanan: {food_description}"
        else:
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
