# Plan Integrasi FatSecret Database

## Executive Summary

Dokumen ini menjelaskan rencana integrasi FatSecret food database ke dalam Telegram Calorie Tracker Bot yang saat ini hanya menggunakan Gemini AI untuk estimasi nutrisi dari foto/teks.

**Tujuan:** Meningkatkan akurasi data nutrisi dengan menggunakan database makanan terverifikasi dari FatSecret, sambil tetap memanfaatkan Gemini AI untuk food recognition.

---

## 1. Current State vs Target State

### Current State (Sekarang)
```
User Input (Foto/Teks)
        ↓
    Gemini AI
        ↓
  Estimasi Nutrisi (AI-generated, tidak terverifikasi)
        ↓
    Response ke User
```

**Kelemahan:**
- Data nutrisi adalah estimasi AI, bukan dari database terverifikasi
- Akurasi bervariasi, terutama untuk makanan Indonesia
- Tidak konsisten untuk makanan yang sama
- Tidak ada referensi ke standard nutritional database

### Target State (Setelah Integrasi)
```
User Input (Foto/Teks)
        ↓
    Gemini AI
        ↓
  Identifikasi Nama Makanan
        ↓
    FatSecret API
        ↓
  Data Nutrisi Terverifikasi
        ↓
    Response ke User (dengan fallback ke Gemini jika tidak ditemukan)
```

**Keunggulan:**
- Data nutrisi dari database terverifikasi (1.9M+ makanan)
- Konsisten untuk makanan yang sama
- Gemini tetap digunakan untuk food recognition dari foto
- Fallback ke estimasi Gemini jika makanan tidak ada di FatSecret

---

## 2. FatSecret API Overview

### Informasi Umum
- **Database:** 1.9 juta+ makanan terverifikasi
- **Coverage:** 56+ negara, 24 bahasa
- **Update:** Database di-update harian
- **Authentication:** OAuth 1.0 dengan HMAC-SHA1

### Endpoint Utama yang Akan Digunakan

| Endpoint | Fungsi | HTTP Method |
|----------|--------|-------------|
| `foods.search` | Cari makanan berdasarkan nama | GET |
| `food.get.v4` | Dapatkan detail nutrisi lengkap | GET |

### Response Format (foods.search)
```json
{
  "foods": {
    "food": [
      {
        "food_id": "33691",
        "food_name": "Nasi Goreng",
        "food_type": "Generic",
        "food_description": "Per 1 serving - Calories: 450kcal | Fat: 18g | Carbs: 55g | Protein: 12g"
      }
    ],
    "max_results": "50",
    "page_number": "0",
    "total_results": "125"
  }
}
```

### Response Format (food.get.v4)
```json
{
  "food": {
    "food_id": "33691",
    "food_name": "Nasi Goreng",
    "servings": {
      "serving": [
        {
          "serving_id": "12345",
          "serving_description": "1 plate (350g)",
          "calories": "450",
          "carbohydrate": "55.00",
          "protein": "12.00",
          "fat": "18.00",
          "fiber": "2.00",
          "sugar": "3.00",
          "sodium": "800"
        }
      ]
    }
  }
}
```

### Kredensial yang Diperlukan
1. **Consumer Key** - Dari FatSecret Developer Account
2. **Consumer Secret** - Dari FatSecret Developer Account
3. **IP Whitelisting** - FatSecret memerlukan IP whitelist

### Cara Mendapatkan API Key
1. Daftar di https://platform.fatsecret.com/
2. Buat aplikasi baru
3. Dapatkan Consumer Key dan Consumer Secret
4. Whitelist IP server (untuk production)

---

## 3. Arsitektur Integrasi

### Flow Diagram Baru

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INPUT                                │
│                    (Foto atau Teks)                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      GEMINI SERVICE                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  analyze_food_image() / analyze_food_text()              │   │
│  │  Output: { "name": "Nasi Goreng", "portion": "1 piring" }│   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FATSECRET SERVICE (BARU)                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  search_food("Nasi Goreng")                              │   │
│  │  → Jika ditemukan: get_food_details(food_id)             │   │
│  │  → Jika tidak: return None (fallback ke Gemini)          │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    NUTRITION RESOLVER (BARU)                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Prioritas:                                              │   │
│  │  1. FatSecret data (jika ditemukan)                      │   │
│  │  2. Gemini estimation (fallback)                         │   │
│  │                                                          │   │
│  │  Tambahkan flag: "source": "fatsecret" atau "gemini_ai"  │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      RESPONSE KE USER                            │
│                                                                  │
│  ✅ Hasil Analisis!                                             │
│  🍽️ Nasi Goreng                                                │
│  📊 Kalori: 450 kkal                                            │
│  🥩 Protein: 12g                                                │
│  🍞 Karbo: 55g                                                  │
│  🧈 Lemak: 18g                                                  │
│  📏 Porsi: 1 piring                                             │
│  📚 Sumber: FatSecret Database ✓                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. File Changes Overview

### File Baru
| File | Deskripsi |
|------|-----------|
| `fatsecret_service.py` | Service untuk integrasi FatSecret API |
| `nutrition_resolver.py` | Logic untuk menggabungkan Gemini + FatSecret |

### File yang Dimodifikasi
| File | Perubahan |
|------|-----------|
| `config.py` | Tambah FATSECRET_CONSUMER_KEY, FATSECRET_CONSUMER_SECRET |
| `.env.example` | Tambah environment variables FatSecret |
| `gemini_service.py` | Modifikasi output untuk fokus ke food identification |
| `bot.py` | Gunakan nutrition_resolver alih-alih langsung gemini_service |
| `requirements.txt` | Tambah `fatsecret` atau `requests-oauthlib` |

---

## 5. Implementation Steps

### Step 1: Setup FatSecret Credentials

**File: `config.py`**
```python
# Tambahkan:
FATSECRET_CONSUMER_KEY = os.getenv("FATSECRET_CONSUMER_KEY")
FATSECRET_CONSUMER_SECRET = os.getenv("FATSECRET_CONSUMER_SECRET")
```

**File: `.env.example`**
```
# Tambahkan:
FATSECRET_CONSUMER_KEY=your_consumer_key
FATSECRET_CONSUMER_SECRET=your_consumer_secret
```

**File: `requirements.txt`**
```
# Tambahkan salah satu:
fatsecret==0.2.3          # Official wrapper
# ATAU
requests-oauthlib==1.3.1  # Jika ingin implementasi manual
```

---

### Step 2: Buat FatSecret Service

**File: `fatsecret_service.py`**

```python
"""
FatSecret API Service

Provides food search and nutrition data from FatSecret database.
"""

from fatsecret import Fatsecret
from config import FATSECRET_CONSUMER_KEY, FATSECRET_CONSUMER_SECRET
import logging

logger = logging.getLogger(__name__)

# Initialize FatSecret client
fs = None

def get_client():
    """Get or create FatSecret client instance."""
    global fs
    if fs is None:
        if not FATSECRET_CONSUMER_KEY or not FATSECRET_CONSUMER_SECRET:
            logger.warning("FatSecret credentials not configured")
            return None
        fs = Fatsecret(FATSECRET_CONSUMER_KEY, FATSECRET_CONSUMER_SECRET)
    return fs


async def search_food(food_name: str, max_results: int = 5) -> list:
    """
    Search for food in FatSecret database.

    Args:
        food_name: Name of food to search (e.g., "nasi goreng")
        max_results: Maximum number of results to return

    Returns:
        List of food items with basic info, or empty list if not found
    """
    try:
        client = get_client()
        if client is None:
            return []

        results = client.foods_search(food_name, max_results=max_results)

        if not results:
            return []

        # Normalize results to list
        foods = results.get('foods', {}).get('food', [])
        if isinstance(foods, dict):  # Single result
            foods = [foods]

        return foods

    except Exception as e:
        logger.error(f"FatSecret search error: {e}")
        return []


async def get_food_details(food_id: str) -> dict | None:
    """
    Get detailed nutrition info for a specific food.

    Args:
        food_id: FatSecret food ID

    Returns:
        Dict with nutrition data or None if not found
    """
    try:
        client = get_client()
        if client is None:
            return None

        food = client.food_get(food_id)

        if not food:
            return None

        # Extract first serving info (default serving)
        servings = food.get('servings', {}).get('serving', [])
        if isinstance(servings, dict):
            servings = [servings]

        if not servings:
            return None

        # Use first serving as default
        serving = servings[0]

        return {
            "food_id": food.get('food_id'),
            "name": food.get('food_name'),
            "calories": float(serving.get('calories', 0)),
            "protein": float(serving.get('protein', 0)),
            "carbs": float(serving.get('carbohydrate', 0)),
            "fat": float(serving.get('fat', 0)),
            "portion": serving.get('serving_description', '1 serving'),
            "source": "fatsecret"
        }

    except Exception as e:
        logger.error(f"FatSecret get details error: {e}")
        return None


async def get_nutrition_by_name(food_name: str) -> dict | None:
    """
    Convenience function: search and get nutrition in one call.

    Args:
        food_name: Name of food to search

    Returns:
        Nutrition dict with best match, or None if not found
    """
    results = await search_food(food_name, max_results=1)

    if not results:
        return None

    food_id = results[0].get('food_id')
    if not food_id:
        return None

    return await get_food_details(food_id)
```

---

### Step 3: Modifikasi Gemini Service

Gemini perlu diubah untuk fokus pada **food identification** saja (nama & porsi), bukan estimasi nutrisi.

**File: `gemini_service.py`** - Tambahkan fungsi baru:

```python
IDENTIFICATION_PROMPT = """Kamu adalah ahli makanan Indonesia. Identifikasi makanan dari input berikut.

Berikan response dalam format JSON ONLY (tanpa markdown):
{
  "name": "nama makanan dalam Bahasa Indonesia (standar, bukan brand)",
  "name_en": "nama makanan dalam Bahasa Inggris (untuk search di database)",
  "portion": "deskripsi porsi, misal: 1 piring, 1 mangkok",
  "confidence": angka 0-100 (tingkat kepercayaan identifikasi)
}

Jika bukan makanan/minuman, return:
{"error": "Tidak dapat mengenali makanan"}

PENTING:
- Gunakan nama generik, bukan brand (misal: "nasi goreng" bukan "Nasi Goreng Gila")
- Sertakan nama Inggris untuk pencarian database internasional
"""


async def identify_food_image(image_bytes: bytes) -> dict:
    """
    Identify food from image (name & portion only, no nutrition).
    Returns: {name, name_en, portion, confidence} or {error: "..."}
    """
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")

        image_part = {
            "mime_type": "image/jpeg",
            "data": image_bytes
        }

        response = model.generate_content([IDENTIFICATION_PROMPT, image_part])
        result_text = response.text.strip()

        # Clean up markdown
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


async def identify_food_text(food_description: str) -> dict:
    """
    Identify food from text description (name & portion only).
    Returns: {name, name_en, portion, confidence} or {error: "..."}
    """
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")

        prompt = f"{IDENTIFICATION_PROMPT}\n\nMakanan: {food_description}"

        response = model.generate_content(prompt)
        result_text = response.text.strip()

        # Clean up markdown
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
```

---

### Step 4: Buat Nutrition Resolver

**File: `nutrition_resolver.py`**

```python
"""
Nutrition Resolver

Combines Gemini AI food identification with FatSecret database lookup.
Provides fallback to Gemini estimation when FatSecret data is unavailable.
"""

import logging
from gemini_service import (
    identify_food_image,
    identify_food_text,
    analyze_food_image,  # Keep old function for fallback
    analyze_food_text    # Keep old function for fallback
)
from fatsecret_service import get_nutrition_by_name, search_food

logger = logging.getLogger(__name__)


async def resolve_nutrition_from_image(image_bytes: bytes) -> dict:
    """
    Get nutrition data for food in image.

    Flow:
    1. Use Gemini to identify food name
    2. Search FatSecret for nutrition data
    3. Fallback to Gemini estimation if not found

    Returns:
        dict with nutrition data and source indicator
    """
    # Step 1: Identify food with Gemini
    identification = await identify_food_image(image_bytes)

    if "error" in identification:
        return identification

    food_name = identification.get("name", "")
    food_name_en = identification.get("name_en", food_name)
    portion = identification.get("portion", "1 porsi")

    # Step 2: Try FatSecret lookup
    # Try Indonesian name first, then English
    nutrition = await get_nutrition_by_name(food_name)

    if nutrition is None:
        nutrition = await get_nutrition_by_name(food_name_en)

    # Step 3: If FatSecret found, use it
    if nutrition is not None:
        nutrition["portion"] = portion  # Use Gemini's portion estimation
        nutrition["source"] = "fatsecret"
        nutrition["source_display"] = "FatSecret Database ✓"
        return nutrition

    # Step 4: Fallback to Gemini estimation
    logger.info(f"FatSecret not found for '{food_name}', using Gemini fallback")
    gemini_result = await analyze_food_image(image_bytes)

    if "error" not in gemini_result:
        gemini_result["source"] = "gemini_ai"
        gemini_result["source_display"] = "Estimasi AI"

    return gemini_result


async def resolve_nutrition_from_text(food_description: str) -> dict:
    """
    Get nutrition data for food described in text.

    Flow:
    1. Use Gemini to parse/standardize food name
    2. Search FatSecret for nutrition data
    3. Fallback to Gemini estimation if not found

    Returns:
        dict with nutrition data and source indicator
    """
    # Step 1: Identify/standardize food with Gemini
    identification = await identify_food_text(food_description)

    if "error" in identification:
        return identification

    food_name = identification.get("name", "")
    food_name_en = identification.get("name_en", food_name)
    portion = identification.get("portion", "1 porsi")

    # Step 2: Try FatSecret lookup
    nutrition = await get_nutrition_by_name(food_name)

    if nutrition is None:
        nutrition = await get_nutrition_by_name(food_name_en)

    # Step 3: If FatSecret found, use it
    if nutrition is not None:
        nutrition["portion"] = portion
        nutrition["source"] = "fatsecret"
        nutrition["source_display"] = "FatSecret Database ✓"
        return nutrition

    # Step 4: Fallback to Gemini estimation
    logger.info(f"FatSecret not found for '{food_name}', using Gemini fallback")
    gemini_result = await analyze_food_text(food_description)

    if "error" not in gemini_result:
        gemini_result["source"] = "gemini_ai"
        gemini_result["source_display"] = "Estimasi AI"

    return gemini_result
```

---

### Step 5: Update Bot Handler

**File: `bot.py`** - Modifikasi imports dan handlers:

```python
# Ganti import
# FROM:
# from gemini_service import analyze_food_image, analyze_food_text

# TO:
from nutrition_resolver import (
    resolve_nutrition_from_image,
    resolve_nutrition_from_text
)

# Update format_nutrition_response untuk menampilkan source
def format_nutrition_response(data: dict) -> str:
    """Format nutrition data into a nice response message."""
    if "error" in data:
        return f"❌ {data['error']}"

    source_line = ""
    if "source_display" in data:
        source_line = f"\n📚 Sumber: {data['source_display']}"

    return f"""✅ Hasil Analisis!

🍽️ {data.get('name', 'Makanan')}
📊 Kalori: {data.get('calories', 0)} kkal
🥩 Protein: {data.get('protein', 0)}g
🍞 Karbo: {data.get('carbs', 0)}g
🧈 Lemak: {data.get('fat', 0)}g
📏 Porsi: {data.get('portion', '-')}{source_line}"""


# Update handle_photo
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle photo messages - analyze food from image."""
    await update.message.reply_text("🔄 Menganalisis foto makanan...")

    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        photo_bytes = await file.download_as_bytearray()

        # CHANGED: Use nutrition resolver instead of direct Gemini
        result = await resolve_nutrition_from_image(bytes(photo_bytes))

        response = format_nutrition_response(result)
        await update.message.reply_text(response)

    except Exception as e:
        logger.error(f"Error handling photo: {e}")
        await update.message.reply_text("❌ Maaf, terjadi kesalahan. Coba lagi nanti.")


# Update handle_text
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages - analyze food from description."""
    text = update.message.text

    if text.startswith("/"):
        return

    await update.message.reply_text("🔄 Menganalisis makanan...")

    try:
        # CHANGED: Use nutrition resolver instead of direct Gemini
        result = await resolve_nutrition_from_text(text)

        response = format_nutrition_response(result)
        await update.message.reply_text(response)

    except Exception as e:
        logger.error(f"Error handling text: {e}")
        await update.message.reply_text("❌ Maaf, terjadi kesalahan. Coba lagi nanti.")
```

---

## 6. Considerations & Trade-offs

### Keuntungan Integrasi FatSecret

| Aspek | Sebelum | Sesudah |
|-------|---------|---------|
| Akurasi Data | Estimasi AI (bervariasi) | Database terverifikasi |
| Konsistensi | Berbeda tiap request | Sama untuk makanan yang sama |
| Detail Nutrisi | Hanya macro (cal, protein, carb, fat) | Bisa include micro (fiber, sodium, dll) |
| Reliabilitas | Bergantung pada AI interpretation | Data dari sumber terpercaya |

### Potensi Tantangan

| Tantangan | Solusi |
|-----------|--------|
| Makanan Indonesia tidak ada di FatSecret | Fallback ke Gemini estimation |
| API rate limit | Implement caching untuk frequent searches |
| Latency bertambah (2 API calls) | Parallel calls atau caching |
| Nama makanan tidak match | Gunakan fuzzy matching atau multiple search terms |
| IP Whitelisting untuk production | Configure saat deployment |

### Rekomendasi Tambahan

1. **Implement Caching**
   - Cache hasil FatSecret search selama 24 jam
   - Gunakan Redis atau in-memory cache (dict) untuk MVP

2. **Fuzzy Matching**
   - Jika exact match gagal, coba variasi nama
   - Contoh: "nasi goreng" → "fried rice" → "indonesian fried rice"

3. **User Feedback Loop**
   - Tambahkan tombol "Data tidak akurat?"
   - Simpan feedback untuk improvement

4. **Analytics**
   - Track success rate FatSecret vs Gemini fallback
   - Identifikasi makanan yang sering fallback untuk di-review

---

## 7. Testing Strategy

### Unit Tests

```python
# test_fatsecret_service.py
async def test_search_food_found():
    """Test food search returns results for common foods."""
    results = await search_food("rice")
    assert len(results) > 0

async def test_search_food_not_found():
    """Test food search returns empty for gibberish."""
    results = await search_food("xyznonexistent123")
    assert len(results) == 0

async def test_get_food_details():
    """Test getting nutrition details by food_id."""
    details = await get_food_details("33691")  # Known food ID
    assert details is not None
    assert "calories" in details
```

### Integration Tests

```python
# test_nutrition_resolver.py
async def test_resolve_with_fatsecret():
    """Test resolution uses FatSecret when available."""
    result = await resolve_nutrition_from_text("chicken breast")
    assert result.get("source") == "fatsecret"

async def test_resolve_fallback_to_gemini():
    """Test resolution falls back to Gemini for unknown foods."""
    result = await resolve_nutrition_from_text("makanan langka xyz")
    assert result.get("source") == "gemini_ai"
```

### Manual Testing Checklist

- [ ] Search makanan umum (nasi goreng, ayam goreng) → FatSecret data
- [ ] Search makanan Indonesia spesifik (gudeg, rawon) → Check if found or fallback
- [ ] Kirim foto makanan → Proper identification and nutrition
- [ ] Kirim foto non-makanan → Error handling
- [ ] Check response time < 5 detik
- [ ] Verify source indicator ditampilkan dengan benar

---

## 8. Implementation Timeline

| Phase | Task | Estimasi |
|-------|------|----------|
| 1 | Setup FatSecret account & get API keys | - |
| 2 | Implement `fatsecret_service.py` | - |
| 3 | Add identification functions to `gemini_service.py` | - |
| 4 | Implement `nutrition_resolver.py` | - |
| 5 | Update `bot.py` handlers | - |
| 6 | Testing & debugging | - |
| 7 | Deploy & monitor | - |

---

## 9. File Structure Setelah Integrasi

```
foodtracker/
├── bot.py                    # Modified - use nutrition_resolver
├── config.py                 # Modified - add FatSecret credentials
├── gemini_service.py         # Modified - add identification functions
├── fatsecret_service.py      # NEW - FatSecret API integration
├── nutrition_resolver.py     # NEW - Combines Gemini + FatSecret
├── requirements.txt          # Modified - add fatsecret package
├── .env.example              # Modified - add FatSecret env vars
├── .env                      # User's actual env file
├── README.md                 # Existing
├── product_plan.md           # Existing
├── mvp_scope.md              # Existing
└── PLAN_FATSECRET_INTEGRATION.md  # This document
```

---

## 10. Kesimpulan

Integrasi FatSecret akan meningkatkan kualitas dan reliabilitas data nutrisi yang diberikan kepada user. Dengan pendekatan hybrid (Gemini untuk identification + FatSecret untuk nutrition data + Gemini fallback), kita mendapatkan:

1. **Best of both worlds**: AI vision untuk identifikasi + verified database untuk nutrisi
2. **Graceful degradation**: Tetap berfungsi jika FatSecret tidak punya data
3. **Transparency**: User tahu sumber data (database vs AI estimation)

**Next Steps:**
1. Daftar FatSecret Developer Account
2. Review dan approve plan ini
3. Mulai implementasi dari Step 1

---

## Sources

- [FatSecret Platform API](https://platform.fatsecret.com/platform-api)
- [FatSecret API Documentation](https://platform.fatsecret.com/docs/guides)
- [pyfatsecret Python Library](https://github.com/walexnelson/pyfatsecret)
- [PyPI - fatsecret package](https://pypi.org/project/fatsecret/)
