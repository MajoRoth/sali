import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import AccountMenu from '../components/AccountMenu'
import ChainMark from '../components/ChainMark'
import HomeMapBackground from '../components/HomeMapBackground'
import { useAuth } from '../lib/auth'
import { formatPrice } from '../lib/geo'
import {
  extractFromImage,
  extractFromUrl,
  extractImageTotal,
  isApiError,
  type ReceiptDocument,
} from '../lib/api'
import {
  createReceipt,
  deleteReceipt,
  formatSavedDate,
  itemsFromDocument,
  listReceipts,
  originFromDocument,
  setActiveReceipt,
  setPendingScan,
  totalOf,
  type SavedReceipt,
} from '../lib/receipts'
import './Home.css'

/**
 * Extraction is one long call, not four steps, so these rotate while it runs
 * rather than reporting progress. They are honest about the order the server
 * does the work in, and the last one holds until the answer comes back.
 */
const FILE_STAGES = ['קוראים את הקבלה…', 'מזהים מוצרים…', 'עוד רגע…']
const URL_STAGES = ['פותחים את הקישור…', 'קוראים את הקבלה…', 'מזהים מוצרים…', 'עוד רגע…']
const STAGE_MS = 2500
/** Set when a signed-out scan awaits sign-in; survives the OAuth redirect. */
const RESUME_KEY = 'sali.resumeAfterAuth'
/** Signals Results to play the savings celebration on its next mount. */
const CELEBRATE_KEY = 'sali.celebrateOnce'

type Scan = { kind: 'url'; url: string } | { kind: 'file'; file: File }

export default function Home() {
  const navigate = useNavigate()
  const { user, loading: authLoading, signInWithGoogle } = useAuth()

  const [receipts, setReceipts] = useState<SavedReceipt[] | null>(null)
  const [stages, setStages] = useState<string[] | null>(null)
  const [stage, setStage] = useState(0)
  /** Item count of the finished extraction, revealed under the spinner. */
  const [scanned, setScanned] = useState<number | null>(null)
  const [scanError, setScanError] = useState<string | null>(null)
  /** Set when a signed-out user finishes a scan and must sign in to continue. */
  const [gateOpen, setGateOpen] = useState(false)

  // Load the signed-in user's receipts.
  useEffect(() => {
    if (authLoading) return
    if (!user) {
      setReceipts([])
      return
    }
    let cancelled = false
    void listReceipts(user.id)
      .then((list) => !cancelled && setReceipts(list))
      .catch(() => !cancelled && setReceipts([]))
    return () => {
      cancelled = true
    }
  }, [user, authLoading])

  /**
   * Run a real extraction, then either continue to the results or stop at the
   * sign-in gate.
   *
   * A photo is tried for its full line items first and falls back to reading
   * just the total, because most photographed receipts are creased, cropped, or
   * lit badly enough that some line is unreadable — and a proven total is still
   * worth showing even though it cannot be compared across stores.
   */
  const runScan = async (scan: Scan) => {
    setActiveReceipt(null)
    setPendingScan(null)
    setScanError(null)
    setScanned(null)
    setStage(0)
    setStages(scan.kind === 'url' ? URL_STAGES : FILE_STAGES)

    try {
      let document: ReceiptDocument
      try {
        document =
          scan.kind === 'url' ? await extractFromUrl(scan.url) : await extractFromImage(scan.file)
      } catch (err) {
        if (scan.kind !== 'file' || !isApiError(err) || err.code !== 'insufficient_evidence') throw err
        const total = await extractImageTotal(scan.file)
        setStages(null)
        setScanError(
          `הצלחנו לקרוא רק את הסכום: ${formatPrice(Number(total.total))}. ` +
            'כדי להשוות מחירים צריך צילום שבו כל השורות קריאות.',
        )
        return
      }

      const items = itemsFromDocument(document)
      setPendingScan({ items, document })
      setScanned(items.length)
      setStages(null)

      if (user) {
        localStorage.setItem(CELEBRATE_KEY, '1')
        navigate('/results')
      } else {
        // Persist the intent: Google sign-in redirects away and reloads the app,
        // wiping React state, so we can't rely on `gateOpen` to resume afterwards.
        localStorage.setItem(RESUME_KEY, '1')
        setGateOpen(true)
      }
    } catch (err) {
      console.error('[sali] scan failed:', err)
      setStages(null)
      setScanError(isApiError(err) ? err.message : 'לא הצלחנו לקרוא את הקבלה. נסו שוב.')
    }
  }

  // Rotate the stage copy while the request is in flight, holding on the last.
  useEffect(() => {
    if (!stages || stage >= stages.length - 1) return
    const t = setTimeout(() => setStage((s) => s + 1), STAGE_MS)
    return () => clearTimeout(t)
  }, [stages, stage])

  // Resume the scanned receipt once signed in — covers both the instant local
  // sign-in and returning from the Google OAuth redirect (fresh page load).
  useEffect(() => {
    if (user && localStorage.getItem(RESUME_KEY)) {
      localStorage.removeItem(RESUME_KEY)
      localStorage.setItem(CELEBRATE_KEY, '1')
      setGateOpen(false)
      navigate('/results')
    }
  }, [user, navigate])

  const openReceipt = (r: SavedReceipt) => {
    // Pass the record along so Results shows it instantly without a refetch.
    localStorage.removeItem(CELEBRATE_KEY) // opening a saved receipt never celebrates
    setActiveReceipt(r.id)
    navigate('/results', { state: { receipt: r } })
  }

  const removeReceipt = async (id: string) => {
    await deleteReceipt(user?.id ?? null, id)
    setReceipts(await listReceipts(user?.id ?? null))
  }

  const createEmpty = async () => {
    localStorage.removeItem(CELEBRATE_KEY) // an empty cart has nothing to celebrate
    const now = new Date()
    const record = await createReceipt(
      user?.id ?? null,
      `קבלה חדשה ${now.getDate()}.${now.getMonth() + 1}`,
      [],
      null,
    )
    setActiveReceipt(record.id)
    navigate('/results')
  }

  if (authLoading || receipts === null) {
    return (
      <div className="home home-loading">
        <div className="spinner" />
      </div>
    )
  }

  const showList = user !== null && receipts.length > 0

  return (
    <div className="home">
      <HomeMapBackground />
      <div className="home-content">
        {scanError && (
          <div className="scan-error" role="alert">
            <span>{scanError}</span>
            <button className="scan-error-close" onClick={() => setScanError(null)} aria-label="סגירה">
              ×
            </button>
          </div>
        )}

        {showList ? (
          <ReceiptListHome
            user={user}
            receipts={receipts}
            onOpen={openReceipt}
            onDelete={removeReceipt}
            onCreateEmpty={createEmpty}
            onScan={runScan}
          />
        ) : (
          <UploadHome onScan={runScan} />
        )}
      </div>

      {stages && (
        <div className="loading-overlay">
          <div className="spinner" />
          <p className="loading-text" key={stage}>
            {stages[stage]}
          </p>
          <p className="loading-meta">
            {scanned === null ? 'קריאת קבלה אמיתית עשויה לקחת עד דקה' : `זוהו ${scanned} מוצרים ✓`}
          </p>
        </div>
      )}

      {gateOpen && (
        <SignInGate
          onSignIn={signInWithGoogle}
          onCancel={() => {
            localStorage.removeItem(RESUME_KEY)
            setGateOpen(false)
          }}
        />
      )}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* Signed out, or signed in with no receipts yet.                      */
/* ------------------------------------------------------------------ */

interface UploadProps {
  onScan: (scan: Scan) => void
}

function UploadHome({ onScan }: UploadProps) {
  const [dragOver, setDragOver] = useState(false)
  const [url, setUrl] = useState('')
  const cameraRef = useRef<HTMLInputElement>(null)
  const uploadRef = useRef<HTMLInputElement>(null)

  return (
    <>
      <header className="home-header">
        <div className="header-account">
          <AccountMenu />
        </div>
        <div className="wordmark" dir="ltr">
          sali<span className="wordmark-dot">_</span>
        </div>
        <p className="tagline">יכולת לחסוך, לא חבל?</p>
      </header>

      <main
        className={`upload-zone ${dragOver ? 'drag-over' : ''}`}
        onDragOver={(e) => {
          e.preventDefault()
          setDragOver(true)
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragOver(false)
          const file = e.dataTransfer.files[0]
          if (file) onScan({ kind: 'file', file })
        }}
      >
        <ReceiptGlyph className="receipt-icon" />
        <h1 className="upload-title">העלו את הקבלה שלכם</h1>
        <p className="upload-sub">קבלה מודפסת או דיגיטלית — שתיהן עובדות 😊</p>

        <div className="tile-grid upload-actions">
          <button className="tile" onClick={() => cameraRef.current?.click()}>
            <CameraIcon />
            מצלמה
          </button>
          <button className="tile" onClick={() => uploadRef.current?.click()}>
            <ImageIcon />
            קובץ
          </button>
        </div>

        <div className="url-divider">
          <span>או הדביקו קישור לקבלה</span>
        </div>

        <form
          className="field-row url-form"
          onSubmit={(e) => {
            e.preventDefault()
            if (url.trim()) onScan({ kind: 'url', url: url.trim() })
          }}
        >
          <input
            className="field mono"
            type="url"
            inputMode="url"
            dir="ltr"
            placeholder="https://..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            aria-label="קישור לקבלה"
          />
          <button className="icon-btn forward" type="submit" disabled={!url.trim()} aria-label="טעינת הקבלה">
            <ArrowIcon />
          </button>
        </form>

        {/* The API accepts JPEG, PNG and WEBP only, so nothing else is offered. */}
        <input
          ref={cameraRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          capture="environment"
          hidden
          onChange={(e) => {
            const file = e.target.files?.[0]
            e.target.value = '' // let the same file be picked twice in a row
            if (file) onScan({ kind: 'file', file })
          }}
        />
        <input
          ref={uploadRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          hidden
          onChange={(e) => {
            const file = e.target.files?.[0]
            e.target.value = ''
            if (file) onScan({ kind: 'file', file })
          }}
        />
      </main>

    </>
  )
}

/* ------------------------------------------------------------------ */
/* Signed in with saved receipts.                                      */
/* ------------------------------------------------------------------ */

interface ListProps {
  user: { name: string | null }
  receipts: SavedReceipt[]
  onOpen: (r: SavedReceipt) => void
  onDelete: (id: string) => void
  onCreateEmpty: () => void
  onScan: (scan: Scan) => void
}

function ReceiptListHome({
  user,
  receipts,
  onOpen,
  onDelete,
  onCreateEmpty,
  onScan,
}: ListProps) {
  const [url, setUrl] = useState('')
  const cameraRef = useRef<HTMLInputElement>(null)
  const uploadRef = useRef<HTMLInputElement>(null)

  return (
    <>
      <header className="list-header">
        <div className="list-heading">
          <div className="wordmark small" dir="ltr">
            sali<span className="wordmark-dot">_</span>
          </div>
          <p className="list-greeting">
            {user.name ? `שלום, ${user.name}` : 'הקבלות שלי'}
          </p>
        </div>

        <div className="header-account">
          <AccountMenu />
        </div>
      </header>

      {/* Echo of the full upload zone — the entry point for a new receipt. */}
      <section className="panel new-receipt">
        <p className="panel-title">קבלה חדשה</p>
        <div className="tile-grid lg">
          <button className="tile lg" onClick={onCreateEmpty}>
            <PlusIcon />
            עגלה ריקה
          </button>
          <button className="tile lg" onClick={() => cameraRef.current?.click()}>
            <CameraIcon />
            מצלמה
          </button>
          <button className="tile lg" onClick={() => uploadRef.current?.click()}>
            <ImageIcon />
            קובץ
          </button>
        </div>

        <form
          className="field-row url-form inline"
          onSubmit={(e) => {
            e.preventDefault()
            if (url.trim()) onScan({ kind: 'url', url: url.trim() })
          }}
        >
          <input
            className="field mono"
            type="url"
            inputMode="url"
            dir="ltr"
            placeholder="הדביקו קישור לקבלה"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            aria-label="קישור לקבלה"
          />
          <button className="icon-btn forward" type="submit" disabled={!url.trim()} aria-label="טעינת הקבלה">
            <ArrowIcon />
          </button>
        </form>
      </section>

      <ul className="receipt-list">
        {receipts.map((r) => {
          const origin = originFromDocument(r.document)
          return (
          <li key={r.id} className="receipt-row">
            <button className="receipt-open" onClick={() => onOpen(r)}>
              <ChainMark chain={origin.chain} logo={origin.logo} className="receipt-row-logo" />
              <div className="receipt-row-info">
                <span className="receipt-row-name">{r.name}</span>
                <span className="receipt-row-meta">
                  {origin.chain} · {formatSavedDate(r.savedAt)}
                </span>
              </div>
              <span className="receipt-row-total mono" dir="ltr">
                {formatPrice(totalOf(r.items))}
              </span>
            </button>
            <button
              className="receipt-delete"
              onClick={() => onDelete(r.id)}
              aria-label={`מחיקת ${r.name}`}
            >
              <TrashIcon />
            </button>
          </li>
          )
        })}
      </ul>

      <input
        ref={cameraRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        capture="environment"
        hidden
        onChange={(e) => {
          const file = e.target.files?.[0]
          e.target.value = ''
          if (file) onScan({ kind: 'file', file })
        }}
      />
      <input
        ref={uploadRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        hidden
        onChange={(e) => {
          const file = e.target.files?.[0]
          e.target.value = ''
          if (file) onScan({ kind: 'file', file })
        }}
      />
    </>
  )
}

/* ------------------------------------------------------------------ */
/* Sign-in gate — shown after a signed-out user finishes a scan.       */
/* ------------------------------------------------------------------ */

function SignInGate({ onSignIn, onCancel }: { onSignIn: () => void; onCancel: () => void }) {
  return (
    <div className="gate-overlay">
      <div className="gate-card">
        <ReceiptGlyph className="gate-icon" />
        <h2>הקבלה מוכנה!</h2>
        <p className="gate-sub">התחברו כדי לראות את השוואת המחירים ולשמור את הקבלה</p>
        <button className="btn btn-white btn-block google-btn" onClick={onSignIn}>
          <GoogleIcon />
          התחברות עם Google
        </button>
        <button className="gate-cancel" onClick={onCancel}>
          ביטול
        </button>
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* Icons                                                               */
/* ------------------------------------------------------------------ */

function ReceiptGlyph({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 64 64" fill="none" aria-hidden="true">
      <path
        d="M16 6h32v50l-5-4-5 4-6-4-6 4-5-4-5 4V6z"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinejoin="round"
      />
      <path d="M24 20h16M24 28h16M24 36h10" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  )
}

function CameraIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" width="20" height="20" aria-hidden="true">
      <path
        d="M4 8a2 2 0 0 1 2-2h1.5l1.2-2h6.6l1.2 2H18a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8z"
        stroke="currentColor"
        strokeWidth="1.8"
      />
      <circle cx="12" cy="13" r="3.5" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  )
}

function ImageIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" width="20" height="20" aria-hidden="true">
      <rect x="4" y="5" width="16" height="14" rx="2" stroke="currentColor" strokeWidth="1.8" />
      <circle cx="9" cy="10" r="1.6" fill="currentColor" />
      <path d="m5 17 4.5-4 3.5 3 3-2.5 3 3.5" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
    </svg>
  )
}


function PlusIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" width="20" height="20" aria-hidden="true">
      <path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  )
}

function TrashIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" width="18" height="18" aria-hidden="true">
      <path
        d="M5 7h14M10 7V5h4v2M6 7l1 12h10l1-12M10 11v5M14 11v5"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function ArrowIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" width="20" height="20" aria-hidden="true">
      <path d="M14 6l6 6-6 6M20 12H5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" width="19" height="19" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M23 12.3c0-.8-.1-1.6-.2-2.3H12v4.5h6.2a5.3 5.3 0 0 1-2.3 3.5v2.9h3.7c2.2-2 3.4-5 3.4-8.6z"
      />
      <path
        fill="#34A853"
        d="M12 23.5c3.1 0 5.700-1 7.6-2.8l-3.7-2.9c-1 .7-2.3 1.1-3.9 1.1-3 0-5.5-2-6.4-4.7H1.8v3C3.7 21 7.6 23.5 12 23.5z"
      />
      <path fill="#FBBC05" d="M5.6 14.2a6.9 6.9 0 0 1 0-4.4v-3H1.8a11.5 11.5 0 0 0 0 10.4l3.8-3z" />
      <path
        fill="#EA4335"
        d="M12 4.8c1.7 0 3.2.6 4.4 1.7l3.3-3.3C17.7 1.3 15.1.3 12 .3 7.6.3 3.7 2.8 1.8 6.5l3.8 3C6.5 6.8 9 4.8 12 4.8z"
      />
    </svg>
  )
}
