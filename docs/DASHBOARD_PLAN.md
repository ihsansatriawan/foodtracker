# Dashboard UI Plan - Food Tracker

## Overview

Dashboard web untuk melihat dan mengelola data food tracking dari Google Sheets dengan kemampuan CRUD (Create, Read, Update, Delete) dan visualisasi gambar makanan.

---

## Tech Stack

### Backend
- **Framework:** FastAPI (Python) - konsisten dengan tech stack existing
- **Template Engine:** Jinja2 untuk server-side rendering
- **Data Layer:** gspread (reuse dari `sheets_service.py`)
- **Authentication:** Simple token-based atau Basic Auth (untuk MVP)

### Frontend
- **CSS Framework:** Tailwind CSS (via CDN untuk simplicity)
- **JavaScript:** Vanilla JS + Alpine.js untuk interactivity
- **Icons:** Heroicons atau Lucide
- **Image Gallery:** Lightbox untuk preview gambar

### Why This Stack?
1. Reuse existing Google Sheets integration
2. Python-based = tim yang sama bisa maintain
3. Minimal dependencies
4. Fast to develop

---

## Data Model (dari Google Sheets)

### Food Log Worksheet
| Column | Field | Type | Dashboard Use |
|--------|-------|------|---------------|
| Tanggal | date | YYYY-MM-DD | Filter, Sort |
| Waktu | time | HH:MM | Sort |
| User ID | user_id | String | Filter |
| Nama Makanan | name | String | Display, Edit |
| Kalori | calories | Float | Display, Edit, Chart |
| Protein | protein | Float | Display, Edit |
| Karbo | carbs | Float | Display, Edit |
| Lemak | fat | Float | Display, Edit |
| Porsi/Berat | portion | String | Display, Edit |
| Image URL | image_url | String | Image Preview |

### User Settings Worksheet
| Column | Field | Type | Dashboard Use |
|--------|-------|------|---------------|
| User ID | user_id | String | Filter |
| Kalori Target | target | Int | Display, Edit |
| Created At | created_at | Timestamp | Display |
| Updated At | updated_at | Timestamp | Display |

---

## UI Design

### Layout Structure

```
┌─────────────────────────────────────────────────────────────┐
│  Header: Logo + Navigation + User Filter Dropdown           │
├─────────────────────────────────────────────────────────────┤
│  Sidebar           │  Main Content                          │
│  ┌───────────────┐ │  ┌─────────────────────────────────┐   │
│  │ Navigation    │ │  │ Stats Cards (Today)             │   │
│  │ - Dashboard   │ │  │ [Kalori] [Protein] [Karbo] [Fat]│   │
│  │ - Food Log    │ │  └─────────────────────────────────┘   │
│  │ - Settings    │ │  ┌─────────────────────────────────┐   │
│  │               │ │  │ Food Entries Table/Grid         │   │
│  │ Date Filter   │ │  │ - Image thumbnail               │   │
│  │ [From] [To]   │ │  │ - Food name                     │   │
│  │               │ │  │ - Nutrition info                │   │
│  │ Quick Links   │ │  │ - Actions (Edit/Delete)         │   │
│  │ - Today       │ │  └─────────────────────────────────┘   │
│  │ - This Week   │ │  ┌─────────────────────────────────┐   │
│  │ - This Month  │ │  │ Pagination                      │   │
│  └───────────────┘ │  └─────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Pages

#### 1. Dashboard (Home)
- **Summary Cards:** Total kalori hari ini, progress bar vs target
- **Quick Stats:** Protein, Karbo, Lemak totals
- **Recent Entries:** 5 entri makanan terakhir dengan thumbnail
- **Weekly Chart:** Line chart kalori 7 hari terakhir

#### 2. Food Log (CRUD)
- **Table View dengan kolom:**
  - Thumbnail gambar (klik untuk fullsize)
  - Tanggal & Waktu
  - Nama Makanan
  - Kalori | Protein | Karbo | Lemak
  - Porsi
  - Actions: Edit | Delete

- **Features:**
  - Filter by date range
  - Filter by user (jika multi-user)
  - Search by food name
  - Sort by any column
  - Pagination (20 items per page)
  - Bulk delete

- **Add New Entry (Create):**
  - Modal form dengan fields:
    - Tanggal (date picker)
    - Waktu (time picker)
    - Nama Makanan (text)
    - Kalori, Protein, Karbo, Lemak (number inputs)
    - Porsi (text)
    - Upload Image (optional, ke ImageKit)

- **Edit Entry (Update):**
  - Same form as Create, pre-filled
  - Can replace image

- **Delete Entry:**
  - Confirmation modal
  - Soft delete atau hard delete

#### 3. Image Gallery
- **Grid View:** Semua gambar makanan
- **Lightbox:** Klik untuk preview fullsize
- **Filter:** By date, by food name
- **Info Overlay:** Nama makanan, kalori, tanggal

#### 4. Settings
- **User Target Management:**
  - View all users dengan target mereka
  - Edit calorie target per user
  - Add new user target
  - Delete user target

---

## API Endpoints

### Food Entries

```
GET    /api/entries                    # List all entries (paginated)
       ?user_id=123
       &date_from=2024-01-01
       &date_to=2024-01-31
       &search=nasi
       &page=1
       &per_page=20

GET    /api/entries/{row_index}        # Get single entry
POST   /api/entries                    # Create new entry
PUT    /api/entries/{row_index}        # Update entry
DELETE /api/entries/{row_index}        # Delete entry

GET    /api/entries/stats              # Get aggregated stats
       ?user_id=123
       &date=2024-01-15
```

### User Settings

```
GET    /api/users                      # List all users with settings
GET    /api/users/{user_id}            # Get user settings
PUT    /api/users/{user_id}/target     # Update calorie target
```

### Images

```
POST   /api/upload                     # Upload image to ImageKit
```

---

## Implementation Phases

### Phase 1: Basic Dashboard (MVP)
- [ ] Setup FastAPI project structure
- [ ] Create dashboard_service.py (extend sheets_service)
- [ ] Basic HTML templates with Tailwind
- [ ] Dashboard home page with stats
- [ ] Food log table (Read only)
- [ ] Image thumbnail display
- [ ] Simple authentication

### Phase 2: CRUD Operations
- [ ] Create entry form + API
- [ ] Edit entry modal + API
- [ ] Delete with confirmation + API
- [ ] Image upload integration
- [ ] Form validation

### Phase 3: Enhanced Features
- [ ] Date range filter
- [ ] Search functionality
- [ ] Sorting
- [ ] Pagination
- [ ] User filter dropdown

### Phase 4: Visualizations
- [ ] Weekly calorie chart (Chart.js)
- [ ] Macro breakdown pie chart
- [ ] Progress bar animation
- [ ] Image gallery with lightbox

### Phase 5: Polish
- [ ] Responsive design (mobile-friendly)
- [ ] Loading states
- [ ] Error handling
- [ ] Toast notifications
- [ ] Export to CSV

---

## File Structure

```
foodtracker/
├── dashboard/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry point
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── pages.py            # HTML page routes
│   │   └── api.py              # REST API routes
│   ├── services/
│   │   ├── __init__.py
│   │   └── dashboard_service.py # Extended sheets operations
│   ├── templates/
│   │   ├── base.html           # Base layout
│   │   ├── dashboard.html      # Home page
│   │   ├── food_log.html       # CRUD table page
│   │   ├── gallery.html        # Image gallery
│   │   ├── settings.html       # User settings
│   │   └── components/
│   │       ├── navbar.html
│   │       ├── sidebar.html
│   │       ├── stats_card.html
│   │       ├── food_table.html
│   │       ├── food_form.html
│   │       └── pagination.html
│   └── static/
│       ├── css/
│       │   └── custom.css
│       └── js/
│           └── app.js
├── requirements.txt            # Add: fastapi, uvicorn, jinja2
└── run_dashboard.py            # Dashboard runner script
```

---

## Security Considerations

1. **Authentication:**
   - Basic Auth untuk MVP
   - Environment variable: `DASHBOARD_PASSWORD`
   - Session-based login

2. **Authorization:**
   - Admin-only access
   - No public access

3. **Data Validation:**
   - Validate all inputs server-side
   - Sanitize food names (prevent XSS)
   - Validate nutrition values (positive numbers)

4. **Rate Limiting:**
   - Limit API calls per minute
   - Prevent abuse

---

## Environment Variables (New)

```env
# Dashboard specific
DASHBOARD_HOST=0.0.0.0
DASHBOARD_PORT=8080
DASHBOARD_PASSWORD=your_secure_password
DASHBOARD_SECRET_KEY=random_secret_for_sessions
```

---

## Running the Dashboard

```bash
# Development
cd foodtracker
python run_dashboard.py

# Or with uvicorn directly
uvicorn dashboard.main:app --reload --host 0.0.0.0 --port 8080

# Production
uvicorn dashboard.main:app --host 0.0.0.0 --port 8080 --workers 4
```

---

## UI Mockups

### Dashboard Home
```
┌─────────────────────────────────────────────────────────────────┐
│  🍽️ Food Tracker Dashboard              [User: 123456] [Logout] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📊 Today's Summary (2024-02-01)                               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │ 🔥 1,250 │ │ 💪 45g   │ │ 🍚 180g  │ │ 🥑 35g   │          │
│  │ Kalori   │ │ Protein  │ │ Karbo    │ │ Lemak    │          │
│  │ /2,000   │ │          │ │          │ │          │          │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘          │
│                                                                 │
│  Progress: [████████████░░░░░░░░] 62.5%                        │
│                                                                 │
│  📋 Recent Entries                              [View All →]   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 🖼️ │ Nasi Goreng        │ 450 kkal │ 14:30 │ [Edit][Del]│   │
│  │ 🖼️ │ Ayam Bakar         │ 320 kkal │ 12:15 │ [Edit][Del]│   │
│  │ 🖼️ │ Teh Manis          │ 80 kkal  │ 10:00 │ [Edit][Del]│   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  📈 Weekly Trend                                               │
│  │    *                                                        │
│  │   * *    *                                                  │
│  │  *   *  * *                                                 │
│  │ *     **                                                    │
│  └─────────────────                                            │
│    Mon Tue Wed Thu Fri Sat Sun                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Food Log Table
```
┌─────────────────────────────────────────────────────────────────┐
│  📋 Food Log                              [+ Add Entry]         │
├─────────────────────────────────────────────────────────────────┤
│  Filter: [Date From ▼] [Date To ▼] [Search... 🔍]   [Apply]    │
├─────────────────────────────────────────────────────────────────┤
│  ┌───┬────────┬─────────────────┬───────┬────┬────┬────┬─────┐ │
│  │ 🖼️│ Date   │ Food Name       │ Kalori│ P  │ K  │ L  │ Act │ │
│  ├───┼────────┼─────────────────┼───────┼────┼────┼────┼─────┤ │
│  │[📷]│02/01 14:30│Nasi Goreng  │ 450   │12g │65g │18g │✏️ 🗑️│ │
│  │[📷]│02/01 12:15│Ayam Bakar   │ 320   │35g │ 0g │15g │✏️ 🗑️│ │
│  │[ ]│02/01 10:00│Teh Manis     │  80   │ 0g │20g │ 0g │✏️ 🗑️│ │
│  │[📷]│01/31 19:30│Mie Ayam     │ 480   │18g │72g │12g │✏️ 🗑️│ │
│  └───┴────────┴─────────────────┴───────┴────┴────┴────┴─────┘ │
│                                                                 │
│  Showing 1-20 of 156 entries    [< Prev] [1] [2] [3] [Next >]  │
└─────────────────────────────────────────────────────────────────┘
```

### Image Gallery
```
┌─────────────────────────────────────────────────────────────────┐
│  🖼️ Image Gallery                        Filter: [All Dates ▼] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │
│  │             │ │             │ │             │ │           │ │
│  │   [Image]   │ │   [Image]   │ │   [Image]   │ │  [Image]  │ │
│  │             │ │             │ │             │ │           │ │
│  ├─────────────┤ ├─────────────┤ ├─────────────┤ ├───────────┤ │
│  │ Nasi Goreng │ │ Ayam Bakar  │ │ Mie Ayam    │ │ Sate Ayam │ │
│  │ 450 kkal    │ │ 320 kkal    │ │ 480 kkal    │ │ 250 kkal  │ │
│  │ 02/01 14:30 │ │ 02/01 12:15 │ │ 01/31 19:30 │ │ 01/31 12:0│ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘ │
│                                                                 │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │
│  │             │ │             │ │             │ │           │ │
│  │   [Image]   │ │   [Image]   │ │   [Image]   │ │  [Image]  │ │
│  │             │ │             │ │             │ │           │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘ │
│                                                                 │
│                    [Load More...]                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Next Steps

1. Review dan approve plan ini
2. Mulai implementasi Phase 1 (MVP)
3. Iterate berdasarkan feedback

---

## Questions to Clarify

1. Apakah dashboard single-user atau multi-user access?
2. Perlu deployment ke cloud (Vercel, Railway, etc)?
3. Apakah perlu fitur export data?
4. Preferensi styling (color scheme)?
