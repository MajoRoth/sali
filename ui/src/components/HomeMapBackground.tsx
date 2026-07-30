import { useEffect } from 'react'
import { MapContainer, TileLayer, Marker, useMap } from 'react-leaflet'
import { divIcon } from 'leaflet'
import { useStores, useUserPosition } from '../lib/useStores'
import { FALLBACK_LOCATION } from '../lib/geo'

/**
 * Keeps the view centered on `pos` (shifted low so the user + pins sit inside the
 * visible band). Re-runs when `pos` changes, so the map recenters once the real
 * geolocation arrives after first painting at the default.
 */
function Recenter({ pos }: { pos: [number, number] }) {
  const map = useMap()
  useEffect(() => {
    const z = map.getZoom()
    const p = map.project(pos, z)
    p.y -= map.getSize().y * 0.26
    map.setView(map.unproject(p, z), z, { animate: false })
  }, [map, pos])
  return null
}

/**
 * Decorative map behind the home content, showing the user + mock nearby stores.
 *
 * Loading is decoupled from geolocation: the map renders immediately at a default
 * location (so tiles start downloading right away), then recenters when the real
 * position resolves. Store pins are computed off the same current center, so they
 * appear without waiting either. Non-interactive; the fade lives in CSS.
 */
export default function HomeMapBackground() {
  const userPos = useUserPosition()
  const center = userPos ?? FALLBACK_LOCATION
  const { physical } = useStores(center)

  return (
    <div className="home-map" aria-hidden="true">
      <MapContainer
        center={center}
        zoom={14}
        className="home-map-leaflet"
        dragging={false}
        scrollWheelZoom={false}
        doubleClickZoom={false}
        touchZoom={false}
        boxZoom={false}
        keyboard={false}
        zoomControl={false}
        attributionControl={false}
      >
        <TileLayer url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png" />
        <Recenter pos={center} />
        <Marker position={center} icon={userIcon()} interactive={false} />
        {physical.map((s) => (
          <Marker key={s.id} position={[s.lat, s.lng]} icon={logoIcon(s.logo)} interactive={false} />
        ))}
      </MapContainer>
    </div>
  )
}

function userIcon() {
  return divIcon({
    className: 'home-marker-wrap',
    html: '<div class="home-user"><span class="home-user-pulse"></span></div>',
    iconSize: [16, 16],
    iconAnchor: [8, 8],
  })
}

function logoIcon(logo: string) {
  return divIcon({
    className: 'home-marker-wrap',
    html: `<div class="home-pin"><img src="${logo}" alt=""></div>`,
    iconSize: [36, 36],
    iconAnchor: [18, 18],
  })
}
