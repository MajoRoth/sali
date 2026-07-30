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
  setActiveReceipt,
  totalOf,
  type SavedReceipt,
} from '../lib/receipts'
import './Home.css'

const RECEIPT_API_URL = 'http://localhost:8000/api/receipts/extract'
const RECEIPT_IMAGE_TOTAL_API_URL = 'http://localhost:8000/api/receipts/extract-image-total'

type ExtractedReceipt = {
  receipt: { totals: { total: string }, transaction: { currency: string | null } }
}

type ExtractedReceiptImageTotal = {
  total: string
  currency: string | null
}

export default function Home() {
  const navigate = useNavigate()
  const { user, loading: authLoading } = useAuth()

  const [receipts, setReceipts] = useState<SavedReceipt[] | null>(null)

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

  const alertTotal = (total: string, currency: string | null) => {
    const amount = currency === 'ILS' ? `₪${total}` : `${total}${currency ? ` ${currency}` : ''}`
    window.alert(`סך הכול בקבלה: ${amount}`)
  }

  const alertReceiptTotal = async (url: string) => {
    try {
      const response = await fetch(RECEIPT_API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      })
      if (!response.ok) throw new Error('receipt extraction failed')
      const receipt = await response.json() as ExtractedReceipt
      alertTotal(receipt.receipt.totals.total, receipt.receipt.transaction.currency)
    } catch {
      window.alert('לא הצלחנו לחלץ את סכום הקבלה.')
    }
  }

  const alertReceiptImageTotal = async (image: File) => {
    const formData = new FormData()
    formData.append('image', image)
    try {
      const response = await fetch(RECEIPT_IMAGE_TOTAL_API_URL, {
        method: 'POST',
        body: formData,
      })
      if (!response.ok) throw new Error('receipt total extraction failed')
      const receipt = await response.json() as ExtractedReceiptImageTotal
      alertTotal(receipt.total, receipt.currency)
    } catch {
      window.alert('לא הצלחנו לחלץ את סכום הקבלה.')
    }
  }

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
          onImageSubmit={alertReceiptImageTotal}
          onUrlSubmit={alertReceiptTotal}
        />
      ) : (
        <UploadHome onImageSubmit={alertReceiptImageTotal} onUrlSubmit={alertReceiptTotal} />
      )}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* Signed out, or signed in with no receipts yet.                      */
/* ------------------------------------------------------------------ */

interface UploadProps {
  onImageSubmit: (image: File) => Promise<void>
  onUrlSubmit: (url: string) => Promise<void>
}

function UploadHome({ onImageSubmit, onUrlSubmit }: UploadProps) {
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
          const image = e.dataTransfer.files[0]
          if (image) void onImageSubmit(image)
        }}
      >
        <div className="scanline" />
        <ReceiptGlyph className="receipt-icon" />
        <h1 className="upload-title">העלו את הקבלה שלכם</h1>
        <p className="upload-sub">קבלה מודפסת או קבלה דיגיטלית — שתיהן עובדות 😊</p>
        <p className="upload-hint">מצלמים את הקבלה מהסופר, או מעלים צילום מסך שקיבלתם במייל</p>

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
          accept="image/jpeg,image/png,image/webp"
          capture="environment"
          hidden
          onChange={(e) => {
            const image = e.target.files?.[0]
            if (image) void onImageSubmit(image)
          }}
        />
        <input
          ref={uploadRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          hidden
          onChange={(e) => {
            const image = e.target.files?.[0]
            if (image) void onImageSubmit(image)
          }}
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
  onImageSubmit: (image: File) => Promise<void>
  onUrlSubmit: (url: string) => Promise<void>
}

function ReceiptListHome({
  user,
  receipts,
  onOpen,
  onDelete,
  onCreateEmpty,
  onImageSubmit,
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
        accept="image/jpeg,image/png,image/webp"
        capture="environment"
        hidden
        onChange={(e) => {
          const image = e.target.files?.[0]
          if (image) void onImageSubmit(image)
        }}
      />
      <input
        ref={uploadRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        hidden
        onChange={(e) => {
          const image = e.target.files?.[0]
          if (image) void onImageSubmit(image)
        }}
      />
    </>
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
