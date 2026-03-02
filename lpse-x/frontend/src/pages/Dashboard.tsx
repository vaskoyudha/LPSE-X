import React, { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { getHealth, listTenders } from '../api/client'
import { RISK_BG, RISK_COLORS } from '../types/models'
import type { TenderWithRisk } from '../types/models'

// ============================================================================
// Risk level mapping: DB stores "high"/"medium"/"low", UI shows Bahasa labels
// ============================================================================

const RISK_LEVEL_LABEL: Record<string, string> = {
  high: 'Risiko Tinggi',
  medium: 'Perlu Pantauan',
  low: 'Aman',
}

// ============================================================================
// Helper components
// ============================================================================

interface RiskBadgeProps {
  level: string
}

function RiskBadge({ level }: RiskBadgeProps): React.ReactElement {
  const label = RISK_LEVEL_LABEL[level] ?? level
  const cls = RISK_BG[label] ?? 'bg-gray-100 text-gray-700'
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${cls}`}>
      {label}
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

const PAGE_SIZE = 20

export function Dashboard(): React.ReactElement {
  const [page, setPage] = useState(1)
  const [tenders, setTenders] = useState<TenderWithRisk[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [fetchError, setFetchError] = useState<string | null>(null)

  // Health check
  const healthQuery = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    retry: 1,
    staleTime: 60_000,
  })

  // Fetch tenders on page change
  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setFetchError(null)
    listTenders({ page, page_size: PAGE_SIZE })
      .then((resp) => {
        if (!cancelled) {
          setTenders(resp.items)
          setTotal(resp.total)
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setFetchError(err instanceof Error ? err.message : 'Gagal memuat data tender')
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [page])

  // Compute risk stat counts from current page
  const counts = { low: 0, medium: 0, high: 0 }
  for (const t of tenders) {
    const lvl = t.prediction?.risk_level
    if (lvl === 'high') counts.high++
    else if (lvl === 'medium') counts.medium++
    else if (lvl === 'low') counts.low++
  }

  const totalPages = Math.ceil(total / PAGE_SIZE)

  const formatAmount = (n: number | undefined): string => {
    if (n === undefined || n === null) return '—'
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
      </div>

      {/* Risk summary cards */}
      {tenders.length > 0 && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            label="Aman"
            value={counts.low}
            color={RISK_COLORS['Aman']}
            icon="✓"
          />
          <StatCard
            label="Perlu Pantauan"
            value={counts.medium}
            color={RISK_COLORS['Perlu Pantauan']}
            icon="⚠"
          />
          <StatCard
            label="Risiko Tinggi"
            value={counts.high}
            color={RISK_COLORS['Risiko Tinggi']}
            icon="🔴"
          />
          <StatCard
            label="Total Halaman Ini"
            value={tenders.length}
            color="#64748b"
            icon="📋"
          />
        </div>
      )}

      {/* Error */}
      {fetchError && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 text-sm">
          <strong>Error:</strong> {fetchError}
        </div>
      )}

      {/* Tender table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-700">Daftar Tender</h2>
          <span className="text-sm text-slate-500">
            {loading ? 'Memuat...' : `${total.toLocaleString('id-ID')} total tender`}
          </span>
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
              {loading ? (
                <tr>
                  <td colSpan={7} className="px-6 py-10 text-center text-slate-400 text-sm">
                    <svg className="w-5 h-5 animate-spin mx-auto mb-2 text-blue-500" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4l3-3-3-3v4a8 8 0 00-8 8h4z" />
                    </svg>
                    Memuat data tender...
                  </td>
                </tr>
              ) : tenders.map((row) => (
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
                    {row.buyer_name}
                  </td>
                  <td className="px-6 py-4 text-right font-medium text-slate-700 whitespace-nowrap">
                    {formatAmount(row.value_amount)}
                  </td>
                  <td className="px-6 py-4 text-center">
                    {row.prediction ? (
                      <RiskBadge level={row.prediction.risk_level} />
                    ) : (
                      <span className="text-slate-400 text-xs">—</span>
                    )}
                  </td>
                  <td className="px-6 py-4 w-40">
                    {row.prediction ? (
                      <ScoreBar score={row.prediction.risk_score} />
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

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-between">
            <span className="text-sm text-slate-500">
              Halaman {page} dari {totalPages}
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1 || loading}
                className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg
                           hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                ← Sebelumnya
              </button>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages || loading}
                className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg
                           hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Berikutnya →
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
