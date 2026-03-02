import React, { useState, useEffect } from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { RISK_BG } from '../types/models'
import { listTenders } from '../api/client'
import type { TenderWithRisk } from '../types/models'

// ============================================================================
// Region coordinate lookup — covers all buyer_names in the DB
// ============================================================================

const REGION_COORDS: Record<string, [number, number]> = {
  // Provinsi
  'Provinsi Aceh': [4.6951, 96.7494],
  'Provinsi Bali': [-8.4095, 115.1889],
  'Provinsi Banten': [-6.4058, 106.0640],
  'Provinsi D. I. Yogyakarta': [-7.7956, 110.3695],
  'Provinsi DKI Jakarta': [-6.2088, 106.8456],
  'Provinsi Jawa Barat': [-6.9175, 107.6191],
  'Provinsi Jawa Tengah': [-7.1509, 110.1403],
  'Provinsi Jawa Timur': [-7.5360, 112.2384],
  'Provinsi Kalimantan Barat': [0.1333, 111.0872],
  'Provinsi Kalimantan Selatan': [-3.0926, 115.2838],
  'Provinsi Kalimantan Timur': [1.6407, 116.4194],
  'Provinsi Kalimantan Utara': [3.0731, 116.0413],
  'Provinsi Kepulauan Riau': [3.9457, 108.1429],
  'Provinsi Lampung': [-4.5585, 105.4068],
  'Provinsi Maluku': [-3.2385, 130.1453],
  'Provinsi Maluku Utara': [1.5709, 127.8088],
  'Provinsi Nusa Tenggara Barat': [-8.6529, 117.3616],
  'Provinsi Nusa Tenggara Timur': [-8.6574, 121.0794],
  'Provinsi Papua': [-4.2699, 138.0804],
  'Provinsi Papua Pegunungan': [-4.5000, 138.5000],
  'Provinsi Papua Selatan': [-6.5000, 140.0000],
  'Provinsi Papua Tengah': [-3.5000, 136.5000],
  'Provinsi Riau': [0.2933, 101.7068],
  'Provinsi Sulawesi Barat': [-2.8441, 119.2321],
  'Provinsi Sulawesi Selatan': [-5.1477, 119.4327],
  'Provinsi Sulawesi Tengah': [-1.4300, 121.4456],
  'Provinsi Sulawesi Tenggara': [-4.1449, 122.1746],
  'Provinsi Sulawesi Utara': [0.6246, 123.9750],
  'Provinsi Sumatera Barat': [-0.7399, 100.8000],
  'Provinsi Sumatera Selatan': [-3.3194, 103.9144],
  'Provinsi Sumatera Utara': [3.5952, 98.6722],
  // Major Kota
  'Kota Balikpapan': [-1.2675, 116.8289],
  'Kota Banda Aceh': [5.5483, 95.3238],
  'Kota Bandar Lampung': [-5.4292, 105.2613],
  'Kota Banjar': [-7.3706, 108.5403],
  'Kota Banjarbaru': [-3.4416, 114.8341],
  'Kota Banjarmasin': [-3.3186, 114.5944],
  'Kota Batam': [1.0456, 104.0305],
  'Kota Bau-Bau': [-5.4667, 122.6167],
  'Kota Bengkulu': [-3.8004, 102.2655],
  'Kota Bima': [-8.4600, 118.7200],
  'Kota Blitar': [-8.0953, 112.1608],
  'Kota Bukit Tinggi': [-0.3051, 100.3691],
  'Kota Cilegon': [-6.0024, 106.0052],
  'Kota Cimahi': [-6.8720, 107.5420],
  'Kota Cirebon': [-6.7063, 108.5570],
  'Kota Denpasar': [-8.6705, 115.2126],
  'Kota Depok': [-6.4025, 106.7942],
  'Kota Dumai': [1.6711, 101.4472],
  'Kota Gorontalo': [0.5435, 123.0568],
  'Kota Gunungsitoli': [1.2817, 97.6227],
  'Kota Jayapura': [-2.5916, 140.6690],
  'Kota Kediri': [-7.8166, 112.0114],
  'Kota Kotamobagu': [0.7282, 124.3167],
  'Kota Kupang': [-10.1771, 123.6070],
  'Kota Langsa': [4.4683, 97.9683],
  'Kota Lhokseumawe': [5.1801, 97.1502],
  'Kota Lubuklinggau': [-3.2949, 102.8621],
  'Kota Madiun': [-7.6298, 111.5239],
  'Kota Magelang': [-7.4705, 110.2179],
  'Kota Makassar': [-5.1477, 119.4327],
  'Kota Malang': [-7.9839, 112.6214],
  'Kota Manado': [1.4748, 124.8421],
  'Kota Mataram': [-8.5833, 116.1167],
  'Kota Medan': [3.5952, 98.6722],
  'Kota Mojokerto': [-7.4722, 112.4338],
  'Kota Padang': [-0.9471, 100.4172],
  'Kota Padang Panjang': [-0.4602, 100.4102],
  'Kota Padang Sidempuan': [1.3820, 99.2722],
  'Kota Pagar Alam': [-4.0179, 103.2549],
  'Kota Palangka Raya': [-2.2136, 113.9108],
  'Kota Palembang': [-2.9761, 104.7754],
  'Kota Palopo': [-3.0049, 120.1973],
  'Kota Palu': [-0.9003, 119.8779],
  'Kota Pangkal Pinang': [-2.1316, 106.1170],
  'Kota Pasuruan': [-7.6453, 112.9075],
  'Kota Payakumbuh': [-0.2271, 100.6319],
  'Kota Pekalongan': [-6.8886, 109.6753],
  'Kota Pekanbaru': [0.5333, 101.4500],
  'Kota Pematang Siantar': [2.9595, 99.0687],
  'Kota Prabumulih': [-3.4321, 104.2293],
  'Kota Probolinggo': [-7.7543, 113.2159],
  'Kota Sabang': [5.8933, 95.3214],
  'Kota Salatiga': [-7.3307, 110.5078],
  'Kota Samarinda': [-0.5016, 117.1537],
  'Kota Sawahlunto': [-0.6787, 100.7791],
  'Kota Semarang': [-6.9932, 110.4203],
  'Kota Serang': [-6.1200, 106.1503],
  'Kota Sibolga': [1.7427, 98.7792],
  'Kota Singkawang': [0.9077, 108.9762],
  'Kota Solok': [-0.7932, 100.6558],
  'Kota Sorong': [-0.8761, 131.2508],
  'Kota Subulussalam': [2.6500, 98.0000],
  'Kota Sukabumi': [-6.9215, 106.9275],
  'Kota Sungai Penuh': [-2.0617, 101.3960],
  'Kota Surabaya': [-7.2575, 112.7521],
  'Kota Surakarta': [-7.5560, 110.8318],
  'Kota Tangerang': [-6.1783, 106.6319],
  'Kota Tangerang Selatan': [-6.2886, 106.7138],
  'Kota Tanjung Balai': [2.9665, 99.8000],
  'Kota Tanjung Pinang': [0.9167, 104.4500],
  'Kota Tarakan': [3.3000, 117.6333],
  'Kota Tasikmalaya': [-7.3506, 108.2207],
  'Kota Tebing Tinggi': [3.3282, 99.1627],
  'Kota Tegal': [-6.8694, 109.1402],
  'Kota Ternate': [0.7833, 127.3833],
  'Kota Tomohon': [1.3247, 124.8300],
  'Kota Tual': [-5.6667, 132.7500],
  'Kota Yogyakarta': [-7.7972, 110.3688],
}

// Province → center coords for Kabupaten grouping
const PROVINCE_CENTERS: Record<string, [number, number]> = {
  Aceh: [4.6951, 96.7494],
  'Sumatera Utara': [2.5000, 99.0000],
  'Sumatera Barat': [-0.7399, 100.8000],
  Riau: [0.2933, 101.7068],
  Jambi: [-1.6101, 103.6131],
  'Sumatera Selatan': [-3.3194, 103.9144],
  Bengkulu: [-3.8004, 102.2655],
  Lampung: [-4.5585, 105.4068],
  'Kepulauan Bangka Belitung': [-2.7410, 106.4406],
  'Kepulauan Riau': [3.9457, 108.1429],
  'DKI Jakarta': [-6.2088, 106.8456],
  'Jawa Barat': [-6.9175, 107.6191],
  'Jawa Tengah': [-7.1509, 110.1403],
  'D.I. Yogyakarta': [-7.7956, 110.3695],
  'Jawa Timur': [-7.5360, 112.2384],
  Banten: [-6.4058, 106.0640],
  Bali: [-8.4095, 115.1889],
  'Nusa Tenggara Barat': [-8.6529, 117.3616],
  'Nusa Tenggara Timur': [-8.6574, 121.0794],
  'Kalimantan Barat': [0.1333, 111.0872],
  'Kalimantan Tengah': [-1.6815, 113.3824],
  'Kalimantan Selatan': [-3.0926, 115.2838],
  'Kalimantan Timur': [1.6407, 116.4194],
  'Kalimantan Utara': [3.0731, 116.0413],
  'Sulawesi Utara': [0.6246, 123.9750],
  'Sulawesi Tengah': [-1.4300, 121.4456],
  'Sulawesi Selatan': [-5.1477, 119.4327],
  'Sulawesi Tenggara': [-4.1449, 122.1746],
  Gorontalo: [0.5435, 123.0568],
  'Sulawesi Barat': [-2.8441, 119.2321],
  Maluku: [-3.2385, 130.1453],
  'Maluku Utara': [1.5709, 127.8088],
  'Papua Barat': [-1.3361, 133.1747],
  Papua: [-4.2699, 138.0804],
}

// Map of kabupaten names to approximate province (derived from common knowledge)
// Only listing ones that appear in the DB based on the seed data
const KABUPATEN_TO_PROVINCE: Record<string, string> = {
  'Kutai Barat': 'Kalimantan Timur',
  'Barito Utara': 'Kalimantan Tengah',
  'Pasangkayu': 'Sulawesi Barat',
  'Pulau Morotai': 'Maluku Utara',
  'Muna Barat': 'Sulawesi Tenggara',
  'Penukal Abab Lematang Ilir': 'Sumatera Selatan',
  'Asmat': 'Papua',
  'Sumba Timur': 'Nusa Tenggara Timur',
  'Bone Bolango': 'Gorontalo',
  'Ogan Komering Ulu Timur': 'Sumatera Selatan',
}

function getBuyerCoords(buyerName: string): [number, number] | null {
  // Direct lookup (Provinsi or Kota)
  if (REGION_COORDS[buyerName]) return REGION_COORDS[buyerName]
  // Try Kabupaten → province center
  if (buyerName.startsWith('Kabupaten ')) {
    const kabName = buyerName.replace('Kabupaten ', '')
    const prov = KABUPATEN_TO_PROVINCE[kabName]
    if (prov && PROVINCE_CENTERS[prov]) return PROVINCE_CENTERS[prov]
  }
  return null
}

// ============================================================================
// Types
// ============================================================================

interface RegionRisk {
  name: string
  lat: number
  lng: number
  kritis: number
  tinggi: number
  pantauan: number
  aman: number
}

function getRiskColor(r: RegionRisk): string {
  const total = r.kritis + r.tinggi + r.pantauan + r.aman
  const criticalRate = (r.kritis + r.tinggi) / total
  if (criticalRate >= 0.25) return '#dc2626'
  if (criticalRate >= 0.15) return '#f97316'
  if (criticalRate >= 0.08) return '#f59e0b'
  return '#22c55e'
}

function getRiskLabel(r: RegionRisk): string {
  const total = r.kritis + r.tinggi + r.pantauan + r.aman
  const criticalRate = (r.kritis + r.tinggi) / total
  if (criticalRate >= 0.25) return 'Risiko Kritis'
  if (criticalRate >= 0.15) return 'Risiko Tinggi'
  if (criticalRate >= 0.08) return 'Perlu Pantauan'
  return 'Aman'
}

function getRadius(r: RegionRisk): number {
  const total = r.kritis + r.tinggi + r.pantauan + r.aman
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
// Region detail table
// ============================================================================

function RegionTable({ regions, selectedRegion, onSelect }: {
  regions: RegionRisk[]
  selectedRegion: string | null
  onSelect: (name: string | null) => void
}): React.ReactElement {
  const sorted = [...regions].sort((a, b) => (b.kritis + b.tinggi) - (a.kritis + a.tinggi))
  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-200 bg-slate-50">
        <h3 className="text-sm font-semibold text-slate-700">Daftar Wilayah</h3>
      </div>
      <div className="overflow-y-auto" style={{ maxHeight: 340 }}>
        <table className="text-xs w-full">
          <thead className="sticky top-0 bg-slate-100">
            <tr>
              <th className="px-3 py-2 text-left text-slate-500 font-medium">Wilayah</th>
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
              const isSelected = selectedRegion === p.name
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
// Aggregate tenders into RegionRisk[]
// ============================================================================

function aggregateTenders(tenders: TenderWithRisk[]): RegionRisk[] {
  const map = new Map<string, RegionRisk>()

  for (const tender of tenders) {
    const coords = getBuyerCoords(tender.buyer_name)
    if (!coords) continue

    const rl = tender.prediction?.risk_level ?? 'low'
    const score = tender.prediction?.risk_score ?? 0

    if (!map.has(tender.buyer_name)) {
      map.set(tender.buyer_name, {
        name: tender.buyer_name,
        lat: coords[0],
        lng: coords[1],
        kritis: 0,
        tinggi: 0,
        pantauan: 0,
        aman: 0,
      })
    }
    const entry = map.get(tender.buyer_name)!
    if (rl === 'high' && score >= 0.75) {
      entry.kritis += 1
    } else if (rl === 'high') {
      entry.tinggi += 1
    } else if (rl === 'medium') {
      entry.pantauan += 1
    } else {
      entry.aman += 1
    }
  }

  return Array.from(map.values())
}

// ============================================================================
// Main RiskMap page
// ============================================================================

export function RiskMap(): React.ReactElement {
  const [selectedRegion, setSelectedRegion] = useState<string | null>(null)
  const [regions, setRegions] = useState<RegionRisk[]>([])
  const [totalTenders, setTotalTenders] = useState(0)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    async function fetchAll(): Promise<void> {
      try {
        // Fetch all 1050 tenders in one request
        const res = await listTenders({ page: 1, page_size: 1050 })
        if (cancelled) return
        setTotalTenders(res.total)
        setRegions(aggregateTenders(res.items))
      } catch {
        // silently fail — show empty map
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    }
    void fetchAll()
    return () => { cancelled = true }
  }, [])

  const totalKritis = regions.reduce((s, p) => s + p.kritis, 0)
  const totalTinggi = regions.reduce((s, p) => s + p.tinggi, 0)
  const totalPantauan = regions.reduce((s, p) => s + p.pantauan, 0)
  const totalAman = regions.reduce((s, p) => s + p.aman, 0)

  const selectedData = selectedRegion ? regions.find((p) => p.name === selectedRegion) : null
  const riskLabel = selectedData ? getRiskLabel(selectedData) : null

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Peta Risiko Geografis</h1>
          <p className="text-sm text-slate-500 mt-1">
            Distribusi risiko pengadaan per wilayah — {totalTenders.toLocaleString('id-ID')} tender
          </p>
        </div>
        {isLoading && (
          <span className="text-sm text-slate-400 animate-pulse">Memuat data peta...</span>
        )}
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-5 gap-3">
        <StatCard label="Total Tender" value={totalTenders.toLocaleString('id-ID')} color="text-slate-700" />
        <StatCard label="Risiko Kritis" value={totalKritis} color="text-red-600"
          sub={totalTenders > 0 ? `${((totalKritis / totalTenders) * 100).toFixed(1)}%` : undefined} />
        <StatCard label="Risiko Tinggi" value={totalTinggi} color="text-orange-500"
          sub={totalTenders > 0 ? `${((totalTinggi / totalTenders) * 100).toFixed(1)}%` : undefined} />
        <StatCard label="Perlu Pantauan" value={totalPantauan} color="text-amber-600"
          sub={totalTenders > 0 ? `${((totalPantauan / totalTenders) * 100).toFixed(1)}%` : undefined} />
        <StatCard label="Aman" value={totalAman} color="text-green-600"
          sub={totalTenders > 0 ? `${((totalAman / totalTenders) * 100).toFixed(1)}%` : undefined} />
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
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            {regions.map((prov) => {
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
                    fillOpacity: selectedRegion === prov.name ? 0.85 : 0.55,
                    weight: selectedRegion === prov.name ? 3 : 1.5,
                  }}
                  eventHandlers={{
                    click: () => setSelectedRegion(
                      selectedRegion === prov.name ? null : prov.name
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
          <RegionTable
            regions={regions}
            selectedRegion={selectedRegion}
            onSelect={setSelectedRegion}
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
            → volume tender wilayah
          </div>
        </div>
      </div>
    </div>
  )
}
