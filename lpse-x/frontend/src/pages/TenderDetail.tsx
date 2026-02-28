import React, { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import Plot from 'react-plotly.js'
import { getXaiExplanation, precomputeDice, getDiceStatus, generateReport } from '../api/client'
import { RISK_BG } from '../types/models'
import type { OracleSandwichResult, XAILayer, ReportResult } from '../types/models'

// ============================================================================
// Demo feature vectors (keyed by tender_id)
// ============================================================================

const DEMO_FEATURES: Record<string, Record<string, number>> = {
  'ID-2024-0001': { n_bidders: 1.0, price_ratio: 0.995, bid_spread: 0.005, winner_bid_rank: 1.0, hhi: 0.95, log_amount: 21.33 },
  'ID-2024-0002': { n_bidders: 5.0, price_ratio: 0.87,  bid_spread: 0.13,  winner_bid_rank: 2.0, hhi: 0.25, log_amount: 20.9  },
  'ID-2024-0003': { n_bidders: 1.0, price_ratio: 0.999, bid_spread: 0.001, winner_bid_rank: 1.0, hhi: 1.0,  log_amount: 19.67 },
  'ID-2024-0004': { n_bidders: 3.0, price_ratio: 0.92,  bid_spread: 0.08,  winner_bid_rank: 1.0, hhi: 0.45, log_amount: 21.75 },
  'ID-2024-0005': { n_bidders: 2.0, price_ratio: 0.985, bid_spread: 0.015, winner_bid_rank: 1.0, hhi: 0.72, log_amount: 22.45 },
}

// ============================================================================
// Sub-components
// ============================================================================

function LayerStatusBadge({ layer }: { layer: XAILayer }): React.ReactElement {
  if (layer.status === 'ok') {
    return <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700">✓ OK</span>
  }
  if (layer.status === 'not_applicable') {
    return <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-500">N/A</span>
  }
  return <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-700">✗ Error</span>
}

// ---- SHAP Waterfall ----

function ShapWaterfall({ layer }: { layer: XAILayer }): React.ReactElement {
  if (layer.status !== 'ok' || !layer.data) {
    return (
      <div className="text-center py-8 text-slate-400 text-sm">
        {layer.status === 'not_applicable' ? 'Data tidak tersedia' : layer.error ?? 'Gagal memuat SHAP'}
      </div>
    )
  }

  const data = layer.data as Record<string, unknown>
  const shapValues = (data.shap_values ?? data.values ?? {}) as Record<string, number>
  const baseValue = typeof data.base_value === 'number' ? data.base_value : 0.5

  const entries = Object.entries(shapValues)
    .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
    .slice(0, 12)

  if (entries.length === 0) {
    return <div className="text-center py-8 text-slate-400 text-sm">Tidak ada data SHAP</div>
  }

  const features = entries.map(([k]) => k)
  const values = entries.map(([, v]) => v)
  const colors = values.map((v) => (v > 0 ? '#ef4444' : '#22c55e'))

  return (
    <Plot
      data={[
        {
          type: 'bar',
          orientation: 'h',
          x: values,
          y: features,
          marker: { color: colors },
          hovertemplate: '<b>%{y}</b><br>SHAP: %{x:.4f}<extra></extra>',
        },
      ]}
      layout={{
        height: Math.max(280, entries.length * 28),
        margin: { l: 140, r: 20, t: 30, b: 40 },
        xaxis: { title: 'Kontribusi SHAP', zeroline: true, zerolinecolor: '#94a3b8' },
        yaxis: { automargin: true },
        shapes: [
          {
            type: 'line',
            x0: 0, x1: 0,
            y0: -0.5, y1: entries.length - 0.5,
            line: { color: '#64748b', width: 1.5, dash: 'dot' },
          },
        ],
        annotations: [
          {
            x: 0,
            y: entries.length + 0.2,
            xref: 'x', yref: 'y',
            text: `Base value: ${baseValue.toFixed(3)}`,
            showarrow: false,
            font: { size: 11, color: '#64748b' },
          },
        ],
        plot_bgcolor: '#f8fafc',
        paper_bgcolor: '#ffffff',
        font: { family: 'Inter, system-ui, sans-serif', size: 12 },
      }}
      config={{ responsive: true, displayModeBar: false }}
      style={{ width: '100%' }}
    />
  )
}

// ---- Anchors Rules ----

function AnchorsDisplay({ layer }: { layer: XAILayer }): React.ReactElement {
  if (layer.status !== 'ok' || !layer.data) {
    return (
      <div className="text-center py-8 text-slate-400 text-sm">
        {layer.status === 'not_applicable' ? 'Data tidak tersedia' : layer.error ?? 'Gagal memuat Anchors'}
      </div>
    )
  }

  const data = layer.data as Record<string, unknown>
  const rules = (data.rules ?? data.anchor ?? []) as string[]
  const precision = typeof data.precision === 'number' ? data.precision : null
  const coverage = typeof data.coverage === 'number' ? data.coverage : null

  return (
    <div className="space-y-3">
      {precision !== null && (
        <div className="flex gap-4 text-sm">
          <div className="flex items-center gap-2">
            <span className="text-slate-500">Presisi:</span>
            <span className="font-semibold text-slate-700">{(precision * 100).toFixed(1)}%</span>
          </div>
          {coverage !== null && (
            <div className="flex items-center gap-2">
              <span className="text-slate-500">Cakupan:</span>
              <span className="font-semibold text-slate-700">{(coverage * 100).toFixed(1)}%</span>
            </div>
          )}
        </div>
      )}
      {rules.length > 0 ? (
        <div className="space-y-2">
          <p className="text-xs text-slate-500 font-medium uppercase tracking-wide">Aturan Penjelas:</p>
          {rules.map((rule, i) => (
            <div
              key={i}
              className="flex items-start gap-2 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2"
            >
              <span className="text-amber-600 font-bold text-sm mt-0.5">IF</span>
              <code className="text-sm text-slate-700 font-mono">{rule}</code>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-4 text-slate-400 text-sm">Tidak ada aturan anchor</div>
      )}
    </div>
  )
}

// ---- DiCE Counterfactuals ----

function DiceDisplay({ layer, tenderId }: { layer: XAILayer; tenderId: string }): React.ReactElement {
  const [loading, setLoading] = useState(false)
  const [triggered, setTriggered] = useState(false)
  const [statusMsg, setStatusMsg] = useState('')

  async function triggerDice(): Promise<void> {
    const features = DEMO_FEATURES[tenderId] ?? {}
    setLoading(true)
    setTriggered(true)
    try {
      await precomputeDice(tenderId, features, 3)
      setStatusMsg('DiCE sedang dihitung di background...')
      // Poll once after 3s
      setTimeout(async () => {
        try {
          const s = await getDiceStatus(tenderId)
          setStatusMsg(
            s.status === 'done'
              ? '✓ DiCE selesai — muat ulang XAI untuk melihat hasil'
              : `Status: ${s.status}`,
          )
        } catch {
          setStatusMsg('Tidak dapat cek status')
        }
      }, 3000)
    } catch (err) {
      setStatusMsg('Gagal memulai DiCE')
    } finally {
      setLoading(false)
    }
  }

  if (layer.status === 'ok' && layer.data) {
    const data = layer.data as Record<string, unknown>
    const cfs = (data.counterfactuals ?? data.cfs ?? []) as Array<Record<string, unknown>>
    if (cfs.length > 0) {
      const allKeys = [...new Set(cfs.flatMap((cf) => Object.keys(cf)))]
      return (
        <div className="overflow-x-auto">
          <p className="text-xs text-slate-500 mb-2">
            {cfs.length} skenario kontrafaktual — perubahan minimal untuk mengurangi risiko:
          </p>
          <table className="text-xs w-full border-collapse">
            <thead>
              <tr className="bg-slate-50">
                <th className="px-3 py-2 text-left text-slate-500 border border-gray-200">#</th>
                {allKeys.map((k) => (
                  <th key={k} className="px-3 py-2 text-left text-slate-500 border border-gray-200">
                    {k}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {cfs.map((cf, i) => (
                <tr key={i} className="hover:bg-blue-50 transition-colors">
                  <td className="px-3 py-2 font-bold text-blue-600 border border-gray-200">{i + 1}</td>
                  {allKeys.map((k) => (
                    <td key={k} className="px-3 py-2 text-slate-700 border border-gray-200 font-mono">
                      {typeof cf[k] === 'number' ? (cf[k] as number).toFixed(3) : String(cf[k] ?? '—')}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )
    }
  }

  return (
    <div className="text-center py-6 space-y-3">
      <p className="text-slate-500 text-sm">
        {layer.status === 'not_applicable'
          ? 'DiCE belum dihitung untuk tender ini.'
          : layer.error ?? 'Hasil DiCE tidak tersedia.'}
      </p>
      {!triggered ? (
        <button
          onClick={() => { void triggerDice() }}
          disabled={loading}
          className="px-4 py-2 bg-purple-600 text-white text-sm font-medium rounded-lg
                     hover:bg-purple-700 disabled:opacity-60 transition-colors"
        >
          {loading ? '⏳ Memulai...' : '🎲 Hitung Kontrafaktual DiCE'}
        </button>
      ) : (
        <p className="text-sm text-purple-600 font-medium">{statusMsg}</p>
      )}
    </div>
  )
}

// ---- Benford Analysis ----

function BenfordDisplay({ layer }: { layer: XAILayer }): React.ReactElement {
  if (layer.status !== 'ok' || !layer.data) {
    return (
      <div className="text-center py-8 text-slate-400 text-sm">
        {layer.status === 'not_applicable'
          ? 'Analisis Benford tidak berlaku (data tidak memenuhi syarat)'
          : layer.error ?? 'Data Benford tidak tersedia'}
      </div>
    )
  }

  const data = layer.data as Record<string, unknown>
  const suspicious = data.suspicious === true
  const chi2 = typeof data.chi2 === 'number' ? data.chi2 : null
  const pValue = typeof data.p_value === 'number' ? data.p_value : null
  const observed = (data.observed_freq ?? data.observed ?? {}) as Record<string, number>
  const expected = (data.expected_freq ?? data.expected ?? {}) as Record<string, number>

  const digits = ['1', '2', '3', '4', '5', '6', '7', '8', '9']
  const obsVals = digits.map((d) => observed[d] ?? 0)
  const expVals = digits.map((d) => expected[d] ?? (Math.log10(1 + 1 / Number(d))))

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <div
          className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-semibold ${
            suspicious
              ? 'bg-red-100 text-red-700 border border-red-300'
              : 'bg-green-100 text-green-700 border border-green-300'
          }`}
        >
          {suspicious ? '⚠ Distribusi Mencurigakan' : '✓ Distribusi Normal'}
        </div>
        {chi2 !== null && (
          <div className="text-sm text-slate-600">
            χ² = <span className="font-mono font-medium">{chi2.toFixed(3)}</span>
            {pValue !== null && (
              <span className="ml-2">
                p = <span className="font-mono font-medium">{pValue.toFixed(4)}</span>
              </span>
            )}
          </div>
        )}
      </div>
      {obsVals.some((v) => v > 0) && (
        <Plot
          data={[
            {
              type: 'bar',
              name: 'Observasi',
              x: digits,
              y: obsVals,
              marker: { color: suspicious ? '#ef4444' : '#3b82f6' },
            },
            {
              type: 'scatter',
              mode: 'lines+markers',
              name: 'Benford Teoritis',
              x: digits,
              y: expVals,
              line: { color: '#64748b', dash: 'dot', width: 2 },
              marker: { color: '#64748b', size: 6 },
            },
          ]}
          layout={{
            height: 240,
            margin: { l: 40, r: 20, t: 20, b: 40 },
            xaxis: { title: 'Digit Pertama' },
            yaxis: { title: 'Frekuensi Relatif' },
            legend: { orientation: 'h', y: -0.25 },
            plot_bgcolor: '#f8fafc',
            paper_bgcolor: '#ffffff',
            font: { family: 'Inter, system-ui, sans-serif', size: 11 },
          }}
          config={{ responsive: true, displayModeBar: false }}
          style={{ width: '100%' }}
        />
      )}
    </div>
  )
}

// ---- Leiden Community ----

function LeidenDisplay({ layer }: { layer: XAILayer }): React.ReactElement {
  if (layer.status !== 'ok' || !layer.data) {
    return (
      <div className="text-center py-8 text-slate-400 text-sm">
        {layer.status === 'not_applicable'
          ? 'Vendor belum terdaftar dalam komunitas kartel'
          : layer.error ?? 'Data Leiden tidak tersedia'}
      </div>
    )
  }

  const data = layer.data as Record<string, unknown>
  const communityId = data.community_id ?? data.leiden_community_id
  const size = data.community_size ?? data.leiden_community_size
  const riskScore = typeof data.risk_score === 'number' ? data.risk_score : null

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-3 gap-3">
        {communityId !== undefined && (
          <div className="bg-slate-50 rounded-lg p-3 text-center">
            <p className="text-xs text-slate-500 mb-1">Komunitas ID</p>
            <p className="text-xl font-bold text-slate-700">#{String(communityId)}</p>
          </div>
        )}
        {size !== undefined && (
          <div className="bg-slate-50 rounded-lg p-3 text-center">
            <p className="text-xs text-slate-500 mb-1">Ukuran Komunitas</p>
            <p className="text-xl font-bold text-slate-700">{String(size)} vendor</p>
          </div>
        )}
        {riskScore !== null && (
          <div className="bg-red-50 rounded-lg p-3 text-center">
            <p className="text-xs text-slate-500 mb-1">Skor Risiko Kartel</p>
            <p className="text-xl font-bold text-red-600">{(riskScore * 100).toFixed(1)}%</p>
          </div>
        )}
      </div>
      <Link
        to="/cartel"
        className="block text-center text-sm text-blue-600 hover:text-blue-800 underline underline-offset-2 transition-colors"
      >
        Lihat Grafik Jaringan Kartel →
      </Link>
    </div>
  )
}

// ============================================================================
// Main TenderDetail page
// ============================================================================

type TabKey = 'shap' | 'anchors' | 'dice' | 'benford' | 'leiden'

const TABS: Array<{ key: TabKey; label: string; emoji: string }> = [
  { key: 'shap',    label: 'SHAP',         emoji: '📊' },
  { key: 'anchors', label: 'Anchors',      emoji: '⚓' },
  { key: 'dice',    label: 'DiCE',         emoji: '🎲' },
  { key: 'benford', label: "Benford",      emoji: '📈' },
  { key: 'leiden',  label: 'Leiden/Graf',  emoji: '🕸' },
]

export function TenderDetail(): React.ReactElement {
  const { id: tenderId = 'ID-2024-0001' } = useParams<{ id: string }>()
  const [activeTab, setActiveTab] = useState<TabKey>('shap')
  const [xaiData, setXaiData] = useState<OracleSandwichResult | null>(null)
  const [report, setReport] = useState<ReportResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [reportLoading, setReportLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function runXai(): Promise<void> {
    const features = DEMO_FEATURES[tenderId] ?? {}
    setLoading(true)
    setError(null)
    try {
      const resp = await getXaiExplanation(tenderId, { features })
      setXaiData(resp.data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Gagal memuat XAI')
    } finally {
      setLoading(false)
    }
  }

  async function runReport(): Promise<void> {
    setReportLoading(true)
    try {
      const oracle = xaiData
        ? {
            tender_id: xaiData.tender_id,
            layers_ok: xaiData.layers_ok,
            layers_failed: xaiData.layers_failed,
            total_seconds: xaiData.total_seconds,
            shap: xaiData.shap,
            anchors: xaiData.anchors,
            leiden: xaiData.leiden,
            benford: xaiData.benford,
            dice: xaiData.dice,
          }
        : undefined
      const r = await generateReport(tenderId, oracle as Record<string, unknown> | undefined)
      setReport(r)
    } catch {
      // silently fail - report is optional
    } finally {
      setReportLoading(false)
    }
  }

  function renderTabContent(): React.ReactElement {
    if (!xaiData) return <></>
    const layerMap: Record<TabKey, XAILayer> = {
      shap:    xaiData.shap,
      anchors: xaiData.anchors,
      dice:    xaiData.dice,
      benford: xaiData.benford,
      leiden:  xaiData.leiden,
    }
    const layer = layerMap[activeTab]
    switch (activeTab) {
      case 'shap':    return <ShapWaterfall layer={layer} />
      case 'anchors': return <AnchorsDisplay layer={layer} />
      case 'dice':    return <DiceDisplay layer={layer} tenderId={tenderId} />
      case 'benford': return <BenfordDisplay layer={layer} />
      case 'leiden':  return <LeidenDisplay layer={layer} />
    }
  }

  const riskCls = report ? (RISK_BG[report.risk_level] ?? 'bg-gray-100 text-gray-700') : ''

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link to="/" className="text-slate-400 hover:text-slate-600 transition-colors text-sm">
          ← Kembali
        </Link>
        <h1 className="text-2xl font-bold text-slate-800">
          Analisis XAI — {tenderId}
        </h1>
      </div>

      {/* Action buttons */}
      <div className="flex gap-3 flex-wrap">
        <button
          onClick={() => { void runXai() }}
          disabled={loading}
          className="px-5 py-2.5 bg-blue-600 text-white text-sm font-semibold rounded-lg
                     hover:bg-blue-700 disabled:opacity-60 transition-colors flex items-center gap-2"
        >
          {loading ? (
            <>
              <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4l3-3-3-3v4a8 8 0 00-8 8h4z" />
              </svg>
              Memuat Oracle Sandwich...
            </>
          ) : (
            <>🔮 Jalankan Oracle Sandwich XAI</>
          )}
        </button>
        {xaiData && (
          <button
            onClick={() => { void runReport() }}
            disabled={reportLoading}
            className="px-5 py-2.5 bg-emerald-600 text-white text-sm font-semibold rounded-lg
                       hover:bg-emerald-700 disabled:opacity-60 transition-colors"
          >
            {reportLoading ? '⏳ Membuat laporan...' : '📋 Buat Laporan IIA 2025'}
          </button>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 text-sm">
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Oracle Sandwich result */}
      {xaiData && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          {/* Summary bar */}
          <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between bg-slate-50">
            <div className="flex items-center gap-4">
              <h2 className="text-lg font-semibold text-slate-700">Oracle Sandwich — 5 Lapisan XAI</h2>
              <span className="text-sm text-slate-500">
                {xaiData.layers_ok}/{xaiData.layers_ok + xaiData.layers_failed} lapisan berhasil
                &nbsp;•&nbsp;{xaiData.total_seconds.toFixed(2)}s
              </span>
            </div>
            <div className="flex gap-2">
              {TABS.map((t) => {
                const lyr = { shap: xaiData.shap, anchors: xaiData.anchors, dice: xaiData.dice, benford: xaiData.benford, leiden: xaiData.leiden }[t.key]
                return (
                  <div key={t.key} className="flex items-center gap-1">
                    <LayerStatusBadge layer={lyr} />
                  </div>
                )
              })}
            </div>
          </div>

          {/* Tabs */}
          <div className="border-b border-gray-200 flex">
            {TABS.map((t) => (
              <button
                key={t.key}
                onClick={() => setActiveTab(t.key)}
                className={`px-5 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === t.key
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
                }`}
              >
                {t.emoji} {t.label}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div className="p-6">
            {renderTabContent()}
          </div>
        </div>
      )}

      {/* Report */}
      {report && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-slate-700">Laporan Pra-Investigasi</h2>
            <div className="flex items-center gap-3">
              <span className={`px-3 py-1 rounded-full text-sm font-semibold ${riskCls}`}>
                {report.risk_level}
              </span>
              <button
                onClick={() => window.print()}
                className="px-3 py-1.5 text-xs bg-gray-100 hover:bg-gray-200 text-slate-700
                           rounded-lg transition-colors font-medium"
              >
                🖨 Cetak / PDF
              </button>
            </div>
          </div>
          <div className="p-6 space-y-4">
            {/* Score + evidence */}
            <div className="flex items-center gap-6 text-sm text-slate-600">
              <span>Skor Risiko: <strong>{report.risk_score}/3</strong></span>
              <span>Bukti: <strong>{report.evidence_count}</strong></span>
              <span>Dibuat: <strong>{new Date(report.generated_at).toLocaleString('id-ID')}</strong></span>
            </div>
            {/* Recommendations */}
            {report.recommendations.length > 0 && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                <p className="text-sm font-semibold text-amber-800 mb-2">Rekomendasi:</p>
                <ul className="space-y-1">
                  {report.recommendations.map((rec, i) => (
                    <li key={i} className="text-sm text-amber-900 flex gap-2">
                      <span className="text-amber-600 font-bold">{i + 1}.</span>
                      {rec}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {/* Full report text */}
            <div className="bg-slate-50 rounded-lg p-5">
              <pre className="text-xs text-slate-700 whitespace-pre-wrap font-mono leading-relaxed">
                {report.report_text}
              </pre>
            </div>
          </div>
        </div>
      )}

      {/* Placeholder before running XAI */}
      {!xaiData && !loading && (
        <div className="bg-slate-50 border-2 border-dashed border-slate-300 rounded-xl p-10 text-center">
          <p className="text-4xl mb-3">🔮</p>
          <p className="text-slate-600 font-medium">Oracle Sandwich siap dijalankan</p>
          <p className="text-slate-400 text-sm mt-1">
            Klik tombol "Jalankan Oracle Sandwich XAI" untuk melihat penjelasan 5-lapisan
          </p>
        </div>
      )}
    </div>
  )
}
