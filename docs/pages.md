# UI Pages — Planning

Mobile-first React app. Three screens for the MVP flow: **upload a receipt → see the ranked price list → see it on a map**.

### Shared control language

Every input across the app is built from one small set of primitives in
`src/styles/controls.css`, so sign-in/out, the receipt list, the upload zone, and
the name field all read as one system:

- `.panel` — dashed-accent container with a `.panel-title` caption
- `.tile` — icon-above-label choice button (the "options" pattern; `.lg` for the full upload zone)
- `.field` / `.field-row` — text input, optionally paired with an `.icon-btn`
- `.btn` (`.btn-primary` / `.btn-white` / `.btn-danger`) and `.icon-btn`

### The origin store (map screen)

The store the receipt was actually bought at, at the price actually paid, is shown as a
distinct **slate-accented** card marked "מקור" under a "קניתם כאן" header — always, even when
it's across town. On the map it gets a pin **only when it's within `ORIGIN_NEARBY_M` (2.5 km)**
of the user, so a receipt from far away never zooms the map out or clutters it. Mock origin
lives in `src/resources/origin.json` (offset from the user; far by default).

### Two prices, everywhere

Every store shows two numbers, and the distinction matters:

- **Best price** (headline, large) — the total *after* swapping in cheaper similar products. This is what ranking and "הכי זול" are based on.
- **Same-cart price** (small, dimmed) — the exact like-for-like total with no substitutions. Keeps the comparison honest.

Design language: **bright & friendly** — light theme (soft mint-white background), warm emerald-green accent, rounded cards with soft shadows, smooth micro-animations, monospace accents for prices. UI copy is **Hebrew (RTL)**; the brand name `sali` stays in Latin script.

> **Mocked for now:** OCR is faked. Any uploaded/captured file — or pasted URL — is ignored;
> nothing is fetched over the network. We show a short loading spinner, load the mock receipt
> from `src/resources/`, and rank real retailers with mock prices.

---

## Screen 1 — Home (conditional)

**Route:** `/`

Home renders one of two modes depending on auth state and whether the user has receipts.

### Mode A — upload (signed out, **or** signed in with no receipts)

Single-action landing screen. Get the user's receipt in as fast as possible.

### Layout (top → bottom)

1. **Header** — `sali` logo/wordmark, small tagline ("Scan. Compare. Save.").
2. **Hero upload zone** (the star of the screen, vertically centered):
   - Large tappable card (~60% of viewport height) with animated dashed/glowing border.
   - Receipt/scan icon with a subtle animated "scanline" effect.
   - Text: "Upload your receipt".
   - Three ways in:
     - 📷 **Camera** — opens device camera (`<input type="file" accept="image/*" capture="environment">`).
     - 🖼 **Upload** — opens file picker for an image or PDF (also accepts drag & drop on desktop).
     - 🔗 **Paste a link** — under an "או הדביקו קישור לקבלה" divider, a URL field + submit
       button for a receipt hosted online (e.g. a retailer's digital-receipt page). Submitting
       runs the same flow with one extra loading stage ("טוענים את הקבלה מהקישור…").
3. **Footer hint** — one line, e.g. "We'll find the cheapest cart near you".

### Behavior

- Any file selected → ignore its contents (mock OCR).
- Transition to a **loading state** (~1.5–2s): full-screen overlay, circular spinner with "Reading your receipt…" then "Finding stores near you…" (staged messages sells the fake OCR).
- Then navigate to Screen 2.

### Mode B — receipt list (signed in, has receipts)

- Centered `sali` wordmark with a greeting; **`+` button top-right**, sign-out top-left.
- `+` opens a menu: **קבלה ריקה** (create an empty receipt) · **צילום קבלה** · **העלאת קובץ** ·
  **מקישור** (reveals the URL field inline).
- Below it, saved receipts newest-first — name, save date, item count, total. Tapping a row
  opens `/results` with that receipt as the baseline; a trash button deletes it.

This replaces the old standalone `/saved` screen, which now redirects to `/`.

### Sign-in gate

A signed-out user can scan freely, but when the loading stages finish they hit a modal —
"הקבלה מוכנה!" with a Google sign-in button — instead of continuing. Signing in resumes
straight to `/results` with the scan intact (it is stashed under `sali.pendingScan`).

### Auth & persistence

`src/lib/auth.tsx` wraps Supabase Google OAuth; `src/lib/receipts.ts` reads and writes the
`receipts` table. **Both fall back to a local mode** when `VITE_SUPABASE_*` is unset: sign-in
is faked and receipts live in `localStorage`, so the UI stays fully usable without credentials.

---

## Screen 2 — Results (Ranked List)

**Route:** `/results`

**Purpose:** the primary comparison view. Answers "where is this cart cheapest?" in one scroll.

### Layout

1. **Header** — back button + "השוואת מחירים".
2. **Receipt card (pinned at top, marked)** — the scanned receipt as the baseline: green-bordered card with a "הקבלה שלכם" badge, the receipt total, item count, and the headline "אפשר לחסוך עד ₪X על אותה עגלה".
3. **Ranked list** — every store, cheapest **best price** first, physical and online interleaved:
   - Rank number, brand logo, name
   - Distance (physical) or delivery fee (online), plus an "אונליין" tag; online rows are tinted blue
   - **Best price** large, **same-cart price** small beneath it, and the swap count
   - Saving vs. the receipt, green when cheaper / red when pricier
   - Cheapest row gets a "הכי זול" tag and a green border
4. **Sticky CTA** — "הצגה על המפה" → Screen 3.

---

### Saving & reopening

After a scan, the receipt card on `/results` offers **"שמירת הקבלה"** → an inline name field
(prefilled with a date-based suggestion like "קניות 30.7") → saved. The card then shows the
name in its badge plus "נשמר בקבלות שלי ✓".

Saved receipts live in `localStorage` (`sali.savedReceipts`), with `sali.activeReceipt` naming
which one the comparison screens should show — `null` means "the receipt just scanned". A new
scan clears it. See `src/lib/receipts.ts`.

---

## Screen 3 — Map (Nearby Stores & Cart Prices)

**Route:** `/map`

**Purpose:** show where the user is, which supermarkets are nearby, and what the scanned cart costs at each — cheapest should pop instantly.

### Layout

1. **Map (full screen, base layer)** — Leaflet + OpenStreetMap tiles, dark map style to match theme.
   - **User marker** at current location (geolocation with graceful fallback to a fixed mock location, e.g. central Tel Aviv) — pulsing dot.
   - **Store markers**: custom pin per supermarket with **brand logo** + **total cart price** badge. Cheapest store gets a highlighted/glowing pin ("BEST" tag).
2. **Top bar (floating, glass)** — back button (→ Home), receipt summary chip: "12 items · scanned cart".
3. **Bottom sheet (draggable, glass)** — horizontally scrollable / stacked list of store cards, sorted by price:
   - Brand logo + name
   - Distance from user (e.g. "650 m")
   - **Total cart price** (big, monospace)
   - Savings vs. most expensive (e.g. "Save ₪38")
   - Tapping a card pans/zooms the map to that store's pin (and vice versa: tapping a pin scrolls to its card).

### Behavior

- On mount: try `navigator.geolocation`; on deny/timeout use mock coords.
- Store data = mock: fake stores positioned relative to the user's location so they always appear "nearby".
- Cheapest store pre-selected (card highlighted, pin glowing).

### States

| State | UI |
|---|---|
| Locating | Map skeleton + "Locating you…" |
| Ready | Map + pins + bottom sheet |
| Geolocation denied | Same, using mock location (silent fallback) |

---

## Mock Data

- `src/resources/receipt.json` — the fake OCR result: store name, date, list of items (name, barcode, qty, unit price).
- `src/resources/supermarkets.json` — real Israeli retailers with mock prices: id, brand, logo path, `online` flag, lat/lng **offsets** from the user (physical stores only), cart total, delivery fee.
  - Physical: שופרסל, סופר יודה, קרפור, טיב טעם — shown on the map **and** in the sheet.
  - Online: Wolt Market, רמי לוי אונליין — **no map pin**; shown in a separate highlighted "משלוח עד הבית" row at the bottom.
- `public/static/logos/` — real brand logos (see `SOURCES.md` there for provenance and licensing caveats).

---

## Tech Stack

- **React + Vite + TypeScript** in `ui/`
- **react-router** — 2 routes (`/`, `/map`)
- **Leaflet / react-leaflet** — map with dark tiles
- **CSS**: plain CSS modules or Tailwind (decide at implementation), dark theme tokens (background `#0a0f0d`-ish, accent electric green `#00e58f`, glass cards)
- No backend — everything from `resources/` mocks

## Flow

```
Home (/) ── file selected ──▶ Loading overlay (~2s, fake OCR)
                                   │
                                   ▼
                         Results (/results) — receipt card + ranked list
                                   │  "הצגה על המפה"
                                   ▼
                            Map (/map) — user pin + store pins + price sheet


Home ── ☰ ──▶ Saved (/saved) ── tap a receipt ──▶ Results (/results)
```

Shared location + store logic lives in `src/lib/useStores.ts`, so both `/results` and `/map`
rank and price identically.
