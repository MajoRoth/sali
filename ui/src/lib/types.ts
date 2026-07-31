import type { NearbyStore } from './api'

/** One line of the shopper's own receipt, at the price they actually paid. */
export interface ReceiptItem {
  name: string;
  /** The code printed on the receipt: a barcode when there was one, else a PLU. */
  barcode: string;
  qty: number;
  unitPrice: number;
}

/** Where the receipt was bought, as the screens label it. */
export interface ReceiptOrigin {
  chain: string;
  branch: string;
  logo: string | null;
}

/**
 * A store as the list and map screens render it.
 *
 * `cartTotal` and `bestPrice` are the two numbers the design is built around:
 * the like-for-like cart, and the cart after swapping in cheaper equivalents.
 * Both come from the backend — nothing here is derived or estimated client-side.
 */
export interface Supermarket {
  id: string;
  brand: string;
  branch: string;
  logo: string | null;
  /** Chain-level estimates have no branch to put on the map. */
  online: boolean;
  /** Price for the exact same cart — the true, like-for-like comparison. */
  cartTotal: number;
  /** Headline price after swapping in cheaper similar products. */
  bestPrice: number;
  /** How many products were swapped to reach `bestPrice`. */
  swaps: number;
  deliveryFee: number;
  /** available / requested, 0..1. Ranking puts coverage before price. */
  coverage: number
  /** Position is the city centre, not the branch. Distance is unknown. */
  approxLocation: boolean;
  /** How many matched products this store had no price for. */
  unavailableCount: number;
  /** The backend record, for screens that need the per-line detail. */
  source: NearbyStore;
}

export interface StoreOnMap extends Supermarket {
  lat: number;
  lng: number;
  distanceM: number;
}

/** A real branch near the shopper, with no claim about what a cart costs there. */
export interface BranchOnMap {
  id: string;
  chain: string;
  branch: string;
  logo: string | null;
  lat: number;
  lng: number;
  distanceM: number;
}
