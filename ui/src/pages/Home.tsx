import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import AccountMenu from '../components/AccountMenu'
import { useAuth } from '../lib/auth'
import { formatPrice } from '../lib/geo'
import {
  countOf,
  createReceipt,
  deleteReceipt,
  formatSavedDate,
  listReceipts,
  scannedItems,
  setActiveReceipt,
  setPendingScan,
  totalOf,
  type SavedReceipt,
} from '../lib/receipts'
import './Home.css'

const FILE_STAGES = ['קוראים את הקבלה…', 'מזהים מוצרים…', 'מחפשים סופרים קרובים…']
const URL_STAGES = ['טוענים את הקבלה מהקישור…', ...FILE_STAGES]
const STAGE_MS = 750
const RECEIPT_API_URL = 'http://localhost:8000/api/receipts/extract'

export default function Home() {
  const navigate = useNavigate()
  const { user, loading: authLoading, signInWithGoogle } = useAuth()

  const [receipts, setReceipts] = useState<SavedReceipt[] | null>(null)
  const [stages, setStages] = useState<string[] | null>(null)
  const [stage, setStage] = useState(0)
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

  // Mock OCR: file scans retain the current placeholder behavior.
  const startScan = (from: 'file' | 'url') => {
    setActiveReceipt(null)
    setPendingScan(scannedItems)
    setStage(0)
    setStages(from === 'url' ? URL_STAGES : FILE_STAGES)
  }

  const alertReceiptTotal = async (url: string) => {
    try {
      const response = await fetch(RECEIPT_API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      })
      if (!response.ok) throw new Error('receipt extraction failed')
      const receipt = await response.json() as {
        receipt: { totals: { total: string }, transaction: { currency: string | null } }
      }
      const currency = receipt.receipt.transaction.currency
      const amount = currency === 'ILS'
        ? `₪${receipt.receipt.totals.total}`
        : `${receipt.receipt.totals.total}${currency ? ` ${currency}` : ''}`
      window.alert(`סך הכול בקבלה: ${amount}`)
    } catch {
      window.alert('לא הצלחנו לחלץ את סכום הקבלה.')
    }
  }

  useEffect(() => {
    if (!stages) return
    if (stage < stages.length - 1) {
      const t = setTimeout(() => setStage((s) => s + 1), STAGE_MS)
      return () => clearTimeout(t)
    }
    const t = setTimeout(() => {
      setStages(null)
      if (user) navigate('/results')
      else setGateOpen(true)
    }, STAGE_MS)
    return () => clearTimeout(t)
  }, [stages, stage, navigate, user])

  // Once signed in at the gate, continue to the results we already "scanned".
  useEffect(() => {
    if (gateOpen && user) {
      setGateOpen(false)
      navigate('/results')
    }
  }, [gateOpen, user, navigate])

  const openReceipt = (id: string) => {
    setActiveReceipt(id)
    navigate('/results')
  }

  const removeReceipt = async (id: string) => {
    await deleteReceipt(user?.id ?? null, id)
    setReceipts(await listReceipts(user?.id ?? null))
  }

  const createEmpty = async () => {
    const now = new Date()
    const record = await createReceipt(user?.id ?? null, `קבלה חדשה ${now.getDate()}.${now.getMonth() + 1}`, [])
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
      {showList ? (
        <ReceiptListHome
          user={user}
          receipts={receipts}
          onOpen={openReceipt}
          onDelete={removeReceipt}
          onCreateEmpty={createEmpty}
          onScan={startScan}
          onUrlSubmit={alertReceiptTotal}
        />
      ) : (
        <UploadHome onScan={startScan} onUrlSubmit={alertReceiptTotal} />
      )}

      {stages && (
        <div className="loading-overlay">
          <div className="spinner" />
          <p className="loading-text" key={stage}>
            {stages[stage]}
          </p>
          {/* Reveal the count once we're past the "reading" stage. */}
          <p className="loading-meta">
            {stage >= stages.length - 2 ? `זוהו ${countOf(scannedItems)} מוצרים ✓` : ' '}
          </p>
        </div>
      )}

      {gateOpen && (
        <SignInGate onSignIn={signInWithGoogle} onCancel={() => setGateOpen(false)} />
      )}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* Signed out, or signed in with no receipts yet.                      */
/* ------------------------------------------------------------------ */

interface UploadProps {
  onScan: (from: 'file' | 'url') => void
  onUrlSubmit: (url: string) => Promise<void>
}

function UploadHome({ onScan, onUrlSubmit }: UploadProps) {
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
        <p className="tagline">סורקים · משווים · חוסכים</p>
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
          onScan('file')
        }}
      >
        <div className="scanline" />
        <ReceiptGlyph className="receipt-icon" />
        <h1 className="upload-title">העלו את הקבלה שלכם</h1>
        <p className="upload-sub">קבלה מודפסת או קבלה דיגיטלית — שתיהן עובדות 😊</p>
        <p className="upload-hint">מצלמים את הקבלה מהסופר, או מעלים צילום מסך / PDF שקיבלתם במייל</p>

        <div className="tile-grid lg upload-actions">
          <button className="tile lg" onClick={() => cameraRef.current?.click()}>
            <CameraIcon />
            מצלמה
          </button>
          <button className="tile lg" onClick={() => uploadRef.current?.click()}>
            <ImageIcon />
            העלאת קובץ
          </button>
        </div>

        <div className="url-divider">
          <span>או הדביקו קישור לקבלה</span>
        </div>

        <form
          className="field-row url-form"
          onSubmit={(e) => {
            e.preventDefault()
            if (url.trim()) void onUrlSubmit(url.trim())
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

        <input
          ref={cameraRef}
          type="file"
          accept="image/*"
          capture="environment"
          hidden
          onChange={(e) => e.target.files?.length && onScan('file')}
        />
        <input
          ref={uploadRef}
          type="file"
          accept="image/*,application/pdf"
          hidden
          onChange={(e) => e.target.files?.length && onScan('file')}
        />
      </main>

      <footer className="home-footer">נמצא לכם את הסל הזול ביותר בסביבה</footer>
    </>
  )
}

/* ------------------------------------------------------------------ */
/* Signed in with saved receipts.                                      */
/* ------------------------------------------------------------------ */

interface ListProps {
  user: { name: string | null }
  receipts: SavedReceipt[]
  onOpen: (id: string) => void
  onDelete: (id: string) => void
  onCreateEmpty: () => void
  onScan: (from: 'file' | 'url') => void
  onUrlSubmit: (url: string) => Promise<void>
}

function ReceiptListHome({
  user,
  receipts,
  onOpen,
  onDelete,
  onCreateEmpty,
  onScan,
  onUrlSubmit,
}: ListProps) {
  const [urlOpen, setUrlOpen] = useState(false)
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

      {/* Compact echo of the upload zone — the entry point for a new receipt. */}
      <section className="panel new-receipt">
        <p className="panel-title">קבלה חדשה</p>
        <div className="tile-grid">
          <button className="tile" onClick={onCreateEmpty}>
            <PlusIcon />
            עגלה ריקה
          </button>
          <button className="tile" onClick={() => cameraRef.current?.click()}>
            <CameraIcon />
            מצלמה
          </button>
          <button className="tile" onClick={() => uploadRef.current?.click()}>
            <ImageIcon />
            קובץ
          </button>
          <button
            className={`tile ${urlOpen ? 'active' : ''}`}
            onClick={() => setUrlOpen((o) => !o)}
          >
            <LinkIcon />
            קישור
          </button>
        </div>

        {urlOpen && (
          <form
            className="field-row url-form inline"
            onSubmit={(e) => {
              e.preventDefault()
              if (url.trim()) {
                setUrlOpen(false)
                void onUrlSubmit(url.trim())
              }
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
              autoFocus
            />
            <button className="icon-btn forward" type="submit" disabled={!url.trim()} aria-label="טעינת הקבלה">
              <ArrowIcon />
            </button>
          </form>
        )}
      </section>

      <ul className="receipt-list">
        {receipts.map((r) => (
          <li key={r.id} className="receipt-row">
            <button className="receipt-open" onClick={() => onOpen(r.id)}>
              <div className="receipt-row-info">
                <span className="receipt-row-name">{r.name}</span>
                <span className="receipt-row-meta">
                  {formatSavedDate(r.savedAt)} · {countOf(r.items)} מוצרים
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
        ))}
      </ul>

      <input
        ref={cameraRef}
        type="file"
        accept="image/*"
        capture="environment"
        hidden
        onChange={(e) => e.target.files?.length && onScan('file')}
      />
      <input
        ref={uploadRef}
        type="file"
        accept="image/*,application/pdf"
        hidden
        onChange={(e) => e.target.files?.length && onScan('file')}
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

function LinkIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" width="20" height="20" aria-hidden="true">
      <path
        d="M10 13a4 4 0 0 0 6 .5l2-2a4 4 0 0 0-5.7-5.7l-1 1M14 11a4 4 0 0 0-6-.5l-2 2A4 4 0 0 0 11.7 18l1-1"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
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
