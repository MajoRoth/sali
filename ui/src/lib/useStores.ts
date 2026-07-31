import { useEffect, useMemo, useState } from 'react'
import {
  isApiError,
  priceNearby,
  storesNearby,
  type NearbyResponse,
  type NearbyStore,
  type ReceiptDocument,
} from './api'
import { chainLogo } from './chains'
import type { BranchOnMap, StoreOnMap, Supermarket } from './types'
import { FALLBACK_LOCATION } from './geo'

/** How far around the shopper to look. 5 km is a drive, not a hike. */
export const SEARCH_RADIUS_M = 5000

/** Locates the user, falling back to central Tel Aviv on deny/timeout. */
export function useUserPosition(): [number, number] | null {
  const [pos, setPos] = useState<[number, number] | null>(null)

  useEffect(() => {
    let done = false
    const fallBack = () => {
      if (!done) {
        done = true
        setPos(FALLBACK_LOCATION)
      }
    }
    if (!navigator.geolocation) {
      fallBack()
      return
    }
    const timer = setTimeout(fallBack, 3000)
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
        fallBack()
      },
      { timeout: 2500, maximumAge: 60000 },
    )
    return () => clearTimeout(timer)
  }, [])

  return pos
}

function toSupermarket(store: NearbyStore): Supermarket {
  return {
    id: `${store.chain}:${store.storeId}`,
    brand: store.chain,
    branch: store.branch,
    logo: chainLogo(store.chain),
    online: store.online,
    cartTotal: store.sameCart.total,
    bestPrice: store.optimalCart.total,
    swaps: store.optimalCart.swaps.length,
    deliveryFee: store.deliveryFee,
    coverage: store.sameCart.coverage,
    approxLocation: store.approximateLocation ?? false,
    unavailableCount: store.sameCart.unavailableCount,
    source: store,
  }
}

export interface Stores {
  /** Priced physical stores, cheapest first. */
  physical: StoreOnMap[]
  /** Priced online/chain-level options, cheapest first. */
  online: Supermarket[]
  /** Everything priced, cheapest first — the order the list screen shows. */
  ranked: Supermarket[]
  /** Best (post-swap) price across every store, or null when nothing priced. */
  cheapestBest: number | null
  /**
   * Real branches around the shopper regardless of pricing. The map always has
   * something true to draw, even when no cart could be priced.
   */
  branches: BranchOnMap[]
  loading: boolean
  /** Set when the request itself failed, as opposed to returning nothing. */
  error: string | null
  /** Server-side notes — why a cart is missing, or a match uncertain. */
  warnings: string[]
  response: NearbyResponse | null
}

const IDLE: Stores = {
  physical: [],
  online: [],
  ranked: [],
  cheapestBest: null,
  branches: [],
  loading: false,
  error: null,
  warnings: [],
  response: null,
}

/**
 * Prices a receipt against the shops around the user.
 *
 * Two requests, deliberately independent: the cart pricing, and the plain list
 * of nearby branches. The second is what keeps the map honest — the price
 * database currently publishes no listings, so pricing legitimately returns no
 * stores, and a map that went blank would read as "there are no supermarkets
 * near you" rather than "we could not price your cart".
 */
export function useStores(
  document: ReceiptDocument | null,
  userPos: [number, number] | null,
  radiusM: number = SEARCH_RADIUS_M,
  allowSubstitutions: boolean = true,
): Stores {
  const [response, setResponse] = useState<NearbyResponse | null>(null)
  const [branches, setBranches] = useState<BranchOnMap[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const lat = userPos?.[0]
  const lng = userPos?.[1]

  useEffect(() => {
    if (lat === undefined || lng === undefined) return
    let cancelled = false

    void storesNearby({ lat, lng }, radiusM)
      .then((found) => {
        if (cancelled) return
        setBranches(
          found.stores.map((s) => ({
            id: `${s.chain_id}:${s.store_id}`,
            chain: s.chain,
            branch: s.branch,
            logo: chainLogo(s.chain),
            lat: s.lat,
            lng: s.lng,
            distanceM: s.distance_m,
          })),
        )
      })
      .catch((err) => {
        // A missing branch list is a degraded map, not a failed screen.
        console.warn('[sali] nearby branches unavailable:', err)
      })

    return () => {
      cancelled = true
    }
  }, [lat, lng, radiusM])

  useEffect(() => {
    if (lat === undefined || lng === undefined || !document) {
      setResponse(null)
      return
    }
    let cancelled = false
    setLoading(true)
    setError(null)

    void priceNearby(document, { lat, lng }, radiusM, allowSubstitutions)
      .then((result) => {
        if (!cancelled) setResponse(result)
      })
      .catch((err) => {
        if (cancelled) return
        console.error('[sali] pricing failed:', err)
        setError(isApiError(err) ? err.message : 'לא הצלחנו להשוות מחירים כרגע.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [document, lat, lng, radiusM, allowSubstitutions])

  return useMemo(() => {
    if (lat === undefined || lng === undefined) return IDLE

    const stores = (response?.stores ?? []).map(toSupermarket)
    const physical: StoreOnMap[] = stores
      .filter((s): s is Supermarket & { source: NearbyStore } => !s.online && s.source.location !== null)
      .map((s) => ({
        ...s,
        lat: s.source.location!.lat,
        lng: s.source.location!.lng,
        distanceM: s.source.distanceM ?? 0,
      }))
    const online = stores.filter((s) => s.online || s.source.location === null)

    return {
      physical,
      online,
      // The backend already ranks coverage-first; preserve that order.
      ranked: stores,
      // Only complete carts. A partial basket is cheap because it is missing
      // things, so headlining it as the best price advertises a saving that
      // does not exist.
      cheapestBest: (() => {
        const whole = stores.filter((s) => s.coverage >= 1)
        return whole.length ? Math.min(...whole.map((s) => s.bestPrice)) : null
      })(),
      branches,
      loading,
      error,
      warnings: response?.warnings ?? [],
      response,
    }
  }, [response, branches, loading, error, lat, lng])
}
