# Plan: Improved Gemini Prompt + RAG Integration

## Masalah dengan Prompt Saat Ini

### Current Prompt
```
Kamu adalah ahli nutrisi Indonesia. Analisis makanan berikut dan berikan estimasi nutrisi.
```

### Kelemahan:
1. **Tidak ada grounding** - AI menebak tanpa referensi ke database valid
2. **Tidak ada context porsi** - Porsi "1 piring" bisa sangat bervariasi
3. **Tidak ada instruksi akurasi** - Tidak diminta untuk konservatif atau realistis
4. **Tidak ada referensi standar** - Tidak mention TKPI atau sumber terpercaya

---

## Solusi: 3 Opsi RAG

### Opsi 1: Gemini Search Grounding (Recommended - Quick Win)

**Cara Kerja:**
- Gemini otomatis search Google untuk data nutrisi
- Grounded ke sumber real-time (FatSecret, nutritionix, USDA, dll)
- Built-in, tidak perlu setup database sendiri

**Pros:**
- Implementasi paling simple (1 parameter tambahan)
- Data selalu up-to-date
- Sudah include citation/source

**Cons:**
- Butuh upgrade plan Gemini (mungkin berbayar)
- Latency sedikit lebih tinggi
- Tidak 100% fokus ke makanan Indonesia

**Implementasi:**
```python
from google import genai
from google.genai.types import Tool, GoogleSearch

client = genai.Client(api_key=GEMINI_API_KEY)

response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=prompt,
    config={
        "tools": [Tool(google_search=GoogleSearch())]
    }
)
```

---

### Opsi 2: Local RAG dengan TKPI Database (Best for Indonesian Food)

**Cara Kerja:**
- Download TKPI (Tabel Komposisi Pangan Indonesia) dari Kemenkes
- Store dalam JSON/SQLite
- Retrieve relevant entries, inject ke prompt

**Pros:**
- Data official dari Kemenkes
- Fokus 100% makanan Indonesia
- Offline, tidak ada API cost tambahan
- Konsisten dan reproducible

**Cons:**
- Perlu setup awal (download, parse, store)
- Data mungkin tidak se-lengkap international DB
- Perlu maintenance jika TKPI update

**Data Source:**
- [TKPI Kemenkes Repository](https://repository.kemkes.go.id/book/668)
- [Panganku.org](https://www.panganku.org/en-EN/tentang_kami)
- [Kaggle Indonesian Food Dataset](https://www.kaggle.com/datasets/anasfikrihanif/indonesian-food-and-drink-nutrition-dataset) (1,346 makanan)

---

### Opsi 3: Hybrid (Search Grounding + Local TKPI)

**Cara Kerja:**
1. Cek dulu di local TKPI database
2. Jika tidak ada, fallback ke Gemini Search Grounding
3. Jika masih tidak ada, pure AI estimation

**Pros:**
- Best accuracy untuk makanan Indonesia
- Fallback untuk makanan international
- Flexibility

**Cons:**
- Implementasi paling kompleks
- Multiple code paths to maintain

---

## Rekomendasi: Opsi 1 + Improved Prompt

Untuk quick win dengan effort minimal, gunakan **Gemini Search Grounding** + **Improved Prompt**.

---

## Improved Prompt Design

### New Prompt Template

```python
IMPROVED_PROMPT = """Kamu adalah ahli nutrisi bersertifikat dengan akses ke database nutrisi.

TUGAS: Analisis makanan berikut dan berikan data nutrisi yang AKURAT.

INSTRUKSI PENTING:
1. CARI data nutrisi dari sumber terpercaya (USDA, FatSecret, TKPI Indonesia)
2. Gunakan data per PORSI STANDAR Indonesia:
   - 1 piring nasi = 150-200g
   - 1 mangkok = 250-300ml
   - 1 potong ayam = 80-100g
   - 1 porsi mie = 200-250g
3. Jika ragu, berikan RANGE (min-max) bukan angka pasti
4. JANGAN mengarang data - jika tidak yakin, katakan "estimasi"

FORMAT RESPONSE (JSON only, tanpa markdown):
{
  "name": "nama makanan dalam Bahasa Indonesia",
  "calories": angka dalam kkal (atau "min-max" jika range),
  "protein": angka dalam gram,
  "carbs": angka dalam gram,
  "fat": angka dalam gram,
  "fiber": angka dalam gram,
  "portion": "deskripsi porsi dengan berat dalam gram",
  "portion_grams": angka berat porsi dalam gram,
  "confidence": "high/medium/low",
  "source": "sumber data (misal: USDA, estimasi, dll)",
  "notes": "catatan tambahan jika ada (opsional)"
}

Jika bukan makanan/minuman:
{"error": "Tidak dapat mengenali makanan"}

CONTOH OUTPUT YANG BAIK:
{
  "name": "Nasi Goreng",
  "calories": 450,
  "protein": 12,
  "carbs": 55,
  "fat": 18,
  "fiber": 2,
  "portion": "1 piring (250g)",
  "portion_grams": 250,
  "confidence": "high",
  "source": "USDA + adjustment untuk resep Indonesia",
  "notes": "Kalori bisa lebih tinggi jika banyak minyak"
}
"""
```

### Key Improvements:

| Aspek | Before | After |
|-------|--------|-------|
| Grounding | Tidak ada | Instruksi cari dari sumber terpercaya |
| Porsi | Ambigu | Standar Indonesia dengan gram |
| Confidence | Tidak ada | Ada level confidence |
| Source | Tidak ada | Wajib cantumkan sumber |
| Range | Tidak support | Support min-max untuk uncertainty |
| Detail | Basic 5 fields | Extended dengan fiber, notes |

---

## Implementation Plan

### Step 1: Update gemini_service.py dengan Improved Prompt

```python
# gemini_service.py

IMPROVED_PROMPT = """..."""  # Prompt di atas

async def analyze_food_image(image_bytes: bytes) -> dict:
    """Analyze food with improved accuracy."""
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")

        image_part = {
            "mime_type": "image/jpeg",
            "data": image_bytes
        }

        response = model.generate_content(
            [IMPROVED_PROMPT, image_part],
            # Enable search grounding jika available
            # tools='google_search_retrieval'  # Uncomment jika punya akses
        )

        result_text = response.text.strip()
        # ... parsing logic

    except Exception as e:
        return {"error": f"Terjadi kesalahan: {str(e)}"}
```

### Step 2: Enable Search Grounding (Jika Available)

```python
# Untuk google-generativeai library versi baru
import google.generativeai as genai

model = genai.GenerativeModel('gemini-2.0-flash')

response = model.generate_content(
    [IMPROVED_PROMPT, image_part],
    tools='google_search_retrieval'  # Enable grounding
)

# Access grounding metadata
if hasattr(response, 'grounding_metadata'):
    sources = response.grounding_metadata.get('grounding_sources', [])
    # Bisa include sources dalam response ke user
```

### Step 3: Update Response Format di bot.py

```python
def format_nutrition_response(data: dict) -> str:
    """Format nutrition data with confidence and source."""
    if "error" in data:
        return f"❌ {data['error']}"

    confidence_emoji = {
        "high": "🟢",
        "medium": "🟡",
        "low": "🔴"
    }

    conf = data.get('confidence', 'medium')
    conf_display = confidence_emoji.get(conf, "🟡")

    source = data.get('source', 'AI estimation')
    notes = data.get('notes', '')
    notes_line = f"\n💡 {notes}" if notes else ""

    return f"""✅ Hasil Analisis!

🍽️ {data.get('name', 'Makanan')}
📊 Kalori: {data.get('calories', 0)} kkal
🥩 Protein: {data.get('protein', 0)}g
🍞 Karbo: {data.get('carbs', 0)}g
🧈 Lemak: {data.get('fat', 0)}g
🌾 Fiber: {data.get('fiber', 0)}g
📏 Porsi: {data.get('portion', '-')}

{conf_display} Confidence: {conf}
📚 Sumber: {source}{notes_line}"""
```

---

## Opsi 2 Detail: Local TKPI RAG

Jika ingin implement local RAG dengan TKPI:

### Step 1: Download dan Parse TKPI Data

```python
# scripts/prepare_tkpi.py

import json
import pandas as pd

# Download dari Kaggle atau parse dari PDF TKPI
# https://www.kaggle.com/datasets/anasfikrihanif/indonesian-food-and-drink-nutrition-dataset

def prepare_tkpi_database():
    """Prepare TKPI data as JSON for RAG."""

    # Load dataset
    df = pd.read_csv('indonesian_food_nutrition.csv')

    # Convert to searchable format
    foods = []
    for _, row in df.iterrows():
        foods.append({
            "name": row['name'],
            "name_lower": row['name'].lower(),
            "calories": row['calories'],
            "protein": row['protein'],
            "carbs": row['carbohydrate'],
            "fat": row['fat'],
            "portion": "100g",  # TKPI uses per 100g
            "source": "TKPI Kemenkes"
        })

    with open('data/tkpi_database.json', 'w') as f:
        json.dump(foods, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(foods)} foods to database")
```

### Step 2: RAG Retrieval Function

```python
# rag_service.py

import json
from difflib import SequenceMatcher

def load_tkpi_database():
    """Load TKPI database."""
    with open('data/tkpi_database.json', 'r') as f:
        return json.load(f)

TKPI_DB = load_tkpi_database()

def search_tkpi(query: str, threshold: float = 0.6) -> list:
    """
    Search TKPI database with fuzzy matching.

    Args:
        query: Food name to search
        threshold: Minimum similarity score (0-1)

    Returns:
        List of matching foods sorted by relevance
    """
    query_lower = query.lower()
    results = []

    for food in TKPI_DB:
        # Exact substring match
        if query_lower in food['name_lower']:
            results.append((food, 1.0))
            continue

        # Fuzzy match
        ratio = SequenceMatcher(None, query_lower, food['name_lower']).ratio()
        if ratio >= threshold:
            results.append((food, ratio))

    # Sort by relevance
    results.sort(key=lambda x: x[1], reverse=True)

    return [r[0] for r in results[:5]]  # Top 5


def get_rag_context(food_name: str) -> str:
    """
    Get RAG context for Gemini prompt.

    Returns formatted string with relevant TKPI data.
    """
    matches = search_tkpi(food_name)

    if not matches:
        return ""

    context = "DATA REFERENSI DARI TKPI (per 100g):\n"
    for food in matches:
        context += f"""
- {food['name']}:
  Kalori: {food['calories']} kkal
  Protein: {food['protein']}g
  Karbo: {food['carbs']}g
  Lemak: {food['fat']}g
"""

    return context
```

### Step 3: Integrate RAG dengan Gemini

```python
# gemini_service.py

from rag_service import get_rag_context

async def analyze_food_with_rag(food_description: str) -> dict:
    """Analyze food with TKPI RAG context."""

    # Get relevant TKPI data
    rag_context = get_rag_context(food_description)

    # Build enhanced prompt
    if rag_context:
        enhanced_prompt = f"""{IMPROVED_PROMPT}

{rag_context}

INSTRUKSI TAMBAHAN:
- Gunakan data TKPI di atas sebagai referensi utama
- Adjust kalori berdasarkan porsi yang dimaksud user
- Jika makanan tidak ada di TKPI, estimasi berdasarkan makanan serupa

Makanan: {food_description}"""
    else:
        enhanced_prompt = f"{IMPROVED_PROMPT}\n\nMakanan: {food_description}"

    # Call Gemini
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(enhanced_prompt)

    # Parse response...
```

---

## File Structure Setelah Implementasi

```
foodtracker/
├── bot.py                    # Updated response format
├── config.py                 # Existing
├── gemini_service.py         # Updated with improved prompt
├── rag_service.py            # NEW - TKPI RAG (Opsi 2)
├── data/
│   └── tkpi_database.json    # NEW - TKPI data (Opsi 2)
├── scripts/
│   └── prepare_tkpi.py       # NEW - Data preparation (Opsi 2)
├── requirements.txt          # May need pandas for Opsi 2
└── ...
```

---

## Comparison Summary

| Aspek | Opsi 1: Search Grounding | Opsi 2: Local TKPI RAG |
|-------|--------------------------|------------------------|
| Setup Effort | Minimal (1 param) | Medium (download, parse) |
| Accuracy Indonesia | Good | Excellent |
| Accuracy International | Excellent | Limited |
| Latency | +200-500ms | +50-100ms |
| Cost | Mungkin berbayar | Free |
| Maintenance | None | Update TKPI periodik |
| Offline | No | Yes |

---

## Rekomendasi Implementasi

### Quick Win (Hari ini):
1. Update prompt ke IMPROVED_PROMPT
2. Test apakah Search Grounding available di plan saat ini

### Medium Term:
3. Download Kaggle Indonesian Food Dataset
4. Implement simple TKPI RAG
5. Hybrid: TKPI first, Search Grounding fallback

### Long Term:
6. FatSecret API integration (plan sebelumnya)
7. User feedback loop untuk improve data

---

## Next Steps

Pilih opsi mana yang mau dieksekusi:

- [ ] **Opsi A**: Improved Prompt saja (paling simple)
- [ ] **Opsi B**: Improved Prompt + Search Grounding
- [ ] **Opsi C**: Improved Prompt + Local TKPI RAG
- [ ] **Opsi D**: Full hybrid (semua)

---

## Sources

- [Gemini Search Grounding Documentation](https://ai.google.dev/gemini-api/docs/google-search)
- [Google Colab Search Grounding Example](https://colab.research.google.com/github/google-gemini/cookbook/blob/main/quickstarts/Search_Grounding.ipynb)
- [TKPI Kemenkes Repository](https://repository.kemkes.go.id/book/668)
- [Panganku.org - Indonesian Food Composition](https://www.panganku.org/en-EN/tentang_kami)
- [Kaggle Indonesian Food Dataset](https://www.kaggle.com/datasets/anasfikrihanif/indonesian-food-and-drink-nutrition-dataset)
