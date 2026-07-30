import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import receipt from '../resources/receipt.json'
import './Home.css'

const LOADING_STAGES = ['קוראים את הקבלה…', 'מזהים מוצרים…', 'מחפשים סופרים קרובים…']
const STAGE_MS = 750

export default function Home() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [stage, setStage] = useState(0)
  const [dragOver, setDragOver] = useState(false)
  const cameraRef = useRef<HTMLInputElement>(null)
  const uploadRef = useRef<HTMLInputElement>(null)

  const itemCount = receipt.items.reduce((n, item) => n + item.qty, 0)

  // Mock OCR: whatever file arrives is ignored — we play the loading
  // stages, then jump to the map with the mock receipt.
  const startScan = () => setLoading(true)

  useEffect(() => {
    if (!loading) return
    if (stage < LOADING_STAGES.length - 1) {
      const t = setTimeout(() => setStage((s) => s + 1), STAGE_MS)
      return () => clearTimeout(t)
    }
    const t = setTimeout(() => navigate('/results'), STAGE_MS)
    return () => clearTimeout(t)
  }, [loading, stage, navigate])

  return (
    <div className="home">
      <header className="home-header">
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
          startScan()
        }}
      >
        <div className="scanline" />
        <svg className="receipt-icon" viewBox="0 0 64 64" fill="none" aria-hidden="true">
          <path
            d="M16 6h32v50l-5-4-5 4-6-4-6 4-5-4-5 4V6z"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinejoin="round"
          />
          <path d="M24 20h16M24 28h16M24 36h10" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
        </svg>
        <h1 className="upload-title">העלו את הקבלה שלכם</h1>
        <p className="upload-sub">קבלה מודפסת או קבלה דיגיטלית — שתיהן עובדות 😊</p>
        <p className="upload-hint">מצלמים את הקבלה מהסופר, או מעלים צילום מסך / PDF שקיבלתם במייל</p>

        <div className="upload-actions">
          <button className="action-btn primary" onClick={() => cameraRef.current?.click()}>
            <CameraIcon />
            מצלמה
          </button>
          <button className="action-btn" onClick={() => uploadRef.current?.click()}>
            <ImageIcon />
            העלאת קובץ
          </button>
        </div>

        <input
          ref={cameraRef}
          type="file"
          accept="image/*"
          capture="environment"
          hidden
          onChange={(e) => e.target.files?.length && startScan()}
        />
        <input
          ref={uploadRef}
          type="file"
          accept="image/*,application/pdf"
          hidden
          onChange={(e) => e.target.files?.length && startScan()}
        />
      </main>

      <footer className="home-footer">נמצא לכם את הסל הזול ביותר בסביבה</footer>

      {loading && (
        <div className="loading-overlay">
          <div className="spinner" />
          <p className="loading-text" key={stage}>
            {LOADING_STAGES[stage]}
          </p>
          <p className="loading-meta">{stage >= 1 ? `זוהו ${itemCount} מוצרים ✓` : ' '}</p>
        </div>
      )}
    </div>
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
