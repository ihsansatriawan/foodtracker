# Dashboard UI Plan - Food Tracker (Simplified)

## Overview

Simple web dashboard untuk melihat data food log dari Google Sheets dalam format tabel dengan gambar makanan yang jelas terlihat, sehingga user bisa memvalidasi dan update data secara manual.

---

## Tech Stack

- **Backend:** FastAPI (Python)
- **Frontend:** HTML + Tailwind CSS (CDN)
- **Data:** gspread (reuse existing)

---

## Fitur Utama

1. **Sheet View** - Tampilan tabel dengan gambar besar
2. **Image Column** - Gambar ditampilkan dalam ukuran yang jelas (bukan thumbnail kecil)
3. **Inline Edit** - Edit cell langsung di tabel (untuk kolom tertentu)
4. **Delete Row** - Hapus entry

---

## Data Columns

| Column | Field | Editable | Notes |
|--------|-------|----------|-------|
| Image | gambar makanan | **No** | Ditampilkan besar (~150px) agar jelas |
| Tanggal | YYYY-MM-DD | **No** | Read-only |
| Waktu | HH:MM | **No** | Read-only |
| Nama Makanan | text | **Yes** | Klik untuk edit |
| Kalori | number | **Yes** | Klik untuk edit |
| Protein | number | **Yes** | Klik untuk edit |
| Karbo | number | **Yes** | Klik untuk edit |
| Lemak | number | **Yes** | Klik untuk edit |
| Porsi | text | **Yes** | Klik untuk edit |

---

## UI Mockup

### Main View - Sheet dengan Image Besar

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│  Food Tracker - Data Sheet                                    [Refresh] [Filter]         │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│ ┌───────────────┬──────────┬───────┬───────────────┬───────┬─────┬─────┬─────┬────────┬───┐
│ │     Image     │ Tanggal  │ Waktu │ Nama Makanan  │ Kalori│ P(g)│ K(g)│ L(g)│ Porsi  │ X │
│ ├───────────────┼──────────┼───────┼───────────────┼───────┼─────┼─────┼─────┼────────┼───┤
│ │ ┌───────────┐ │          │       │               │       │     │     │     │        │   │
│ │ │           │ │          │       │               │       │     │     │     │        │   │
│ │ │   [Foto   │ │2024-02-01│ 14:30 │ Nasi Goreng   │  450  │  12 │  65 │  18 │ 250g   │ 🗑 │
│ │ │   Nasi    │ │          │       │               │       │     │     │     │        │   │
│ │ │  Goreng]  │ │          │       │               │       │     │     │     │        │   │
│ │ │           │ │          │       │               │       │     │     │     │        │   │
│ │ └───────────┘ │          │       │               │       │     │     │     │        │   │
│ ├───────────────┼──────────┼───────┼───────────────┼───────┼─────┼─────┼─────┼────────┼───┤
│ │ ┌───────────┐ │          │       │               │       │     │     │     │        │   │
│ │ │           │ │          │       │               │       │     │     │     │        │   │
│ │ │   [Foto   │ │2024-02-01│ 12:15 │ Ayam Bakar    │  320  │  35 │   0 │  15 │1 potong│ 🗑 │
│ │ │   Ayam    │ │          │       │               │       │     │     │     │        │   │
│ │ │  Bakar]   │ │          │       │               │       │     │     │     │        │   │
│ │ │           │ │          │       │               │       │     │     │     │        │   │
│ │ └───────────┘ │          │       │               │       │     │     │     │        │   │
│ ├───────────────┼──────────┼───────┼───────────────┼───────┼─────┼─────┼─────┼────────┼───┤
│ │               │          │       │               │       │     │     │     │        │   │
│ │  [No Image]   │2024-02-01│ 10:00 │ Teh Manis     │   80  │   0 │  20 │   0 │ 1 gelas│ 🗑 │
│ │               │          │       │               │       │     │     │     │        │   │
│ ├───────────────┼──────────┼───────┼───────────────┼───────┼─────┼─────┼─────┼────────┼───┤
│ │ ┌───────────┐ │          │       │               │       │     │     │     │        │   │
│ │ │           │ │          │       │               │       │     │     │     │        │   │
│ │ │   [Foto   │ │2024-01-31│ 19:30 │ Mie Ayam      │  480  │  18 │  72 │  12 │1 mangkok│🗑 │
│ │ │   Mie     │ │          │       │               │       │     │     │     │        │   │
│ │ │  Ayam]    │ │          │       │               │       │     │     │     │        │   │
│ │ │           │ │          │       │               │       │     │     │     │        │   │
│ │ └───────────┘ │          │       │               │       │     │     │     │        │   │
│ └───────────────┴──────────┴───────┴───────────────┴───────┴─────┴─────┴─────┴────────┴───┘
│                                                                                          │
│  Showing 1-20 of 156                                     [< Prev] [1] [2] [3] [Next >]   │
│                                                                                          │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

### Inline Edit - Klik Cell untuk Edit

Kolom yang bisa di-edit: **Nama Makanan, Kalori, Protein, Karbo, Lemak, Porsi**

```
┌───────────────┬──────────┬───────┬───────────────────────┬───────┬─────┬─────┬─────┬────────┐
│     Image     │ Tanggal  │ Waktu │ Nama Makanan          │ Kalori│ P(g)│ K(g)│ L(g)│ Porsi  │
├───────────────┼──────────┼───────┼───────────────────────┼───────┼─────┼─────┼─────┼────────┤
│ ┌───────────┐ │          │       │                       │       │     │     │     │        │
│ │           │ │          │       │┌─────────────────────┐│       │     │     │     │        │
│ │   [Foto]  │ │2024-02-01│ 14:30 ││ Nasi Goreng Spesial ││  450  │  12 │  65 │  18 │ 250g   │
│ │           │ │          │       │└─────────────────────┘│       │     │     │     │        │
│ │           │ │  (gray)  │(gray) │ [Save] [Cancel]       │(click)│(click│(click│(click│(click) │
│ └───────────┘ │          │       │                       │       │     │     │     │        │
└───────────────┴──────────┴───────┴───────────────────────┴───────┴─────┴─────┴─────┴────────┘

Legend:
- (gray) = Read-only, tidak bisa di-edit
- (click) = Klik untuk edit inline
```

### Edit Angka (Kalori/Protein/Karbo/Lemak)

```
│ ... │  ┌─────┐  │ ... │
│ ... │  │ 450 │  │ ... │
│ ... │  └─────┘  │ ... │
│ ... │  [✓] [✗]  │ ... │
```

---

## User Flow

1. **Buka dashboard** → Lihat semua data dalam tabel dengan gambar besar
2. **Lihat gambar** → Gambar sudah terlihat jelas di kolom Image (±150x150px)
3. **Klik cell editable** → Muncul input field untuk edit
4. **Save/Cancel** → Simpan perubahan atau batalkan
5. **Delete** → Klik tombol hapus → konfirmasi → hapus row

---

## API Endpoints

```
GET  /                           # Main page dengan tabel
GET  /api/entries?page=1         # Get entries (paginated)
PUT  /api/entries/{row}          # Update entry fields
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
3. [ ] Tampilkan gambar dalam ukuran besar (~150px)
4. [ ] Implementasi inline edit untuk: Nama, Kalori, Protein, Karbo, Lemak, Porsi
5. [ ] Tambah delete dengan konfirmasi
6. [ ] Pagination

---

## Running

```bash
python run_dashboard.py
# atau
uvicorn dashboard.main:app --reload --port 8080
```

Akses di: `http://localhost:8080`
