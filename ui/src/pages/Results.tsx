import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import Celebration from '../components/Celebration'
import SavingBadge from '../components/SavingBadge'
import CrownIcon from '../components/CrownIcon'
import type { StoreOnMap, Supermarket } from '../lib/types'
import { formatDistance, formatPrice } from '../lib/geo'
import { useStores, useUserPosition } from '../lib/useStores'
import { cartStores, type PricedStore } from '../lib/pricing'
import { useAuth } from '../lib/auth'
import {
  countOf,
  createReceipt,
  receiptOrigin,
  renameReceipt,
  setActiveReceipt,
  totalOf,
  useActiveReceipt,
  type SavedReceipt,
} from '../lib/receipts'
import './Results.css'

export default function Results() {
  const navigate = useNavigate()
  const userPos = useUserPosition()
  const { ranked, cheapestBest } = useStores(userPos)

  const { user } = useAuth()
  // Home passes the opened receipt in router state — use it directly, no refetch.
  const location = useLocation()
  const preloaded = (location.state as { receipt?: SavedReceipt } | null)?.receipt ?? null
  const active = useActiveReceipt(user?.id ?? null, preloaded)
  const [savedName, setSavedName] = useState<string | null>(null)
  const [savedId, setSavedId] = useState<string | null>(active.id)
  const [draftName, setDraftName] = useState('')
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [showPriceHelp, setShowPriceHelp] = useState(false)
  // Show the savings celebration once, only when arriving fresh from a scan.
  // Home signals it via `?celebrate=1` — a query param survives the OAuth
  // redirect + reload where router state does not. Cleaned below so a refresh
  // or back-nav won't repeat it.
  // Home sets `sali.celebrateOnce` right before navigating from a fresh scan.
  // Read once on mount; cleared only when the celebration ENDS (never at mount),
  // so React StrictMode's double-mount and a reload/redirect both keep it intact.
  const [celebrate, setCelebrate] = useState(() => localStorage.getItem('sali.celebrateOnce') === '1')
  const endCelebration = () => {
    setCelebrate(false)
    localStorage.removeItem('sali.celebrateOnce')
  }

  const receiptTotal = totalOf(active.items)
  const receiptItemCount = countOf(active.items)
  const name = savedName ?? active.name
  const receiptId = savedId ?? active.id
  const origin = receiptOrigin(receiptId)

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
    if (!chosen || saving) return
    setSaving(true)
    setSaveError(null)
    try {
      if (receiptId) {
        await renameReceipt(user?.id ?? null, receiptId, chosen)
      } else {
        const record = await createReceipt(user?.id ?? null, chosen, active.items)
        setActiveReceipt(record.id)
        setSavedId(record.id)
      }
      setSavedName(chosen)
      setEditing(false)
    } catch (err) {
      console.error('[sali] save failed:', err)
      const e = err as { code?: string; message?: string }
      const detail = [e.message, e.code && `(${e.code})`].filter(Boolean).join(' ')
      setSaveError(
        e.code === '42501'
          ? 'שמירה נכשלה: אין הרשאה (RLS). כנראה אינכם מחוברים — התחברו ונסו שוב.'
          : `שמירה נכשלה: ${detail || 'שגיאה לא ידועה'}`,
      )
    } finally {
      setSaving(false)
    }
  }

  const startEdit = () => {
    setDraftName(name ?? '')
    setEditing(true)
  }

  const originStore = cartStores(active.items)[0]
  const openCart = (store: PricedStore) => {
    navigate('/cart', { state: { store, items: active.items, name } })
  }

  return (
    <div className="results">
      {/* Fixed top: floating nav chips + the pinned price summary. Doesn't scroll. */}
      <div className="results-fixed">
      {/* Floating, decomposed nav: three separate rounded chips. */}
      <nav className="float-nav">
        <button className="nav-chip nav-icon" onClick={() => navigate('/')} aria-label="חזרה">
          →
        </button>

        {naming ? (
          <form
            className="nav-chip nav-name"
            onSubmit={(e) => {
              e.preventDefault()
              void commitSave()
            }}
          >
            <input
              className="nav-name-input"
              value={draftName}
              onChange={(e) => setDraftName(e.target.value)}
              placeholder="שם הקבלה"
              aria-label="שם הקבלה"
              maxLength={40}
              autoFocus={editing}
            />
          </form>
        ) : (
          <div className="nav-chip nav-name">
            <span className="nav-name-text">{name}</span>
          </div>
        )}

        {naming ? (
          <button
            className="nav-chip nav-save"
            onClick={() => void commitSave()}
            disabled={!draftName.trim() || saving}
          >
            {saving ? '…' : 'שמירה'}
          </button>
        ) : (
          <button className="nav-chip nav-icon" onClick={startEdit} aria-label="עריכת השם">
            <EditIcon />
          </button>
        )}
      </nav>

        {/* The receipt itself — the baseline, pinned below the nav. Tap for the
            origin store's exact per-item prices. */}
        <div className="receipt-card" onClick={() => openCart(originStore)} role="button">
          <div className="receipt-origin">
            <span className="receipt-origin-logo">
              <img src={origin.logo} alt={origin.chain} />
            </span>
            <div className="receipt-origin-info">
              <span className="receipt-origin-chain">{origin.chain}</span>
              <span className="receipt-origin-branch">{origin.branch}</span>
            </div>
          </div>
          <div className="receipt-price">
            <div className="receipt-total mono" dir="ltr">
              {formatPrice(receiptTotal)}
            </div>
            <p className="receipt-meta">
              {receiptItemCount} מוצרים
              {bestSaving > 0 && (
                <>
                  {' · אפשר לחסוך '}
                  <strong className="mono" dir="ltr">{formatPrice(bestSaving)}</strong>
                </>
              )}
            </p>
          </div>
        </div>
      </div>

      {saveError && <p className="save-error">{saveError}</p>}

      <div className="results-scroll">
        <div className="list-subhead reveal">
          <div className="subhead-title">
            המחיר הטוב ביותר בכל סופר
            <button
              className="price-help"
              onClick={() => setShowPriceHelp((v) => !v)}
              aria-label="הסבר על המחירים"
            >
              ?
            </button>
          </div>
          <span className="subhead-note">כולל החלפה למוצרים דומים וזולים יותר</span>
          {showPriceHelp && (
            <div className="price-help-pop">
              המספרים בסוגריים <b dir="ltr">(א/ב)</b>:
              <br />
              <b>א</b> — המחיר לאותה עגלה בדיוק.
              <br />
              <b>ב</b> — המחיר לאחר החלפה למוצרים דומים וזולים יותר.
              <br />
              החיסכון מחושב מול מה ששילמתם בקבלה.
            </div>
          )}
        </div>

        <ol className="store-list">
          {ranked.map((store, i) => (
            <StoreRow
              key={store.id}
              store={store}
              best={store.bestPrice === cheapestBest}
              receiptTotal={receiptTotal}
              style={{ animationDelay: `${Math.min(i, 6) * 55}ms` }}
              onOpen={() =>
                openCart({
                  id: store.id,
                  brand: store.brand,
                  logo: store.logo,
                  online: store.online,
                  isOrigin: false,
                  cartTotal: store.cartTotal,
                })
              }
            />
          ))}
        </ol>
      </div>

      <div className="results-cta">
        <button className="map-btn" onClick={() => navigate('/map')}>
          <MapIcon />
          הצגה על המפה
        </button>
      </div>

      {celebrate && bestSaving > 0 && (
        <Celebration amount={bestSaving} onDone={endCelebration} />
      )}
    </div>
  )
}

function StoreRow({
  store,
  best,
  receiptTotal,
  style,
  onOpen,
}: {
  store: Supermarket
  best: boolean
  receiptTotal: number
  style?: React.CSSProperties
  onOpen?: () => void
}) {
  const diff = receiptTotal - store.bestPrice

  const where = store.online
    ? store.deliveryFee === 0
      ? 'משלוח חינם'
      : `משלוח ${formatPrice(store.deliveryFee)}`
    : formatDistance((store as StoreOnMap).distanceM)

  return (
    <li
      className={`store-row reveal ${best ? 'best' : ''} ${store.online ? 'online' : ''}`}
      style={style}
      onClick={onOpen}
      role="button"
    >
      {best && (
        <span className="best-crown" aria-label="הכי זול">
          <CrownIcon />
        </span>
      )}

      {/* Logo + online tag — right side (RTL start). */}
      <div className="store-logo-col">
        <span className="row-logo">
          <img src={store.logo} alt={store.brand} />
        </span>
        {store.online && <span className="online-tag">אונליין</span>}
      </div>

      <div className="row-info">
        <span className="row-name">{store.brand}</span>
        <span className="row-where">{where}</span>
      </div>

      {/* Savings — the headline value, left side (RTL end). */}
      <div className="row-savings">
        <SavingBadge amount={Math.abs(diff)} save={diff > 0} size="lg" />
        <span className="price-xy mono" dir="ltr">
          {formatPrice(store.cartTotal)} / {formatPrice(store.bestPrice)}
        </span>
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

function MapIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" width="19" height="19" aria-hidden="true">
      <path
        d="M9 4 3.5 6v14L9 18l6 2 5.5-2V4L15 6 9 4z"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinejoin="round"
      />
      <path d="M9 4v14M15 6v14" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
    </svg>
  )
}
