import { useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { formatPrice } from '../lib/geo'
import type { PricedLine, PricedStore } from '../lib/pricing'
import ChainMark from '../components/ChainMark'
import SavingBadge from '../components/SavingBadge'
import SwapIcon from '../components/SwapIcon'
import type { ReceiptItem } from '../lib/types'
import './CartView.css'

interface CartNavState {
  store?: PricedStore
  items?: ReceiptItem[]
  name?: string
}

/**
 * One basket, line by line.
 *
 * For the origin it is the shopper's own receipt, so every line is simply what
 * they paid. For any other store each line is compared against what they paid,
 * and a line the store has no price for is shown as unavailable — never filled
 * in with an estimate, because on screen a guess and a fact look identical.
 */
export default function CartView() {
  const navigate = useNavigate()
  const location = useLocation()
  const state = (location.state as CartNavState | null) ?? {}

  // Reached without context (e.g. a refresh) — nothing to show.
  useEffect(() => {
    if (!state.store) navigate('/', { replace: true })
  }, [state.store, navigate])
  if (!state.store) return null

  const { store } = state
  const rows = [...store.lines]
    // The origin basket is compared against itself, so every line would read
    // "saved ₪0.00" — no badge there, just the prices from the receipt.
    .map((line) => ({ line, diff: store.isOrigin ? null : savingOf(line) }))
    // Biggest difference first: the reason to look at this screen is the
    // outliers, and they are what a shopper acts on.
    .sort((a, b) => (b.diff ?? -Infinity) - (a.diff ?? -Infinity))

  // Compare like with like: the store's total covers only the lines it could
  // price, so the baseline is what the shopper paid *for those same lines*.
  // Measuring a partial cart against the whole receipt books every product the
  // store does not stock as a saving — the more it is missing, the better it
  // looks, which is exactly backwards.
  const paidForPriced = store.lines.reduce(
    (sum, line) => (line.available && line.paidLineTotal !== null ? sum + line.paidLineTotal : sum),
    0,
  )
  const totalDiff = store.isOrigin ? 0 : paidForPriced - store.cartTotal
  const totalSave = totalDiff >= -0.005

  // Says what the numbers on each row mean, above the rows. The origin basket
  // is the receipt itself, so there is nothing to compare it against — only
  // the other stores carry a per-line difference.
  const listNote = store.isOrigin
    ? 'אלו המחירים ששילמתם בפועל, לפי הקבלה'
    : 'ההפרש מציג את החיסכון על כל מוצר לעומת המחיר בחנות המקורית'

  return (
    <div className="cartview">
      <header className="cartview-header">
        <button className="nav-chip nav-icon" onClick={() => navigate(-1)} aria-label="חזרה">
          →
        </button>
        <div className="cartview-store">
          <ChainMark chain={store.brand} logo={store.logo} className="cartview-logo" />
          <div className="cartview-store-info">
            <span className="cartview-brand">{store.brand}</span>
            <span className="cartview-sub">
              {store.isOrigin ? 'המחירים מהקבלה שלכם' : store.branch || 'מחירי המאגר הציבורי'}
            </span>
          </div>
        </div>
        <div className="cartview-totals">
          <span className="cartview-total mono" dir="ltr">
            {formatPrice(store.cartTotal)}
          </span>
          {!store.isOrigin && (
            <SavingBadge
              amount={Math.abs(totalDiff)}
              save={totalSave}
              size="sm"
              label={totalSave ? 'חוסכים' : 'יקר יותר'}
            />
          )}
        </div>
      </header>

      {store.unavailableCount > 0 && (
        <p className="cartview-warn">
          {store.unavailableCount} מוצרים אינם במלאי המתומחר של הסניף ואינם נכללים בסכום ובחיסכון.
        </p>
      )}

      <div className="cartview-list">
        <p className="cartview-note">{listNote}</p>
        {rows.map(({ line, diff }, i) => (
          <div className={`citem ${line.available ? '' : 'unavailable'}`} key={`${line.barcode}-${i}`}>
            <div className="citem-top">
              <span className="citem-name">{line.name}</span>
              {/* This store's price for the line, with the difference beneath it. */}
              <div className="citem-vals">
                {line.available && line.lineTotal !== null && (
                  <span className="citem-price mono" dir="ltr">
                    {formatPrice(line.lineTotal)}
                  </span>
                )}
                {diff !== null && <SavingBadge amount={Math.abs(diff)} save={diff >= -0.005} size="sm" />}
              </div>
            </div>
            <div className="citem-meta">
              {line.available && line.unitPrice !== null
                ? `${line.qty} × ${formatPrice(line.unitPrice)} ליחידה`
                : 'אין מחיר עדכני בסניף'}
              {line.swappedFrom && (
                <span className="citem-swap">
                  {' · '}
                  <SwapIcon size={12} />
                  במקום {line.swappedFrom}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

/** What this line saves against what the shopper paid; null when unknowable. */
function savingOf(line: PricedLine): number | null {
  if (!line.available || line.unitPrice === null || line.paidUnitPrice === null) return null
  return (line.paidUnitPrice - line.unitPrice) * line.qty
}
