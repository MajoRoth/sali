import { chainColor, chainMonogram } from '../lib/chains'
import './ChainMark.css'

/**
 * A chain's logo, or a monogram when we don't have one.
 *
 * The price database names 58 chains and the app ships six logos, so the
 * fallback is the common case rather than the exception — it has to look
 * deliberate. A per-chain colour keeps two shops in a list from reading as the
 * same brand.
 */
export default function ChainMark({
  chain,
  logo,
  className = '',
}: {
  chain: string
  logo: string | null
  className?: string
}) {
  if (logo) {
    return (
      <span className={`chain-mark ${className}`}>
        <img src={logo} alt={chain} />
      </span>
    )
  }
  return (
    <span
      className={`chain-mark monogram ${className}`}
      style={{ background: chainColor(chain) }}
      aria-label={chain}
      title={chain}
    >
      {chainMonogram(chain)}
    </span>
  )
}
