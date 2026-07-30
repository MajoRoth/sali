import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { MapContainer, TileLayer, Marker, useMap } from 'react-leaflet'
import { divIcon } from 'leaflet'
import type { BranchOnMap, StoreOnMap, Supermarket } from '../lib/types'
import { formatDistance, formatPrice } from '../lib/geo'
import { useStores, useUserPosition } from '../lib/useStores'
import { useAuth } from '../lib/auth'
import { countOf, documentTotal, totalOf, useActiveReceipt } from '../lib/receipts'
import { chainColor, chainLogo, chainMonogram } from '../lib/chains'
import ChainMark from '../components/ChainMark'
import SavingBadge from '../components/SavingBadge'
import CrownIcon from '../components/CrownIcon'
import './MapScreen.css'

/** The origin store gets a map pin only when it's within this radius of the
 *  user — a receipt bought across town shouldn't zoom the map out to reach it. */
const ORIGIN_NEARBY_M = 2500
const ORIGIN_ID = '__origin__'

export default function MapScreen() {
  const navigate = useNavigate()
  const userPos = useUserPosition()

  const { user } = useAuth()
  const active = useActiveReceipt(user?.id ?? null)
  const { physical, online, cheapestBest, branches, response } = useStores(
    active.document,
    userPos,
  )
  const receiptTotal = documentTotal(active.document) ?? totalOf(active.items)
  const receiptItemCount = countOf(active.items)

  // The store the receipt was actually bought at, at the price actually paid.
  // The backend resolves it against the real branch directory, so it only
  // appears on the map when it could genuinely be placed.
  const resolved = response?.origin ?? null
  const origin = resolved
    ? {
        brand: resolved.chain,
        branch: resolved.branch,
        logo: chainLogo(resolved.chain),
        lat: resolved.location?.lat ?? null,
        lng: resolved.location?.lng ?? null,
        distanceM: resolved.distanceM,
        price: receiptTotal,
      }
    : null
  const originOnMap =
    origin !== null &&
    origin.lat !== null &&
    origin.lng !== null &&
    origin.distanceM !== null &&
    origin.distanceM <= ORIGIN_NEARBY_M

  // Priced stores own their pin; everything else nearby is drawn as a plain
  // branch dot, so the map is never empty just because pricing was.
  const pricedIds = new Set(physical.map((s) => s.id))
  const plainBranches = branches.filter((b) => !pricedIds.has(b.id))
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const cardRefs = useRef<Record<string, HTMLButtonElement | null>>({})

  const cheapestNearby = physical[0]

  // Pre-select the cheapest nearby store once located.
  useEffect(() => {
    if (cheapestNearby && !selectedId) setSelectedId(cheapestNearby.id)
  }, [cheapestNearby, selectedId])

  const selectedPos: [number, number] | null =
    selectedId === ORIGIN_ID && origin && origin.lat !== null && origin.lng !== null
      ? [origin.lat, origin.lng]
      : (() => {
          const s = physical.find((p) => p.id === selectedId)
          return s ? [s.lat, s.lng] : null
        })()

  const selectStore = (id: string, scrollCard: boolean) => {
    setSelectedId(id)
    if (scrollCard) {
      cardRefs.current[id]?.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' })
    }
  }

  const selectOrigin = () => {
    setSelectedId(ORIGIN_ID)
    cardRefs.current[ORIGIN_ID]?.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' })
  }

  if (!userPos) {
    return (
      <div className="map-screen locating">
        <div className="spinner-sm" />
        <p>מאתרים אתכם…</p>
      </div>
    )
  }

  return (
    <div className="map-screen">
      <MapContainer
        center={userPos}
        zoom={15}
        className="map"
        zoomControl={false}
        attributionControl={false}
      >
        <TileLayer url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png" />
        <FlyTo target={selectedPos} />

        <Marker position={userPos} icon={userIcon()} interactive={false} />

        {/* Real branches we could not price — the map's honest floor. */}
        {plainBranches.map((b) => (
          <Marker key={b.id} position={[b.lat, b.lng]} icon={branchIcon(b)} />
        ))}

        {physical.map((s) => (
          <Marker
            key={s.id}
            position={[s.lat, s.lng]}
            icon={storeIcon(s, s.id === selectedId, s.bestPrice === cheapestBest)}
            eventHandlers={{ click: () => selectStore(s.id, true) }}
          />
        ))}

        {/* Origin pin only when it's genuinely nearby. */}
        {originOnMap && origin && origin.lat !== null && origin.lng !== null && (
          <Marker
            position={[origin.lat, origin.lng]}
            icon={originIcon(origin.brand, origin.logo, origin.price, selectedId === ORIGIN_ID)}
            eventHandlers={{ click: () => selectOrigin() }}
          />
        )}
      </MapContainer>

      <header className="map-topbar">
        <button className="back-btn" onClick={() => navigate('/results')} aria-label="חזרה לרשימה">
          →
        </button>
        <div className="receipt-chip">
          <span className="chip-count">{receiptItemCount} מוצרים</span>
          <span className="chip-sep">·</span>
          <span>{active.name ?? 'עגלה סרוקה'}</span>
        </div>
      </header>

      <section className="store-sheet">
        <div className="store-cards">
          {origin && (
            <button
              ref={(el) => {
                cardRefs.current[ORIGIN_ID] = el
              }}
              className={`store-card origin ${selectedId === ORIGIN_ID ? 'selected' : ''}`}
              onClick={selectOrigin}
            >
              <span className="origin-tag">מקור</span>
              <div className="card-top">
                <ChainMark chain={origin.brand} logo={origin.logo} className="brand-logo" />
                <div className="brand-info">
                  <span className="brand-name">{origin.brand}</span>
                  <span className="brand-distance">
                    {[origin.branch, origin.distanceM !== null ? formatDistance(origin.distanceM) : null]
                      .filter(Boolean)
                      .join(' · ')}
                  </span>
                </div>
              </div>
              <div className="card-price mono" dir="ltr">
                {formatPrice(origin.price)}
              </div>
              <div className="card-save-note">קניתם כאן</div>
            </button>
          )}

          {physical.map((s) => (
            <StoreCard
              key={s.id}
              ref={(el) => {
                cardRefs.current[s.id] = el
              }}
              store={s}
              selected={s.id === selectedId}
              best={s.bestPrice === cheapestBest}
              receiptTotal={receiptTotal}
              onClick={() => selectStore(s.id, false)}
            />
          ))}
        </div>

        {/* No priced carts: name the branches that are genuinely there rather
            than showing an empty sheet, which reads as "nowhere to shop". */}
        {physical.length === 0 && plainBranches.length > 0 && (
          <>
            <p className="sheet-subhead">
              {plainBranches.length} סניפים בסביבה · אין כרגע מחירים להשוואה
            </p>
            <div className="store-cards">
              {plainBranches.slice(0, 20).map((b) => (
                <div key={b.id} className="store-card branch-only">
                  <div className="card-top">
                    <ChainMark chain={b.chain} logo={b.logo} className="brand-logo" />
                    <div className="brand-info">
                      <span className="brand-name">{b.chain}</span>
                      <span className="brand-distance">
                        {b.branch ? `${b.branch} · ` : ''}
                        {formatDistance(b.distanceM)}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {online.length > 0 && (
          <>
            <p className="sheet-subhead">
              <span className="online-dot" />
              משלוח עד הבית
            </p>
            <div className="store-cards">
              {online.map((s) => (
                <StoreCard
                  key={s.id}
                  store={s}
                  selected={false}
                  best={s.bestPrice === cheapestBest}
                  receiptTotal={receiptTotal}
                />
              ))}
            </div>
          </>
        )}
      </section>
    </div>
  )
}

interface CardProps {
  store: Supermarket
  selected: boolean
  best: boolean
  receiptTotal: number
  onClick?: () => void
  ref?: React.Ref<HTMLButtonElement>
}

function StoreCard({ store, selected, best, receiptTotal, onClick, ref }: CardProps) {
  const diff = receiptTotal - store.bestPrice
  const sub = store.online
    ? store.deliveryFee === 0
      ? 'משלוח חינם'
      : `משלוח ${formatPrice(store.deliveryFee)}`
    : formatDistance((store as StoreOnMap).distanceM)

  return (
    <button
      ref={ref}
      className={`store-card ${selected ? 'selected' : ''} ${store.online ? 'online' : ''}`}
      onClick={onClick}
    >
      {best && (
        <span className="best-crown" aria-label="הכי זול">
          <CrownIcon />
        </span>
      )}
      <div className="card-top">
        <div className="store-logo-col">
          <ChainMark chain={store.brand} logo={store.logo} className="brand-logo" />
          {store.online && <span className="online-tag">אונליין</span>}
        </div>
        <div className="brand-info">
          <span className="brand-name">{store.brand}</span>
          <span className="brand-distance">{store.branch ? `${store.branch} · ${sub}` : sub}</span>
        </div>
      </div>

      <SavingBadge amount={Math.abs(diff)} save={diff > 0} size="md" />
      <span className="price-xy mono" dir="ltr">
        {formatPrice(store.cartTotal)} / {formatPrice(store.bestPrice)}
      </span>
    </button>
  )
}

/** Pans the map whenever the selected store changes. */
function FlyTo({ target }: { target: [number, number] | null }) {
  const map = useMap()
  useEffect(() => {
    if (target) map.flyTo(target, map.getZoom(), { duration: 0.6 })
  }, [target, map])
  return null
}

function userIcon() {
  return divIcon({
    className: 'user-marker-wrap',
    html: '<div class="user-marker"><div class="user-pulse"></div></div>',
    iconSize: [18, 18],
    iconAnchor: [9, 9],
  })
}

const CROWN_SVG =
  '<svg viewBox="0 0 24 24" fill="#ffffff" width="12" height="12"><path d="M3 8l3.5 3L12 5l5.5 6L21 8l-1.6 9.2a1 1 0 0 1-1 .8H5.6a1 1 0 0 1-1-.8L3 8z"/></svg>'

/** Leaflet pins are raw HTML, so chain names are escaped by hand here. */
function escapeHtml(text: string): string {
  return text.replace(
    /[&<>"']/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!,
  )
}

/** The logo, or the same monogram the React `ChainMark` renders. */
function markHtml(chain: string, logo: string | null): string {
  if (logo) return `<span class="pin-logo"><img src="${escapeHtml(logo)}" alt=""></span>`
  return `<span class="pin-logo mono" style="background:${chainColor(chain)}">${escapeHtml(
    chainMonogram(chain),
  )}</span>`
}

function storeIcon(s: StoreOnMap, selected: boolean, best: boolean) {
  return divIcon({
    className: 'store-marker-wrap',
    html: `
      <div class="store-pin ${selected ? 'selected' : ''} ${best ? 'best' : ''}">
        ${best ? `<span class="pin-crown">${CROWN_SVG}</span>` : ''}
        ${markHtml(s.brand, s.logo)}
        <span class="pin-price">${formatPrice(s.bestPrice)}</span>
      </div>`,
    iconSize: [0, 0],
    iconAnchor: [50, 22],
  })
}

/** A branch with no price: present on the map, but making no claim. */
function branchIcon(b: BranchOnMap) {
  return divIcon({
    className: 'store-marker-wrap',
    html: `<div class="branch-pin" title="${escapeHtml(`${b.chain} · ${b.branch}`)}">
        ${markHtml(b.chain, b.logo)}
      </div>`,
    iconSize: [0, 0],
    iconAnchor: [11, 11],
  })
}

function originIcon(chain: string, logo: string | null, price: number, selected: boolean) {
  return divIcon({
    className: 'store-marker-wrap',
    html: `
      <div class="store-pin origin ${selected ? 'selected' : ''}">
        <span class="pin-best origin">מקור</span>
        ${markHtml(chain, logo)}
        <span class="pin-price">${formatPrice(price)}</span>
      </div>`,
    iconSize: [0, 0],
    iconAnchor: [50, 22],
  })
}
