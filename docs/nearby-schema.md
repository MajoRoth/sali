# Nearby-supermarkets calculation — I/O contract

Contract between the app and the algorithm service: given the user's current cart, their
location, and a radius, return nearby supermarkets each with two priced carts — the **same
cart** (like-for-like) and an **optimal cart** (after swapping to cheaper similar products).

Types below are TypeScript for precision; the wire format is JSON. Field names match the
frontend (`ui/src/lib/types.ts`) so the output can feed the UI with minimal mapping.

Money is a number in **`currency`** minor-unit-inclusive decimal (e.g. `12.90`). All prices are
assumed **VAT-inclusive shelf prices** — confirm (see Open decisions). Distances in **meters**,
coordinates **WGS84** `lat`/`lng`.

---

## Input

```ts
interface NearbyRequest {
  cart: CartItem[];
  location: GeoPoint;       // user's current position
  radiusM: number;          // search radius in meters

  // Strongly recommended (see gaps #5, #7, #9):
  currency?: 'ILS';         // default ILS
  pricesAsOf?: string;      // ISO date — which day's published prices to use; default: latest
  includeOnline?: boolean;  // include delivery-only stores that have no location; default false
  limit?: number;           // max stores to return
}

interface CartItem {
  barcode: string;          // GTIN — the join key for matching across stores (see gap #1)
  name: string;
  qty: number;              // amount, interpreted with `unit`
  unit: 'unit' | 'kg' | 'g' | 'l' | 'ml';  // (see gap #2)
  unitPrice: number;        // price PAID at the origin store, per `unit`
  // Optional aids for matching / fallback:
  plu?: string;             // for loose produce/deli with no barcode (see gap #1)
  brand?: string;
  size?: string;            // e.g. "1L", "500g" — the package size
}

interface GeoPoint { lat: number; lng: number; }
```

---

## Output

```ts
interface NearbyResponse {
  computedAt: string;       // ISO timestamp of this calculation
  pricesAsOf: string;       // date of the price data actually used
  currency: 'ILS';
  origin?: NearbyStore;     // where the receipt was bought, at the price paid (see gap #10)
  stores: NearbyStore[];    // ranked; state the sort key (see gap #7)
}

interface NearbyStore {
  storeId: string;
  chain: string;            // "שופרסל"
  branch: string;           // "רמת גן"
  logo?: string;
  online: boolean;
  location: GeoPoint | null;   // null for online-only stores
  distanceM: number | null;    // null for online-only stores
  deliveryFee: number;         // 0 if none/pickup; excluded from cart totals

  sameCart: Cart;              // the exact same products
  optimalCart: OptimalCart;    // after cheaper-similar swaps
}

interface Cart {
  items: CartLine[];
  total: number;               // sum of AVAILABLE line totals only (see gap #3)
  unavailableCount: number;    // input items this store doesn't carry
  coverage: number;            // 0..1 = availableItems / inputItems
}

interface CartLine {
  barcode: string;
  name: string;                // this store's product name
  qty: number;
  unit: 'unit' | 'kg' | 'g' | 'l' | 'ml';
  unitPrice: number | null;    // null if unavailable
  lineTotal: number | null;    // unitPrice * qty, or null if unavailable
  available: boolean;
  matchConfidence?: number;    // 0..1 when matched by name/fuzzy rather than exact barcode
}

interface OptimalCart extends Cart {
  swaps: Swap[];
  savingsVsSameCart: number;   // sameCart.total - optimalCart.total
}

interface Swap {
  // The original line being replaced, and its replacement:
  from: { barcode: string; name: string; unitPrice: number };
  to:   { barcode: string; name: string; unitPrice: number };
  qty: number;
  unit: 'unit' | 'kg' | 'g' | 'l' | 'ml';
  lineSavings: number;         // (from.unitPrice - to.unitPrice) * qty, normalized per unit
  reason: 'cheaper_similar' | 'store_brand' | 'promotion' | 'larger_pack_unit_price';
  category?: string;           // the equivalence class the swap stayed within
  similarity?: number;         // 0..1 how close the substitute is
}
```

### Totals — be explicit
- `total` **excludes** `deliveryFee` (kept separate so the UI can add it per user choice).
- `total` sums **only available** lines. A store missing items has lower `total` **and** lower
  `coverage` — the UI must compare on coverage, not price alone, or cheap-because-incomplete
  stores win falsely.
- State whether prices include VAT and bottle deposit (**pikadon**). See Open decisions.

---

## Example (one store, abbreviated)

```json
{
  "computedAt": "2026-07-30T18:04:00Z",
  "pricesAsOf": "2026-07-30",
  "currency": "ILS",
  "stores": [
    {
      "storeId": "shufersal-7290027600007-042",
      "chain": "שופרסל",
      "branch": "דיזנגוף סנטר",
      "logo": "/static/logos/shufersal.svg",
      "online": false,
      "location": { "lat": 32.0755, "lng": 34.7748 },
      "distanceM": 470,
      "deliveryFee": 0,
      "sameCart": {
        "total": 171.40,
        "unavailableCount": 1,
        "coverage": 0.92,
        "items": [
          { "barcode": "7290000042563", "name": "חלב 3% 1ל", "qty": 2, "unit": "unit",
            "unitPrice": 6.40, "lineTotal": 12.80, "available": true },
          { "barcode": "7290003333333", "name": "חזה עוף טרי", "qty": 1, "unit": "kg",
            "unitPrice": null, "lineTotal": null, "available": false }
        ]
      },
      "optimalCart": {
        "total": 158.90,
        "unavailableCount": 1,
        "coverage": 0.92,
        "savingsVsSameCart": 12.50,
        "items": [ "…same shape as sameCart…" ],
        "swaps": [
          {
            "from": { "barcode": "7290000042563", "name": "חלב תנובה 3% 1ל", "unitPrice": 6.40 },
            "to":   { "barcode": "7290111111116", "name": "חלב מותג הבית 3% 1ל", "unitPrice": 4.90 },
            "qty": 2, "unit": "unit", "lineSavings": 3.00,
            "reason": "store_brand", "category": "milk_3pct_1l", "similarity": 0.95
          }
        ]
      }
    }
  ]
}
```

---

## What the sketch was missing (review)

Ordered by how badly each will bite:

1. **A join key on cart items.** `name + price` can't reliably match a product across chains.
   Send the **barcode (GTIN)** per item — it's the primary key the algorithm matches on. Add a
   **`plu`/department fallback** for loose produce and deli that have no barcode.
2. **Quantity + unit.** "2 milks" vs "1.4 kg tomatoes" — totals are wrong without `qty` and a
   `unit`. Loose-by-weight vs packaged must be unambiguous.
3. **Availability / missing items — the biggest gap.** A store may not stock every item, so the
   "same cart" is often *partial*. Every line needs `available`, and the total needs a defined
   rule (we chose: sum available only + report `coverage`). Without this, a store that's cheap
   only because it's missing the expensive items looks like the winner.
4. **What makes a valid swap.** Define the equivalence constraint (same normalized unit/size,
   same `category`) and the criterion (distance from category average / store brand / active
   promotion). Some items will have **no** swap and stay as-is. Each swap links to the line it
   replaces (`from`/`to` + `qty`).
5. **Price semantics + date.** Currency; VAT-inclusive?; bottle **deposit (pikadon)**; regular
   vs **promotional** price. And **which day's prices** — the regulation feeds are per-day and go
   stale, so echo back `pricesAsOf`.
6. **Store metadata.** `storeId`, `chain`, `branch`, `location`, `distanceM`, `deliveryFee`,
   `online`, `logo`. (Nice-to-have: address, opening hours, delivery min-order.)
7. **Sort key + limit.** Say how `stores` is ordered (by `optimalCart.total`? by distance?) and
   cap results with `limit`.
8. **Units & datum on the input.** `radiusM` in meters, `location` as WGS84 lat/lng.
9. **Online stores.** They have no location, so `location`/`distanceM` are null and they can't be
   found by radius. Decide: include them here behind `includeOnline`, or a separate call.
10. **The origin store + paid total.** To show "you saved ₪X vs what you paid", the response
    should carry the origin store and the actually-paid total (`origin`), and/or the UI passes
    the input cart's total through.
11. **Match confidence & partial failures.** Surface `matchConfidence` for fuzzy matches, and
    define behavior for empty results / a store carrying none of the cart.

---

## Open decisions (please confirm with the algo team)

- Prices are VAT-inclusive shelf prices? Deposit (pikadon) included in line price or separate?
- Optimal cart: use **regular** prices only, or fold in active **promotions**? (Affects whether
  `reason: "promotion"` swaps exist.)
- Missing-item rule: exclude & report coverage (current spec) vs. substitute a nearest product.
- Swap equivalence: how strict on brand/size? Is "larger pack, lower unit price" an allowed swap?
- `stores` sort key and default `limit`.
