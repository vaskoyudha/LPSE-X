import React, { useState, useEffect } from 'react'
import { generateReport, getReport, listTenders } from '../api/client'
import type { ReportResult } from '../types/models'

const DARK_RISK_BG: Record<string, string> = {
  'Aman':           'bg-green-900/40 text-green-300',
  'Perlu Pantauan': 'bg-amber-900/40 text-amber-300',
  'Risiko Tinggi':  'bg-red-900/40 text-red-300',
  'Risiko Kritis':  'bg-red-950 text-red-200',
}

// ============================================================================
// Risk score visual — glowing dots
// ============================================================================

function RiskScoreDots({ score, max = 3 }: { score: number; max?: number }): React.ReactElement {
  return (
    <div className="flex gap-1 items-center">
      {Array.from({ length: max }, (_, i) => (
        <span
          key={i}
          className={`w-3 h-3 rounded-full ${
            i < score
              ? 'bg-red-400 shadow-[0_0_6px_rgba(244,63,94,0.6)]'
              : 'bg-white/10'
          }`}
        />
      ))}
    </div>
  )
}

// ============================================================================
// High-risk tender buttons
// ============================================================================

function HighRiskButtons({
  onLoad,
  loadingId,
  loadedIds,
}: {
  onLoad: (tid: string) => void
  loadingId: string | null
  loadedIds: string[]
}): React.ReactElement {
  const [highRiskIds, setHighRiskIds] = useState<string[]>([])
  const [fetching, setFetching] = useState(true)

  useEffect(() => {
    let cancelled = false
    async function fetch(): Promise<void> {
      try {
        const res = await listTenders({ risk_level: 'high', page_size: 10 })
        if (!cancelled) setHighRiskIds(res.items.map((t) => t.tender_id))
      } catch {
        // silently fail
      } finally {
        if (!cancelled) setFetching(false)
      }
    }
    void fetch()
    return () => { cancelled = true }
  }, [])

  if (fetching) {
    return (
      <div>
        <p className="text-xs text-slate-500 mb-2 font-medium">Tender Risiko Tinggi:</p>
        <div className="flex gap-2">
          {Array.from({ length: 5 }, (_, i) => (
            <div key={i} className="h-7 w-36 bg-white/5 rounded-lg motion-safe:animate-pulse" />
          ))}
        </div>
      </div>
    )
  }

  if (highRiskIds.length === 0) return <></>

  return (
    <div>
      <p className="text-xs text-slate-500 mb-2 font-medium uppercase tracking-wide">Tender Risiko Tinggi:</p>
      <div className="flex flex-wrap gap-2">
        {highRiskIds.map((tid) => {
          const isLoaded = loadedIds.includes(tid)
          const isLoading = loadingId === tid
          return (
            <button
              key={tid}
              onClick={() => onLoad(tid)}
              disabled={isLoading}
              className={`px-3 py-1.5 text-xs font-mono rounded-lg border motion-safe:transition-all duration-200 ${
                isLoaded
                  ? 'bg-emerald-900/40 border-emerald-700/50 text-emerald-300 hover:bg-emerald-900/60 shadow-[0_0_10px_rgba(16,185,129,0.2)]'
                  : 'bg-white/5 border-white/10 text-slate-300 hover:bg-white/10 hover:border-white/20'
              } disabled:opacity-60`}
            >
              {isLoading ? '⏳' : isLoaded ? '✓' : '📄'} {tid}
            </button>
          )
        })}
      </div>
    </div>
  )
}

// ============================================================================
// Single report card (compact list view)
// ============================================================================

function ReportCard({
  tenderId,
  report,
  onSelect,
  isSelected,
}: {
  tenderId: string
  report: ReportResult
  onSelect: () => void
  isSelected: boolean
}): React.ReactElement {
  const bgClass = DARK_RISK_BG[report.risk_level] ?? 'bg-slate-700 text-slate-300'
  return (
    <button
      onClick={onSelect}
      className={`w-full text-left px-4 py-3 rounded-xl border motion-safe:transition-all duration-200 ${
        isSelected
          ? 'bg-white/10 border-cyan-500/30 shadow-[0_0_20px_rgba(6,182,212,0.2)]'
          : 'bg-white/5 border-white/10 hover:bg-white/10 hover:border-white/20'
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-slate-200 font-mono">{tenderId}</p>
          <p className="text-xs text-slate-500 mt-0.5">
            {new Date(report.generated_at).toLocaleString('id-ID')}
          </p>
        </div>
        <div className="flex flex-col items-end gap-1.5 flex-shrink-0">
          <span className={`text-xs px-2 py-0.5 rounded font-semibold ${bgClass}`}>
            {report.risk_level}
          </span>
          <RiskScoreDots score={report.risk_score} />
        </div>
      </div>
      <div className="mt-2 flex items-center gap-3 text-xs text-slate-500">
        <span>{report.evidence_count} bukti</span>
        <span>•</span>
        <span>{report.recommendations.length} rekomendasi</span>
      </div>
    </button>
  )
}

// ============================================================================
// Full report viewer
// ============================================================================

function ReportViewer({ report }: { report: ReportResult }): React.ReactElement {
  const bgClass = DARK_RISK_BG[report.risk_level] ?? 'bg-slate-700 text-slate-300'
  const isHighRisk = report.risk_level === 'Risiko Kritis' || report.risk_level === 'Risiko Tinggi'

  return (
    <div className="glass-card overflow-hidden">
      {/* Header bar */}
      <div className="px-6 py-4 border-b border-white/10 bg-white/5 flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-slate-200">
            Laporan Pra-Investigasi —{' '}
            <span className="font-mono text-cyan-400">{report.tender_id}</span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Dibuat: {new Date(report.generated_at).toLocaleString('id-ID')} &nbsp;|&nbsp;
            Hash: {report.tender_id.replace(/[^A-Z0-9]/g, '').toLowerCase()}
          </p>
        </div>
        <div className="flex items-center gap-3 print:hidden">
          <span className={`px-3 py-1 rounded-full text-sm font-bold ${bgClass} ${
            isHighRisk ? 'shadow-[0_0_15px_rgba(244,63,94,0.3)]' : ''
          }`}>
            {report.risk_level}
          </span>
          <button
            onClick={() => window.print()}
            className="px-3 py-1.5 text-xs bg-white/5 hover:bg-white/10 text-slate-300 border border-white/10 rounded-lg motion-safe:transition-all duration-200 flex items-center gap-1.5"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
            </svg>
            Cetak / PDF
          </button>
        </div>
      </div>

      <div className="p-6 space-y-5">
        {/* Metadata grid */}
        <div className="grid grid-cols-3 gap-4">
          {[
            {
              label: 'Skor Risiko',
              content: (
                <div className="flex items-center gap-2">
                  <RiskScoreDots score={report.risk_score} />
                  <span className="text-xl font-bold font-mono text-white">{report.risk_score}/3</span>
                </div>
              ),
              grad: 'from-red-600/10 to-rose-900/30 border-red-500/20',
            },
            {
              label: 'Jumlah Bukti',
              content: <p className="text-xl font-bold font-mono text-white">{report.evidence_count}</p>,
              grad: 'from-amber-600/10 to-amber-900/30 border-amber-500/20',
            },
            {
              label: 'Rekomendasi',
              content: <p className="text-xl font-bold font-mono text-white">{report.recommendations.length}</p>,
              grad: 'from-cyan-600/10 to-sky-900/30 border-cyan-500/20',
            },
          ].map(({ label, content, grad }) => (
            <div key={label} className={`bg-gradient-to-br ${grad} border rounded-xl p-3`}>
              <p className="text-xs text-slate-500 mb-2 font-medium uppercase tracking-wide">{label}</p>
              {content}
            </div>
          ))}
        </div>

        {/* Recommendations */}
        {report.recommendations.length > 0 && (
          <div className="bg-amber-950/30 border border-amber-800/50 rounded-xl p-4">
            <p className="text-sm font-bold text-amber-400 mb-3 flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="motion-safe:animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500" />
              </span>
              Rekomendasi Tindak Lanjut
            </p>
            <ol className="space-y-2">
              {report.recommendations.map((rec, i) => (
                <li key={i} className="flex gap-3 text-sm text-amber-200/80">
                  <span className="flex-shrink-0 w-5 h-5 rounded-full bg-amber-900/50 border border-amber-700/50 text-amber-400
                                   flex items-center justify-center text-xs font-bold">
                    {i + 1}
                  </span>
                  <span>{rec}</span>
                </li>
              ))}
            </ol>
          </div>
        )}

        {/* Sections */}
        {Object.keys(report.sections).length > 0 && (
          <div className="space-y-4">
            {Object.entries(report.sections).map(([sectionKey, content]) => (
              <div key={sectionKey}>
                <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                  {sectionKey.replace(/_/g, ' ')}
                </h4>
                <div className="bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-sm text-slate-300 whitespace-pre-wrap">
                  {content}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Full report text */}
        {report.report_text && (
          <div>
            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
              Teks Laporan Lengkap
            </h4>
            <pre className="bg-white/5 border border-white/10 rounded-xl p-5 text-xs text-slate-300 font-mono whitespace-pre-wrap leading-relaxed overflow-x-auto">
              {report.report_text}
            </pre>
          </div>
        )}
      </div>
    </div>
  )
}

// ============================================================================
// Main Reports page
// ============================================================================

interface ReportEntry {
  tenderId: string
  report: ReportResult
}

export function Reports(): React.ReactElement {
  const [reports, setReports] = useState<ReportEntry[]>([])
  const [selectedTenderId, setSelectedTenderId] = useState<string | null>(null)
  const [customTenderId, setCustomTenderId] = useState('')
  const [loadingId, setLoadingId] = useState<string | null>(null)
  const [errors, setErrors] = useState<Record<string, string>>({})

  async function loadReport(tenderId: string): Promise<void> {
    if (!tenderId.trim()) return
    setLoadingId(tenderId)
    setErrors((prev) => {
      const { [tenderId]: _, ...rest } = prev
      return rest
    })
    try {
      let report: ReportResult
      try {
        report = await getReport(tenderId)
      } catch {
        report = await generateReport(tenderId)
      }
      setReports((prev) => {
        const filtered = prev.filter((r) => r.tenderId !== tenderId)
        return [...filtered, { tenderId, report }]
      })
      setSelectedTenderId(tenderId)
    } catch (err) {
      setErrors((prev) => ({
        ...prev,
        [tenderId]: err instanceof Error ? err.message : 'Gagal memuat laporan',
      }))
    } finally {
      setLoadingId(null)
    }
  }

  async function handleCustomLoad(): Promise<void> {
    const id = customTenderId.trim()
    if (id) {
      await loadReport(id)
      setCustomTenderId('')
    }
  }

  const selectedReport = reports.find((r) => r.tenderId === selectedTenderId)

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="motion-safe:animate-[fade-in-up_0.4s_ease-out_both]">
        <h1 className="text-2xl font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
          Laporan Pra-Investigasi
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Generate dan lihat laporan berformat IIA 2025 untuk tender yang dipilih
        </p>
      </div>

      {/* Generate controls */}
      <div className="glass-card p-5 space-y-4">
        <h2 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
          <span className="w-1.5 h-4 rounded-full bg-gradient-to-b from-cyan-400 to-indigo-500" />
          Generate Laporan
        </h2>

        <HighRiskButtons
          onLoad={(tid) => { void loadReport(tid) }}
          loadingId={loadingId}
          loadedIds={reports.map((r) => r.tenderId)}
        />

        {/* Custom input */}
        <div className="flex gap-2">
          <input
            type="text"
            value={customTenderId}
            onChange={(e) => setCustomTenderId(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') { void handleCustomLoad() } }}
            placeholder="Masukkan Tender ID custom (e.g. SYN-2018-00627)"
            className="flex-1 px-3 py-2 text-sm bg-white/5 border border-white/10 rounded-lg text-slate-200
                       focus:outline-none focus:border-cyan-500/50 focus:shadow-[0_0_15px_rgba(6,182,212,0.2)]
                       motion-safe:transition-all placeholder:text-slate-600 font-mono"
          />
          <button
            onClick={() => { void handleCustomLoad() }}
            disabled={!customTenderId.trim() || loadingId === customTenderId}
            className="px-5 py-2 bg-gradient-to-r from-indigo-600 to-cyan-600 hover:from-indigo-500 hover:to-cyan-500
                       text-white text-sm font-semibold rounded-lg disabled:opacity-60
                       motion-safe:hover:scale-105 motion-safe:hover:shadow-[0_0_20px_rgba(6,182,212,0.35)]
                       motion-safe:transition-all duration-200"
          >
            Generate
          </button>
        </div>
      </div>

      {/* Main content: list + viewer */}
      {reports.length > 0 ? (
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
          {/* Report list */}
          <div className="xl:col-span-1 space-y-2">
            <p className="text-xs text-slate-500 font-medium uppercase tracking-wide px-1">
              {reports.length} laporan dimuat
            </p>
            {reports.map(({ tenderId, report }) => (
              <ReportCard
                key={tenderId}
                tenderId={tenderId}
                report={report}
                onSelect={() => setSelectedTenderId(tenderId)}
                isSelected={selectedTenderId === tenderId}
              />
            ))}
          </div>

          {/* Report viewer */}
          <div className="xl:col-span-2">
            {selectedReport ? (
              <ReportViewer report={selectedReport.report} />
            ) : (
              <div className="glass-card border-2 border-dashed border-white/10 flex items-center justify-center" style={{ minHeight: 400 }}>
                <div className="text-center">
                  <p className="text-3xl mb-2">📋</p>
                  <p className="text-sm font-medium text-slate-400">Pilih laporan untuk melihat detail</p>
                </div>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="glass-card border-2 border-dashed border-white/10 flex items-center justify-center" style={{ minHeight: 300 }}>
          <div className="text-center max-w-xs">
            <p className="text-4xl mb-3">📄</p>
            <p className="text-sm font-medium text-slate-400">Belum ada laporan</p>
            <p className="text-xs text-slate-500 mt-1">
              Klik salah satu tender di atas atau masukkan Tender ID untuk generate laporan
            </p>
          </div>
        </div>
      )}

      {/* Errors */}
      {Object.entries(errors).length > 0 && (
        <div className="space-y-2">
          {Object.entries(errors).map(([tid, err]) => (
            <div
              key={tid}
              className="bg-red-950/40 border border-red-700/50 rounded-xl px-4 py-3 text-sm text-red-300 flex items-center justify-between"
            >
              <div className="flex items-center gap-2">
                <span className="relative flex h-2 w-2">
                  <span className="motion-safe:animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500" />
                </span>
                <span><strong>{tid}:</strong> {err}</span>
              </div>
              <button
                onClick={() => setErrors((prev) => {
                  const { [tid]: _, ...rest } = prev
                  return rest
                })}
                className="text-red-500 hover:text-red-300 motion-safe:transition-colors ml-4"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
