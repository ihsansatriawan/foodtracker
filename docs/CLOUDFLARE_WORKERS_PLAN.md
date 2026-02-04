# Cloudflare Workers Deployment - Feasibility Plan

## Overview

Analisis kelayakan untuk deploy Food Tracker Dashboard ke Cloudflare Workers.

---

## Current Stack vs Cloudflare Workers

| Aspect | Current | Cloudflare Workers |
|--------|---------|-------------------|
| **Runtime** | Python (FastAPI) | JavaScript/TypeScript (V8) |
| **Template** | Jinja2 (server-side) | Must use JS-based or static |
| **Database** | Google Sheets API | Need to access from Edge |
| **Hosting** | Self-hosted / VPS | Edge (global CDN) |

---

## Feasibility Assessment

### 1. Runtime Compatibility

**Problem:** Cloudflare Workers hanya support JavaScript/TypeScript (dan Rust via WASM). Python **tidak** didukung secara native.

**Options:**

| Option | Effort | Pros | Cons |
|--------|--------|------|------|
| **A. Rewrite to TypeScript** | High | Native CF support, fast | Complete rewrite needed |
| **B. Cloudflare Pages + API** | Medium | Static UI + Functions | Split architecture |
| **C. Python on separate service** | Low | Keep existing code | Not fully on CF |
| **D. Use Pyodide (WASM)** | Very High | Keep Python | Experimental, slow cold start |

**Recommendation:** Option **B** - Cloudflare Pages dengan Functions

---

### 2. Google Sheets API Access

**Challenge:** Perlu akses Google Sheets API dari Cloudflare Workers.

**Solution:**
- Google Sheets REST API bisa diakses via `fetch()` dari Workers
- Service Account credentials disimpan di Workers Secrets/KV
- JWT token generation di edge (ada library: `@tsndr/cloudflare-worker-jwt`)

**Feasibility:** ✅ **Possible** - tapi perlu rewrite service layer ke JavaScript

---

### 3. Authentication

**Current:** None (open access)

**On CF Workers:**
- Bisa pakai Cloudflare Access (Zero Trust)
- Atau simple password via Workers KV
- JWT-based auth

**Feasibility:** ✅ **Easier on CF** - Cloudflare Access built-in

---

### 4. Image Handling

**Current:** Images di-load dari ImageKit URLs

**On CF Workers:**
- Images tetap dari ImageKit (external CDN)
- Tidak perlu perubahan
- Bisa cache via CF Cache API jika perlu

**Feasibility:** ✅ **No change needed**

---

## Recommended Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Cloudflare Edge                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐     ┌─────────────────────────────┐   │
│  │ Cloudflare      │     │ Cloudflare Pages Functions  │   │
│  │ Pages           │────▶│ (API Routes)                │   │
│  │ (Static HTML)   │     │                             │   │
│  └─────────────────┘     │ /api/entries                │   │
│         │                │ /api/entries/:id            │   │
│         │                └──────────────┬──────────────┘   │
│         │                               │                   │
│  ┌──────▼──────┐         ┌──────────────▼──────────────┐   │
│  │ Workers KV  │         │ Google Sheets API           │   │
│  │ (Cache/     │         │ (External)                  │   │
│  │  Secrets)   │         └─────────────────────────────┘   │
│  └─────────────┘                                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ ImageKit CDN    │
                    │ (Food Images)   │
                    └─────────────────┘
```

---

## Implementation Plan

### Phase 1: Setup Project Structure

```
dashboard-cf/
├── src/
│   ├── index.ts              # Main worker entry
│   ├── api/
│   │   ├── entries.ts        # GET/PUT/DELETE entries
│   │   └── sheets.ts         # Google Sheets service
│   └── lib/
│       ├── auth.ts           # Google auth (JWT)
│       └── response.ts       # Helper functions
├── public/
│   └── index.html            # Static HTML (SPA)
├── wrangler.toml             # CF config
├── package.json
└── tsconfig.json
```

### Phase 2: Rewrite Components

| Component | Python | TypeScript |
|-----------|--------|------------|
| API Routes | FastAPI routes | Hono/itty-router |
| Sheets Service | gspread | Google Sheets REST API + fetch |
| Auth | - | Cloudflare Access / JWT |
| Template | Jinja2 | Static HTML + JS fetch |

### Phase 3: API Endpoints (TypeScript)

```typescript
// Using Hono framework (lightweight, CF-optimized)
import { Hono } from 'hono'

const app = new Hono()

// Get entries
app.get('/api/entries', async (c) => {
  const page = Number(c.req.query('page')) || 1
  const entries = await getEntriesFromSheets(page)
  return c.json(entries)
})

// Update entry
app.put('/api/entries/:row', async (c) => {
  const row = c.req.param('row')
  const body = await c.req.json()
  const success = await updateSheetRow(row, body)
  return c.json({ success })
})

// Delete entry
app.delete('/api/entries/:row', async (c) => {
  const row = c.req.param('row')
  const success = await deleteSheetRow(row)
  return c.json({ success })
})

export default app
```

### Phase 4: Google Sheets Integration

```typescript
// sheets.ts - Access Google Sheets from Workers
import { SignJWT } from 'jose'

interface Env {
  GOOGLE_SERVICE_ACCOUNT: string  // JSON string
  SHEETS_ID: string
}

async function getAccessToken(env: Env): Promise<string> {
  const sa = JSON.parse(env.GOOGLE_SERVICE_ACCOUNT)

  const jwt = await new SignJWT({
    scope: 'https://www.googleapis.com/auth/spreadsheets'
  })
    .setProtectedHeader({ alg: 'RS256', typ: 'JWT' })
    .setIssuer(sa.client_email)
    .setAudience('https://oauth2.googleapis.com/token')
    .setIssuedAt()
    .setExpirationTime('1h')
    .sign(await importPrivateKey(sa.private_key))

  const tokenRes = await fetch('https://oauth2.googleapis.com/token', {
    method: 'POST',
    body: new URLSearchParams({
      grant_type: 'urn:ietf:params:oauth:grant-type:jwt-bearer',
      assertion: jwt
    })
  })

  const { access_token } = await tokenRes.json()
  return access_token
}

async function getSheetData(env: Env): Promise<any[]> {
  const token = await getAccessToken(env)

  const res = await fetch(
    `https://sheets.googleapis.com/v4/spreadsheets/${env.SHEETS_ID}/values/Food%20Log!A:J`,
    { headers: { Authorization: `Bearer ${token}` } }
  )

  return (await res.json()).values
}
```

### Phase 5: Static Frontend

Convert current Jinja2 template to static HTML + JavaScript:

```html
<!-- public/index.html -->
<!DOCTYPE html>
<html>
<head>
  <title>Food Tracker Dashboard</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body>
  <div id="app"></div>

  <script>
    // Fetch data from API
    async function loadEntries(page = 1) {
      const res = await fetch(`/api/entries?page=${page}`)
      const data = await res.json()
      renderTable(data.entries)
    }

    // Render table
    function renderTable(entries) {
      // ... same logic as current template
    }

    loadEntries()
  </script>
</body>
</html>
```

---

## Effort Estimation

| Task | Effort | Notes |
|------|--------|-------|
| Project setup (wrangler, TS) | 1-2 hours | Boilerplate |
| Rewrite API routes | 2-3 hours | FastAPI → Hono |
| Google Sheets service | 3-4 hours | JWT auth + REST API |
| Convert HTML to static SPA | 2-3 hours | Remove Jinja2, add fetch |
| Testing & debugging | 2-3 hours | Edge quirks |
| Deployment config | 1 hour | wrangler.toml, secrets |

**Total: ~12-16 hours**

---

## Pros & Cons

### Pros ✅
1. **Global Edge Deployment** - Fast response worldwide
2. **Free Tier Generous** - 100k requests/day free
3. **No Server Management** - Serverless
4. **Built-in Security** - Cloudflare Access, DDoS protection
5. **Auto Scaling** - No cold start worries

### Cons ❌
1. **Complete Rewrite** - Python → TypeScript
2. **Learning Curve** - CF Workers ecosystem
3. **Limited Runtime** - 10ms CPU time (free), 50ms (paid)
4. **Google Auth Complexity** - JWT signing at edge
5. **Debugging** - Edge environment different from local

---

## Alternative: Hybrid Approach

Jika tidak mau full rewrite, bisa hybrid:

```
┌─────────────────────────────────────────────────────┐
│ Cloudflare Pages (Static Frontend)                  │
│ - HTML/CSS/JS only                                  │
│ - Fetch from external API                           │
└───────────────────────────┬─────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────┐
│ Railway/Render/Fly.io (Python Backend)              │
│ - Keep existing FastAPI code                        │
│ - Expose as API                                     │
└─────────────────────────────────────────────────────┘
```

**Pros:** Keep Python, still get CF edge caching for static assets
**Cons:** Two services to manage, added latency for API calls

---

## Recommendation

| Scenario | Recommendation |
|----------|----------------|
| **Want full CF** | Option B: Rewrite to TypeScript (~16 hours) |
| **Keep Python** | Hybrid: CF Pages + External Python API |
| **Quickest** | Deploy Python to Railway/Render (30 mins) |

---

## Next Steps

1. [ ] Decide: Full CF rewrite atau Hybrid?
2. [ ] Jika full CF: Setup wrangler project
3. [ ] Jika Hybrid: Deploy Python to Railway, static to CF Pages

---

## Questions to Clarify

1. Apakah harus 100% di Cloudflare Workers?
2. Budget untuk paid tier? (affects CPU limits)
3. Timeline? (full rewrite = ~2-3 days)
