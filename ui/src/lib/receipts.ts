import { useEffect, useState } from 'react'
import receiptJson from '../resources/receipt.json'
import type { ReceiptItem } from './types'
import { supabase } from './supabase'

const SAVED_KEY = 'sali.savedReceipts'
const ACTIVE_KEY = 'sali.activeReceipt'

export interface SavedReceipt {
  id: string
  name: string
  /** ISO timestamp of when it was saved. */
  savedAt: string
  items: ReceiptItem[]
}

/** The mock OCR result — what every fresh scan produces for now. */
export const scannedItems = receiptJson.items as ReceiptItem[]

export function totalOf(items: ReceiptItem[]): number {
  return items.reduce((sum, i) => sum + i.qty * i.unitPrice, 0)
}

export function countOf(items: ReceiptItem[]): number {
  return items.reduce((n, i) => n + i.qty, 0)
}

/* ------------------------------------------------------------------ */
/* Local (browser) storage — used until Supabase is configured.        */
/* ------------------------------------------------------------------ */

function readLocal(): SavedReceipt[] {
  try {
    const raw = localStorage.getItem(SAVED_KEY)
    return raw ? (JSON.parse(raw) as SavedReceipt[]) : []
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
  created_at: string
}

const fromRow = (r: ReceiptRow): SavedReceipt => ({
  id: r.id,
  name: r.name,
  savedAt: r.created_at,
  items: r.items,
})

/** Newest first. */
export async function listReceipts(userId: string | null): Promise<SavedReceipt[]> {
  if (supabase && userId) {
    const { data, error } = await supabase
      .from('receipts')
      .select('id, name, items, created_at')
      .order('created_at', { ascending: false })
    if (error) throw error
    return (data as ReceiptRow[]).map(fromRow)
  }
  return readLocal().sort((a, b) => b.savedAt.localeCompare(a.savedAt))
}

export async function getReceipt(userId: string | null, id: string): Promise<SavedReceipt | null> {
  if (supabase && userId) {
    const { data, error } = await supabase
      .from('receipts')
      .select('id, name, items, created_at')
      .eq('id', id)
      .maybeSingle()
    if (error) throw error
    return data ? fromRow(data as ReceiptRow) : null
  }
  return readLocal().find((r) => r.id === id) ?? null
}

export async function createReceipt(
  userId: string | null,
  name: string,
  items: ReceiptItem[],
): Promise<SavedReceipt> {
  if (supabase && userId) {
    const { data, error } = await supabase
      .from('receipts')
      .insert({ user_id: userId, name, items })
      .select('id, name, items, created_at')
      .single()
    if (error) throw error
    return fromRow(data as ReceiptRow)
  }
  const record: SavedReceipt = {
    id: crypto.randomUUID(),
    name,
    savedAt: new Date().toISOString(),
    items,
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

export function setPendingScan(items: ReceiptItem[] | null) {
  if (items) localStorage.setItem(PENDING_KEY, JSON.stringify(items))
  else localStorage.removeItem(PENDING_KEY)
}

function readPendingScan(): ReceiptItem[] | null {
  try {
    const raw = localStorage.getItem(PENDING_KEY)
    return raw ? (JSON.parse(raw) as ReceiptItem[]) : null
  } catch {
    return null
  }
}

export interface ActiveReceipt {
  /** null while the scan is unsaved. */
  id: string | null
  name: string | null
  items: ReceiptItem[]
  loading: boolean
}

/**
 * Resolves the receipt the comparison screens should show: a saved one if an
 * id is active, otherwise the pending scan (or the mock scan as a fallback).
 */
export function useActiveReceipt(userId: string | null): ActiveReceipt {
  const [state, setState] = useState<ActiveReceipt>(() => {
    const id = localStorage.getItem(ACTIVE_KEY)
    return {
      id,
      name: null,
      items: readPendingScan() ?? scannedItems,
      loading: id !== null,
    }
  })

  const activeId = state.id

  useEffect(() => {
    if (!activeId) return
    let cancelled = false
    void getReceipt(userId, activeId).then((saved) => {
      if (cancelled) return
      setState(
        saved
          ? { id: saved.id, name: saved.name, items: saved.items, loading: false }
          : { id: null, name: null, items: readPendingScan() ?? scannedItems, loading: false },
      )
    })
    return () => {
      cancelled = true
    }
  }, [activeId, userId])

  return state
}

export function formatSavedDate(iso: string): string {
  return new Date(iso).toLocaleDateString('he-IL', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}
