# Food Tracker Bot - Roadmap 🗺️

Development roadmap for the Food Tracker Telegram bot.

---

## ✅ Completed (MVP)

### Phase 1: Setup & Configuration ✅
- [x] `requirements.txt` - Python dependencies
- [x] `config.py` - Environment variables loader  
- [x] `.env.example` - Credentials template

### Phase 2: Gemini Vision Integration ✅
- [x] `gemini_service.py` - Gemini API integration
  - [x] `analyze_food_image(image_bytes, weight_grams)` - Vision-based analysis
  - [x] `analyze_food_text(description, weight_grams)` - Text-based analysis
  - [x] `parse_weight_from_text(text)` - Weight parsing (gram/kg)
- [x] Multi-food detection in single image
- [x] Response normalization to `{foods: [...], total: {...}}`

### Phase 3: Telegram Bot Core ✅
- [x] `bot.py` - Main bot with handlers
  - [x] `/start` - Welcome message
  - [x] `/help` - Usage guide
  - [x] Photo handler with caption weight support
  - [x] Text handler with inline weight parsing
- [x] Indonesian language interface
- [x] Emoji-rich nutrition response formatting

### Weight Input Feature ✅
- [x] Photo + weight caption (e.g., "250 gram")
- [x] Text + weight (e.g., "nasi goreng 200g")
- [x] Supported formats: `gram`, `g`, `gr`, `kg`, `kilogram`
- [x] Precise nutrition calculation based on actual weight

### Phase 4: Data Persistence ✅
- [x] `sheets_service.py` - Google Sheets integration
  - [x] Service account authentication
  - [x] Auto-create "Food Log" worksheet with headers
  - [x] `log_food_entry()` - Save entries with timestamp
  - [x] `get_today_entries()` - Filter by date and user
  - [x] `get_recent_entries()` - Paginated history
  - [x] `delete_last_entry()` - Undo support
- [x] `/today` command - Daily calorie summary
- [x] `/history` command - Recent food entries (last 10)
- [x] `/undo` command - Delete last entry
- [x] Auto-logging after successful analysis

**Google Sheets Schema:**
| Column | Description |
|--------|-------------|
| Tanggal | Date (YYYY-MM-DD) |
| Waktu | Time (HH:MM) |
| User ID | Telegram user ID |
| Nama Makanan | Food name |
| Kalori | Calories (kkal) |
| Protein | Protein (gram) |
| Karbo | Carbs (gram) |
| Lemak | Fat (gram) |
| Porsi/Berat | Portion or weight |
| Image URL | Telegram file URL for manual validation |

---

## 🔜 Planned Features

### Phase 5: Goal Tracking 🎯
*Priority: Medium*

| Feature | Priority | Description |
|---------|----------|-------------|
| `/target <kkal>` | 🔴 High | Set daily calorie target |
| Daily Progress Bar | 🟡 Medium | Visual progress towards goal |
| Calorie Warning | 🟡 Medium | Alert when approaching limit |
| Weekly Summary | 🟢 Low | Automated weekly report |

---

### Phase 6: Enhanced Analysis 🔬
*Priority: Medium*

| Feature | Priority | Description |
|---------|----------|-------------|
| Per-item Weight | 🟡 Medium | "nasi 200g, ayam 150g" format |
| Nutrition per 100g | 🟡 Medium | Standardized display option |
| AI Weight Hint | 🟢 Low | AI suggests approximate weight |
| Correction Keyboard | 🟢 Low | Inline keyboard to adjust estimates |
| Barcode Scanning | 🟢 Low | Scan packaged food barcodes |

---

### Phase 7: User Experience 💫
*Priority: Medium*

| Feature | Priority | Description |
|---------|----------|-------------|
| Quick Buttons | 🟡 Medium | Inline buttons for common foods |
| Favorites | 🟡 Medium | One-tap logging for frequent meals |
| Meal Templates | 🟢 Low | Reusable meal combinations |
| Voice Input | 🟢 Low | Voice messages for food logging |

---

### Phase 8: Multi-user & Social 👥
*Priority: Low*

| Feature | Priority | Description |
|---------|----------|-------------|
| User Profiles | 🟡 Medium | Per-user settings and data |
| Group Chat | 🟢 Low | Family/group calorie tracking |
| Leaderboards | 🟢 Low | Weekly challenges |
| Multi-language | 🟢 Low | English and other languages |

---

### Phase 9: Integrations 🔗
*Priority: Low*

| Feature | Priority | Description |
|---------|----------|-------------|
| Fitness App Export | 🟢 Low | Export to MyFitnessPal, etc. |
| Smartwatch Sync | 🟢 Low | Apple Health / Google Fit |
| Nutritionist Mode | 🟢 Low | Share with dietitian |

---

## Technical Improvements 🔧

| Improvement | Priority | Description |
|-------------|----------|-------------|
| Unit Tests | 🔴 High | Add pytest test suite |
| Rate Limiting | 🟡 Medium | Handle Gemini API limits |
| Error Analytics | 🟡 Medium | Track and report bot errors |
| Docker Support | 🟢 Low | Containerized deployment |
| Railway Deploy | 🟢 Low | Production deployment guide |

---

## Legend

| Symbol | Priority |
|--------|----------|
| 🔴 | High - Next release |
| 🟡 | Medium - 1-2 releases |
| 🟢 | Low - Future |

---

*Last updated: February 2025*
