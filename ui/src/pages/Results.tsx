import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { StoreOnMap, Supermarket } from '../lib/types'
import { formatDistance, formatPrice } from '../lib/geo'
import { useStores, useUserPosition } from '../lib/useStores'
import { useAuth } from '../lib/auth'
import {
  countOf,
  createReceipt,
  renameReceipt,
  setActiveReceipt,
  totalOf,
  useActiveReceipt,
} from '../lib/receipts'
import './Results.css'

export default function Results() {
  const navigate = useNavigate()
  const userPos = useUserPosition()
  const { ranked, cheapestBest } = useStores(userPos)

  const { user } = useAuth()
  const active = useActiveReceipt(user?.id ?? null)
  const [savedName, setSavedName] = useState<string | null>(null)
  const [savedId, setSavedId] = useState<string | null>(active.id)
  const [draftName, setDraftName] = useState('')
  const [editing, setEditing] = useState(false)

  const receiptTotal = totalOf(active.items)
  const receiptItemCount = countOf(active.items)
  const name = savedName ?? active.name
  const receiptId = savedId ?? active.id

  if (!userPos || active.loading) {
    return (
      <div className="results loading-state">
        <div className="spinner-sm" />
        <p>מאתרים אתכם…</p>
      </div>
    )
  }

  const bestSaving = receiptTotal - cheapestBest
  // Show the name field when there's no name yet, or the user is renaming.
  const naming = !name || editing

  const commitSave = async () => {
    const chosen = draftName.trim()
    if (!chosen) return
    if (receiptId) {
      await renameReceipt(user?.id ?? null, receiptId, chosen)
    } else {
      const record = await createReceipt(user?.id ?? null, chosen, active.items)
      setActiveReceipt(record.id)
      setSavedId(record.id)
    }
    setSavedName(chosen)
    setEditing(false)
  }

  const startEdit = () => {
    setDraftName(name ?? '')
    setEditing(true)
  }

  return (
    <div className="results">
      <header className="results-header">
        <button className="back-btn" onClick={() => navigate('/')} aria-label="חזרה">
          →
        </button>
        {naming ? (
          /* The page title doubles as the name field — saving is blocked until it has one. */
          <form
            className="field-row title-name-form"
            onSubmit={(e) => {
              e.preventDefault()
              void commitSave()
            }}
          >
            <input
              className="field"
              value={draftName}
              onChange={(e) => setDraftName(e.target.value)}
              placeholder="שם הקבלה"
              aria-label="שם הקבלה"
              maxLength={40}
              autoFocus={editing}
            />
            <button className="btn btn-primary" type="submit" disabled={!draftName.trim()}>
              שמירה
            </button>
          </form>
        ) : (
          <>
            <h1 className="results-title">{name}</h1>
            <button className="title-edit" onClick={startEdit} aria-label="עריכת השם">
              <EditIcon />
            </button>
          </>
        )}
      </header>

      <div className="results-scroll">
        {/* The receipt itself — the baseline everything else is compared to. */}
        <div className="receipt-card">
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
              receiptTotal={receiptTotal}
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

function StoreRow({
  store,
  rank,
  best,
  receiptTotal,
}: {
  store: Supermarket
  rank: number
  best: boolean
  receiptTotal: number
}) {
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

function EditIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" width="18" height="18" aria-hidden="true">
      <path
        d="M4 20h4L18.5 9.5a2 2 0 0 0-2.83-2.83L5 17v3z"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinejoin="round"
      />
      <path d="M13.5 7.5 16.5 10.5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
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
