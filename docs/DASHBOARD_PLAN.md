# Dashboard UI Plan - Food Tracker (Simplified)

## Overview

Simple web dashboard untuk melihat data food log dari Google Sheets dalam format tabel/spreadsheet dengan preview gambar, sehingga user bisa memvalidasi dan update data secara manual.

---

## Tech Stack

- **Backend:** FastAPI (Python)
- **Frontend:** HTML + Tailwind CSS (CDN)
- **Data:** gspread (reuse existing)

---

## Fitur Utama

1. **Sheet View** - Tampilan tabel seperti spreadsheet
2. **Image Preview** - Klik thumbnail untuk lihat gambar full size
3. **Inline Edit** - Edit cell langsung di tabel
4. **Delete Row** - Hapus entry

---

## Data Columns

| Column | Field | Editable |
|--------|-------|----------|
| Image | thumbnail (klik = fullsize) | No |
| Tanggal | YYYY-MM-DD | Yes |
| Waktu | HH:MM | Yes |
| Nama Makanan | text | Yes |
| Kalori | number | Yes |
| Protein | number | Yes |
| Karbo | number | Yes |
| Lemak | number | Yes |
| Porsi | text | Yes |

---

## UI Mockup

### Main View - Sheet dengan Image Column

```
┌────────────────────────────────────────────────────────────────────────────────────┐
│  Food Tracker - Data Sheet                              [Refresh] [Filter ▼]       │
├────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                    │
│  ┌────────┬──────────┬───────┬───────────────┬───────┬─────┬─────┬─────┬────────┬───┐
│  │ Image  │ Tanggal  │ Waktu │ Nama Makanan  │ Kalori│ P(g)│ K(g)│ L(g)│ Porsi  │ X │
│  ├────────┼──────────┼───────┼───────────────┼───────┼─────┼─────┼─────┼────────┼───┤
│  │ ┌────┐ │2024-02-01│ 14:30 │ Nasi Goreng   │  450  │  12 │  65 │  18 │ 250g   │ 🗑 │
│  │ │ 📷 │ │          │       │               │       │     │     │     │        │   │
│  │ └────┘ │          │       │               │       │     │     │     │        │   │
│  ├────────┼──────────┼───────┼───────────────┼───────┼─────┼─────┼─────┼────────┼───┤
│  │ ┌────┐ │2024-02-01│ 12:15 │ Ayam Bakar    │  320  │  35 │   0 │  15 │ 1 potong│ 🗑 │
│  │ │ 📷 │ │          │       │               │       │     │     │     │        │   │
│  │ └────┘ │          │       │               │       │     │     │     │        │   │
│  ├────────┼──────────┼───────┼───────────────┼───────┼─────┼─────┼─────┼────────┼───┤
│  │ ┌────┐ │2024-02-01│ 10:00 │ Teh Manis     │   80  │   0 │  20 │   0 │ 1 gelas│ 🗑 │
│  │ │ -- │ │          │       │               │       │     │     │     │        │   │
│  │ └────┘ │          │       │               │       │     │     │     │        │   │
│  ├────────┼──────────┼───────┼───────────────┼───────┼─────┼─────┼─────┼────────┼───┤
│  │ ┌────┐ │2024-01-31│ 19:30 │ Mie Ayam      │  480  │  18 │  72 │  12 │ 1 mangkok│ 🗑│
│  │ │ 📷 │ │          │       │               │       │     │     │     │        │   │
│  │ └────┘ │          │       │               │       │     │     │     │        │   │
│  └────────┴──────────┴───────┴───────────────┴───────┴─────┴─────┴─────┴────────┴───┘
│                                                                                    │
│  Showing 1-20 of 156                               [< Prev] [1] [2] [3] [Next >]   │
│                                                                                    │
└────────────────────────────────────────────────────────────────────────────────────┘
```

### Image Preview (Klik Thumbnail)

```
┌────────────────────────────────────────────────────────────────────────────────────┐
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ ░░░░░░░░░░  ┌──────────────────────────────────────────────────┐  ░░░░░░░░░░░░░░ │
│ ░░░░░░░░░░  │                                                  │  ░░░░░░░░░░░░░░ │
│ ░░░░░░░░░░  │                                                  │  ░░░░░░░░░░░░░░ │
│ ░░░░░░░░░░  │                                                  │  ░░░░░░░░░░░░░░ │
│ ░░░░░░░░░░  │              [Full Size Food Image]              │  ░░░░░░░░░░░░░░ │
│ ░░░░░░░░░░  │                                                  │  ░░░░░░░░░░░░░░ │
│ ░░░░░░░░░░  │                                                  │  ░░░░░░░░░░░░░░ │
│ ░░░░░░░░░░  │                                                  │  ░░░░░░░░░░░░░░ │
│ ░░░░░░░░░░  └──────────────────────────────────────────────────┘  ░░░░░░░░░░░░░░ │
│ ░░░░░░░░░░                                                        ░░░░░░░░░░░░░░ │
│ ░░░░░░░░░░         Nasi Goreng | 450 kkal | 2024-02-01 14:30      ░░░░░░░░░░░░░░ │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░[X]░░ │
└────────────────────────────────────────────────────────────────────────────────────┘
```

### Inline Edit (Klik Cell)

```
┌────────┬──────────┬───────┬───────────────────────┬───────┬─────┬─────┬─────┐
│ Image  │ Tanggal  │ Waktu │ Nama Makanan          │ Kalori│ P(g)│ K(g)│ L(g)│
├────────┼──────────┼───────┼───────────────────────┼───────┼─────┼─────┼─────┤
│ ┌────┐ │2024-02-01│ 14:30 │┌─────────────────────┐│  450  │  12 │  65 │  18 │
│ │ 📷 │ │          │       ││ Nasi Goreng Spesial │││       │     │     │     │
│ └────┘ │          │       │└─────────────────────┘│       │     │     │     │
│        │          │       │ [Save] [Cancel]       │       │     │     │     │
└────────┴──────────┴───────┴───────────────────────┴───────┴─────┴─────┴─────┘
```

---

## User Flow

1. Buka dashboard → lihat semua data dalam tabel
2. Klik thumbnail → lihat gambar fullsize untuk validasi
3. Klik cell → edit value langsung
4. Save → update ke Google Sheets
5. Klik delete → konfirmasi → hapus row

---

## API Endpoints

```
GET  /                           # Main page dengan tabel
GET  /api/entries?page=1         # Get entries (paginated)
PUT  /api/entries/{row}          # Update single cell/row
DELETE /api/entries/{row}        # Delete entry
```

---

## File Structure

```
foodtracker/
├── dashboard/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── service.py           # Sheets operations
│   └── templates/
│       └── index.html       # Single page with table
└── run_dashboard.py         # Runner script
```

---

## Implementation Steps

1. [ ] Setup FastAPI dengan single HTML template
2. [ ] Buat tabel dengan data dari Sheets
3. [ ] Tambah image thumbnail column
4. [ ] Implementasi lightbox untuk image preview
5. [ ] Tambah inline edit functionality
6. [ ] Tambah delete dengan konfirmasi
7. [ ] Pagination

---

## Running

```bash
python run_dashboard.py
# atau
uvicorn dashboard.main:app --reload --port 8080
```

Akses di: `http://localhost:8080`
