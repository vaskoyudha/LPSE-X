import React, { useState } from 'react'
import { generateReport, getReport } from '../api/client'
import { RISK_BG } from '../types/models'
import type { ReportResult } from '../types/models'

// ============================================================================
// Demo tender IDs to generate reports for
// ============================================================================

const DEMO_TENDER_IDS = [
  'ID-2024-0001',
  'ID-2024-0002',
  'ID-2024-0003',
  'ID-2024-0004',
  'ID-2024-0005',
]

// ============================================================================
// Risk score visual
// ============================================================================

function RiskScoreDots({ score, max = 3 }: { score: number; max?: number }): React.ReactElement {
  return (
    <div className="flex gap-1 items-center">
      {Array.from({ length: max }, (_, i) => (
        <span
          key={i}
          className={`w-3 h-3 rounded-full ${
            i < score ? 'bg-red-500' : 'bg-gray-200'
          }`}
        />
      ))}
    </div>
  )
}

// ============================================================================
// Single report card (compact view in list)
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
  const bgClass = RISK_BG[report.risk_level] ?? 'bg-gray-100 text-gray-700'
  return (
    <button
      onClick={onSelect}
      className={`w-full text-left px-4 py-3 rounded-lg border transition-all ${
        isSelected
          ? 'border-blue-400 bg-blue-50 shadow-sm'
          : 'border-gray-200 bg-white hover:border-gray-300 hover:bg-slate-50'
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-slate-700 font-mono">{tenderId}</p>
          <p className="text-xs text-slate-400 mt-0.5">
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
  const bgClass = RISK_BG[report.risk_level] ?? 'bg-gray-100 text-gray-700'

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      {/* Header bar */}
      <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between bg-slate-50 print:bg-white">
        <div>
          <h2 className="text-base font-bold text-slate-700">
            Laporan Pra-Investigasi — {report.tender_id}
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Dibuat: {new Date(report.generated_at).toLocaleString('id-ID')} &nbsp;|&nbsp;
            Hash: {report.tender_id.replace(/[^A-Z0-9]/g, '').toLowerCase()}
          </p>
        </div>
        <div className="flex items-center gap-3 print:hidden">
          <span className={`px-3 py-1 rounded-full text-sm font-bold ${bgClass}`}>
            {report.risk_level}
          </span>
          <button
            onClick={() => window.print()}
            className="px-3 py-1.5 text-xs bg-gray-100 hover:bg-gray-200 text-slate-700
                       rounded-lg transition-colors font-medium flex items-center gap-1.5"
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
          <div className="bg-slate-50 rounded-lg p-3">
            <p className="text-xs text-slate-500 mb-1 font-medium uppercase tracking-wide">Skor Risiko</p>
            <div className="flex items-center gap-2">
              <RiskScoreDots score={report.risk_score} />
              <span className="text-sm font-bold text-slate-700">{report.risk_score}/3</span>
            </div>
          </div>
          <div className="bg-slate-50 rounded-lg p-3">
            <p className="text-xs text-slate-500 mb-1 font-medium uppercase tracking-wide">Jumlah Bukti</p>
            <p className="text-xl font-bold text-slate-700">{report.evidence_count}</p>
          </div>
          <div className="bg-slate-50 rounded-lg p-3">
            <p className="text-xs text-slate-500 mb-1 font-medium uppercase tracking-wide">Rekomendasi</p>
            <p className="text-xl font-bold text-slate-700">{report.recommendations.length}</p>
          </div>
        </div>

        {/* Recommendations */}
        {report.recommendations.length > 0 && (
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
            <p className="text-sm font-bold text-amber-800 mb-3">
              ⚠ Rekomendasi Tindak Lanjut
            </p>
            <ol className="space-y-2">
              {report.recommendations.map((rec, i) => (
                <li key={i} className="flex gap-3 text-sm text-amber-900">
                  <span className="flex-shrink-0 w-5 h-5 rounded-full bg-amber-200 text-amber-800
                                   flex items-center justify-center text-xs font-bold">
                    {i + 1}
                  </span>
                  <span>{rec}</span>
                </li>
              ))}
            </ol>
          </div>
        )}

        {/* Sections (if available) */}
        {Object.keys(report.sections).length > 0 && (
          <div className="space-y-4">
            {Object.entries(report.sections).map(([sectionKey, content]) => (
              <div key={sectionKey}>
                <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                  {sectionKey.replace(/_/g, ' ')}
                </h4>
                <div className="bg-slate-50 rounded-lg px-4 py-3 text-sm text-slate-700 whitespace-pre-wrap leading-relaxed">
                  {content}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Full report text (Jinja2 template rendered) */}
        {report.report_text && (
          <div>
            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
              Teks Laporan Lengkap
            </h4>
            <pre className="bg-slate-50 border border-gray-200 rounded-xl p-5 text-xs text-slate-700
                            whitespace-pre-wrap font-mono leading-relaxed overflow-x-auto">
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
      // Try GET first, fallback to POST (generate)
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
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Laporan Pra-Investigasi</h1>
        <p className="text-sm text-slate-500 mt-1">
          Generate dan lihat laporan berformat IIA 2025 untuk tender yang dipilih
        </p>
      </div>

      {/* Generate controls */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
        <h2 className="text-sm font-semibold text-slate-700">Generate Laporan</h2>

        {/* Demo tender buttons */}
        <div>
          <p className="text-xs text-slate-500 mb-2 font-medium">Tender demo tersedia:</p>
          <div className="flex flex-wrap gap-2">
            {DEMO_TENDER_IDS.map((tid) => {
              const isLoaded = reports.some((r) => r.tenderId === tid)
              const isLoading = loadingId === tid
              return (
                <button
                  key={tid}
                  onClick={() => { void loadReport(tid) }}
                  disabled={isLoading}
                  className={`px-3 py-1.5 text-xs font-mono rounded-lg border transition-all ${
                    isLoaded
                      ? 'bg-emerald-50 border-emerald-300 text-emerald-700 hover:bg-emerald-100'
                      : 'bg-white border-gray-300 text-slate-600 hover:bg-slate-50'
                  } disabled:opacity-60`}
                >
                  {isLoading ? '⏳' : isLoaded ? '✓' : '📄'} {tid}
                </button>
              )
            })}
          </div>
        </div>

        {/* Custom tender ID input */}
        <div className="flex gap-2">
          <input
            type="text"
            value={customTenderId}
            onChange={(e) => setCustomTenderId(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') { void handleCustomLoad() } }}
            placeholder="Masukkan Tender ID custom (e.g. ID-2024-0123)"
            className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg
                       focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                       placeholder:text-gray-400 font-mono"
          />
          <button
            onClick={() => { void handleCustomLoad() }}
            disabled={!customTenderId.trim() || loadingId === customTenderId}
            className="px-4 py-2 bg-blue-600 text-white text-sm font-semibold rounded-lg
                       hover:bg-blue-700 disabled:opacity-60 transition-colors"
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
              <div className="bg-slate-50 border-2 border-dashed border-slate-300 rounded-xl
                              flex items-center justify-center" style={{ minHeight: 400 }}>
                <div className="text-center text-slate-400">
                  <p className="text-3xl mb-2">📋</p>
                  <p className="text-sm font-medium">Pilih laporan untuk melihat detail</p>
                </div>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="bg-slate-50 border-2 border-dashed border-slate-300 rounded-xl
                        flex items-center justify-center" style={{ minHeight: 300 }}>
          <div className="text-center text-slate-400 max-w-xs">
            <p className="text-4xl mb-3">📄</p>
            <p className="text-sm font-medium text-slate-600">Belum ada laporan</p>
            <p className="text-xs mt-1">
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
              className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700 flex items-center justify-between"
            >
              <span><strong>{tid}:</strong> {err}</span>
              <button
                onClick={() => setErrors((prev) => {
                  const { [tid]: _, ...rest } = prev
                  return rest
                })}
                className="text-red-400 hover:text-red-600 transition-colors ml-4"
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
