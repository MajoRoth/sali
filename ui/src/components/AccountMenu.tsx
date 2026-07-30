import { useEffect, useRef, useState } from 'react'
import { useAuth } from '../lib/auth'
import './AccountMenu.css'

/**
 * Classic account control: avatar button that opens a popover showing the
 * signed-in user with a sign-out action, or a Google sign-in prompt.
 */
export default function AccountMenu() {
  const { user, signInWithGoogle, signOut } = useAuth()
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)

  // Close on outside click or Escape.
  useEffect(() => {
    if (!open) return
    const onDown = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  const initial = user?.name?.trim()?.[0] ?? user?.email?.[0]?.toUpperCase() ?? null

  return (
    <div className="account" ref={rootRef}>
      <button
        className={`account-btn ${user ? 'signed-in' : ''}`}
        onClick={() => setOpen((o) => !o)}
        aria-label={user ? 'החשבון שלי' : 'התחברות'}
        aria-expanded={open}
      >
        {user?.avatarUrl ? (
          <img src={user.avatarUrl} alt="" />
        ) : initial ? (
          <span className="account-initial">{initial}</span>
        ) : (
          <UserIcon />
        )}
      </button>

      {open && (
        <div className="account-popover" role="dialog">
          {user ? (
            <>
              <div className="account-identity">
                <span className="account-avatar">
                  {user.avatarUrl ? <img src={user.avatarUrl} alt="" /> : initial}
                </span>
                <div className="account-who">
                  <span className="account-name">{user.name ?? 'משתמש'}</span>
                  {user.email && (
                    <span className="account-email" dir="ltr">
                      {user.email}
                    </span>
                  )}
                </div>
              </div>
              <button
                className="btn btn-danger btn-block"
                onClick={() => {
                  setOpen(false)
                  void signOut()
                }}
              >
                התנתקות
              </button>
            </>
          ) : (
            <>
              <p className="account-pitch">התחברו כדי לשמור את הקבלות שלכם ולראות אותן בכל מכשיר</p>
              <button
                className="btn btn-white btn-block"
                onClick={() => {
                  setOpen(false)
                  void signInWithGoogle()
                }}
              >
                <GoogleIcon />
                התחברות עם Google
              </button>
            </>
          )}
        </div>
      )}
    </div>
  )
}

function UserIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" width="21" height="21" aria-hidden="true">
      <circle cx="12" cy="8.5" r="3.6" stroke="currentColor" strokeWidth="1.8" />
      <path
        d="M4.8 20a7.2 7.2 0 0 1 14.4 0"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  )
}

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M23 12.3c0-.8-.1-1.6-.2-2.3H12v4.5h6.2a5.3 5.3 0 0 1-2.3 3.5v2.9h3.7c2.2-2 3.4-5 3.4-8.6z"
      />
      <path
        fill="#34A853"
        d="M12 23.5c3.1 0 5.7-1 7.6-2.8l-3.7-2.9c-1 .7-2.3 1.1-3.9 1.1-3 0-5.5-2-6.4-4.7H1.8v3C3.7 21 7.6 23.5 12 23.5z"
      />
      <path fill="#FBBC05" d="M5.6 14.2a6.9 6.9 0 0 1 0-4.4v-3H1.8a11.5 11.5 0 0 0 0 10.4l3.8-3z" />
      <path
        fill="#EA4335"
        d="M12 4.8c1.7 0 3.2.6 4.4 1.7l3.3-3.3C17.7 1.3 15.1.3 12 .3 7.6.3 3.7 2.8 1.8 6.5l3.8 3C6.5 6.8 9 4.8 12 4.8z"
      />
    </svg>
  )
}
