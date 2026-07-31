import type { CartLine, NearbyStore } from './api'
import { chainLogo } from './chains'
import type { ReceiptItem, ReceiptOrigin } from './types'

/**
 * A basket the cart screen can render line by line.
 *
 * There are exactly two kinds, and the distinction is the whole point of the
 * screen. The **origin** basket is what the shopper actually paid, taken from
 * their own receipt. Every other basket is what one store quotes for the same
 * products, taken from the price database. Nothing here is estimated: a line a
 * store has no price for is shown as unavailable rather than filled in, because
 * a guessed price is indistinguishable from a real one once it is on screen.
 */
export interface PricedStore {
  id: string
  brand: string
  branch: string
  logo: string | null
  online: boolean
  isOrigin: boolean
  cartTotal: number
  /** Priced lines, in receipt order. */
  lines: PricedLine[]
  /** Set on non-origin stores: how many lines it could not price. */
  unavailableCount: number
}

export interface PricedLine {
  name: string
  barcode: string
  qty: number
  /** null when this store has no current price for the product. */
  unitPrice: number | null
  lineTotal: number | null
  available: boolean
  /** The receipt's own per-unit price, for the side-by-side comparison. */
  paidUnitPrice: number | null
  /** What the shopper paid for this line in full, for the header's arithmetic. */
  paidLineTotal: number | null
  /** Set when this line was swapped for a cheaper equivalent. */
  swappedFrom?: string
}

/** The shopper's own receipt as a basket — the baseline everything compares to. */
export function originStore(items: ReceiptItem[], origin: ReceiptOrigin): PricedStore {
  return {
    id: 'origin',
    brand: origin.chain,
    branch: origin.branch,
    logo: origin.logo,
    online: false,
    isOrigin: true,
    cartTotal: items.reduce((sum, i) => sum + i.qty * i.unitPrice, 0),
    unavailableCount: 0,
    lines: items.map((i) => ({
      name: i.name,
      barcode: i.barcode,
      qty: i.qty,
      unitPrice: i.unitPrice,
      lineTotal: i.qty * i.unitPrice,
      available: true,
      paidUnitPrice: i.unitPrice,
      paidLineTotal: i.qty * i.unitPrice,
    })),
  }
}

/**
 * One store's quote for the cart, from the backend.
 *
 * Reads the optimal (post-swap) basket, since that is the total the list screen
 * ranks on, and labels any line the swap engine replaced so the shopper can see
 * that it is not literally what they bought.
 */
/**
 * Join a cart line to the receipt line it answers.
 *
 * On the position the server stamps on every line, never on list index: a store
 * cart holds only the lines that could be matched, so one unmatched product
 * shifts every line after it and compares the shopper's chocolate against what
 * they paid for dish soap.
 *
 * `paid` is in receipt order, so a receipt saved before the server carried
 * `position` still lines up on the 1-based printed position.
 */
function paidLineFor(
  paid: ReceiptItem[],
  position: number | undefined,
  index: number,
): ReceiptItem | undefined {
  return position === undefined ? paid[index] : paid[position - 1]
}

/**
 * What the shopper paid for just the lines this store can price.
 *
 * The baseline any saving has to be measured against. Comparing a store's total
 * to the whole receipt books every product it does not stock as a saving — the
 * more it is missing, the cheaper it looks, which is exactly backwards.
 */
export function paidForPricedLines(store: NearbyStore, paid: ReceiptItem[]): number {
  return store.optimalCart.items.reduce((sum, entry, index) => {
    if (!entry.available) return sum
    const source = paidLineFor(paid, entry.position, index)
    return source ? sum + source.unitPrice * source.qty : sum
  }, 0)
}

export function pricedStore(store: NearbyStore, paid: ReceiptItem[]): PricedStore {
  const swappedFrom = new Map(store.optimalCart.swaps.map((s) => [s.to.barcode, s.from.name]))

  const paidAt = (position: number | undefined, index: number): ReceiptItem | undefined =>
    paidLineFor(paid, position, index)

  const line = (entry: CartLine, index: number): PricedLine => {
    const source = paidAt(entry.position, index)
    return {
      name: entry.name,
      barcode: entry.barcode,
      qty: entry.qty,
      unitPrice: entry.unitPrice,
      lineTotal: entry.lineTotal,
      available: entry.available,
      paidUnitPrice: source?.unitPrice ?? null,
      paidLineTotal: source ? source.unitPrice * source.qty : null,
      swappedFrom: swappedFrom.get(entry.barcode),
    }
  }

  return {
    id: `${store.chain}:${store.storeId}`,
    brand: store.chain,
    branch: store.branch,
    logo: chainLogo(store.chain),
    online: store.online,
    isOrigin: false,
    cartTotal: store.optimalCart.total,
    unavailableCount: store.optimalCart.unavailableCount,
    lines: store.optimalCart.items.map(line),
  }
}
