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
      "weight_grams": {weight}
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


def apply_correction_ratio(result: dict, ratio: float) -> dict:
    """
    Apply correction ratio ke semua estimasi berat dan nutrisi.

    Args:
        result: Nutrition analysis result
        ratio: Correction ratio to apply

    Returns:
        Adjusted result with correction ratio applied
    """
    adjusted_result = result.copy()

    # Adjust each food item
    for food in adjusted_result.get("foods", []):
        if "weight_grams" in food:
            original = food["weight_grams"]
            adjusted = int(original * ratio)
            food["weight_grams"] = adjusted
            food["_original_estimate"] = original

        # Adjust nutrition proportionally
        for nutrient in ["calories", "protein", "carbs", "fat"]:
            if nutrient in food:
                food[nutrient] = int(food[nutrient] * ratio)

    # Update totals
    if "total" in adjusted_result:
        for key in adjusted_result["total"]:
            if isinstance(adjusted_result["total"][key], (int, float)):
                adjusted_result["total"][key] = int(adjusted_result["total"][key] * ratio)

    return adjusted_result


async def analyze_food_image_with_learning(image_bytes: bytes, weight_grams: int = None,
                                           user_id: int = None) -> dict:
    """
    Analyze dengan adjustment berdasarkan historical corrections.

    Args:
        image_bytes: Raw image data
        weight_grams: Optional weight in grams for precise calculation
        user_id: Optional user ID to apply personalized corrections

    Returns: {foods: [...], total: {...}} with optional adjustment metadata
    """
    # Get base analysis from Gemini
    result = await analyze_food_image(image_bytes, weight_grams)

    if "error" in result:
        return result

    if weight_grams:
        # User sudah specify weight, tidak perlu adjustment
        return result

    if user_id:
        # Import here to avoid circular dependency
        from sheets_service import get_average_correction_ratio

        # Apply user-specific correction ratio
        correction_ratio = get_average_correction_ratio(user_id)

        if correction_ratio != 1.0 and 0.8 <= correction_ratio <= 1.3:
            # Only apply if ratio is reasonable (not too extreme)
            result = apply_correction_ratio(result, correction_ratio)
            result["_adjustment_applied"] = {
                "ratio": correction_ratio,
                "source": "user_history"
            }

    return result


async def analyze_food_text_with_learning(food_description: str, weight_grams: int = None,
                                          user_id: int = None) -> dict:
    """
    Analyze text dengan adjustment berdasarkan historical corrections.

    Args:
        food_description: Food description text
        weight_grams: Optional weight in grams for precise calculation
        user_id: Optional user ID to apply personalized corrections

    Returns: {foods: [...], total: {...}} with optional adjustment metadata
    """
    # Get base analysis from Gemini
    result = await analyze_food_text(food_description, weight_grams)

    if "error" in result:
        return result

    if weight_grams:
        # User sudah specify weight, tidak perlu adjustment
        return result

    if user_id:
        # Import here to avoid circular dependency
        from sheets_service import get_average_correction_ratio

        # Apply user-specific correction ratio
        correction_ratio = get_average_correction_ratio(user_id)

        if correction_ratio != 1.0 and 0.8 <= correction_ratio <= 1.3:
            # Only apply if ratio is reasonable (not too extreme)
            result = apply_correction_ratio(result, correction_ratio)
            result["_adjustment_applied"] = {
                "ratio": correction_ratio,
                "source": "user_history"
            }

    return result
