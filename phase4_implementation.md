# Phase 4: Data Persistence - Implementation Plan 📊

## Overview
Phase 4 adds food logging persistence via Google Sheets, enabling users to track their daily intake and view history.

---

## Tasks Breakdown

### 1. Google Sheets Integration Setup (High Priority)
**New file: `sheets_service.py`**

| Task | Description |
|------|-------------|
| Add `gspread` and `google-auth` to requirements.txt | Google Sheets API libraries |
| Create service account credentials setup | Document how to get `credentials.json` |
| Add `GOOGLE_SHEETS_ID` to config.py | Spreadsheet ID from URL |
| Implement `get_sheet_client()` | Auth and connect to Google Sheets |
| Implement `log_food_entry(user_id, food_data)` | Append row with timestamp + nutrition |
| Auto-create sheet if not exists | Initialize with header row |

**Google Sheets Schema:**
```
| Tanggal | Waktu | User ID | Nama Makanan | Kalori | Protein | Karbo | Lemak | Porsi/Berat |
```

---

### 2. Modify bot.py to Log Entries (High Priority)

| Task | Description |
|------|-------------|
| Import sheets_service | Connect to persistence layer |
| Call `log_food_entry()` after successful analysis | Auto-save every food entry |
| Add confirmation message | "✅ Tersimpan ke log" |
| Handle logging errors gracefully | Don't block user if sheets fails |

---

### 3. `/today` Command (High Priority)

| Task | Description |
|------|-------------|
| Add `/today` handler in bot.py | New command |
| Implement `get_today_entries(user_id)` in sheets_service | Filter by date + user |
| Calculate daily totals | Sum calories, protein, carbs, fat |
| Format response with emoji | Show list + total summary |

**Response format:**
```
📅 Makanan Hari Ini (1 Feb 2026)

1. Nasi Goreng - 450 kkal
2. Kopi Susu - 120 kkal
3. Ayam Bakar - 280 kkal

📊 Total Hari Ini:
🔥 Kalori: 850 kkal
🥩 Protein: 45g
🍚 Karbo: 95g
🧈 Lemak: 28g
```

---

### 4. `/history` Command (Medium Priority)

| Task | Description |
|------|-------------|
| Add `/history` handler in bot.py | New command |
| Implement `get_recent_entries(user_id, limit=10)` in sheets_service | Last N entries |
| Format with date grouping | Group by day |

---

### 5. `/undo` Command (Medium Priority)

| Task | Description |
|------|-------------|
| Add `/undo` handler in bot.py | New command |
| Implement `delete_last_entry(user_id)` in sheets_service | Remove most recent row |
| Confirmation with deleted item info | "🗑️ Dihapus: Nasi Goreng (450 kkal)" |

---

## Dependencies to Add
```
gspread>=5.12.0
google-auth>=2.23.0
```

---

## Files to Create/Modify

| File | Action |
|------|--------|
| `sheets_service.py` | **CREATE** - Google Sheets integration |
| `requirements.txt` | **MODIFY** - Add gspread dependencies |
| `config.py` | **MODIFY** - Add GOOGLE_SHEETS_ID |
| `bot.py` | **MODIFY** - Add commands & logging |
| `.env.example` | **MODIFY** - Add sheets config example |

---

## Implementation Order

- [x] **Step 1:** Setup - Add dependencies & config
- [x] **Step 2:** Core - Create `sheets_service.py` with auth + logging
- [x] **Step 3:** Integration - Modify bot.py to auto-log entries
- [x] **Step 4:** `/today` - Implement daily summary command
- [x] **Step 5:** `/history` - Implement history command
- [x] **Step 6:** `/undo` - Implement undo command
- [x] **Step 7:** Docs - Update ROADMAP.md & README

---

*Created: February 2026*
*Completed: February 2026*
