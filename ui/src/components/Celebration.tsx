import { useEffect } from 'react'
import { formatPrice } from '../lib/geo'
import './Celebration.css'

/** Firework burst positions (%) with a stagger and a base colour. */
const BURSTS = [
  { x: 28, y: 34, delay: 0, hue: 145 },
  { x: 72, y: 30, delay: 0.3, hue: 42 },
  { x: 50, y: 22, delay: 0.6, hue: 210 },
  { x: 22, y: 60, delay: 0.9, hue: 320 },
  { x: 78, y: 58, delay: 1.15, hue: 175 },
]
const SPARKS = 16

export default function Celebration({ amount, onDone }: { amount: number; onDone: () => void }) {
  // Auto-dismiss; tapping also dismisses.
  useEffect(() => {
    const t = setTimeout(onDone, 3200)
    return () => clearTimeout(t)
  }, [onDone])

  return (
    <div className="celebrate" onClick={onDone}>
      <div className="fireworks">
        {BURSTS.map((b, i) => (
          <div
            key={i}
            className="firework"
            style={{ left: `${b.x}%`, top: `${b.y}%` }}
          >
            {Array.from({ length: SPARKS }).map((_, s) => (
              <span
                key={s}
                className="spark"
                style={
                  {
                    '--angle': `${(360 / SPARKS) * s}deg`,
                    '--hue': `${b.hue + (s % 3) * 14}`,
                    animationDelay: `${b.delay}s`,
                  } as React.CSSProperties
                }
              />
            ))}
          </div>
        ))}
      </div>

      <div className="celebrate-text">
        <p className="celebrate-lead">אתה יכול לחסוך</p>
        <p className="celebrate-amount mono" dir="ltr">
          {formatPrice(amount)}!
        </p>
      </div>
    </div>
  )
}
