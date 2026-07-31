/**
 * The sali backend, as the screens use it.
 *
 * Two families, and the split matters. **Extraction** turns a link or a photo
 * into a Receipt Document — the merchant's own words, reconciled against the
 * receipt's own arithmetic. **Nearby** takes that document plus where the
 * shopper is standing and answers what the cart would cost around them.
 *
 * They are separate calls on purpose: extraction is slow and happens once,
 * while pricing depends on a location the user may not have granted yet and is
 * re-run whenever they move or reopen a saved receipt.
 *
 * Nearby speaks camelCase (see `docs/nearby-schema.md`, whose field names match
 * `./types.ts`); extraction speaks snake_case. That is the server's split, not
 * ours — it is documented in `src/sali/nearby/models.py`.
 */

/**
 * `127.0.0.1`, not `localhost`, and that is not a style choice.
 *
 * The dev server binds IPv4 loopback only, while `localhost` resolves to `::1`
 * first on macOS — so every call spent a refused IPv6 connection before falling
 * back, and anything stricter than a browser about that fallback just failed.
 */
const BASE_URL = (import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000').replace(/\/$/, '')

/* ------------------------------------------------------------------ */
/* Receipt Document — the extraction contract (snake_case).            */
/* ------------------------------------------------------------------ */

export interface ReceiptAdjustment {
  description: string | null
  amount: string
}

export interface ReceiptDocumentItem {
  position: number
  code: string | null
  name: string
  categories: string[]
  quantity: string | null
  unit: string | null
  unit_price: string | null
  gross_total: string | null
  adjustments: ReceiptAdjustment[]
  final_total: string
}

export interface ReceiptDocument {
  schema_version: string
  receipt: {
    merchant: { name: string | null; branch_name: string | null; branch_number: string | null }
    transaction: {
      receipt_id: string | null
      purchased_at: string | null
      transaction_number: string | null
      type: string | null
      currency: string | null
    }
    totals: { subtotal: string | null; discounts: string | null; total: string }
    items: ReceiptDocumentItem[]
  }
  warnings: string[]
}

/* ------------------------------------------------------------------ */
/* Nearby — the pricing contract (camelCase, docs/nearby-schema.md).   */
/* ------------------------------------------------------------------ */

export type MeasureUnit = 'unit' | 'kg' | 'g' | 'l' | 'ml'

export interface GeoPoint {
  lat: number
  lng: number
}

export interface CartLine {
  /**
   * The receipt line this answers, as printed on it — the join key back to the
   * cart. Optional only because a receipt saved before the server emitted it
   * has to keep opening; new responses always carry it.
   */
  position?: number
  barcode: string
  name: string
  qty: number
  unit: MeasureUnit
  unitPrice: number | null
  lineTotal: number | null
  available: boolean
  matchConfidence?: number | null
}

export interface Cart {
  items: CartLine[]
  total: number
  unavailableCount: number
  coverage: number
}

export interface Swap {
  from: { barcode: string; name: string; unitPrice: number }
  to: { barcode: string; name: string; unitPrice: number }
  qty: number
  unit: MeasureUnit
  lineSavings: number
  reason: string
  category?: string | null
  similarity?: number | null
}

export interface OptimalCart extends Cart {
  swaps: Swap[]
  savingsVsSameCart: number
}

export interface NearbyStore {
  storeId: string
  chain: string
  branch: string
  online: boolean
  location: GeoPoint | null
  distanceM: number | null
  deliveryFee: number
  city: string | null
  address: string | null
  chainLevelEstimate: boolean
  /**
   * These totals are simulated, not read from the price database — the branch
   * is real, the money is not. Must be labelled wherever it is shown.
   */
  simulated?: boolean
  /**
   * `location` is the centre of the branch's city, not the branch — no
   * coordinates are published for it. `distanceM` is null when this is set,
   * because the city is known and the walk is not.
   */
  approximateLocation?: boolean
  sameCart: Cart
  optimalCart: OptimalCart
}

export interface NearbyResponse {
  schemaVersion: string
  computedAt: string
  currency: string
  origin: NearbyStore | null
  stores: NearbyStore[]
  unmatched: { position: number; name: string; code: string | null; paid: number; reason: string }[]
  warnings: string[]
  /** Real branches inside the radius, whether or not any of them could be priced. */
  storesInRadius: number
}

export interface StoreSummary {
  store_id: string
  chain_id: string
  chain: string
  branch: string
  city: string | null
  address: string | null
  lat: number
  lng: number
  distance_m: number
}

/* ------------------------------------------------------------------ */
/* Errors                                                              */
/* ------------------------------------------------------------------ */

/** A failure the user can be told about, in their language. */
export class ApiError extends Error {
  readonly code: string
  readonly requestId: string | null

  constructor(code: string, message: string, requestId: string | null) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.requestId = requestId
  }
}

/** Hebrew copy per failure code. The server's own message is English. */
const MESSAGES: Record<string, string> = {
  invalid_url: 'הקישור אינו תקין. הדביקו קישור HTTPS ציבורי לקבלה.',
  invalid_image: 'העלו תמונת קבלה אחת בפורמט JPEG, PNG או WEBP, עד 10 מגה־בייט.',
  invalid_request: 'לא נשלחה קבלה לחילוץ.',
  not_receipt: 'לא זוהתה קבלה בקישור או בתמונה.',
  insufficient_evidence: 'זוהתה קבלה, אבל לא היה בה מספיק מידע לחילוץ.',
  blocked: 'לא הצלחנו לגשת לקבלה.',
  unreachable: 'לא הצלחנו להגיע לקבלה.',
  refused: 'לא הצלחנו לעבד את הקבלה.',
  extraction_unavailable: 'שירות חילוץ הקבלות אינו זמין כרגע. נסו שוב בעוד רגע.',
  price_database_unavailable: 'מאגר המחירים אינו זמין כרגע. נסו שוב בעוד רגע.',
  network: 'לא הצלחנו להתחבר לשרת. ודאו שה־API רץ על http://127.0.0.1:8000.',
}

function messageFor(code: string, fallback: string): string {
  return MESSAGES[code] ?? fallback
}

async function readError(response: Response): Promise<ApiError> {
  try {
    const body = (await response.json()) as { error?: { code?: string; message?: string; request_id?: string } }
    const code = body.error?.code ?? `http_${response.status}`
    return new ApiError(code, messageFor(code, body.error?.message ?? 'הבקשה נכשלה.'), body.error?.request_id ?? null)
  } catch {
    return new ApiError(`http_${response.status}`, `הבקשה נכשלה (${response.status}).`, null)
  }
}

async function request<T>(path: string, init: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${BASE_URL}${path}`, init)
  } catch {
    // fetch only rejects on a transport failure, which for this app almost
    // always means the local API is not running.
    throw new ApiError('network', MESSAGES.network, null)
  }
  if (!response.ok) throw await readError(response)
  return (await response.json()) as T
}

const json = (body: unknown): RequestInit => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

/* ------------------------------------------------------------------ */
/* Calls                                                               */
/* ------------------------------------------------------------------ */

/** Read a Digital Receipt from a public link. Slow: it opens a real browser. */
export function extractFromUrl(url: string): Promise<ReceiptDocument> {
  return request<ReceiptDocument>('/api/receipts/extract', json({ url }))
}

/** Read a photographed receipt, including every line item. */
export function extractFromImage(image: File): Promise<ReceiptDocument> {
  const form = new FormData()
  form.append('image', image)
  return request<ReceiptDocument>('/api/receipts/extract-image', { method: 'POST', body: form })
}

/**
 * Read only the total from a photo. The fallback for a picture that proves what
 * was paid but whose line items cannot all be read — a crumpled or cropped
 * receipt, which is most of them.
 */
export function extractImageTotal(image: File): Promise<{ total: string; currency: string | null; warnings: string[] }> {
  const form = new FormData()
  form.append('image', image)
  return request('/api/receipts/extract-image-total', { method: 'POST', body: form })
}

/** Price an extracted receipt against the stores around the shopper. */
export function priceNearby(
  document: ReceiptDocument,
  location: GeoPoint,
  radiusM: number,
): Promise<NearbyResponse> {
  return request<NearbyResponse>(
    '/api/carts/nearby',
    json({ document, location, radiusM, includeOnline: true }),
  )
}

/** Real branches around a point — the map's floor when nothing can be priced. */
export function storesNearby(location: GeoPoint, radiusM: number, limit = 60): Promise<{ stores: StoreSummary[]; total_in_radius: number }> {
  const query = new URLSearchParams({
    lat: String(location.lat),
    lng: String(location.lng),
    radius_m: String(radiusM),
    limit: String(limit),
  })
  return request(`/api/stores/nearby?${query}`, { method: 'GET' })
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError
}

/**
 * Server warnings in the user's language.
 *
 * `warnings` are English diagnostics naming field paths — written for whoever
 * has to debug an extraction, not for a shopper. The few a shopper can act on
 * are restated in Hebrew here; the rest stay in the console, where they belong.
 * Returns null for a warning that should not be surfaced.
 */
export function warningText(warning: string): string | null {
  const unreachable = /^(\d+) of (\d+) receipt lines could not be checked at all/.exec(warning)
  if (unreachable) {
    return `${unreachable[1]} מתוך ${unreachable[2]} שורות בקבלה לא נבדקו כלל — מאגר המחירים לא הגיב. זו תקלה זמנית במאגר, לא קביעה לגבי המוצרים שלכם.`
  }
  const unmatched = /^(\d+) of (\d+) receipt lines could not be matched/.exec(warning)
  if (unmatched) {
    // Simulated totals are built from the receipt, so those lines *are* priced —
    // saying they were excluded would contradict the numbers on screen.
    const simulated = warning.includes('simulated totals')
    return simulated
      ? `${unmatched[1]} מתוך ${unmatched[2]} שורות בקבלה לא נמצאו במאגר המחירים; בהדגמה הן מתומחרות לפי הקבלה עצמה.`
      : `${unmatched[1]} מתוך ${unmatched[2]} שורות בקבלה לא נמצאו במאגר המחירים ואינן נכללות בהשוואה.`
  }
  if (warning.startsWith('demo prices:')) {
    return 'מאגר המחירים אינו זמין כרגע. הסכומים המוצגים הם הדגמה בלבד — הם מחושבים מהקבלה שלכם ואינם מחירים אמיתיים בסניפים.'
  }
  const unplaceable = /^prices were found at (\d+) branches/.exec(warning)
  if (unplaceable) {
    return `נמצאו מחירים ב־${unplaceable[1]} סניפים, אבל אף אחד מהם לא ניתן למיקום ברדיוס שלכם — מאגר המחירים ומאגר המיקומים לא מכסים את אותן רשתות.`
  }
  const silent = /^(\d+) of (\d+) branches within your radius belong to chains that published no price/.exec(warning)
  if (silent) {
    return `${silent[1]} מתוך ${silent[2]} הסניפים בסביבתכם שייכים לרשתות שלא פרסמו מחיר לאף פריט בקבלה — הם מוצגים על המפה אך לא ניתן לדרג אותם.`
  }
  if (warning.startsWith('no store prices')) {
    return 'מאגר המחירים אינו מכיל כרגע מחירים בפועל לאף אחד מהמוצרים בקבלה.'
  }
  if (warning.startsWith('no supermarket branch is within')) {
    return 'לא נמצא סניף ברדיוס החיפוש. נסו להרחיב את הרדיוס.'
  }
  if (warning.startsWith('no store nearby carries every matched product')) {
    return 'אף סניף בסביבה לא מחזיק את כל המוצרים — הדירוג לפי כיסוי העגלה ואז לפי מחיר.'
  }
  if (warning.startsWith('some totals are chain-level estimates')) {
    return 'חלק מהסכומים הם הערכה ברמת הרשת, כי אין פירוט לפי סניף.'
  }
  // `uncertain:` names a receipt line and a catalogue product; useful when
  // debugging a wrong match, meaningless to a shopper.
  return null
}
