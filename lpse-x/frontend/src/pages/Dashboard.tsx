import React, { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { getHealth, listTenders } from '../api/client'
import type { TenderWithRisk } from '../types/models'
import { CheckCircle, AlertTriangle, AlertOctagon, LayoutList } from 'lucide-react'

// ============================================================================
// Risk level mapping: DB stores "high"/"medium"/"low", UI shows Bahasa labels
// ============================================================================

const RISK_LEVEL_LABEL: Record<string, string> = {
  high: 'Risiko Tinggi',
  medium: 'Perlu Pantauan',
  low: 'Aman',
}

const DARK_RISK_BG: Record<string, string> = {
  'Aman':           'bg-emerald-900/40 text-emerald-300 ring-1 ring-emerald-700/50',
  'Perlu Pantauan': 'bg-amber-900/40 text-amber-300 ring-1 ring-amber-700/50',
  'Risiko Tinggi':  'bg-red-900/40 text-red-300 ring-1 ring-red-700/50 shadow-[0_0_8px_rgba(244,63,94,0.3)]',
  'Risiko Kritis':  'bg-red-950 text-red-200 ring-1 ring-red-800 shadow-[0_0_10px_rgba(244,63,94,0.5)]',
}

// ============================================================================
// Helper components
// ============================================================================

interface RiskBadgeProps {
  level: string
}

function RiskBadge({ level }: RiskBadgeProps): React.ReactElement {
  const label = RISK_LEVEL_LABEL[level] ?? level
  const cls = DARK_RISK_BG[label] ?? 'bg-slate-800 text-slate-300 ring-1 ring-slate-700'
  const isPulsing = label === 'Risiko Tinggi' || label === 'Risiko Kritis'
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold ${cls}`}>
      {isPulsing && (
        <span className="relative flex h-2 w-2">
          <span className="motion-safe:animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500" />
        </span>
      )}
      {label}
    </span>
  )
}

interface StatCardProps {
  label: string
  value: number
  icon: React.ReactNode
  valueColor: string
  gradientFrom: string
  gradientTo: string
  delay?: string
}

function StatCard({ label, value, icon, valueColor, gradientFrom, gradientTo, delay }: StatCardProps): React.ReactElement {
  return (
    <div
      className="glass-card p-5 flex items-center gap-4 motion-safe:animate-[fade-in-up_0.5s_ease-out_both]"
      style={{ animationDelay: delay ?? '0s' }}
    >
      <div className={`w-11 h-11 rounded-xl bg-gradient-to-br ${gradientFrom} ${gradientTo} flex items-center justify-center flex-shrink-0`}>
        {icon}
      </div>
      <div>
        <p className={`text-3xl font-bold font-mono ${valueColor}`}>{value}</p>
        <p className="text-xs text-slate-400 mt-0.5 uppercase tracking-wider">{label}</p>
      </div>
    </div>
  )
}

// ============================================================================
// Score bar
// ============================================================================

function ScoreBar({ score }: { score: number }): React.ReactElement {
  const pct = Math.round(score * 100)
  let barClass = 'bg-gradient-to-r from-green-500 to-emerald-400'
  if (score >= 0.75) barClass = 'bg-gradient-to-r from-red-600 to-rose-400'
  else if (score >= 0.5) barClass = 'bg-gradient-to-r from-red-500 to-rose-300'
  else if (score >= 0.25) barClass = 'bg-gradient-to-r from-amber-500 to-orange-400'

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-white/5 rounded-full h-2 overflow-hidden">
        <div
          className={`h-2 rounded-full motion-safe:transition-all duration-500 ${barClass}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs font-mono font-medium text-slate-500 w-9 text-right">{pct}%</span>
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
          <h1 className="text-2xl font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
            Dasbor Pengadaan
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Analisis Risiko Pengadaan Pemerintah — LPSE-X v1.0
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <span
            className={`inline-block w-2.5 h-2.5 rounded-full ${
              healthQuery.isSuccess
                ? 'bg-emerald-400 shadow-[0_0_8px_rgba(16,185,129,0.6)]'
                : healthQuery.isError
                ? 'bg-red-400'
                : 'bg-amber-400 motion-safe:animate-pulse'
            }`}
          />
          <span className="text-slate-400 font-mono text-xs">
            {healthQuery.isSuccess
              ? `Backend OK · v${healthQuery.data.version}`
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
            icon={<CheckCircle className="w-5 h-5 text-emerald-300" />}
            valueColor="text-emerald-400"
            gradientFrom="from-emerald-600/20"
            gradientTo="to-teal-900/40"
            delay="0s"
          />
          <StatCard
            label="Perlu Pantauan"
            value={counts.medium}
            icon={<AlertTriangle className="w-5 h-5 text-amber-300" />}
            valueColor="text-amber-400"
            gradientFrom="from-amber-600/20"
            gradientTo="to-orange-900/40"
            delay="0.1s"
          />
          <StatCard
            label="Risiko Tinggi"
            value={counts.high}
            icon={<AlertOctagon className="w-5 h-5 text-rose-300" />}
            valueColor="text-rose-400"
            gradientFrom="from-rose-600/20"
            gradientTo="to-red-900/40"
            delay="0.2s"
          />
          <StatCard
            label="Total Halaman Ini"
            value={tenders.length}
            icon={<LayoutList className="w-5 h-5 text-cyan-300" />}
            valueColor="text-cyan-400"
            gradientFrom="from-cyan-600/20"
            gradientTo="to-indigo-900/40"
            delay="0.3s"
          />
        </div>
      )}

      {/* Error */}
      {fetchError && (
        <div className="bg-red-950/50 border border-red-800/50 rounded-xl p-4 text-red-300 text-sm shadow-[0_0_15px_rgba(244,63,94,0.1)]">
          <strong>Error:</strong> {fetchError}
        </div>
      )}

      {/* Tender table */}
      <div className="glass-card overflow-hidden">
        <div className="px-6 py-4 border-b border-white/10 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-200">Daftar Tender</h2>
          <span className="text-xs text-slate-500 font-mono">
            {loading ? 'Memuat...' : `${total.toLocaleString('id-ID')} total tender`}
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-white/5 text-xs text-slate-500 uppercase tracking-wider">
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
            <tbody className="divide-y divide-white/5">
              {loading ? (
                <tr>
                  <td colSpan={7} className="px-6 py-10 text-center text-slate-500 text-sm">
                    <svg className="w-5 h-5 motion-safe:animate-spin mx-auto mb-2 text-cyan-400" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4l3-3-3-3v4a8 8 0 00-8 8h4z" />
                    </svg>
                    Memuat data tender...
                  </td>
                </tr>
              ) : tenders.map((row) => {
                const riskLevel = row.prediction?.risk_level
                const isHighRisk = riskLevel === 'high'
                return (
                  <tr
                    key={row.tender_id}
                    className={`motion-safe:hover:bg-white/5 motion-safe:hover:shadow-[0_0_25px_rgba(6,182,212,0.1)] motion-safe:transition-all duration-200 ${
                      isHighRisk ? 'shadow-[0_0_15px_rgba(244,63,94,0.1)]' : ''
                    }`}
                  >
                    <td className="px-6 py-4 font-mono text-xs text-slate-500">
                      {row.tender_id}
                    </td>
                    <td className="px-6 py-4 font-medium text-slate-200 max-w-xs truncate">
                      {row.title}
                    </td>
                    <td className="px-6 py-4 text-slate-400 max-w-xs truncate">
                      {row.buyer_name}
                    </td>
                    <td className="px-6 py-4 text-right font-mono font-medium text-slate-300 whitespace-nowrap">
                      {formatAmount(row.value_amount)}
                    </td>
                    <td className="px-6 py-4 text-center">
                      {row.prediction ? (
                        <RiskBadge level={row.prediction.risk_level} />
                      ) : (
                        <span className="text-slate-500 text-xs">—</span>
                      )}
                    </td>
                    <td className="px-6 py-4 w-40">
                      {row.prediction ? (
                        <ScoreBar score={row.prediction.risk_score} />
                      ) : (
                        <span className="text-slate-500 text-xs">—</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-center">
                      <Link
                        to={`/tender/${row.tender_id}`}
                        className="text-cyan-400 hover:text-cyan-300 text-xs font-medium motion-safe:transition-colors hover:underline"
                      >
                        Detail XAI →
                      </Link>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="px-6 py-4 border-t border-white/10 flex items-center justify-between">
            <span className="text-xs text-slate-500 font-mono">
              Halaman {page} dari {totalPages}
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1 || loading}
                className="px-3 py-1.5 text-xs bg-white/5 text-slate-300 border border-white/10 rounded-lg hover:bg-white/10 disabled:opacity-40 disabled:cursor-not-allowed motion-safe:transition-all"
              >
                ← Sebelumnya
              </button>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages || loading}
                className="px-3 py-1.5 text-xs bg-white/5 text-slate-300 border border-white/10 rounded-lg hover:bg-white/10 disabled:opacity-40 disabled:cursor-not-allowed motion-safe:transition-all"
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
