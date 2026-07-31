import { useEffect, useState } from 'react'
import type { ReceiptDocument } from './api'
import { chainLogo } from './chains'
import type { ReceiptItem, ReceiptOrigin } from './types'
import { supabase } from './supabase'

/* ------------------------------------------------------------------ */
/* Receipt Document -> what the screens render                         */
/* ------------------------------------------------------------------ */

/**
 * The per-unit price of a line.
 *
 * `unit_price` is what the receipt printed, and `final_total` is what was
 * actually paid after that line's own discounts. When a line carries a
 * discount the two disagree, and the screens compare against money that left
 * the shopper's pocket — so the paid total, spread over the quantity, wins.
 */
function paidUnitPrice(item: ReceiptDocument['receipt']['items'][number]): number {
  const qty = Number(item.quantity ?? '1')
  const finalTotal = Number(item.final_total)
  if (Number.isFinite(finalTotal) && Number.isFinite(qty) && qty > 0) return finalTotal / qty
  const printed = Number(item.unit_price ?? '0')
  return Number.isFinite(printed) ? printed : 0
}

export function itemsFromDocument(document: ReceiptDocument): ReceiptItem[] {
  return document.receipt.items.map((item) => {
    const qty = Number(item.quantity ?? '1')
    return {
      name: item.name,
      barcode: item.code ?? '',
      qty: Number.isFinite(qty) && qty > 0 ? qty : 1,
      unitPrice: paidUnitPrice(item),
    }
  })
}

/** The shop named on the receipt. Falls back to neutral copy, never to a guess. */
export function originFromDocument(document: ReceiptDocument | null): ReceiptOrigin {
  const merchant = document?.receipt.merchant
  const chain = merchant?.name ?? 'הקבלה שלכם'
  return {
    chain,
    branch: merchant?.branch_name ?? '',
    logo: merchant?.name ? chainLogo(merchant.name) : null,
  }
}

/** The receipt's own printed total — authoritative over any sum we compute. */
export function documentTotal(document: ReceiptDocument | null): number | null {
  if (!document) return null
  const total = Number(document.receipt.totals.total)
  return Number.isFinite(total) ? total : null
}

const SAVED_KEY = 'sali.savedReceipts'
const ACTIVE_KEY = 'sali.activeReceipt'

export interface SavedReceipt {
  id: string
  name: string
  /** ISO timestamp of when it was saved. */
  savedAt: string
  items: ReceiptItem[]
  /** The full extraction, kept so reopening can re-price at today's location. */
  document: ReceiptDocument | null
}

export function totalOf(items: ReceiptItem[]): number {
  return items.reduce((sum, i) => sum + i.qty * i.unitPrice, 0)
}

/**
 * How many products are on the receipt.
 *
 * Counts lines, not quantities. Summing `qty` looks right until the cart holds
 * anything weighed: 0.565 kg of tomatoes plus 1.334 kg of peppers turns "how
 * many products" into "44.899 מוצרים". A line is one product bought, whatever
 * it weighed.
 */
export function countOf(items: ReceiptItem[]): number {
  return items.length
}

/* ------------------------------------------------------------------ */
/* Local (browser) storage — used until Supabase is configured.        */
/* ------------------------------------------------------------------ */

function readLocal(): SavedReceipt[] {
  try {
    const raw = localStorage.getItem(SAVED_KEY)
    if (!raw) return []
    // `document` post-dates the first saved receipts, so it may be absent.
    return (JSON.parse(raw) as SavedReceipt[]).map((r) => ({ ...r, document: r.document ?? null }))
  } catch {
    return []
  }
}

function writeLocal(list: SavedReceipt[]) {
  localStorage.setItem(SAVED_KEY, JSON.stringify(list))
}

/* ------------------------------------------------------------------ */
/* Repository — same async shape for both backends.                    */
/* ------------------------------------------------------------------ */

interface ReceiptRow {
  id: string
  name: string
  items: ReceiptItem[]
  document?: ReceiptDocument | null
  created_at: string
}

const fromRow = (r: ReceiptRow): SavedReceipt => ({
  id: r.id,
  name: r.name,
  savedAt: r.created_at,
  items: r.items,
  document: r.document ?? null,
})

const COLUMNS = 'id, name, items, document, created_at'
const COLUMNS_LEGACY = 'id, name, items, created_at'

/**
 * The two ways "there is no `document` column" comes back.
 *
 * A *select* naming a missing column reaches Postgres, which answers `42703`.
 * An *insert* whose body names one does not: PostgREST rejects it against its
 * own schema cache first and answers `PGRST204`. Matching only the Postgres
 * code meant reading a receipt degraded gracefully while saving one failed
 * outright — the same missing column, reported by a different layer.
 */
const UNDEFINED_COLUMN = '42703'
const UNKNOWN_COLUMN_IN_BODY = 'PGRST204'

function isMissingDocumentColumn(error: { code?: string; message?: string } | null): boolean {
  if (error?.code === UNDEFINED_COLUMN) return true
  // PGRST204 is "some column in the body is unknown" — only ours should retry.
  return error?.code === UNKNOWN_COLUMN_IN_BODY && (error.message ?? '').includes("'document'")
}

interface Queried {
  data: unknown
  error: { code?: string; message?: string } | null
}

/**
 * Run a query that wants the `document` column, retrying without it.
 *
 * `document` was added after the first receipts were saved, so a project that
 * ran the original `docs/supabase-setup.sql` has no such column. Rather than
 * making everyone migrate before the app works again, the narrower query is
 * tried on exactly the error that means "that column isn't there".
 */
async function withDocumentColumn(
  full: () => PromiseLike<Queried>,
  legacy: () => PromiseLike<Queried>,
): Promise<unknown> {
  const first = await full()
  if (!isMissingDocumentColumn(first.error)) {
    if (first.error) throw first.error
    return first.data
  }
  console.warn('[sali] receipts.document column missing — run docs/supabase-setup.sql to keep full receipts')
  const second = await legacy()
  if (second.error) throw second.error
  return second.data
}

/** Newest first. */
export async function listReceipts(userId: string | null): Promise<SavedReceipt[]> {
  if (supabase && userId) {
    const client = supabase
    const data = await withDocumentColumn(
      () => client.from('receipts').select(COLUMNS).order('created_at', { ascending: false }),
      () => client.from('receipts').select(COLUMNS_LEGACY).order('created_at', { ascending: false }),
    )
    return (data as ReceiptRow[]).map(fromRow)
  }
  return readLocal().sort((a, b) => b.savedAt.localeCompare(a.savedAt))
}

export async function getReceipt(userId: string | null, id: string): Promise<SavedReceipt | null> {
  if (supabase && userId) {
    const client = supabase
    const data = await withDocumentColumn(
      () => client.from('receipts').select(COLUMNS).eq('id', id).maybeSingle(),
      () => client.from('receipts').select(COLUMNS_LEGACY).eq('id', id).maybeSingle(),
    )
    return data ? fromRow(data as ReceiptRow) : null
  }
  return readLocal().find((r) => r.id === id) ?? null
}

export async function createReceipt(
  userId: string | null,
  name: string,
  items: ReceiptItem[],
  document: ReceiptDocument | null = null,
): Promise<SavedReceipt> {
  if (supabase && userId) {
    const client = supabase
    const data = await withDocumentColumn(
      () =>
        client
          .from('receipts')
          .insert({ user_id: userId, name, items, document })
          .select(COLUMNS)
          .single(),
      () =>
        client
          .from('receipts')
          .insert({ user_id: userId, name, items })
          .select(COLUMNS_LEGACY)
          .single(),
    )
    return fromRow(data as ReceiptRow)
  }
  const record: SavedReceipt = {
    id: crypto.randomUUID(),
    name,
    savedAt: new Date().toISOString(),
    items,
    document,
  }
  writeLocal([record, ...readLocal()])
  return record
}

export async function renameReceipt(
  userId: string | null,
  id: string,
  name: string,
): Promise<void> {
  if (supabase && userId) {
    const { error } = await supabase.from('receipts').update({ name }).eq('id', id)
    if (error) throw error
    return
  }
  writeLocal(readLocal().map((r) => (r.id === id ? { ...r, name } : r)))
}

export async function deleteReceipt(userId: string | null, id: string): Promise<void> {
  if (supabase && userId) {
    const { error } = await supabase.from('receipts').delete().eq('id', id)
    if (error) throw error
  } else {
    writeLocal(readLocal().filter((r) => r.id !== id))
  }
  if (localStorage.getItem(ACTIVE_KEY) === id) setActiveReceipt(null)
}

/* ------------------------------------------------------------------ */
/* Active receipt — which one the comparison screens are showing.      */
/* ------------------------------------------------------------------ */

/** `null` means "the receipt just scanned". */
export function setActiveReceipt(id: string | null) {
  if (id) localStorage.setItem(ACTIVE_KEY, id)
  else localStorage.removeItem(ACTIVE_KEY)
}

/** Stashed by Home so /results can show it before it has been saved. */
const PENDING_KEY = 'sali.pendingScan'

export interface PendingScan {
  items: ReceiptItem[]
  document: ReceiptDocument | null
}

export function setPendingScan(scan: PendingScan | null) {
  if (scan) localStorage.setItem(PENDING_KEY, JSON.stringify(scan))
  else localStorage.removeItem(PENDING_KEY)
}

function readPendingScan(): PendingScan | null {
  try {
    const raw = localStorage.getItem(PENDING_KEY)
    return raw ? (JSON.parse(raw) as PendingScan) : null
  } catch {
    return null
  }
}

export interface ActiveReceipt {
  /** null while the scan is unsaved. */
  id: string | null
  name: string | null
  items: ReceiptItem[]
  document: ReceiptDocument | null
  loading: boolean
  /** True when there is no scan at all — an empty cart, not a failure. */
  empty: boolean
}

const EMPTY: ActiveReceipt = {
  id: null,
  name: null,
  items: [],
  document: null,
  loading: false,
  empty: true,
}

function fromPending(): ActiveReceipt {
  const pending = readPendingScan()
  if (!pending) return EMPTY
  return {
    id: null,
    name: null,
    items: pending.items,
    document: pending.document,
    loading: false,
    empty: pending.items.length === 0,
  }
}

/**
 * Resolves the receipt the comparison screens should show. If `preloaded` is
 * given (the caller already has the record, e.g. Home passing it via router
 * state), it's used directly with no fetch. Otherwise a saved id is fetched,
 * falling back to the pending scan.
 */
export function useActiveReceipt(
  userId: string | null,
  preloaded?: SavedReceipt | null,
): ActiveReceipt {
  const [state, setState] = useState<ActiveReceipt>(() => {
    if (preloaded) {
      return {
        id: preloaded.id,
        name: preloaded.name,
        items: preloaded.items,
        document: preloaded.document,
        loading: false,
        empty: preloaded.items.length === 0,
      }
    }
    const id = localStorage.getItem(ACTIVE_KEY)
    if (!id) return fromPending()
    return { ...EMPTY, id, loading: true, empty: false }
  })

  const activeId = state.id
  const needFetch = state.loading && !preloaded

  useEffect(() => {
    if (!activeId || !needFetch) return
    let cancelled = false
    getReceipt(userId, activeId)
      .then((saved) => {
        if (cancelled) return
        setState(
          saved
            ? {
                id: saved.id,
                name: saved.name,
                items: saved.items,
                document: saved.document,
                loading: false,
                empty: saved.items.length === 0,
              }
            : fromPending(),
        )
      })
      // Never leave the screen stuck loading if the fetch fails.
      .catch((err) => {
        console.error('[sali] failed to load receipt:', err)
        if (!cancelled) setState((s) => ({ ...s, loading: false }))
      })
    return () => {
      cancelled = true
    }
  }, [activeId, userId, needFetch])

  return state
}

export function formatSavedDate(iso: string): string {
  return new Date(iso).toLocaleDateString('he-IL', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}
