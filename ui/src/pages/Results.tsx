import { useNavigate } from 'react-router-dom'
import type { StoreOnMap, Supermarket } from '../lib/types'
import { formatDistance, formatPrice } from '../lib/geo'
import { receiptItemCount, receiptTotal, useStores, useUserPosition } from '../lib/useStores'
import './Results.css'

export default function Results() {
  const navigate = useNavigate()
  const userPos = useUserPosition()
  const { ranked, cheapestBest } = useStores(userPos)

  if (!userPos) {
    return (
      <div className="results loading-state">
        <div className="spinner-sm" />
        <p>מאתרים אתכם…</p>
      </div>
    )
  }

  const bestSaving = receiptTotal - cheapestBest

  return (
    <div className="results">
      <header className="results-header">
        <button className="back-btn" onClick={() => navigate('/')} aria-label="חזרה">
          →
        </button>
        <h1>השוואת מחירים</h1>
      </header>

      <div className="results-scroll">
        {/* The scanned receipt itself — the baseline everything else is compared to. */}
        <div className="receipt-card">
          <span className="receipt-badge">הקבלה שלכם</span>
          <div className="receipt-total mono" dir="ltr">
            {formatPrice(receiptTotal)}
          </div>
          <p className="receipt-meta">{receiptItemCount} מוצרים נסרקו</p>
          {bestSaving > 0 && (
            <p className="receipt-saving">
              אפשר לחסוך עד <strong className="mono">{formatPrice(bestSaving)}</strong> על אותה עגלה
            </p>
          )}
        </div>

        <p className="list-subhead">
          המחיר הטוב ביותר בכל סופר
          <span className="subhead-note">כולל החלפה למוצרים דומים וזולים יותר</span>
        </p>

        <ol className="store-list">
          {ranked.map((store, i) => (
            <StoreRow
              key={store.id}
              store={store}
              rank={i + 1}
              best={store.bestPrice === cheapestBest}
            />
          ))}
        </ol>
      </div>

      <div className="results-cta">
        <button className="map-btn" onClick={() => navigate('/map')}>
          <PinIcon />
          הצגה על המפה
        </button>
      </div>
    </div>
  )
}

function StoreRow({ store, rank, best }: { store: Supermarket; rank: number; best: boolean }) {
  const diff = receiptTotal - store.bestPrice

  const where = store.online
    ? store.deliveryFee === 0
      ? 'משלוח חינם'
      : `משלוח ${formatPrice(store.deliveryFee)}`
    : formatDistance((store as StoreOnMap).distanceM)

  return (
    <li className={`store-row ${best ? 'best' : ''} ${store.online ? 'online' : ''}`}>
      <span className="row-rank mono">{rank}</span>
      <span className="row-logo">
        <img src={store.logo} alt={store.brand} />
      </span>

      <div className="row-info">
        <span className="row-name">
          {store.brand}
          {best && <span className="best-tag">הכי זול</span>}
        </span>
        <span className="row-sub">
          <span className="row-where">{where}</span>
          {store.online && <span className="online-tag">אונליין</span>}
        </span>
        <span className={`row-diff ${diff > 0 ? 'cheaper' : 'pricier'}`}>
          {diff > 0 ? `חוסכים ${formatPrice(diff)}` : `יקר ב־${formatPrice(-diff)}`}
        </span>
      </div>

      <div className="row-price">
        <span className="price-best mono" dir="ltr">
          {formatPrice(store.bestPrice)}
        </span>
        <span className="price-true">
          אותה עגלה{' '}
          <span className="mono" dir="ltr">
            {formatPrice(store.cartTotal)}
          </span>
        </span>
        <span className="price-swaps">{store.swaps} החלפות</span>
      </div>
    </li>
  )
}

function PinIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" width="19" height="19" aria-hidden="true">
      <path
        d="M12 21s7-5.5 7-11a7 7 0 1 0-14 0c0 5.5 7 11 7 11z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
      <circle cx="12" cy="10" r="2.6" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  )
}
