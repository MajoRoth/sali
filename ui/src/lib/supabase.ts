import { createClient, type SupabaseClient } from '@supabase/supabase-js'

const url = import.meta.env.VITE_SUPABASE_URL
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

/**
 * Null until the project is configured. Everything downstream falls back to a
 * local-only mode so the UI stays usable before credentials land.
 */
export const supabase: SupabaseClient | null =
  url && anonKey ? createClient(url, anonKey) : null

export const isSupabaseConfigured = supabase !== null

if (!isSupabaseConfigured) {
  console.warn(
    '[sali] Supabase not configured — running in local mode. ' +
      'Sign-in is faked and receipts stay in this browser. ' +
      'Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in ui/.env.local.',
  )
}
