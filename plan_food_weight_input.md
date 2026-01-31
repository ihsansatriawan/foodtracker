# Plan: Input Berat (Gram) Makanan untuk Kalkulasi Nutrisi

## Summary

Menambahkan fitur dimana user dapat memberikan input berat (gram) makanan dari gambar yang dikirim, dan sistem akan menghitung ulang kandungan nutrisi berdasarkan berat tersebut.

## Problem Statement

Saat ini, estimasi nutrisi makanan dari foto bergantung sepenuhnya pada AI untuk menebak porsi. Dengan fitur ini:
- User dapat mengirim foto makanan + berat dalam gram
- AI akan menggunakan berat tersebut sebagai referensi akurat untuk kalkulasi nutrisi
- Hasil lebih presisi karena berbasis berat aktual, bukan estimasi visual

## User Flow

### Flow 1: Foto dengan Caption Berat
```
User: [Kirim foto makanan dengan caption "250 gram"]
Bot: 🔄 Menganalisis foto makanan (250 gram)...
Bot: ✅ Hasil Analisis!
     🍽️ Nasi Goreng
     📊 Kalori: 375 kkal
     🥩 Protein: 10g
     🍞 Karbo: 45g
     🧈 Lemak: 15g
     ⚖️ Berat: 250 gram
```

### Flow 2: Foto Tanpa Caption (Default - Estimasi AI)
```
User: [Kirim foto makanan tanpa caption]
Bot: 🔄 Menganalisis foto makanan...
Bot: ✅ Hasil Analisis!
     🍽️ Nasi Goreng
     📊 Kalori: 450 kkal
     ...
     📏 Porsi: ~1 piring (estimasi)
```

### Flow 3: Text dengan Berat
```
User: "nasi goreng 200 gram"
Bot: ✅ Hasil Analisis!
     🍽️ Nasi Goreng
     📊 Kalori: 300 kkal
     ...
     ⚖️ Berat: 200 gram
```

---

## Technical Implementation

### Phase 1: Parsing Input Berat

#### Step 1.1: Buat Utility Function untuk Parsing Berat

**File:** `gemini_service.py` atau buat `utils.py`

```python
import re

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

    return (cleaned_text, weight)
```

---

### Phase 2: Update Gemini Service

#### Step 2.1: Update Prompt Template untuk Menerima Berat

**File:** `gemini_service.py`

Buat prompt baru yang menerima parameter berat:

```python
PROMPT_WITH_WEIGHT = """Kamu adalah ahli nutrisi Indonesia. Analisis makanan dalam gambar.
PENTING: User sudah menimbang makanan ini dengan berat {weight} gram.
Hitung kandungan nutrisi berdasarkan berat {weight} gram tersebut.

Berikan response dalam format JSON ONLY (tanpa markdown):
{
  "foods": [
    {
      "name": "nama makanan dalam Bahasa Indonesia",
      "calories": angka dalam kkal untuk {weight} gram,
      "protein": angka dalam gram,
      "carbs": angka dalam gram,
      "fat": angka dalam gram,
      "weight_grams": {weight}
    }
  ],
  "total": {
    "calories": total kkal,
    "protein": total gram,
    "carbs": total gram,
    "fat": total gram,
    "weight_grams": total gram
  }
}

Jika bukan makanan/minuman, return:
{"error": "Tidak dapat mengenali makanan"}"""
```

#### Step 2.2: Update Function `analyze_food_image`

```python
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

        # ... rest of processing
        return normalize_response(json.loads(result_text))
    except Exception as e:
        return {"error": f"Terjadi kesalahan: {str(e)}"}
```

#### Step 2.3: Update Function `analyze_food_text`

```python
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
        # ... rest of processing
    except Exception as e:
        return {"error": f"Terjadi kesalahan: {str(e)}"}
```

---

### Phase 3: Update Bot Handlers

#### Step 3.1: Update `handle_photo` untuk Membaca Caption

**File:** `bot.py`

```python
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
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        photo_bytes = await file.download_as_bytearray()

        # Pass weight to analyzer
        result = await analyze_food_image(bytes(photo_bytes), weight_grams=weight_grams)

        response = format_nutrition_response(result)
        await update.message.reply_text(response)

    except Exception as e:
        logger.error(f"Error handling photo: {e}")
        await update.message.reply_text("❌ Maaf, terjadi kesalahan. Coba lagi nanti.")
```

#### Step 3.2: Update `handle_text` untuk Parse Berat

```python
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages - analyze food from description."""
    text = update.message.text

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
        result = await analyze_food_text(food_description, weight_grams=weight_grams)
        response = format_nutrition_response(result)
        await update.message.reply_text(response)

    except Exception as e:
        logger.error(f"Error handling text: {e}")
        await update.message.reply_text("❌ Maaf, terjadi kesalahan. Coba lagi nanti.")
```

---

### Phase 4: Update Response Format

#### Step 4.1: Update `format_nutrition_response`

Tampilkan berat jika tersedia:

```python
def format_nutrition_response(data: dict) -> str:
    """Format nutrition data into a nice response message."""
    if "error" in data:
        return f"❌ {data['error']}"

    foods = data.get("foods", [])
    total = data.get("total", {})

    if not foods:
        return "❌ Tidak ada makanan yang terdeteksi"

    lines = ["✅ Hasil Analisis!"]

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

    # Total section for multiple foods
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
```

---

### Phase 5: Update Dokumentasi & Help Message

#### Step 5.1: Update HELP_MESSAGE di `bot.py`

```python
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
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `gemini_service.py` | Add `PROMPT_WITH_WEIGHT`, update `analyze_food_image()` and `analyze_food_text()` to accept weight parameter |
| `bot.py` | Add `parse_weight_from_text()`, update handlers to parse weight from caption/text, update response format |
| `README.md` | Document new weight input feature |

---

## Testing Checklist

- [ ] Kirim foto dengan caption "250 gram" → hasil nutrisi berdasarkan 250g
- [ ] Kirim foto dengan caption "0.5 kg" → hasil nutrisi berdasarkan 500g
- [ ] Kirim foto tanpa caption → hasil nutrisi dengan estimasi porsi (behavior existing)
- [ ] Kirim text "nasi goreng 200 gram" → hasil nutrisi berdasarkan 200g
- [ ] Kirim text "nasi goreng 1 piring" → hasil nutrisi dengan estimasi porsi
- [ ] Kirim foto dengan caption random (bukan berat) → ignore caption, analyze normally
- [ ] Multiple foods dalam 1 foto dengan berat → distribusi nutrisi proporsional

---

## Edge Cases to Handle

1. **Caption dengan text + berat**: "ini makan siang 300 gram" → parse 300 gram
2. **Format berat tidak valid**: "banyak gram" → ignore, use estimation
3. **Berat 0 atau negatif**: validate dan ignore jika invalid
4. **Multiple weights in text**: "250 gram nasi 100 gram ayam" → currently not supported, use first match or total

---

## Future Enhancements

1. **Per-item weight for multiple foods**: "nasi 200g, ayam 150g"
2. **Weight estimation hint**: AI suggest approximate weight based on visual
3. **Nutrition per 100g option**: Show standardized nutrition per 100 gram
4. **Weight history**: Track total grams consumed per day
