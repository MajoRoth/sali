import supermarketsJson from '../resources/supermarkets.json'
import originJson from '../resources/origin.json'
import type { ReceiptItem } from './types'

/**
 * A store for the cart view. Mock: we only have store-level totals, so per-item
 * prices are generated deterministically (see `itemPrices`). The origin store
 * uses the exact receipt prices; the rest are estimates scaled to their total.
 */
export interface PricedStore {
  id: string
  brand: string
  logo: string
  online: boolean
  isOrigin: boolean
  cartTotal: number
}

interface RawStore {
  id: string
  brand: string
  logo: string
  online: boolean
  cartTotal: number
}

/** The origin store (exact receipt prices) plus every comparison store. */
export function cartStores(items: ReceiptItem[]): PricedStore[] {
  const receiptTotal = items.reduce((s, i) => s + i.qty * i.unitPrice, 0)
  const origin: PricedStore = {
    id: 'origin',
    brand: originJson.brand,
    logo: originJson.logo,
    online: false,
    isOrigin: true,
    cartTotal: receiptTotal,
  }
  const alternatives = (supermarketsJson as RawStore[]).map((s) => ({
    id: s.id,
    brand: s.brand,
    logo: s.logo,
    online: s.online,
    isOrigin: false,
    cartTotal: s.cartTotal,
  }))
  return [origin, ...alternatives]
}

/** Stable per-(store, item) multiplier in ~0.82–1.28. */
function factor(seed: string): number {
  let h = 0
  for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) >>> 0
  return 0.82 + ((h % 1000) / 1000) * 0.46
}

/**
 * Per-unit price of each receipt item at a store. The origin returns exact
 * receipt prices; others are generated and scaled so the line totals sum to
 * that store's cart total (keeping the cart view consistent with the list).
 */
export function itemPrices(store: PricedStore, items: ReceiptItem[]): number[] {
  if (store.isOrigin) return items.map((i) => i.unitPrice)
  const raw = items.map((i) => i.unitPrice * factor(`${store.id}|${i.barcode}`))
  const rawTotal = raw.reduce((s, p, idx) => s + p * items[idx].qty, 0)
  const scale = rawTotal > 0 ? store.cartTotal / rawTotal : 1
  return raw.map((p) => Math.round(p * scale * 100) / 100)
}

export interface ItemRange {
  min: number
  max: number
}

/** Cheapest/most-expensive per-unit price of each item across all stores. */
export function itemRanges(items: ReceiptItem[]): ItemRange[] {
  const perStore = cartStores(items).map((s) => itemPrices(s, items))
  return items.map((_, idx) => {
    const col = perStore.map((prices) => prices[idx])
    return { min: Math.min(...col), max: Math.max(...col) }
  })
}
