# Weight Feedback Loop - Implementation Plan

## Overview

Fitur untuk meningkatkan akurasi estimasi berat makanan melalui user feedback. Sistem akan belajar dari koreksi user untuk memberikan estimasi yang lebih akurat di masa depan.

**Target Improvement:** 20-30% peningkatan akurasi estimasi berat

---

## Current Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| Google Sheets Integration | ✅ Done | `sheets_service.py` with 10-column schema |
| ImageKit Integration | ✅ Done | `imagekit_service.py` for permanent image URLs |
| Food Logging | ✅ Done | Auto-log with `log_multiple_foods()` |
| `/today`, `/history`, `/undo` | ✅ Done | Basic tracking commands |
| Inline Keyboard Feedback | ⏳ Planned | Phase 1 of this plan |
| Schema Extension (feedback columns) | ⏳ Planned | Phase 2 of this plan |
| Learning System | ⏳ Planned | Phase 3 of this plan |
| `/accuracy` Command | ⏳ Planned | Phase 4 of this plan |

### Existing Infrastructure to Build On

**Current Google Sheets Schema (10 columns):**
```
| Tanggal | Waktu | User ID | Nama Makanan | Kalori | Protein | Karbo | Lemak | Porsi/Berat | Image URL |
```

**Existing Functions in `sheets_service.py`:**
- `log_food_entry()` - Single food logging
- `log_multiple_foods()` - Batch logging with image URL
- `get_today_entries()` - Filter by date/user
- `get_recent_entries()` - Paginated history
- `delete_last_entry()` - Undo support
- `is_sheets_configured()` - Config check

**Existing Functions in `imagekit_service.py`:**
- `upload_food_image()` - Upload with auto-naming
- `is_imagekit_configured()` - Config check

---

## Konsep Utama

```
┌─────────────────────────────────────────────────────────────────┐
│                     FEEDBACK LOOP FLOW                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   User kirim foto    AI estimasi      User koreksi (optional)   │
│        │                 │                    │                 │
│        ▼                 ▼                    ▼                 │
│   ┌─────────┐      ┌──────────┐        ┌───────────┐           │
│   │  Photo  │ ───► │ AI: 150g │ ───►   │ Actual:   │           │
│   │  Nasi   │      │ estimated│        │   200g    │           │
│   └─────────┘      └──────────┘        └───────────┘           │
│                          │                    │                 │
│                          ▼                    ▼                 │
│                    ┌──────────────────────────────┐            │
│                    │     Google Sheets Log        │            │
│                    │  - Original estimate: 150g   │            │
│                    │  - User correction: 200g     │            │
│                    │  - Correction ratio: 1.33x   │            │
│                    └──────────────────────────────┘            │
│                                   │                             │
│                                   ▼                             │
│                    ┌──────────────────────────────┐            │
│                    │   Future Analysis Uses       │            │
│                    │   Historical Corrections     │            │
│                    │   to Adjust Estimates        │            │
│                    └──────────────────────────────┘            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Inline Keyboard untuk Feedback (MVP)

### 1.1 Modifikasi Response Bot

Setelah AI memberikan estimasi, tampilkan inline keyboard:

```
🍚 Nasi Putih
├─ 🔥 Kalori: 260 kkal
├─ 🥩 Protein: 5g
├─ 🍞 Karbo: 58g
├─ 🧈 Lemak: 0.4g
└─ 📏 Berat: ~150 gram (estimasi)

✅ Tersimpan ke log

[✅ Benar] [🔧 Koreksi Berat] [❌ Salah]
```

### 1.2 Callback Button Actions

| Button | Action | Data |
|--------|--------|------|
| ✅ Benar | Mark as verified, no correction needed | `feedback:correct:{entry_id}` |
| 🔧 Koreksi Berat | Prompt user untuk input berat sebenarnya | `feedback:adjust:{entry_id}` |
| ❌ Salah | Delete entry, minta re-submit | `feedback:wrong:{entry_id}` |

### 1.3 File Changes: `bot.py`

```python
# Tambah imports
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Tambah callback handler
async def handle_feedback_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data  # format: "feedback:{action}:{entry_id}"
    _, action, entry_id = data.split(":")

    if action == "correct":
        # Mark entry as verified
        await mark_entry_verified(entry_id, query.from_user.id)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("✅ Terima kasih! Data telah diverifikasi.")

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
        deleted = await delete_entry_by_id(entry_id, query.from_user.id)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            "❌ Entry dihapus.\n"
            "Silakan kirim ulang foto/deskripsi yang benar."
        )

# Modifikasi text handler untuk handle weight correction
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if awaiting weight correction
    if context.user_data.get("awaiting_weight"):
        weight_text = update.message.text
        _, weight = parse_weight_from_text(weight_text + " gram")

        if weight:
            entry_id = context.user_data.get("pending_correction")
            await update_entry_weight(entry_id, weight, update.effective_user.id)

            context.user_data["awaiting_weight"] = False
            context.user_data["pending_correction"] = None

            await update.message.reply_text(
                f"✅ Berat diupdate menjadi {weight}g\n"
                "Terima kasih atas koreksinya!"
            )
            return

    # ... existing text analysis logic ...

# Register handler di main()
application.add_handler(CallbackQueryHandler(handle_feedback_callback, pattern="^feedback:"))
```

### 1.4 Keyboard Builder Function

```python
def build_feedback_keyboard(entry_id: str) -> InlineKeyboardMarkup:
    """Build inline keyboard untuk feedback setelah food logging."""
    keyboard = [
        [
            InlineKeyboardButton("✅ Benar", callback_data=f"feedback:correct:{entry_id}"),
            InlineKeyboardButton("🔧 Koreksi Berat", callback_data=f"feedback:adjust:{entry_id}"),
            InlineKeyboardButton("❌ Salah", callback_data=f"feedback:wrong:{entry_id}"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
```

---

## Phase 2: Schema Extension untuk Feedback Storage

### 2.1 New Columns di Google Sheets

| Column | Name | Type | Description |
|--------|------|------|-------------|
| J | Entry ID | string | UUID untuk track individual entries |
| K | AI Estimate (g) | integer | Berat estimasi dari AI |
| L | User Verified | boolean | TRUE jika user confirm benar |
| M | Actual Weight (g) | integer | Berat sebenarnya dari user |
| N | Correction Ratio | float | actual/estimate (untuk learning) |
| O | Feedback Date | datetime | Kapan feedback diberikan |

### 2.2 File Changes: `sheets_service.py`

```python
# Update HEADERS constant
HEADERS = [
    "Tanggal", "Waktu", "User ID", "Nama Makanan",
    "Kalori", "Protein", "Karbo", "Lemak", "Porsi/Berat", "Image URL",
    # New feedback columns
    "Entry ID", "AI Estimate (g)", "User Verified",
    "Actual Weight (g)", "Correction Ratio", "Feedback Date"
]

def generate_entry_id() -> str:
    """Generate unique entry ID."""
    import uuid
    return str(uuid.uuid4())[:8]

def log_food_with_tracking(user_id: int, food: dict, image_url: str = None) -> str:
    """Log food entry dengan tracking ID untuk feedback."""
    entry_id = generate_entry_id()

    # Extract AI estimate from food dict
    ai_estimate = food.get("weight_grams") or extract_weight_from_portion(food.get("portion", ""))

    row = [
        datetime.now().strftime("%Y-%m-%d"),
        datetime.now().strftime("%H:%M"),
        str(user_id),
        food.get("name", "Unknown"),
        food.get("calories", 0),
        food.get("protein", 0),
        food.get("carbs", 0),
        food.get("fat", 0),
        food.get("portion", food.get("weight_grams", "N/A")),
        image_url or "",
        # Feedback columns
        entry_id,
        ai_estimate or "",
        "",  # User Verified (empty = pending)
        "",  # Actual Weight
        "",  # Correction Ratio
        "",  # Feedback Date
    ]

    worksheet.append_row(row)
    return entry_id

def update_entry_feedback(entry_id: str, user_id: int, verified: bool = None,
                          actual_weight: int = None) -> bool:
    """Update entry dengan feedback dari user."""
    # Find row by entry_id
    all_rows = worksheet.get_all_values()

    for i, row in enumerate(all_rows[1:], start=2):  # Skip header
        if len(row) > 10 and row[10] == entry_id and row[2] == str(user_id):
            # Found the entry
            updates = {}

            if verified is not None:
                updates["M" + str(i)] = "TRUE" if verified else "FALSE"

            if actual_weight is not None:
                updates["N" + str(i)] = actual_weight
                # Calculate correction ratio
                ai_estimate = int(row[11]) if row[11] else None
                if ai_estimate:
                    ratio = round(actual_weight / ai_estimate, 2)
                    updates["O" + str(i)] = ratio

            updates["P" + str(i)] = datetime.now().strftime("%Y-%m-%d %H:%M")

            # Batch update
            for cell, value in updates.items():
                worksheet.update_acell(cell, value)

            return True

    return False

def get_user_correction_history(user_id: int) -> list:
    """Get correction history untuk user tertentu."""
    all_rows = worksheet.get_all_values()
    corrections = []

    for row in all_rows[1:]:
        if len(row) > 14 and row[2] == str(user_id) and row[13]:  # Has actual weight
            corrections.append({
                "food_name": row[3],
                "ai_estimate": int(row[11]) if row[11] else None,
                "actual_weight": int(row[13]) if row[13] else None,
                "correction_ratio": float(row[14]) if row[14] else None,
                "date": row[0],
            })

    return corrections

def get_average_correction_ratio(user_id: int, food_category: str = None) -> float:
    """
    Hitung rata-rata correction ratio untuk user.
    Bisa filtered by food category untuk accuracy yang lebih tinggi.
    """
    corrections = get_user_correction_history(user_id)

    if not corrections:
        return 1.0  # No corrections, use 1:1 ratio

    # TODO: Filter by food_category jika ada
    ratios = [c["correction_ratio"] for c in corrections if c["correction_ratio"]]

    if not ratios:
        return 1.0

    return sum(ratios) / len(ratios)
```

---

## Phase 3: Learning dari Historical Data

### 3.1 Adjustment di Gemini Service

```python
# gemini_service.py

def analyze_food_image_with_learning(image_bytes: bytes, weight_grams: int = None,
                                      user_id: int = None) -> dict:
    """Analyze dengan adjustment berdasarkan historical corrections."""

    # Get base analysis from Gemini
    result = analyze_food_image(image_bytes, weight_grams)

    if weight_grams:
        # User sudah specify weight, tidak perlu adjustment
        return result

    if user_id:
        # Apply user-specific correction ratio
        correction_ratio = get_average_correction_ratio(user_id)

        if correction_ratio != 1.0:
            result = apply_correction_ratio(result, correction_ratio)
            result["_adjustment_applied"] = {
                "ratio": correction_ratio,
                "source": "user_history"
            }

    return result

def apply_correction_ratio(result: dict, ratio: float) -> dict:
    """Apply correction ratio ke semua estimasi berat."""

    for food in result.get("foods", []):
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
    if "total" in result:
        for key in result["total"]:
            if isinstance(result["total"][key], (int, float)):
                result["total"][key] = int(result["total"][key] * ratio)

    return result
```

### 3.2 Enhanced Response Format

Ketika adjustment diterapkan, tampilkan ke user:

```
🍚 Nasi Putih
├─ 🔥 Kalori: 346 kkal
├─ 🥩 Protein: 6.7g
├─ 🍞 Karbo: 77g
├─ 🧈 Lemak: 0.5g
└─ 📏 Berat: ~200 gram (adjusted*)

* Estimasi disesuaikan berdasarkan 5 koreksi sebelumnya

✅ Tersimpan ke log

[✅ Benar] [🔧 Koreksi Berat] [❌ Salah]
```

---

## Phase 4: Analytics & Insights

### 4.1 New Command: `/accuracy`

```python
async def accuracy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's correction statistics."""
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
    avg_ratio = sum(c["correction_ratio"] for c in corrections) / total_corrections

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
        message += f"\n• {c['food_name']}: {c['ai_estimate']}g → {c['actual_weight']}g"

    await update.message.reply_text(message, parse_mode="Markdown")
```

### 4.2 Admin Dashboard (Optional)

Tambah sheet terpisah untuk aggregate statistics:

| Metric | Value |
|--------|-------|
| Total entries with feedback | 150 |
| Average correction ratio (all users) | 1.15 |
| Most underestimated food | Nasi |
| Most overestimated food | Sayur |
| Users with 5+ corrections | 12 |

---

## Implementation Checklist

### Phase 1: MVP Feedback UI
- [ ] Add inline keyboard builder function
- [ ] Add callback query handler
- [ ] Implement "Benar" button (mark verified)
- [ ] Implement "Koreksi Berat" flow
- [ ] Implement "Salah" button (delete entry)
- [ ] Add conversation state management

### Phase 2: Schema & Storage
- [ ] Extend Google Sheets headers
- [ ] Generate entry IDs
- [ ] Implement `log_food_with_tracking()`
- [ ] Implement `update_entry_feedback()`
- [ ] Implement `get_user_correction_history()`
- [ ] Implement `get_average_correction_ratio()`

### Phase 3: Learning System
- [ ] Implement `analyze_food_image_with_learning()`
- [ ] Implement `apply_correction_ratio()`
- [ ] Update response format untuk show adjustment
- [ ] Test with various correction scenarios

### Phase 4: Analytics
- [ ] Implement `/accuracy` command
- [ ] Create aggregate statistics sheet
- [ ] Add trend analysis

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Correction ratio convergence | → 1.0 over time | Average ratio trending toward 1.0 |
| User engagement | 30% feedback rate | % entries with user feedback |
| Accuracy improvement | 20-30% better | Comparison before/after learning |
| Response quality | < 3s latency | Include learning lookup time |

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Users don't provide feedback | Learning tidak jalan | Gamify dengan stats, reminder |
| Outlier corrections skew average | Estimasi jadi tidak akurat | Use median instead of mean, cap ratio 0.5-2.0 |
| Different foods need different ratios | One ratio doesn't fit all | Implement per-category ratios (Phase 4) |
| Cold start untuk user baru | No historical data | Use global average dari all users |

---

## Timeline Estimate

| Phase | Scope | Priority |
|-------|-------|----------|
| Phase 1 | Feedback UI | High |
| Phase 2 | Storage | High |
| Phase 3 | Learning | Medium |
| Phase 4 | Analytics | Low |

---

## Next Steps

1. Review plan ini
2. Decide scope untuk initial implementation
3. Start dengan Phase 1 (MVP)
4. Iterate based on user feedback

---

*Last updated: 2026-02-02*
