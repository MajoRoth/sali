export interface ReceiptItem {
  name: string;
  barcode: string;
  qty: number;
  unitPrice: number;
}

export interface Receipt {
  store: string;
  date: string;
  currency: string;
  items: ReceiptItem[];
}

export interface Supermarket {
  id: string;
  brand: string;
  logo: string;
  /** Online-only stores have no physical branch, so they're not placed on the map. */
  online: boolean;
  /** Offset from the user's position — physical stores only. */
  dLat?: number;
  dLng?: number;
  /** Price for the exact same cart — the true, like-for-like comparison. */
  cartTotal: number;
  /** Headline price after swapping in cheaper similar products. */
  bestPrice: number;
  /** How many products were swapped to reach `bestPrice`. */
  swaps: number;
  deliveryFee: number;
}

export interface StoreOnMap extends Supermarket {
  lat: number;
  lng: number;
  distanceM: number;
}
