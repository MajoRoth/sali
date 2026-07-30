import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import Celebration from '../components/Celebration'
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
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  // Show the savings celebration once, only when arriving fresh from a scan
  // (Home passes `state.celebrate`). Strip it so refresh/back-nav won't repeat.
  const location = useLocation()
  const [celebrate, setCelebrate] = useState(
    () => Boolean((location.state as { celebrate?: boolean } | null)?.celebrate),
  )
  useEffect(() => {
    if (window.history.state?.usr?.celebrate) window.history.replaceState(null, '')
  }, [])

  const receiptTotal = totalOf(active.items)
  const receiptItemCount = countOf(active.items)
  const name = savedName ?? active.name
  const receiptId = savedId ?? active.id
  // Roll `.reveal` cards into view as they enter the scroll container.
  const scrollRef = useScrollReveal(ranked.length)

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

        {/* The receipt itself — the baseline, pinned below the nav. */}
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
      </div>

      {saveError && <p className="save-error">{saveError}</p>}

      <div className="results-scroll" ref={scrollRef}>
        <p className="list-subhead reveal">
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
              style={{ transitionDelay: `${Math.min(i, 6) * 55}ms` }}
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

      {celebrate && bestSaving > 0 && (
        <Celebration amount={bestSaving} onDone={() => setCelebrate(false)} />
      )}
    </div>
  )
}

function StoreRow({
  store,
  rank,
  best,
  receiptTotal,
  style,
}: {
  store: Supermarket
  rank: number
  best: boolean
  receiptTotal: number
  style?: React.CSSProperties
}) {
  const diff = receiptTotal - store.bestPrice

  const where = store.online
    ? store.deliveryFee === 0
      ? 'משלוח חינם'
      : `משלוח ${formatPrice(store.deliveryFee)}`
    : formatDistance((store as StoreOnMap).distanceM)

  return (
    <li className={`store-row reveal ${best ? 'best' : ''} ${store.online ? 'online' : ''}`} style={style}>
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

/**
 * Rolls `.reveal` elements into view as they enter the scroll container.
 * `ready` changes (0 → N) once the list renders, so the observer attaches then.
 *
 * Fail-safe: `.reveal` starts at opacity 0, so anything the observer misses would
 * stay invisible. We use threshold 0 (the roll transform foreshortens rows and can
 * defeat higher thresholds) plus a timeout that force-reveals whatever is already
 * on screen — content must never get stuck hidden.
 */
function useScrollReveal(ready: number) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const root = ref.current
    if (!root) return
    const els = Array.from(root.querySelectorAll<HTMLElement>('.reveal'))
    if (!('IntersectionObserver' in window)) {
      els.forEach((el) => el.classList.add('in'))
      return
    }
    const io = new IntersectionObserver(
      (entries) =>
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add('in')
            io.unobserve(e.target)
          }
        }),
      { root, threshold: 0, rootMargin: '0px 0px -6% 0px' },
    )
    els.forEach((el) => io.observe(el))
    // Safety net for anything on screen the observer didn't catch.
    const t = setTimeout(() => {
      const rootRect = root.getBoundingClientRect()
      els.forEach((el) => {
        if (el.classList.contains('in')) return
        const r = el.getBoundingClientRect()
        if (r.top < rootRect.bottom && r.bottom > rootRect.top) {
          el.classList.add('in')
          io.unobserve(el)
        }
      })
    }, 300)
    return () => {
      clearTimeout(t)
      io.disconnect()
    }
  }, [ready])
  return ref
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
