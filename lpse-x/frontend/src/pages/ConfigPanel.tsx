import React, { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { injectConfig, getConfig, getConfigLog } from '../api/client'
import type { InjectionRequest, InjectionResponse, ProcurementScope, AnomalyMethod, OutputFormat } from '../types/models'

// ============================================================================
// Field validation helpers
// ============================================================================

function clampThreshold(v: string): number | undefined {
  const n = parseFloat(v)
  if (isNaN(n)) return undefined
  return Math.min(1.0, Math.max(0.0, n))
}

function parseYearRange(v: string): [number, number] | undefined {
  const parts = v.split(',').map((s) => parseInt(s.trim(), 10))
  if (parts.length === 2 && parts[0] && parts[1] && !isNaN(parts[0]) && !isNaN(parts[1])) {
    return [parts[0], parts[1]] as [number, number]
  }
  return undefined
}

function parseInstitutions(v: string): string[] | undefined {
  const arr = v.split(',').map((s) => s.trim()).filter(Boolean)
  return arr.length > 0 ? arr : undefined
}

function parseCustomParams(v: string): Record<string, unknown> | undefined {
  if (!v.trim()) return undefined
  try {
    const parsed: unknown = JSON.parse(v)
    if (typeof parsed === 'object' && parsed !== null && !Array.isArray(parsed)) {
      return parsed as Record<string, unknown>
    }
    return undefined
  } catch {
    return undefined
  }
}

// ============================================================================
// Injection result banner
// ============================================================================

function InjectionResultBanner({ result }: { result: InjectionResponse }): React.ReactElement {
  if (!result.success) {
    return (
      <div className="bg-red-950/40 border border-red-700/50 rounded-xl p-4 text-sm text-red-300 space-y-2">
        <p className="font-bold text-red-400 flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="motion-safe:animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500" />
          </span>
          Injeksi Gagal
        </p>
        {result.validation_errors && result.validation_errors.length > 0 && (
          <ul className="list-disc list-inside space-y-0.5">
            {result.validation_errors.map((err, i) => (
              <li key={i}>{err}</li>
            ))}
          </ul>
        )}
      </div>
    )
  }

  const changes = Object.entries(result.new_values).filter(([k, v]) => {
    const old = result.old_values[k]
    return JSON.stringify(v) !== JSON.stringify(old)
  })

  return (
    <div className="bg-emerald-950/40 border border-emerald-700/50 rounded-xl p-4 text-sm text-emerald-300 space-y-2">
      <p className="font-bold text-emerald-400 flex items-center gap-2">
        <span className="relative flex h-2 w-2">
          <span className="motion-safe:animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
        </span>
        Injeksi Berhasil — {new Date(result.injected_at).toLocaleString('id-ID')}
      </p>
      {changes.length > 0 && (
        <div className="space-y-1 font-mono text-xs">
          {changes.map(([k, v]) => (
            <div key={k} className="flex items-center gap-2 bg-white/5 rounded-lg px-3 py-1.5">
              <span className="text-emerald-400 font-medium">{k}:</span>
              <span className="text-slate-500 line-through">{JSON.stringify(result.old_values[k])}</span>
              <span className="text-emerald-300 font-bold">→ {JSON.stringify(v)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ============================================================================
// Current config viewer — glass terminal style
// ============================================================================

function CurrentConfigViewer({ config }: { config: Record<string, unknown> }): React.ReactElement {
  return (
    <div className="bg-white/5 border border-white/10 rounded-xl p-4 overflow-x-auto">
      <p className="text-xs text-slate-400 font-semibold uppercase tracking-wide mb-3 flex items-center gap-2">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.8)]" />
        Konfigurasi Runtime Aktif
      </p>
      <pre className="text-xs text-emerald-300 font-mono leading-relaxed">
        {JSON.stringify(config, null, 2)}
      </pre>
    </div>
  )
}

// ============================================================================
// Injection log
// ============================================================================

function InjectionLog({ total, log }: { total: number; log: Array<{ timestamp: string; updates: Record<string, unknown> }> }): React.ReactElement {
  const [expanded, setExpanded] = useState(false)

  if (total === 0) {
    return (
      <div className="text-xs text-slate-500 italic text-center py-4">
        Belum ada injeksi konfigurasi
      </div>
    )
  }

  const shown = expanded ? log : log.slice(-3)

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">
          Riwayat Injeksi ({total} total)
        </p>
        {log.length > 3 && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-xs text-cyan-400 hover:text-cyan-300 motion-safe:transition-colors"
          >
            {expanded ? 'Sembunyikan' : `Lihat semua (${log.length})`}
          </button>
        )}
      </div>
      <div className="space-y-1.5">
        {shown.map((entry, i) => (
          <div key={i} className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-xs">
            <div className="flex items-center justify-between mb-1">
              <span className="text-slate-500 font-mono">
                {new Date(entry.timestamp).toLocaleString('id-ID')}
              </span>
              <span className="text-slate-500 bg-white/5 px-2 py-0.5 rounded-full">
                {Object.keys(entry.updates).length} field
              </span>
            </div>
            <div className="font-mono text-slate-500 space-y-0.5">
              {Object.entries(entry.updates).map(([k, v]) => (
                <div key={k}>
                  <span className="text-cyan-400">{k}</span>: <span className="text-slate-300">{JSON.stringify(v)}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ============================================================================
// Form field wrappers
// ============================================================================

function FormRow({ label, help, children }: {
  label: string
  help?: string
  children: React.ReactNode
}): React.ReactElement {
  return (
    <div>
      <label className="block text-sm font-semibold text-slate-300 mb-1">{label}</label>
      {help && <p className="text-xs text-slate-500 mb-1.5">{help}</p>}
      {children}
    </div>
  )
}

const INPUT_CLS = `w-full px-3 py-2 text-sm bg-white/5 border border-white/10 rounded-lg
  text-slate-200 focus:outline-none focus:border-cyan-500/50 focus:shadow-[0_0_15px_rgba(6,182,212,0.2)]
  motion-safe:transition-all placeholder:text-slate-600`

const SELECT_CLS = `w-full px-3 py-2 text-sm bg-white/5 border border-white/10 rounded-lg
  text-slate-200 focus:outline-none focus:border-cyan-500/50 focus:shadow-[0_0_15px_rgba(6,182,212,0.2)]
  motion-safe:transition-all`

// ============================================================================
// Main ConfigPanel page
// ============================================================================

export function ConfigPanel(): React.ReactElement {
  const queryClient = useQueryClient()

  // Form state
  const [procurementScope, setProcurementScope] = useState<ProcurementScope | ''>('')
  const [institutionFilter, setInstitutionFilter] = useState('')
  const [riskThreshold, setRiskThreshold] = useState('')
  const [yearRange, setYearRange] = useState('')
  const [anomalyMethod, setAnomalyMethod] = useState<AnomalyMethod | ''>('')
  const [outputFormat, setOutputFormat] = useState<OutputFormat | ''>('')
  const [customParams, setCustomParams] = useState('')
  const [customParamsError, setCustomParamsError] = useState<string | null>(null)
  const [injectionResult, setInjectionResult] = useState<InjectionResponse | null>(null)

  // Queries
  const configQuery = useQuery({
    queryKey: ['config'],
    queryFn: getConfig,
    staleTime: 30_000,
    retry: 1,
  })

  const logQuery = useQuery({
    queryKey: ['config-log'],
    queryFn: getConfigLog,
    staleTime: 30_000,
    retry: 1,
  })

  // Mutation
  const injectMutation = useMutation({
    mutationFn: (req: InjectionRequest) => injectConfig(req),
    onSuccess: (data) => {
      setInjectionResult(data)
      void queryClient.invalidateQueries({ queryKey: ['config'] })
      void queryClient.invalidateQueries({ queryKey: ['config-log'] })
    },
    onError: () => {
      setInjectionResult(null)
    },
  })

  // Pre-populate form from current config
  useEffect(() => {
    if (configQuery.data && !injectMutation.isSuccess) {
      const c = configQuery.data
      if (typeof c['procurement_scope'] === 'string' && !procurementScope) {
        setProcurementScope(c['procurement_scope'] as ProcurementScope)
      }
      if (Array.isArray(c['institution_filter']) && !institutionFilter) {
        setInstitutionFilter((c['institution_filter'] as string[]).join(', '))
      }
      if (typeof c['risk_threshold'] === 'number' && !riskThreshold) {
        setRiskThreshold(String(c['risk_threshold']))
      }
      if (Array.isArray(c['year_range']) && !yearRange) {
        setYearRange((c['year_range'] as number[]).join(', '))
      }
      if (typeof c['anomaly_method'] === 'string' && !anomalyMethod) {
        setAnomalyMethod(c['anomaly_method'] as AnomalyMethod)
      }
      if (typeof c['output_format'] === 'string' && !outputFormat) {
        setOutputFormat(c['output_format'] as OutputFormat)
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [configQuery.data])

  function validateCustomParams(): boolean {
    if (!customParams.trim()) {
      setCustomParamsError(null)
      return true
    }
    try {
      const parsed: unknown = JSON.parse(customParams)
      if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
        setCustomParamsError('Harus berupa JSON object: {"key": "value"}')
        return false
      }
      setCustomParamsError(null)
      return true
    } catch {
      setCustomParamsError('JSON tidak valid')
      return false
    }
  }

  function handleSubmit(e: React.FormEvent): void {
    e.preventDefault()
    if (!validateCustomParams()) return

    const req: InjectionRequest = {}
    if (procurementScope) req.procurement_scope = procurementScope
    if (institutionFilter.trim()) {
      const parsed = parseInstitutions(institutionFilter)
      if (parsed) req.institution_filter = parsed
    }
    if (riskThreshold.trim()) {
      const parsed = clampThreshold(riskThreshold)
      if (parsed !== undefined) req.risk_threshold = parsed
    }
    if (yearRange.trim()) {
      const parsed = parseYearRange(yearRange)
      if (parsed) req.year_range = parsed
    }
    if (anomalyMethod) req.anomaly_method = anomalyMethod
    if (outputFormat) req.output_format = outputFormat
    if (customParams.trim()) {
      const parsed = parseCustomParams(customParams)
      if (parsed) req.custom_params = parsed
    }

    injectMutation.mutate(req)
  }

  function handleReset(): void {
    setProcurementScope('')
    setInstitutionFilter('')
    setRiskThreshold('')
    setYearRange('')
    setAnomalyMethod('')
    setOutputFormat('')
    setCustomParams('')
    setCustomParamsError(null)
    setInjectionResult(null)
  }

  return (
    <div className="space-y-5 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between motion-safe:animate-[fade-in-up_0.4s_ease-out_both]">
        <div>
          <h1 className="text-2xl font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
            Dynamic Injection
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Injeksi variabel konfigurasi runtime secara dinamis tanpa restart sistem
          </p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 bg-red-950/50 border border-red-700/50 rounded-lg text-xs text-red-400 font-semibold shadow-[0_0_15px_rgba(244,63,94,0.15)]">
          <span className="relative flex h-2 w-2">
            <span className="motion-safe:animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500" />
          </span>
          COMPETITION FEATURE
        </div>
      </div>

      {/* Competition notice */}
      <div className="bg-amber-950/30 border border-amber-700/50 rounded-xl p-4 text-sm text-amber-300/90 space-y-1 motion-safe:animate-[fade-in-up_0.5s_ease-out_both]">
        <p className="font-bold text-amber-400 flex items-center gap-2">
          <span className="text-base">⚠</span>
          Fitur Wajib Kompetisi (Find IT! 2026)
        </p>
        <p>
          Sistem WAJIB menerima dan memproses variabel/logika dadakan dari juri.
          Kegagalan mengimplementasikan Dynamic Injection dapat mengakibatkan{' '}
          <strong>diskualifikasi</strong>.
          Gunakan field{' '}
          <code className="bg-amber-900/40 border border-amber-700/40 px-1.5 py-0.5 rounded text-amber-300 font-mono text-xs">
            custom_params
          </code>{' '}
          untuk parameter arbitrary dari juri.
        </p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
        {/* Injection Form */}
        <div className="glass-card overflow-hidden">
          <div className="px-5 py-4 border-b border-white/10 bg-white/5">
            <h2 className="text-sm font-bold text-slate-200 flex items-center gap-2">
              <span className="w-1.5 h-4 rounded-full bg-gradient-to-b from-cyan-400 to-indigo-500" />
              Form Injeksi Konfigurasi
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Kosongkan field untuk tidak mengubah nilai tersebut
            </p>
          </div>
          <form onSubmit={handleSubmit} className="p-5 space-y-4">

            <FormRow label="Procurement Scope" help="Filter jenis pengadaan yang dianalisis">
              <select
                value={procurementScope}
                onChange={(e) => setProcurementScope(e.target.value as ProcurementScope | '')}
                className={SELECT_CLS}
              >
                <option value="">— Tidak diubah —</option>
                <option value="konstruksi">konstruksi</option>
                <option value="barang">barang</option>
                <option value="jasa_konsultansi">jasa_konsultansi</option>
                <option value="jasa_lainnya">jasa_lainnya</option>
              </select>
            </FormRow>

            <FormRow label="Institution Filter" help="Daftar kode instansi dipisah koma (kosongkan untuk semua)">
              <input
                type="text"
                value={institutionFilter}
                onChange={(e) => setInstitutionFilter(e.target.value)}
                placeholder="KemenPU, KemenHub, BPN (pisah koma)"
                className={INPUT_CLS}
              />
            </FormRow>

            <FormRow label="Risk Threshold" help="Ambang batas skor risiko (0.0 – 1.0). Default dari runtime_config.yaml">
              <input
                type="number"
                step="0.01"
                min="0"
                max="1"
                value={riskThreshold}
                onChange={(e) => setRiskThreshold(e.target.value)}
                placeholder="0.5"
                className={INPUT_CLS}
              />
            </FormRow>

            <FormRow label="Year Range" help='Rentang tahun analisis, format: "2020, 2024"'>
              <input
                type="text"
                value={yearRange}
                onChange={(e) => setYearRange(e.target.value)}
                placeholder="2020, 2024"
                className={INPUT_CLS}
              />
            </FormRow>

            <FormRow label="Anomaly Method" help="Algoritma deteksi anomali yang digunakan">
              <select
                value={anomalyMethod}
                onChange={(e) => setAnomalyMethod(e.target.value as AnomalyMethod | '')}
                className={SELECT_CLS}
              >
                <option value="">— Tidak diubah —</option>
                <option value="isolation_forest">isolation_forest</option>
                <option value="xgboost">xgboost</option>
                <option value="ensemble">ensemble</option>
              </select>
            </FormRow>

            <FormRow label="Output Format" help="Format output sistem">
              <select
                value={outputFormat}
                onChange={(e) => setOutputFormat(e.target.value as OutputFormat | '')}
                className={SELECT_CLS}
              >
                <option value="">— Tidak diubah —</option>
                <option value="dashboard">dashboard</option>
                <option value="api_json">api_json</option>
                <option value="audit_report">audit_report</option>
              </select>
            </FormRow>

            <FormRow
              label="Custom Params (JSON) — Wildcard Juri"
              help='Parameter arbitrary dari juri. Format JSON object: {"key": "value", "flag": true}'
            >
              <textarea
                value={customParams}
                onChange={(e) => {
                  setCustomParams(e.target.value)
                  if (customParamsError) setCustomParamsError(null)
                }}
                onBlur={validateCustomParams}
                rows={4}
                placeholder={'{"analysis_depth": "deep", "include_sanctions": true, "max_vendors": 50}'}
                className={`${INPUT_CLS} font-mono resize-y`}
              />
              {customParamsError && (
                <p className="text-xs text-red-400 mt-1 flex items-center gap-1">
                  <span>⚠</span> {customParamsError}
                </p>
              )}
            </FormRow>

            {/* Mutation error */}
            {injectMutation.isError && (
              <div className="bg-red-950/40 border border-red-700/50 rounded-lg p-3 text-xs text-red-300">
                Error: {injectMutation.error instanceof Error
                  ? injectMutation.error.message
                  : 'Injeksi gagal — pastikan backend berjalan'}
              </div>
            )}

            {/* Buttons */}
            <div className="flex gap-3 pt-2">
              <button
                type="submit"
                disabled={injectMutation.isPending}
                className="flex-1 px-4 py-2.5 bg-gradient-to-r from-indigo-600 to-cyan-600
                           hover:from-indigo-500 hover:to-cyan-500 text-white text-sm font-bold rounded-lg
                           disabled:opacity-60 motion-safe:hover:scale-[1.02]
                           motion-safe:hover:shadow-[0_0_20px_rgba(6,182,212,0.35)]
                           motion-safe:transition-all duration-200 flex items-center justify-center gap-2"
              >
                {injectMutation.isPending ? (
                  <>
                    <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4l3-3-3-3v4a8 8 0 00-8 8h4z" />
                    </svg>
                    Menginjeksi...
                  </>
                ) : (
                  '🚀 Inject Konfigurasi'
                )}
              </button>
              <button
                type="button"
                onClick={handleReset}
                className="px-4 py-2.5 bg-white/5 border border-white/10 text-slate-300 text-sm font-medium rounded-lg
                           hover:bg-white/10 motion-safe:transition-all duration-200"
              >
                Reset
              </button>
            </div>
          </form>

          {/* Injection result */}
          {injectionResult && (
            <div className="px-5 pb-5">
              <InjectionResultBanner result={injectionResult} />
            </div>
          )}
        </div>

        {/* Right column: current config + log */}
        <div className="space-y-4">
          {/* Current config */}
          <div className="glass-card overflow-hidden">
            <div className="px-5 py-3 border-b border-white/10 bg-white/5 flex items-center justify-between">
              <h2 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.8)]" />
                Konfigurasi Runtime Saat Ini
              </h2>
              <button
                onClick={() => void configQuery.refetch()}
                disabled={configQuery.isFetching}
                className="text-xs text-cyan-400 hover:text-cyan-300 motion-safe:transition-colors disabled:opacity-50"
              >
                {configQuery.isFetching ? '⟳ Memuat...' : '⟳ Refresh'}
              </button>
            </div>
            <div className="p-4">
              {configQuery.isLoading && (
                <p className="text-xs text-slate-500 italic text-center py-4">Memuat konfigurasi...</p>
              )}
              {configQuery.isError && (
                <p className="text-xs text-red-400 italic text-center py-4">
                  Backend offline — konfigurasi tidak tersedia
                </p>
              )}
              {configQuery.isSuccess && configQuery.data && (
                <CurrentConfigViewer config={configQuery.data} />
              )}
            </div>
          </div>

          {/* Injection log */}
          <div className="glass-card overflow-hidden">
            <div className="px-5 py-3 border-b border-white/10 bg-white/5 flex items-center justify-between">
              <h2 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 shadow-[0_0_6px_rgba(6,182,212,0.8)]" />
                Log Injeksi
              </h2>
              <button
                onClick={() => void logQuery.refetch()}
                disabled={logQuery.isFetching}
                className="text-xs text-cyan-400 hover:text-cyan-300 motion-safe:transition-colors disabled:opacity-50"
              >
                {logQuery.isFetching ? '⟳' : '⟳ Refresh'}
              </button>
            </div>
            <div className="p-4">
              {logQuery.isLoading && (
                <p className="text-xs text-slate-500 italic text-center py-4">Memuat log...</p>
              )}
              {logQuery.isError && (
                <p className="text-xs text-red-400 italic text-center py-4">Log tidak tersedia</p>
              )}
              {logQuery.isSuccess && logQuery.data && (
                <InjectionLog
                  total={logQuery.data.total_injections}
                  log={logQuery.data.injection_log}
                />
              )}
            </div>
          </div>

          {/* Field reference table */}
          <div className="glass-card p-4">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">
              Referensi Field yang Dapat Diinjeksi
            </p>
            <table className="text-xs w-full">
              <thead>
                <tr className="text-left text-slate-500">
                  <th className="pb-2 pr-3">Field</th>
                  <th className="pb-2 pr-3">Tipe</th>
                  <th className="pb-2">Deskripsi</th>
                </tr>
              </thead>
              <tbody className="text-slate-400 divide-y divide-white/5">
                {[
                  { field: 'procurement_scope', type: 'enum',       desc: 'Jenis pengadaan yang dianalisis' },
                  { field: 'institution_filter', type: 'string[]',  desc: 'Filter kode instansi' },
                  { field: 'risk_threshold',     type: 'float 0–1', desc: 'Ambang batas risiko' },
                  { field: 'year_range',         type: '[int, int]', desc: 'Rentang tahun data' },
                  { field: 'anomaly_method',     type: 'enum',       desc: 'Algoritma deteksi anomali' },
                  { field: 'output_format',      type: 'enum',       desc: 'Format output sistem' },
                  { field: 'custom_params',      type: 'JSON obj',   desc: 'Parameter wildcard (juri)' },
                ].map(({ field, type, desc }) => (
                  <tr key={field} className="motion-safe:hover:bg-white/5 motion-safe:transition-colors">
                    <td className="py-1.5 pr-3 font-mono text-cyan-400 font-medium">{field}</td>
                    <td className="py-1.5 pr-3 text-slate-500 italic">{type}</td>
                    <td className="py-1.5 text-slate-400">{desc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
