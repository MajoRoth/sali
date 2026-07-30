import { formatPrice } from '../lib/geo'
import './SavingBadge.css'

/**
 * The headline savings figure. Saving money → blue with a downward arrow;
 * paying more → red with an upward arrow. `amount` is the absolute difference.
 */
export default function SavingBadge({
  amount,
  save,
  size = 'md',
  label,
}: {
  amount: number
  save: boolean
  size?: 'sm' | 'md' | 'lg'
  label?: string
}) {
  return (
    <span className={`saving-badge ${save ? 'save' : 'lose'} size-${size}`}>
      <span className="mono">{formatPrice(amount)}</span>
      <TrendArrow down={save} />
      {label && <span className="saving-label">{label}</span>}
    </span>
  )
}

function TrendArrow({ down }: { down: boolean }) {
  return down ? (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true" className="trend-arrow">
      <path d="M12 5v13M6 12l6 6 6-6" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ) : (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true" className="trend-arrow">
      <path d="M12 19V6M6 12l6-6 6 6" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}
