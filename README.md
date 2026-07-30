# sali

Analyze and compare supermarket prices. Compare shopping carts across stores and get recommendations for cheaper alternatives.

## Data source

Prices are published under Israel's price transparency regulations:
https://www.gov.il/he/pages/cpfta_prices_regulations

## Setup

```bash
uv sync
cp .env.example .env
```

## Run

```bash
uv run sali
```

## Digital Receipt API

Run the local FastAPI service in a separate terminal:

```bash
uv run sali-api
```

It exposes `POST /api/receipts/extract` with a JSON body such as
`{"url":"https://merchant.example/receipt/public-token"}`, plus
`POST /api/receipts/extract-image` with one `multipart/form-data` field named
`image`, which returns a reconciled Receipt Document only when all line items
can be read. `POST /api/receipts/extract-image-total` accepts the same upload
but returns only a verified final total when a complete cart is unreadable. The
image endpoints accept JPEG, PNG, and WEBP receipt images up to 10 MiB; they do
not support PDFs, HEIC, GIF, or multi-image receipts. The service does not
store receipt URLs, images, or extraction results. By default, browser requests
are allowed only from `http://localhost:5173`; set
`SALI_CORS_ORIGINS` to a comma-separated allowlist when using another trusted
UI origin.

For example:

```bash
curl -X POST http://localhost:8000/api/receipts/extract-image-total \
  -F 'image=@/path/to/receipt.jpg;type=image/jpeg'
```

## UI

Mobile-first React app in `ui/` (upload a receipt → compare the cart across nearby stores).
Selecting or dropping a supported receipt image calls the local total-only API
and shows the extracted receipt total. Cart comparison still uses the sample
cart in `ui/src/resources/`.

```bash
npm install --prefix ui
```

```bash
npm run dev --prefix ui
```

Then open http://localhost:5173.

For local receipt extraction, run the API at `http://localhost:8000`.

### Auth & saved receipts (Supabase)

The UI runs without Supabase — sign-in is faked and receipts stay in `localStorage`.
To enable real Google sign-in and cloud-persisted receipts:

1. Copy `ui/.env.example` to `ui/.env.local` and fill in `VITE_SUPABASE_URL` and
   `VITE_SUPABASE_ANON_KEY` (Supabase → Settings → API). Only publishable keys belong
   here — anything `VITE_*` ships inside the browser bundle.
2. Run `docs/supabase-setup.sql` in the Supabase SQL editor to create the `receipts`
   table and its row-level-security policy.
3. Supabase → Authentication → Providers → enable **Google**, using a Google Cloud
   OAuth client whose redirect URI is the one Supabase shows on that page.
4. Supabase → Authentication → URL Configuration → add `http://localhost:5173` to the
   allowed redirect URLs for local development.
