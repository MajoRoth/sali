import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import Celebration from '../components/Celebration'
import ChainMark from '../components/ChainMark'
import SavingBadge from '../components/SavingBadge'
import CrownIcon from '../components/CrownIcon'
import { warningText } from '../lib/api'
import type { StoreOnMap, Supermarket } from '../lib/types'
import { formatDistance, formatPrice } from '../lib/geo'
import { useStores, useUserPosition } from '../lib/useStores'
import { originStore, pricedStore, type PricedStore } from '../lib/pricing'
import { useAuth } from '../lib/auth'
import {
  countOf,
  createReceipt,
  documentTotal,
  originFromDocument,
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

  const {
    ranked,
    cheapestBest,
    branches,
    loading: pricing,
    error: pricingError,
    warnings,
  } = useStores(active.document, userPos)
  const branchCount = branches.length
  // The server flags simulated figures with a `demo prices:` warning. Everything
  // derived from money — the banner, and the savings celebration — keys off this.
  const demoNote = warnings.some((w) => w.startsWith('demo prices:'))
    ? warningText('demo prices:')
    : null

  // The receipt's own printed total is authoritative; summing the lines is only
  // a fallback for a cart with no document behind it.
  const receiptTotal = documentTotal(active.document) ?? totalOf(active.items)
  const receiptItemCount = countOf(active.items)
  const name = savedName ?? active.name
  const receiptId = savedId ?? active.id
  const origin = originFromDocument(active.document)

  if (!userPos || active.loading) {
    return (
      <div className="results loading-state">
        <div className="spinner-sm" />
        <p>מאתרים אתכם…</p>
      </div>
    )
  }

  const bestSaving = cheapestBest === null ? 0 : receiptTotal - cheapestBest
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
        const record = await createReceipt(user?.id ?? null, chosen, active.items, active.document)
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

  const receiptBasket = originStore(active.items, origin)
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
        <div className="receipt-card" onClick={() => openCart(receiptBasket)} role="button">
          <div className="receipt-origin">
            <ChainMark chain={origin.chain} logo={origin.logo} className="receipt-origin-logo" />
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
          <span className="subhead-note">
            <SwapIcon size={13} />
            כולל החלפה למוצרים דומים וזולים יותר
          </span>
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

        {pricing && (
          <div className="stores-pending">
            <div className="spinner-sm" />
            <p>משווים מחירים בסופרים שסביבכם…</p>
          </div>
        )}

        {!pricing && pricingError && (
          <div className="stores-empty error" role="alert">
            <p className="stores-empty-title">ההשוואה נכשלה</p>
            <p className="stores-empty-body">{pricingError}</p>
          </div>
        )}

        {!pricing && !pricingError && ranked.length === 0 && (
          <NoPrices warnings={warnings} branchCount={branchCount} />
        )}

        {/*
          The price database is down and the server sent simulated figures.
          This banner is the only thing standing between a demo and a lie, so
          it sits above the list rather than below it, and it is not dismissible.
        */}
        {!pricing && demoNote && (
          <p className="demo-banner" role="status">
            {demoNote}
          </p>
        )}

        {!pricing && ranked.length > 0 && (
          <>
            <ol className="store-list">
              {ranked.map((store, i) => (
                <StoreRow
                  key={store.id}
                  store={store}
                  best={store.bestPrice === cheapestBest}
                  receiptTotal={receiptTotal}
                  style={{ animationDelay: `${Math.min(i, 6) * 55}ms` }}
                  onOpen={() => openCart(pricedStore(store.source, active.items))}
                />
              ))}
            </ol>
            {/*
              What the ranking left out, said under it: lines the price database
              could not match, and the branches whose chains publish no prices.
              Without this, a missing שופרסל reads as the app ignoring it.
            */}
            <div className="store-list-notes">
              {warnings
                .map(warningText)
                .filter((text): text is string => text !== null)
                .map((note) => (
                  <p key={note} className="stores-empty-note">
                    {note}
                  </p>
                ))}
            </div>
          </>
        )}
      </div>

      <div className="results-cta">
        <button className="map-btn" onClick={() => navigate('/map')}>
          <MapIcon />
          הצגה על המפה
        </button>
      </div>

      {celebrate && bestSaving > 0 && !demoNote && (
        <Celebration amount={bestSaving} onDone={endCelebration} />
      )}
    </div>
  )
}

/**
 * Shown when the cart could not be priced anywhere.
 *
 * Not a rare edge: a receipt full of a chain's own-brand goods, or one bought
 * somewhere whose prices the database has not refreshed, ends up here. Saying
 * which of those it was — and still reporting the branches we did find — is
 * the honest thing; an empty list with no explanation reads as "there is
 * nothing near you", which is false and is the one message we can disprove.
 */
function NoPrices({ warnings, branchCount }: { warnings: string[]; branchCount: number }) {
  const noListings = warnings.some((w) => w.startsWith('no store prices'))
  // The server's warnings are English diagnostics; only the few a shopper can
  // act on have Hebrew copy, and `warningText` returns null for the rest.
  const notes = warnings
    .filter((w) => !w.startsWith('no store prices'))
    .map(warningText)
    .filter((text): text is string => text !== null)

  return (
    <div className="stores-empty">
      <p className="stores-empty-title">
        {noListings ? 'אין כרגע מחירים להשוואה' : 'לא נמצאה עגלה מתומחרת בסביבה'}
      </p>
      <p className="stores-empty-body">
        {noListings
          ? 'מאגר המחירים לא מחזיק כרגע מחיר עדכני לאף אחד מהמוצרים שבקבלה. ' +
            'ברגע שיתפרסמו מחירים חדשים, ההשוואה כאן תתמלא מאליה.'
          : 'לא נמצא סניף בסביבה עם מחיר עדכני למוצרים שבקבלה.'}
      </p>
      {branchCount > 0 && (
        <p className="stores-empty-note">
          מצאנו {branchCount} סניפים אמיתיים בסביבתכם — אפשר לראות אותם על המפה.
        </p>
      )}
      {notes.map((note) => (
        <p key={note} className="stores-empty-note">
          {note}
        </p>
      ))}
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

  // An approximate position is the city centre, so there is no distance to
  // quote — naming the city is the honest version of the same information.
  // The list renders plain Supermarkets, whose distance lives on the server
  // response (`source.distanceM`); only map rows carry their own copy.
  const meters = (store as StoreOnMap).distanceM ?? store.source.distanceM
  const where = store.online
    ? store.deliveryFee === 0
      ? 'משלוח חינם'
      : `משלוח ${formatPrice(store.deliveryFee)}`
    : store.approxLocation || meters == null
      ? (store.source.city ?? 'מיקום משוער')
      : formatDistance(meters)

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
        <ChainMark chain={store.brand} logo={store.logo} className="row-logo" />
        {store.online && <span className="online-tag">אונליין</span>}
      </div>

      <div className="row-info">
        <span className="row-name">{store.brand}</span>
        <span className="row-where">
          {store.branch ? `${store.branch} · ${where}` : where}
        </span>
        {store.coverage < 1 && (
          <span className="row-gap">חסרים {store.unavailableCount} מוצרים</span>
        )}
      </div>

      {/* Left side (RTL end). A saving is only meaningful for a store that
          actually stocks the cart: "save ₪552" off a basket holding 11% of the
          items is the price of the missing 89%, not a discount. Partial stores
          therefore show what they cover and nothing else. */}
      <div className="row-savings">
        {store.coverage < 1 ? (
          <>
            <span className="row-partial mono" dir="ltr">
              {formatPrice(store.bestPrice)}
            </span>
            <span className="price-xy">עבור {Math.round(store.coverage * 100)}% מהעגלה</span>
          </>
        ) : (
          <>
            <SavingBadge amount={Math.abs(diff)} save={diff > 0} size="lg" />
            <span className="price-xy mono" dir="ltr">
              {formatPrice(store.cartTotal)} /{' '}
              <span className="swap-price">
                <SwapIcon />
                {formatPrice(store.bestPrice)}
              </span>
            </span>
          </>
        )}
      </div>
    </li>
  )
}


// Two round arrows forming a circle — the "swap for a cheaper item" cycle.
function SwapIcon({ size = 14 }: { size?: number }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" width={size} height={size} aria-hidden="true">
      <path
        d="M18.5 8.5A8 8 0 0 0 5.2 7.3"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
      />
      <path d="M18.9 4.6v4h-4" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
      <path
        d="M5.5 15.5a8 8 0 0 0 13.3 1.2"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
      />
      <path d="M5.1 19.4v-4h4" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
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
