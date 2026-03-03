import React, { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import Plot from 'react-plotly.js'
import { getTender, getXaiExplanation, precomputeDice, getDiceStatus, generateReport } from '../api/client'
import type { OracleSandwichResult, XAILayer, ReportResult, TenderDetailResponse } from '../types/models'

const DARK_RISK_BG: Record<string, string> = {
  'Aman':           'bg-green-900/40 text-green-300 ring-1 ring-green-700/50',
  'Perlu Pantauan': 'bg-amber-900/40 text-amber-300 ring-1 ring-amber-700/50',
  'Risiko Tinggi':  'bg-red-900/40 text-red-300 ring-1 ring-red-700/50',
  'Risiko Kritis':  'bg-red-950 text-red-200 ring-1 ring-red-800',
}

// ============================================================================
// Sub-components
// ============================================================================

function LayerStatusBadge({ layer }: { layer: XAILayer }): React.ReactElement {
  if (layer.status === 'ok') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-emerald-900/40 text-emerald-300 ring-1 ring-emerald-700/50 shadow-[0_0_8px_rgba(16,185,129,0.2)]">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
        OK
      </span>
    )
  }
  if (layer.status === 'not_applicable') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-white/5 text-slate-400 ring-1 ring-white/10">
        N/A
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-red-900/40 text-red-300 ring-1 ring-red-700/50 shadow-[0_0_8px_rgba(244,63,94,0.2)]">
      <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
      Error
    </span>
  )
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
  const baseValue = typeof data.base_value === 'number' ? data.base_value : 0.5
  // Backend returns feature_names[] + shap_values[] as parallel arrays
  // Zip them into [name, value] entries sorted by |SHAP|
  let entries: Array<[string, number]> = []
  const featureNames = data.feature_names as string[] | undefined
  const shapArr = data.shap_values as number[] | undefined
  if (Array.isArray(featureNames) && Array.isArray(shapArr)) {
    entries = featureNames
      .map((name, i): [string, number] => [name, shapArr[i] ?? 0])
      .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
      .slice(0, 12)
  } else {
    // Fallback: shap_values as Record<string, number>
    const shapObj = (data.shap_values ?? data.values ?? {}) as Record<string, number>
    entries = Object.entries(shapObj)
      .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
      .slice(0, 12)
  }

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
        xaxis: { title: 'Kontribusi SHAP', zeroline: true, zerolinecolor: '#334155', color: '#64748b', gridcolor: '#1e293b' },
        yaxis: { automargin: true, color: '#94a3b8', gridcolor: '#1e293b' },
        shapes: [
          {
            type: 'line',
            x0: 0, x1: 0,
            y0: -0.5, y1: entries.length - 0.5,
            line: { color: '#475569', width: 1.5, dash: 'dot' },
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
        plot_bgcolor: '#0f172a',
        paper_bgcolor: 'rgba(255,255,255,0.03)',
        font: { family: 'Inter, system-ui, sans-serif', size: 12, color: '#94a3b8' },
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
          <div className="flex items-center gap-2 bg-white/5 border border-white/10 rounded-lg px-3 py-1.5">
            <span className="text-slate-500">Presisi:</span>
            <span className="font-semibold font-mono text-slate-200">{(precision * 100).toFixed(1)}%</span>
          </div>
          {coverage !== null && (
            <div className="flex items-center gap-2 bg-white/5 border border-white/10 rounded-lg px-3 py-1.5">
              <span className="text-slate-500">Cakupan:</span>
              <span className="font-semibold font-mono text-slate-200">{(coverage * 100).toFixed(1)}%</span>
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
              className="flex items-start gap-2 bg-indigo-950/40 border border-indigo-700/40 rounded-lg px-3 py-2"
            >
              <span className="text-indigo-400 font-bold text-sm mt-0.5">IF</span>
              <code className="text-slate-300 text-sm font-mono">{rule}</code>
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

function DiceDisplay({ layer, features }: { layer: XAILayer; features: Record<string, number> }): React.ReactElement {
  const [loading, setLoading] = useState(false)
  const [triggered, setTriggered] = useState(false)
  const [statusMsg, setStatusMsg] = useState('')
  const [tenderId, setTenderId] = useState('')

  async function triggerDice(tid: string): Promise<void> {
    setLoading(true)
    setTriggered(true)
    try {
      await precomputeDice(tid, features, 3)
      setStatusMsg('DiCE sedang dihitung di background...')
      setTimeout(async () => {
        try {
          const s = await getDiceStatus(tid)
          setStatusMsg(
            s.status === 'done'
              ? '✓ DiCE selesai — muat ulang XAI untuk melihat hasil'
              : `Status: ${s.status}`,
          )
        } catch {
          setStatusMsg('Tidak dapat cek status')
        }
      }, 3000)
    } catch {
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
        <div className="overflow-x-auto bg-white/5 border border-white/10 rounded-xl">
          <p className="text-xs text-slate-400 p-4 pb-0">
            {cfs.length} skenario kontrafaktual — perubahan minimal untuk mengurangi risiko:
          </p>
          <table className="text-xs w-full border-collapse mt-2">
            <thead className="bg-white/5 text-slate-400">
              <tr>
                <th className="px-3 py-2 text-left border border-white/10">#</th>
                {allKeys.map((k) => (
                  <th key={k} className="px-3 py-2 text-left border border-white/10">
                    {k}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {cfs.map((cf, i) => (
                <tr key={i} className="motion-safe:hover:bg-white/5 motion-safe:transition-colors">
                  <td className="px-3 py-2 font-bold text-slate-300 border border-white/10">{i + 1}</td>
                  {allKeys.map((k) => (
                    <td key={k} className="px-3 py-2 text-slate-300 border border-white/10 font-mono">
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
        <div className="space-y-2">
          <input
            type="text"
            placeholder="Tender ID"
            value={tenderId}
            onChange={(e) => setTenderId(e.target.value)}
            className="bg-white/5 border border-white/10 text-slate-200 placeholder:text-slate-600 rounded-lg px-3 py-1.5 text-sm font-mono
                       focus:border-cyan-500/50 focus:shadow-[0_0_15px_rgba(6,182,212,0.2)] focus:outline-none
                       motion-safe:transition-all w-48"
          />
          <div>
            <button
              onClick={() => { void triggerDice(tenderId) }}
              disabled={loading || !tenderId.trim()}
              className="px-4 py-2 bg-gradient-to-r from-indigo-600 to-cyan-600 hover:from-indigo-500 hover:to-cyan-500
                         text-white text-sm font-medium rounded-lg disabled:opacity-60
                         motion-safe:hover:scale-105 motion-safe:hover:shadow-[0_0_20px_rgba(6,182,212,0.3)]
                         motion-safe:transition-all duration-200"
            >
              {loading ? '⏳ Memulai...' : '🎲 Hitung Kontrafaktual DiCE'}
            </button>
          </div>
        </div>
      ) : (
        <p className="text-sm text-cyan-400 font-medium">{statusMsg}</p>
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
          className={`flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-semibold border ${
            suspicious
              ? 'bg-red-900/40 text-red-300 border-red-700/50 shadow-[0_0_15px_rgba(244,63,94,0.2)]'
              : 'bg-emerald-900/40 text-emerald-300 border-emerald-700/50 shadow-[0_0_15px_rgba(16,185,129,0.2)]'
          }`}
        >
          {suspicious ? '⚠ Distribusi Mencurigakan' : '✓ Distribusi Normal'}
        </div>
        {chi2 !== null && (
          <div className="text-sm text-slate-400 bg-white/5 border border-white/10 rounded-lg px-3 py-1.5">
            χ² = <span className="font-mono font-medium text-slate-200">{chi2.toFixed(3)}</span>
            {pValue !== null && (
              <span className="ml-2">
                p = <span className="font-mono font-medium text-slate-200">{pValue.toFixed(4)}</span>
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
            xaxis: { title: 'Digit Pertama', color: '#64748b', gridcolor: '#1e293b' },
            yaxis: { title: 'Frekuensi Relatif', color: '#64748b', gridcolor: '#1e293b' },
            legend: { orientation: 'h', y: -0.25, font: { color: '#94a3b8' } },
            plot_bgcolor: '#0f172a',
            paper_bgcolor: 'rgba(255,255,255,0.03)',
            font: { family: 'Inter, system-ui, sans-serif', size: 11, color: '#94a3b8' },
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
          <div className="bg-gradient-to-br from-indigo-600/20 to-indigo-900/40 border border-indigo-500/20 rounded-xl p-3 text-center">
            <p className="text-xs text-slate-400 mb-1">Komunitas ID</p>
            <p className="text-xl font-bold font-mono text-white">#{String(communityId)}</p>
          </div>
        )}
        {size !== undefined && (
          <div className="bg-gradient-to-br from-cyan-600/20 to-sky-900/40 border border-cyan-500/20 rounded-xl p-3 text-center">
            <p className="text-xs text-slate-400 mb-1">Ukuran Komunitas</p>
            <p className="text-xl font-bold font-mono text-white">{String(size)} vendor</p>
          </div>
        )}
        {riskScore !== null && (
          <div className="bg-gradient-to-br from-red-600/20 to-rose-900/40 border border-red-500/20 rounded-xl p-3 text-center">
            <p className="text-xs text-slate-400 mb-1">Skor Risiko Kartel</p>
            <p className="text-xl font-bold font-mono text-white">{(riskScore * 100).toFixed(1)}%</p>
          </div>
        )}
      </div>
      <Link
        to="/cartel"
        className="block text-center text-sm text-cyan-400 hover:text-cyan-300 motion-safe:transition-colors underline underline-offset-2"
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
  { key: 'shap',    label: 'SHAP',        emoji: '📊' },
  { key: 'anchors', label: 'Anchors',     emoji: '⚓' },
  { key: 'dice',    label: 'DiCE',        emoji: '🎲' },
  { key: 'benford', label: 'Benford',     emoji: '📈' },
  { key: 'leiden',  label: 'Leiden/Graf', emoji: '🕸' },
]

const RISK_LEVEL_LABEL: Record<string, string> = {
  high:   'Risiko Tinggi',
  medium: 'Perlu Pantauan',
  low:    'Aman',
}

export function TenderDetail(): React.ReactElement {
  const { id: tenderId = '' } = useParams<{ id: string }>()
  const [activeTab, setActiveTab] = useState<TabKey>('shap')
  const [tenderData, setTenderData] = useState<TenderDetailResponse | null>(null)
  const [tenderLoading, setTenderLoading] = useState(false)
  const [tenderError, setTenderError] = useState<string | null>(null)
  const [xaiData, setXaiData] = useState<OracleSandwichResult | null>(null)
  const [report, setReport] = useState<ReportResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [reportLoading, setReportLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!tenderId) return
    setTenderLoading(true)
    setTenderError(null)
    getTender(tenderId)
      .then((resp) => { setTenderData(resp) })
      .catch((err: unknown) => {
        setTenderError(err instanceof Error ? err.message : 'Gagal memuat data tender')
      })
      .finally(() => { setTenderLoading(false) })
  }, [tenderId])

  async function runXai(): Promise<void> {
    const features = tenderData?.features ?? {}
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
    const features = tenderData?.features ?? {}
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
      case 'dice':    return <DiceDisplay layer={layer} features={features} />
      case 'benford': return <BenfordDisplay layer={layer} />
      case 'leiden':  return <LeidenDisplay layer={layer} />
    }
  }

  const riskCls = report ? (DARK_RISK_BG[report.risk_level] ?? 'bg-white/5 text-slate-400 ring-1 ring-white/10') : ''

  const predLevel = tenderData?.prediction?.risk_level
  const predLabel = predLevel ? (RISK_LEVEL_LABEL[predLevel] ?? predLevel) : null
  const predScore = tenderData?.prediction?.risk_score
  const isHighRisk = predLevel === 'high'

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3 motion-safe:animate-[fade-in-up_0.4s_ease-out_both]">
        <Link
          to="/"
          className="flex items-center gap-1.5 px-3 py-1.5 bg-white/5 border border-white/10 text-slate-400
                     hover:bg-white/10 hover:text-slate-200 rounded-lg text-sm motion-safe:transition-all duration-200"
        >
          ← Kembali
        </Link>
        <h1 className="text-2xl font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
          Analisis XAI — <span className="font-mono text-cyan-400">{tenderId}</span>
        </h1>
      </div>

      {/* Tender metadata card */}
      {tenderLoading && (
        <div className="glass-card p-4 text-sm text-slate-400 flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="motion-safe:animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500" />
          </span>
          Memuat data tender...
        </div>
      )}
      {tenderError && (
        <div className="bg-red-950/40 border border-red-700/50 rounded-xl p-4 text-red-300 text-sm">
          <strong>Error memuat tender:</strong> {tenderError}
        </div>
      )}
      {tenderData && (
        <div className={`glass-card p-5 flex flex-wrap gap-6 items-start ${
          isHighRisk ? 'border-red-500/20 shadow-[0_0_20px_rgba(244,63,94,0.1)]' : ''
        }`}>
          <div className="flex-1 min-w-0">
            <p className="text-base font-semibold text-slate-200 truncate">{tenderData.title}</p>
            <p className="text-sm text-slate-400 mt-1">{tenderData.buyer_name}</p>
          </div>
          {predLabel && (
            <span className={`px-3 py-1 rounded-full text-sm font-bold flex-shrink-0
              ${DARK_RISK_BG[predLabel] ?? 'bg-white/5 text-slate-400 ring-1 ring-white/10'}
              ${isHighRisk ? 'shadow-[0_0_15px_rgba(244,63,94,0.3)]' : ''}`}>
              {predLabel} {predScore !== undefined ? `(${Math.round(predScore * 100)}%)` : ''}
            </span>
          )}
        </div>
      )}

      {/* Action buttons */}
      <div className="flex gap-3 flex-wrap">
        <button
          onClick={() => { void runXai() }}
          disabled={loading || tenderLoading}
          className="px-5 py-2.5 bg-gradient-to-r from-indigo-600 to-cyan-600
                     hover:from-indigo-500 hover:to-cyan-500 text-white text-sm font-semibold rounded-lg
                     disabled:opacity-60 motion-safe:hover:scale-105
                     motion-safe:hover:shadow-[0_0_20px_rgba(6,182,212,0.35)]
                     motion-safe:transition-all duration-200 flex items-center gap-2"
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
            className="px-5 py-2.5 bg-gradient-to-r from-emerald-700 to-teal-600
                       hover:from-emerald-600 hover:to-teal-500 text-white text-sm font-semibold rounded-lg
                       disabled:opacity-60 motion-safe:hover:scale-105
                       motion-safe:hover:shadow-[0_0_20px_rgba(16,185,129,0.3)]
                       motion-safe:transition-all duration-200"
          >
            {reportLoading ? '⏳ Membuat laporan...' : '📋 Buat Laporan IIA 2025'}
          </button>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-950/40 border border-red-700/50 rounded-xl p-4 text-red-300 text-sm">
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Oracle Sandwich result */}
      {xaiData && (
        <div className="glass-card overflow-hidden motion-safe:animate-[fade-in-up_0.4s_ease-out_both]">
          {/* Summary bar */}
          <div className="px-6 py-4 border-b border-white/10 bg-white/5 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <h2 className="text-base font-semibold text-slate-200">Oracle Sandwich — 5 Lapisan XAI</h2>
              <span className="text-sm text-slate-500 bg-white/5 px-3 py-1 rounded-full font-mono">
                {xaiData.layers_ok}/{xaiData.layers_ok + xaiData.layers_failed} lapisan
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
          <div className="border-b border-white/10 flex bg-white/5">
            {TABS.map((t) => (
              <button
                key={t.key}
                onClick={() => setActiveTab(t.key)}
                className={`px-5 py-3 text-sm font-medium border-b-2 motion-safe:transition-all duration-200 ${
                  activeTab === t.key
                    ? 'border-cyan-400 text-cyan-300 bg-white/5 shadow-[0_-2px_20px_rgba(6,182,212,0.1)]'
                    : 'border-transparent text-slate-500 hover:text-slate-300 hover:border-white/20'
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
        <div className="glass-card overflow-hidden motion-safe:animate-[fade-in-up_0.4s_ease-out_both]">
          <div className="px-6 py-4 border-b border-white/10 bg-white/5 flex items-center justify-between">
            <h2 className="text-base font-semibold text-slate-200 flex items-center gap-2">
              <span className="w-1.5 h-4 rounded-full bg-gradient-to-b from-cyan-400 to-indigo-500" />
              Laporan Pra-Investigasi
            </h2>
            <div className="flex items-center gap-3">
              <span className={`px-3 py-1 rounded-full text-sm font-semibold ${riskCls}`}>
                {report.risk_level}
              </span>
              <button
                onClick={() => window.print()}
                className="px-3 py-1.5 text-xs bg-white/5 border border-white/10 hover:bg-white/10 text-slate-300 rounded-lg motion-safe:transition-all duration-200"
              >
                🖨 Cetak / PDF
              </button>
            </div>
          </div>
          <div className="p-6 space-y-4">
            {/* Score + evidence */}
            <div className="flex items-center gap-4 text-sm">
              {[
                { label: 'Skor Risiko', value: `${report.risk_score}/3`, cls: 'text-red-400' },
                { label: 'Bukti', value: String(report.evidence_count), cls: 'text-amber-400' },
                { label: 'Dibuat', value: new Date(report.generated_at).toLocaleString('id-ID'), cls: 'text-slate-300' },
              ].map(({ label, value, cls }) => (
                <div key={label} className="flex items-center gap-2 bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-xs">
                  <span className="text-slate-500">{label}:</span>
                  <strong className={`font-mono ${cls}`}>{value}</strong>
                </div>
              ))}
            </div>
            {/* Recommendations */}
            {report.recommendations.length > 0 && (
              <div className="bg-amber-950/30 border border-amber-700/50 rounded-xl p-4">
                <p className="text-sm font-semibold text-amber-300 mb-2">Rekomendasi:</p>
                <ul className="space-y-1">
                  {report.recommendations.map((rec, i) => (
                    <li key={i} className="text-sm text-amber-200/80 flex gap-2">
                      <span className="text-amber-600 font-bold">{i + 1}.</span>
                      {rec}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {/* Full report text */}
            <div>
              <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                Teks Laporan Lengkap
              </h4>
              <pre className="bg-white/5 border border-white/10 rounded-xl p-5 text-xs text-slate-300 font-mono whitespace-pre-wrap leading-relaxed overflow-x-auto">
                {report.report_text}
              </pre>
            </div>
          </div>
        </div>
      )}

      {/* Placeholder before running XAI */}
      {!xaiData && !loading && (
        <div className="glass-card border-2 border-dashed border-white/10 p-10 text-center">
          <p className="text-4xl mb-3">🔮</p>
          <p className="text-slate-400 font-medium">Oracle Sandwich siap dijalankan</p>
          <p className="text-slate-500 text-sm mt-1">
            Klik tombol "Jalankan Oracle Sandwich XAI" untuk melihat penjelasan 5-lapisan
          </p>
        </div>
      )}
    </div>
  )
}
