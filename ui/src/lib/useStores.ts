import { useEffect, useMemo, useState } from 'react'
import receipt from '../resources/receipt.json'
import supermarkets from '../resources/supermarkets.json'
import type { StoreOnMap, Supermarket } from './types'
import { FALLBACK_LOCATION, distanceMeters } from './geo'

const all = supermarkets as Supermarket[]

export const receiptTotal = receipt.items.reduce((sum, i) => sum + i.qty * i.unitPrice, 0)
export const receiptItemCount = receipt.items.reduce((n, i) => n + i.qty, 0)

/** Locates the user, falling back silently to mock coords on deny/timeout. */
export function useUserPosition(): [number, number] | null {
  const [pos, setPos] = useState<[number, number] | null>(null)

  useEffect(() => {
    let done = false
    const useFallback = () => {
      if (!done) {
        done = true
        setPos(FALLBACK_LOCATION)
      }
    }
    if (!navigator.geolocation) {
      useFallback()
      return
    }
    const timer = setTimeout(useFallback, 3000)
    navigator.geolocation.getCurrentPosition(
      (p) => {
        clearTimeout(timer)
        if (!done) {
          done = true
          setPos([p.coords.latitude, p.coords.longitude])
        }
      },
      () => {
        clearTimeout(timer)
        useFallback()
      },
      { timeout: 2500, maximumAge: 60000 },
    )
    return () => clearTimeout(timer)
  }, [])

  return pos
}

export interface Stores {
  /** Physical stores, positioned relative to the user, cheapest first. */
  physical: StoreOnMap[]
  /** Online-only stores (no map pin), cheapest first. */
  online: Supermarket[]
  /** Everything together, cheapest first — the order the list screen shows. */
  ranked: Supermarket[]
  /** Best (post-swap) price across every store — what "הכי זול" marks. */
  cheapestBest: number
  priciestBest: number
}

export function useStores(userPos: [number, number] | null): Stores {
  return useMemo(() => {
    // Ranking follows the headline (post-swap) price, not the like-for-like one.
    const byPrice = (a: Supermarket, b: Supermarket) => a.bestPrice - b.bestPrice

    const physical: StoreOnMap[] = userPos
      ? all
          .filter((s) => !s.online)
          .map((s) => {
            const lat = userPos[0] + (s.dLat ?? 0)
            const lng = userPos[1] + (s.dLng ?? 0)
            return { ...s, lat, lng, distanceM: distanceMeters(userPos, [lat, lng]) }
          })
          .sort(byPrice)
      : []

    return {
      physical,
      online: all.filter((s) => s.online).sort(byPrice),
      ranked: [...physical, ...all.filter((s) => s.online)].sort(byPrice),
      cheapestBest: Math.min(...all.map((s) => s.bestPrice)),
      priciestBest: Math.max(...all.map((s) => s.bestPrice)),
    }
  }, [userPos])
}
