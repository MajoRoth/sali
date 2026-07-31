import { useEffect } from 'react'
import { MapContainer, TileLayer, Marker, useMap } from 'react-leaflet'
import { divIcon } from 'leaflet'
import { useStores, useUserPosition } from '../lib/useStores'
import { chainColor, chainMonogram } from '../lib/chains'
import { FALLBACK_LOCATION } from '../lib/geo'
import type { BranchOnMap } from '../lib/types'

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
 * Decorative map behind the home content, showing the user and the real
 * supermarkets around them.
 *
 * Loading is decoupled from geolocation: the map renders immediately at a default
 * location (so tiles start downloading right away), then recenters when the real
 * position resolves. Pins are the genuine branch directory rather than scenery —
 * passing no receipt asks for the branches without pricing anything, which is
 * one cheap call. Non-interactive; the fade lives in CSS.
 */
export default function HomeMapBackground() {
  const userPos = useUserPosition()
  const center = userPos ?? FALLBACK_LOCATION
  const { branches } = useStores(null, center)

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
        {branches.slice(0, 40).map((b) => (
          <Marker key={b.id} position={[b.lat, b.lng]} icon={brandIcon(b)} interactive={false} />
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

function brandIcon(branch: BranchOnMap) {
  const inner = branch.logo
    ? `<img src="${branch.logo}" alt="">`
    : `<span class="home-pin-mono" style="background:${chainColor(branch.chain)}">${chainMonogram(
        branch.chain,
      )}</span>`
  return divIcon({
    className: 'home-marker-wrap',
    html: `<div class="home-pin">${inner}</div>`,
    iconSize: [36, 36],
    iconAnchor: [18, 18],
  })
}
