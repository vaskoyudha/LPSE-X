import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { getHealth, predictTender } from '../api/client'
import { RISK_BG, RISK_COLORS } from '../types/models'
import type { RiskPrediction } from '../types/models'

// ============================================================================
// Mock/Demo tender data for hackathon demo (real data comes from pipeline)
// ============================================================================

const DEMO_TENDERS = [
  {
    tender_id: 'ID-2024-0001',
    title: 'Konstruksi Gedung Kantor Dinas PUPR',
    buyer: 'Dinas PUPR Kabupaten Sleman',
    year: 2024,
    amount: 4_980_000_000,
    features: {
      n_bidders: 1.0,
      price_ratio: 0.995,
      bid_spread: 0.005,
      winner_bid_rank: 1.0,
      hhi: 0.95,
      log_amount: 21.33,
    },
    icw_raw_score: 78.5,
  },
  {
    tender_id: 'ID-2024-0002',
    title: 'Rehabilitasi Jalan Raya Bantul–Yogyakarta',
    buyer: 'Dinas Bina Marga Bantul',
    year: 2024,
    amount: 1_200_000_000,
    features: {
      n_bidders: 5.0,
      price_ratio: 0.87,
      bid_spread: 0.13,
      winner_bid_rank: 2.0,
      hhi: 0.25,
      log_amount: 20.9,
    },
    icw_raw_score: 22.0,
  },
  {
    tender_id: 'ID-2024-0003',
    title: 'Pengadaan Meja Kursi Kantor Pemerintah',
    buyer: 'Sekretariat Daerah Gunungkidul',
    year: 2024,
    amount: 350_000_000,
    features: {
      n_bidders: 1.0,
      price_ratio: 0.999,
      bid_spread: 0.001,
      winner_bid_rank: 1.0,
      hhi: 1.0,
      log_amount: 19.67,
    },
    icw_raw_score: 91.2,
  },
  {
    tender_id: 'ID-2024-0004',
    title: 'Jasa Konsultansi AMDAL Kawasan Industri',
    buyer: 'BPPD Kota Yogyakarta',
    year: 2024,
    amount: 2_800_000_000,
    features: {
      n_bidders: 3.0,
      price_ratio: 0.92,
      bid_spread: 0.08,
      winner_bid_rank: 1.0,
      hhi: 0.45,
      log_amount: 21.75,
    },
    icw_raw_score: 45.0,
  },
  {
    tender_id: 'ID-2024-0005',
    title: 'Penyediaan Alat Kesehatan Puskesmas',
    buyer: 'Dinas Kesehatan Kulon Progo',
    year: 2024,
    amount: 5_600_000_000,
    features: {
      n_bidders: 2.0,
      price_ratio: 0.985,
      bid_spread: 0.015,
      winner_bid_rank: 1.0,
      hhi: 0.72,
      log_amount: 22.45,
    },
    icw_raw_score: 66.5,
  },
]

// ============================================================================
// Helper components
// ============================================================================

interface RiskBadgeProps {
  level: string
}

function RiskBadge({ level }: RiskBadgeProps): React.ReactElement {
  const cls = RISK_BG[level] ?? 'bg-gray-100 text-gray-700'
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${cls}`}>
      {level}
    </span>
  )
}

interface StatCardProps {
  label: string
  value: number
  color: string
  icon: string
}

function StatCard({ label, value, color, icon }: StatCardProps): React.ReactElement {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 flex items-center gap-4">
      <div
        className="w-12 h-12 rounded-lg flex items-center justify-center text-white text-xl font-bold flex-shrink-0"
        style={{ backgroundColor: color }}
      >
        {icon}
      </div>
      <div>
        <p className="text-2xl font-bold text-slate-800">{value}</p>
        <p className="text-sm text-slate-500 mt-0.5">{label}</p>
      </div>
    </div>
  )
}

// ============================================================================
// Score bar
// ============================================================================

function ScoreBar({ score }: { score: number }): React.ReactElement {
  const pct = Math.round(score * 100)
  let barColor = 'bg-green-500'
  if (score >= 0.75) barColor = 'bg-red-700'
  else if (score >= 0.5) barColor = 'bg-red-500'
  else if (score >= 0.25) barColor = 'bg-amber-400'

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-gray-200 rounded-full h-2 overflow-hidden">
        <div
          className={`h-2 rounded-full transition-all duration-500 ${barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs font-medium text-slate-600 w-9 text-right">{pct}%</span>
    </div>
  )
}

// ============================================================================
// Main Dashboard
// ============================================================================

interface TenderRow {
  tender_id: string
  title: string
  buyer: string
  year: number
  amount: number
  prediction: RiskPrediction | null
  loading: boolean
  error: boolean
}

export function Dashboard(): React.ReactElement {
  const [rows, setRows] = useState<TenderRow[]>(
    DEMO_TENDERS.map((t) => ({
      tender_id: t.tender_id,
      title: t.title,
      buyer: t.buyer,
      year: t.year,
      amount: t.amount,
      prediction: null,
      loading: false,
      error: false,
    })),
  )
  const [allLoading, setAllLoading] = useState(false)

  // Health check
  const healthQuery = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    retry: 1,
    staleTime: 60_000,
  })

  // Run all predictions
  async function runAllPredictions(): Promise<void> {
    setAllLoading(true)
    const results = await Promise.allSettled(
      DEMO_TENDERS.map((t) =>
        predictTender({
          tender_id: t.tender_id,
          features: t.features,
          icw_raw_score: t.icw_raw_score,
        }),
      ),
    )
    setRows((prev) =>
      prev.map((row, i) => {
        const r = results[i]
        if (r.status === 'fulfilled') {
          return { ...row, prediction: r.value, loading: false, error: false }
        }
        return { ...row, prediction: null, loading: false, error: true }
      }),
    )
    setAllLoading(false)
  }

  // Compute stats from predictions
  const withPredictions = rows.filter((r) => r.prediction !== null)
  const counts = {
    'Aman': 0,
    'Perlu Pantauan': 0,
    'Risiko Tinggi': 0,
    'Risiko Kritis': 0,
  }
  for (const row of withPredictions) {
    if (row.prediction) {
      const lvl = row.prediction.risk_level as keyof typeof counts
      if (lvl in counts) counts[lvl]++
    }
  }

  const formatAmount = (n: number): string => {
    if (n >= 1_000_000_000) return `Rp ${(n / 1_000_000_000).toFixed(2)} M`
    if (n >= 1_000_000) return `Rp ${(n / 1_000_000).toFixed(1)} Jt`
    return `Rp ${n.toLocaleString('id-ID')}`
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Dasbor Pengadaan</h1>
          <p className="text-sm text-slate-500 mt-1">
            Analisis Risiko Pengadaan Pemerintah — LPSE-X v1.0
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Backend status indicator */}
          <div className="flex items-center gap-2 text-sm">
            <span
              className={`inline-block w-2.5 h-2.5 rounded-full ${
                healthQuery.isSuccess
                  ? 'bg-green-500'
                  : healthQuery.isError
                  ? 'bg-red-500'
                  : 'bg-amber-400 animate-pulse'
              }`}
            />
            <span className="text-slate-600">
              {healthQuery.isSuccess
                ? `Backend OK • v${healthQuery.data.version}`
                : healthQuery.isError
                ? 'Backend offline'
                : 'Connecting...'}
            </span>
          </div>
          <button
            onClick={() => { void runAllPredictions() }}
            disabled={allLoading}
            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg
                       hover:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed
                       transition-colors flex items-center gap-2"
          >
            {allLoading ? (
              <>
                <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4l3-3-3-3v4a8 8 0 00-8 8h4z" />
                </svg>
                Menganalisis...
              </>
            ) : (
              <>🔍 Analisis Semua Tender</>
            )}
          </button>
        </div>
      </div>

      {/* Risk summary cards (visible after predictions run) */}
      {withPredictions.length > 0 && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            label="Aman"
            value={counts['Aman']}
            color={RISK_COLORS['Aman']}
            icon="✓"
          />
          <StatCard
            label="Perlu Pantauan"
            value={counts['Perlu Pantauan']}
            color={RISK_COLORS['Perlu Pantauan']}
            icon="⚠"
          />
          <StatCard
            label="Risiko Tinggi"
            value={counts['Risiko Tinggi']}
            color={RISK_COLORS['Risiko Tinggi']}
            icon="🔴"
          />
          <StatCard
            label="Risiko Kritis"
            value={counts['Risiko Kritis']}
            color={RISK_COLORS['Risiko Kritis']}
            icon="🚨"
          />
        </div>
      )}

      {/* Tender table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-700">Daftar Tender</h2>
          <span className="text-sm text-slate-500">{rows.length} tender</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-xs text-slate-500 uppercase tracking-wide">
              <tr>
                <th className="px-6 py-3 text-left">ID Tender</th>
                <th className="px-6 py-3 text-left">Nama Paket</th>
                <th className="px-6 py-3 text-left">Satuan Kerja</th>
                <th className="px-6 py-3 text-right">Nilai HPS</th>
                <th className="px-6 py-3 text-center">Tingkat Risiko</th>
                <th className="px-6 py-3 text-left">Skor Risiko</th>
                <th className="px-6 py-3 text-center">Aksi</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {rows.map((row) => (
                <tr
                  key={row.tender_id}
                  className="hover:bg-slate-50 transition-colors"
                >
                  <td className="px-6 py-4 font-mono text-xs text-slate-500">
                    {row.tender_id}
                  </td>
                  <td className="px-6 py-4 font-medium text-slate-800 max-w-xs truncate">
                    {row.title}
                  </td>
                  <td className="px-6 py-4 text-slate-600 max-w-xs truncate">
                    {row.buyer}
                  </td>
                  <td className="px-6 py-4 text-right font-medium text-slate-700 whitespace-nowrap">
                    {formatAmount(row.amount)}
                  </td>
                  <td className="px-6 py-4 text-center">
                    {row.loading ? (
                      <span className="text-slate-400 text-xs">Memproses...</span>
                    ) : row.error ? (
                      <span className="text-red-500 text-xs">Error</span>
                    ) : row.prediction ? (
                      <RiskBadge level={row.prediction.risk_level} />
                    ) : (
                      <span className="text-slate-400 text-xs">—</span>
                    )}
                  </td>
                  <td className="px-6 py-4 w-40">
                    {row.prediction ? (
                      <ScoreBar score={row.prediction.final_score} />
                    ) : (
                      <span className="text-slate-300 text-xs">—</span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-center">
                    <Link
                      to={`/tender/${row.tender_id}`}
                      className="text-blue-600 hover:text-blue-800 text-xs font-medium
                                 underline underline-offset-2 transition-colors"
                    >
                      Detail XAI →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Hint when no predictions loaded */}
      {withPredictions.length === 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-5 text-center">
          <p className="text-blue-700 text-sm">
            Klik <strong>"Analisis Semua Tender"</strong> untuk menjalankan model AI dan
            mendapatkan klasifikasi risiko.
          </p>
        </div>
      )}
    </div>
  )
}
