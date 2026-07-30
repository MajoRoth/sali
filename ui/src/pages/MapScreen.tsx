import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { MapContainer, TileLayer, Marker, useMap } from 'react-leaflet'
import { divIcon } from 'leaflet'
import type { StoreOnMap, Supermarket } from '../lib/types'
import { formatDistance, formatPrice } from '../lib/geo'
import { receiptItemCount, receiptTotal, useStores, useUserPosition } from '../lib/useStores'
import './MapScreen.css'

export default function MapScreen() {
  const navigate = useNavigate()
  const userPos = useUserPosition()
  const { physical, online, cheapestBest } = useStores(userPos)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const cardRefs = useRef<Record<string, HTMLButtonElement | null>>({})

  const cheapestNearby = physical[0]

  // Pre-select the cheapest nearby store once located.
  useEffect(() => {
    if (cheapestNearby && !selectedId) setSelectedId(cheapestNearby.id)
  }, [cheapestNearby, selectedId])

  const selected = physical.find((s) => s.id === selectedId)

  const selectStore = (id: string, scrollCard: boolean) => {
    setSelectedId(id)
    if (scrollCard) {
      cardRefs.current[id]?.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' })
    }
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
        <FlyTo target={selected ? [selected.lat, selected.lng] : null} />

        <Marker position={userPos} icon={userIcon()} interactive={false} />

        {physical.map((s) => (
          <Marker
            key={s.id}
            position={[s.lat, s.lng]}
            icon={storeIcon(s, s.id === selectedId, s.bestPrice === cheapestBest)}
            eventHandlers={{ click: () => selectStore(s.id, true) }}
          />
        ))}
      </MapContainer>

      <header className="map-topbar">
        <button className="back-btn" onClick={() => navigate('/results')} aria-label="חזרה לרשימה">
          →
        </button>
        <div className="receipt-chip">
          <span className="chip-count">{receiptItemCount} מוצרים</span>
          <span className="chip-sep">·</span>
          <span>עגלה סרוקה</span>
        </div>
      </header>

      <section className="store-sheet">
        <p className="sheet-hint">
          המחיר הטוב ביותר — חיסכון של עד{' '}
          <strong className="mono">{formatPrice(receiptTotal - cheapestBest)}</strong>
        </p>

        <div className="store-cards">
          {physical.map((s) => (
            <StoreCard
              key={s.id}
              ref={(el) => {
                cardRefs.current[s.id] = el
              }}
              store={s}
              sub={formatDistance(s.distanceM)}
              selected={s.id === selectedId}
              best={s.bestPrice === cheapestBest}
              onClick={() => selectStore(s.id, false)}
            />
          ))}
        </div>

        <p className="sheet-subhead">
          <span className="online-dot" />
          משלוח עד הבית
        </p>
        <div className="store-cards">
          {online.map((s) => (
            <div key={s.id} className="online-card">
              <span className="brand-logo">
                <img src={s.logo} alt={s.brand} />
              </span>
              <div className="brand-info">
                <span className="brand-name">{s.brand}</span>
                <span className="brand-distance">
                  {s.deliveryFee === 0 ? 'משלוח חינם' : `משלוח ${formatPrice(s.deliveryFee)}`}
                </span>
              </div>
              <div className="online-price">
                <div className="price-stack">
                  <span className="mono" dir="ltr">
                    {formatPrice(s.bestPrice)}
                  </span>
                  <span className="price-true">
                    אותה עגלה{' '}
                    <span className="mono" dir="ltr">
                      {formatPrice(s.cartTotal)}
                    </span>
                  </span>
                </div>
                {s.bestPrice === cheapestBest && <span className="best-tag">הכי זול</span>}
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}

interface CardProps {
  store: Supermarket
  sub: string
  selected: boolean
  best: boolean
  onClick?: () => void
  ref?: React.Ref<HTMLButtonElement>
}

function StoreCard({ store, sub, selected, best, onClick, ref }: CardProps) {
  const saving = receiptTotal - store.bestPrice

  return (
    <button ref={ref} className={`store-card ${selected ? 'selected' : ''}`} onClick={onClick}>
      <div className="card-top">
        <span className="brand-logo">
          <img src={store.logo} alt={store.brand} />
        </span>
        <div className="brand-info">
          <span className="brand-name">{store.brand}</span>
          <span className="brand-distance">{sub}</span>
        </div>
        {best && <span className="best-tag">הכי זול</span>}
      </div>

      <div className="card-price mono" dir="ltr">
        {formatPrice(store.bestPrice)}
      </div>
      <div className="price-true">
        אותה עגלה{' '}
        <span className="mono" dir="ltr">
          {formatPrice(store.cartTotal)}
        </span>
      </div>
      <div className="card-save">
        {saving > 0 ? (
          <>
            חוסכים <span className="mono">{formatPrice(saving)}</span>
          </>
        ) : (
          <span className="save-none">יקר מהקבלה</span>
        )}
      </div>
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

function storeIcon(s: StoreOnMap, selected: boolean, best: boolean) {
  return divIcon({
    className: 'store-marker-wrap',
    html: `
      <div class="store-pin ${selected ? 'selected' : ''} ${best ? 'best' : ''}">
        ${best ? '<span class="pin-best">הכי זול</span>' : ''}
        <span class="pin-logo"><img src="${s.logo}" alt=""></span>
        <span class="pin-prices">
          <span class="pin-price">${formatPrice(s.bestPrice)}</span>
          <span class="pin-true">${formatPrice(s.cartTotal)}</span>
        </span>
      </div>`,
    iconSize: [0, 0],
    iconAnchor: [55, 22],
  })
}
