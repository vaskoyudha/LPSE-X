import React, { useState } from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { RISK_BG } from '../types/models'

// ============================================================================
// Demo province data — real data would come from POST /api/predict aggregation
// ============================================================================

interface ProvinceRisk {
  name: string
  lat: number
  lng: number
  kritis: number
  tinggi: number
  pantauan: number
  aman: number
}

const DEMO_PROVINCES: ProvinceRisk[] = [
  { name: 'DKI Jakarta',    lat: -6.2088,  lng: 106.8456, kritis: 12, tinggi: 34, pantauan: 48, aman: 106 },
  { name: 'Jawa Barat',     lat: -6.9175,  lng: 107.6191, kritis: 8,  tinggi: 21, pantauan: 37, aman: 89  },
  { name: 'Jawa Tengah',    lat: -7.1509,  lng: 110.1403, kritis: 5,  tinggi: 18, pantauan: 29, aman: 74  },
  { name: 'Yogyakarta',     lat: -7.7956,  lng: 110.3695, kritis: 3,  tinggi: 11, pantauan: 17, aman: 52  },
  { name: 'Jawa Timur',     lat: -7.5360,  lng: 112.2384, kritis: 9,  tinggi: 29, pantauan: 41, aman: 95  },
  { name: 'Banten',         lat: -6.4058,  lng: 106.0640, kritis: 4,  tinggi: 13, pantauan: 22, aman: 61  },
  { name: 'Sumatera Utara', lat: 3.5952,   lng: 98.6722,  kritis: 6,  tinggi: 17, pantauan: 31, aman: 72  },
  { name: 'Sulawesi Selatan', lat: -5.1477, lng: 119.4327, kritis: 7, tinggi: 20, pantauan: 28, aman: 63 },
  { name: 'Kalimantan Timur', lat: 1.6407,  lng: 116.4194, kritis: 5, tinggi: 14, pantauan: 19, aman: 58 },
  { name: 'Bali',           lat: -8.4095,  lng: 115.1889, kritis: 2,  tinggi: 8,  pantauan: 14, aman: 48  },
]

function getRiskColor(prov: ProvinceRisk): string {
  const total = prov.kritis + prov.tinggi + prov.pantauan + prov.aman
  const criticalRate = (prov.kritis + prov.tinggi) / total
  if (criticalRate >= 0.25) return '#dc2626'   // red-600
  if (criticalRate >= 0.15) return '#f97316'   // orange-500
  if (criticalRate >= 0.08) return '#f59e0b'   // amber-400
  return '#22c55e'                              // green-500
}

function getRiskLabel(prov: ProvinceRisk): string {
  const total = prov.kritis + prov.tinggi + prov.pantauan + prov.aman
  const criticalRate = (prov.kritis + prov.tinggi) / total
  if (criticalRate >= 0.25) return 'Risiko Kritis'
  if (criticalRate >= 0.15) return 'Risiko Tinggi'
  if (criticalRate >= 0.08) return 'Perlu Pantauan'
  return 'Aman'
}

function getRadius(prov: ProvinceRisk): number {
  const total = prov.kritis + prov.tinggi + prov.pantauan + prov.aman
  return Math.max(12, Math.min(34, Math.sqrt(total) * 2.2))
}

// ============================================================================
// Statistics card
// ============================================================================

function StatCard({ label, value, sub, color }: {
  label: string
  value: number | string
  sub?: string
  color?: string
}): React.ReactElement {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 text-center">
      <p className="text-xs text-slate-500 mb-1 font-medium uppercase tracking-wide">{label}</p>
      <p className={`text-2xl font-bold ${color ?? 'text-slate-700'}`}>{value}</p>
      {sub && <p className="text-xs text-slate-400 mt-1">{sub}</p>}
    </div>
  )
}

// ============================================================================
// Province detail table
// ============================================================================

function ProvinceTable({ provinces, selectedProvince, onSelect }: {
  provinces: ProvinceRisk[]
  selectedProvince: string | null
  onSelect: (name: string | null) => void
}): React.ReactElement {
  const sorted = [...provinces].sort((a, b) => (b.kritis + b.tinggi) - (a.kritis + a.tinggi))
  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-200 bg-slate-50">
        <h3 className="text-sm font-semibold text-slate-700">Daftar Provinsi</h3>
      </div>
      <div className="overflow-y-auto" style={{ maxHeight: 340 }}>
        <table className="text-xs w-full">
          <thead className="sticky top-0 bg-slate-100">
            <tr>
              <th className="px-3 py-2 text-left text-slate-500 font-medium">Provinsi</th>
              <th className="px-3 py-2 text-right text-red-600 font-medium">Kritis</th>
              <th className="px-3 py-2 text-right text-orange-500 font-medium">Tinggi</th>
              <th className="px-3 py-2 text-right text-amber-500 font-medium">Pantauan</th>
              <th className="px-3 py-2 text-right text-green-600 font-medium">Aman</th>
              <th className="px-3 py-2 text-right text-slate-500 font-medium">Total</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {sorted.map((p) => {
              const total = p.kritis + p.tinggi + p.pantauan + p.aman
              const isSelected = selectedProvince === p.name
              return (
                <tr
                  key={p.name}
                  onClick={() => onSelect(isSelected ? null : p.name)}
                  className={`cursor-pointer transition-colors ${
                    isSelected ? 'bg-blue-50' : 'hover:bg-slate-50'
                  }`}
                >
                  <td className="px-3 py-2">
                    <div className="flex items-center gap-2">
                      <span
                        className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                        style={{ backgroundColor: getRiskColor(p) }}
                      />
                      <span className="font-medium text-slate-700">{p.name}</span>
                    </div>
                  </td>
                  <td className="px-3 py-2 text-right text-red-600 font-medium">{p.kritis}</td>
                  <td className="px-3 py-2 text-right text-orange-500 font-medium">{p.tinggi}</td>
                  <td className="px-3 py-2 text-right text-amber-600 font-medium">{p.pantauan}</td>
                  <td className="px-3 py-2 text-right text-green-600 font-medium">{p.aman}</td>
                  <td className="px-3 py-2 text-right text-slate-500">{total}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ============================================================================
// Main RiskMap page
// ============================================================================

export function RiskMap(): React.ReactElement {
  const [selectedProvince, setSelectedProvince] = useState<string | null>(null)

  // Aggregate totals
  const totalKritis = DEMO_PROVINCES.reduce((s, p) => s + p.kritis, 0)
  const totalTinggi = DEMO_PROVINCES.reduce((s, p) => s + p.tinggi, 0)
  const totalPantauan = DEMO_PROVINCES.reduce((s, p) => s + p.pantauan, 0)
  const totalAman = DEMO_PROVINCES.reduce((s, p) => s + p.aman, 0)
  const totalAll = totalKritis + totalTinggi + totalPantauan + totalAman

  const selectedData = selectedProvince ? DEMO_PROVINCES.find((p) => p.name === selectedProvince) : null
  const riskLabel = selectedData ? getRiskLabel(selectedData) : null

  return (
    <div className="space-y-4">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Peta Risiko Geografis</h1>
        <p className="text-sm text-slate-500 mt-1">
          Distribusi risiko pengadaan per provinsi — data demo (jalankan pipeline untuk data nyata)
        </p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-5 gap-3">
        <StatCard label="Total Tender" value={totalAll} color="text-slate-700" />
        <StatCard label="Risiko Kritis" value={totalKritis} color="text-red-600"
          sub={`${((totalKritis / totalAll) * 100).toFixed(1)}%`} />
        <StatCard label="Risiko Tinggi" value={totalTinggi} color="text-orange-500"
          sub={`${((totalTinggi / totalAll) * 100).toFixed(1)}%`} />
        <StatCard label="Perlu Pantauan" value={totalPantauan} color="text-amber-600"
          sub={`${((totalPantauan / totalAll) * 100).toFixed(1)}%`} />
        <StatCard label="Aman" value={totalAman} color="text-green-600"
          sub={`${((totalAman / totalAll) * 100).toFixed(1)}%`} />
      </div>

      {/* Map + table */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        {/* Map */}
        <div className="xl:col-span-2 rounded-xl overflow-hidden border border-gray-200 shadow-sm" style={{ height: 460 }}>
          <MapContainer
            center={[-2.5, 117.8]}
            zoom={5}
            style={{ height: '100%', width: '100%' }}
            scrollWheelZoom
          >
            {/* OpenStreetMap tiles — offline note: would use local tile server in production */}
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            {DEMO_PROVINCES.map((prov) => {
              const color = getRiskColor(prov)
              const radius = getRadius(prov)
              const total = prov.kritis + prov.tinggi + prov.pantauan + prov.aman
              const rLabel = getRiskLabel(prov)
              const bgClass = RISK_BG[rLabel] ?? 'bg-gray-100 text-gray-700'
              return (
                <CircleMarker
                  key={prov.name}
                  center={[prov.lat, prov.lng]}
                  radius={radius}
                  pathOptions={{
                    color,
                    fillColor: color,
                    fillOpacity: selectedProvince === prov.name ? 0.85 : 0.55,
                    weight: selectedProvince === prov.name ? 3 : 1.5,
                  }}
                  eventHandlers={{
                    click: () => setSelectedProvince(
                      selectedProvince === prov.name ? null : prov.name
                    ),
                  }}
                >
                  <Popup>
                    <div className="text-sm font-medium">{prov.name}</div>
                    <span className={`inline-block text-xs px-2 py-0.5 rounded font-medium mt-1 ${bgClass}`}>
                      {rLabel}
                    </span>
                    <div className="mt-2 text-xs space-y-0.5">
                      <div>🔴 Kritis: <strong>{prov.kritis}</strong></div>
                      <div>🟠 Tinggi: <strong>{prov.tinggi}</strong></div>
                      <div>🟡 Pantauan: <strong>{prov.pantauan}</strong></div>
                      <div>🟢 Aman: <strong>{prov.aman}</strong></div>
                      <div className="border-t pt-1 mt-1">Total: <strong>{total}</strong></div>
                    </div>
                  </Popup>
                </CircleMarker>
              )
            })}
          </MapContainer>
        </div>

        {/* Sidebar: table + selected detail */}
        <div className="xl:col-span-1 space-y-3">
          <ProvinceTable
            provinces={DEMO_PROVINCES}
            selectedProvince={selectedProvince}
            onSelect={setSelectedProvince}
          />

          {/* Selected detail card */}
          {selectedData && riskLabel && (
            <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-slate-700">{selectedData.name}</h3>
                <span className={`text-xs px-2 py-1 rounded-full font-semibold ${RISK_BG[riskLabel] ?? 'bg-gray-100 text-gray-700'}`}>
                  {riskLabel}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {[
                  { label: 'Kritis', value: selectedData.kritis, cls: 'text-red-600' },
                  { label: 'Tinggi', value: selectedData.tinggi, cls: 'text-orange-500' },
                  { label: 'Pantauan', value: selectedData.pantauan, cls: 'text-amber-600' },
                  { label: 'Aman', value: selectedData.aman, cls: 'text-green-600' },
                ].map(({ label, value, cls }) => (
                  <div key={label} className="bg-slate-50 rounded-lg p-2 text-center">
                    <p className="text-xs text-slate-500">{label}</p>
                    <p className={`text-lg font-bold ${cls}`}>{value}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Legend */}
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
          Legenda Warna Marker
        </p>
        <div className="flex flex-wrap gap-5 text-xs text-slate-600">
          <div className="flex items-center gap-2">
            <span className="w-4 h-4 rounded-full bg-red-600 opacity-70 border-2 border-red-600" />
            Risiko Kritis (≥25% tender bermasalah)
          </div>
          <div className="flex items-center gap-2">
            <span className="w-4 h-4 rounded-full bg-orange-500 opacity-70 border-2 border-orange-500" />
            Risiko Tinggi (15–25%)
          </div>
          <div className="flex items-center gap-2">
            <span className="w-4 h-4 rounded-full bg-amber-400 opacity-70 border-2 border-amber-400" />
            Perlu Pantauan (8–15%)
          </div>
          <div className="flex items-center gap-2">
            <span className="w-4 h-4 rounded-full bg-green-500 opacity-70 border-2 border-green-500" />
            Aman (&lt;8%)
          </div>
          <div className="flex items-center gap-2 ml-4 pl-4 border-l border-gray-200">
            <span className="text-slate-400">Ukuran marker</span>
            → volume tender provinsi
          </div>
        </div>
      </div>
    </div>
  )
}
