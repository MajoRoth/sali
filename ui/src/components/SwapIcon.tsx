import './SwapIcon.css'

/**
 * Two round arrows forming a circle — the "swap for a cheaper item" cycle.
 *
 * Wherever a number or a label is the result of swapping a product for a
 * cheaper equivalent, this icon marks it. That is the only thing telling a
 * shopper that a price is not for the cart they literally handed over, so it
 * has to look the same on every screen that shows one.
 */
export default function SwapIcon({ size = 14 }: { size?: number }) {
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
