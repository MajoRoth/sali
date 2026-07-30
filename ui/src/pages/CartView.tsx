import { useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { formatPrice } from '../lib/geo'
import { itemPrices, itemRanges, type PricedStore } from '../lib/pricing'
import SavingBadge from '../components/SavingBadge'
import type { ReceiptItem } from '../lib/types'
import './CartView.css'

interface CartNavState {
  store?: PricedStore
  items?: ReceiptItem[]
  name?: string
}

export default function CartView() {
  const navigate = useNavigate()
  const location = useLocation()
  const state = (location.state as CartNavState | null) ?? {}

  // Reached without context (e.g. a refresh) — nothing to show.
  useEffect(() => {
    if (!state.store || !state.items) navigate('/', { replace: true })
  }, [state.store, state.items, navigate])
  if (!state.store || !state.items) return null

  const { store, items } = state
  const prices = itemPrices(store, items)
  const ranges = itemRanges(items)
  const total = items.reduce((s, it, i) => s + prices[i] * it.qty, 0)

  // Per-item comparison. Non-origin: saving vs the receipt's paid price.
  // Origin: difference from the lowest price across all supermarkets.
  const rows = items
    .map((it, i) => {
      const price = prices[i]
      const lineTotal = price * it.qty
      if (store.isOrigin) {
        const overpay = (price - ranges[i].min) * it.qty // ≥ 0
        return { it, i, price, lineTotal, amount: overpay, save: overpay < 0.005, sortVal: overpay }
      }
      const lineSave = (it.unitPrice - price) * it.qty
      return { it, i, price, lineTotal, amount: Math.abs(lineSave), save: lineSave >= -0.005, sortVal: lineSave }
    })
    .sort((a, b) => b.sortVal - a.sortVal)

  // Total headline. Non-origin: saved vs receipt. Origin: total overpay vs the
  // cheapest-per-item basket (i.e. how much you could have saved).
  const receiptTotal = items.reduce((s, it) => s + it.unitPrice * it.qty, 0)
  const lowestTotal = items.reduce((s, it, i) => s + ranges[i].min * it.qty, 0)
  const totalDiff = store.isOrigin ? total - lowestTotal : receiptTotal - total
  const totalSave = store.isOrigin ? totalDiff < 0.005 : totalDiff >= -0.005
  const totalLabel = store.isOrigin ? 'יכולת לחסוך' : totalSave ? 'חוסכים' : 'יקר יותר'

  return (
    <div className="cartview">
      <header className="cartview-header">
        <button className="nav-chip nav-icon" onClick={() => navigate(-1)} aria-label="חזרה">
          →
        </button>
        <div className="cartview-store">
          <span className="cartview-logo">
            <img src={store.logo} alt={store.brand} />
          </span>
          <div className="cartview-store-info">
            <span className="cartview-brand">{store.brand}</span>
            <span className="cartview-sub">
              {store.isOrigin ? 'המחירים מהקבלה' : 'מחירים משוערים'}
            </span>
          </div>
        </div>
        <div className="cartview-totals">
          <span className="cartview-total mono" dir="ltr">
            {formatPrice(total)}
          </span>
          <SavingBadge amount={Math.abs(totalDiff)} save={totalSave} size="sm" label={totalLabel} />
        </div>
      </header>

      <div className="cartview-list">
        {rows.map(({ it, i, price, lineTotal, amount, save }) => (
          <div className="citem" key={`${it.barcode}-${i}`}>
            <div className="citem-top">
              <span className="citem-name">{it.name}</span>
              <SavingBadge amount={amount} save={save} size="sm" />
            </div>
            <div className="citem-meta">
              {it.qty} × {formatPrice(price)} ={' '}
              <span className="mono" dir="ltr">
                {formatPrice(lineTotal)}
              </span>
              {store.isOrigin && !save && ' · יקר מהזול ביותר'}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
