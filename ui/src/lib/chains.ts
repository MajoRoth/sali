/**
 * Brand identity for a chain the price database names.
 *
 * The database knows 58 chains; `public/static/logos/` holds six. So a logo is
 * a bonus, never a requirement — anything unrecognised gets a coloured monogram
 * built from its own name, which is stable, readable, and honest about being
 * generated. The alternative, a shared placeholder glyph, makes every unknown
 * chain look like the same shop.
 */

/** Substring probes against the chain name, most specific first. */
const LOGOS: [RegExp, string][] = [
  [/שופרסל|shufersal/i, '/static/logos/shufersal.svg'],
  [/רמי\s*לוי|ramilevy|rami\s*levy/i, '/static/logos/ramilevy.png'],
  [/קרפור|carrefour/i, '/static/logos/carrefour.png'],
  [/טיב\s*טעם|tiv\s*taam/i, '/static/logos/tivtaam.svg'],
  [/סופר\s*יודה|superyuda/i, '/static/logos/superyuda.png'],
  [/דור\s*אלון|dor\s*alon/i, '/static/logos/doralon.svg'],
  [/wolt/i, '/static/logos/wolt.png'],
]

export function chainLogo(chain: string): string | null {
  for (const [probe, logo] of LOGOS) if (probe.test(chain)) return logo
  return null
}

/** Up to two leading letters — the monogram shown when there's no logo. */
export function chainMonogram(chain: string): string {
  const words = chain
    .replace(/בע["׳']?מ|בעמ|\(.*?\)/g, ' ')
    .split(/[\s\-־]+/)
    .filter((w) => w.length > 0 && /[\p{L}]/u.test(w))
  if (words.length === 0) return '?'
  if (words.length === 1) return words[0].slice(0, 2)
  return words[0][0] + words[1][0]
}

/**
 * A stable colour per chain, so the same shop is the same colour on every
 * screen and two chains side by side are rarely the same hue.
 */
export function chainColor(chain: string): string {
  let hash = 0
  for (let i = 0; i < chain.length; i++) hash = (hash * 31 + chain.charCodeAt(i)) >>> 0
  return `hsl(${hash % 360} 58% 42%)`
}
