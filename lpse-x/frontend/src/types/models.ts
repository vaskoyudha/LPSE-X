/**
 * LPSE-X TypeScript Models — Mirror of Python Pydantic schemas
 * Ensures frontend type safety and API contract validation
 */

// ============================================================================
// ENUMS (CRITICAL FOR COMPETITION)
// ============================================================================

export type RiskLevel = "Aman" | "Perlu Pantauan" | "Risiko Tinggi" | "Risiko Kritis" | "Berisiko" | "Kritis";

export type ProcurementScope = "konstruksi" | "barang" | "jasa_konsultansi" | "jasa_lainnya";

export type AnomalyMethod = "isolation_forest" | "xgboost" | "ensemble";

export type OutputFormat = "dashboard" | "api_json" | "audit_report";

export const RISK_COLORS: Record<string, string> = {
  "Aman":           "#22c55e",
  "Perlu Pantauan": "#f59e0b",
  "Risiko Tinggi":  "#ef4444",
  "Risiko Kritis":  "#7c2d12",
  "Berisiko":       "#ef4444",
  "Kritis":         "#7c2d12",
};

export const RISK_BG: Record<string, string> = {
  "Aman":           "bg-green-100 text-green-800",
  "Perlu Pantauan": "bg-amber-100 text-amber-800",
  "Risiko Tinggi":  "bg-red-100 text-red-800",
  "Risiko Kritis":  "bg-red-900 text-white",
  "Berisiko":       "bg-red-100 text-red-800",
  "Kritis":         "bg-red-900 text-white",
};

// ============================================================================
// DATA MODELS
// ============================================================================

/**
 * OCDS-format tender record with OCP red flags.
 */
export interface TenderRecord {
  tender_id: string;
  buyer: string;
  buyer_lpse?: string;
  title: string;
  procurement_scope: string;
  method: string;
  amount?: number;
  hps?: number;
  year: number;
  province?: string;
  winner_npwp_hash?: string;
  winner_name?: string;
  participant_count?: number;
  ocds_data?: Record<string, unknown>;
  icw_total_score?: number;
  created_at?: string;
}

/**
 * Risk prediction result from POST /api/predict
 */
export interface RiskPrediction {
  status: string;
  tender_id: string;
  risk_level: RiskLevel;
  final_score: number;
  individual_scores: Record<string, number>;
  disagreement_flag: boolean;
  disagreement_detail: string;
  risk_threshold: number;
  timestamp: string;
}

/**
 * Single XAI layer result
 */
export interface XAILayer {
  status: string;
  data: Record<string, unknown> | null;
  error: string | null;
}

/**
 * Oracle Sandwich XAI result from POST /api/xai/{tender_id}
 */
export interface OracleSandwichResult {
  tender_id: string;
  layers_ok: number;
  layers_failed: number;
  total_seconds: number;
  shap: XAILayer;
  anchors: XAILayer;
  leiden: XAILayer;
  benford: XAILayer;
  dice: XAILayer;
  timestamp: string;
}

export interface XAIResponse {
  status: string;
  data: OracleSandwichResult;
}

/**
 * DiCE precompute response
 */
export interface DicePrecomputeResponse {
  status: string;
  tender_id: string;
  n_cfs?: number;
  message: string;
  timestamp: string;
}

export interface DiceStatusResponse {
  tender_id: string;
  status: "not_started" | "pending" | "running" | "done" | "error";
  result_available: boolean;
  timestamp: string;
}

/**
 * Graph community from GET /api/graph
 */
export interface GraphCommunity {
  community_id: number;
  members: string[];
  edge_weights: Record<string, number>;
  tender_ids: string[];
  risk_score?: number;
  leiden_modularity?: number;
  detected_at?: string;
}

export interface GraphResponse {
  status: string;
  communities: GraphCommunity[];
  total: number;
  filters: Record<string, unknown>;
  timestamp: string;
  note?: string;
}

export interface VendorCommunityResponse {
  status: string;
  vendor_id: string;
  in_community: boolean;
  community_id: number | null;
  community_risk_score: number | null;
  co_bidders: string[];
  timestamp: string;
  note?: string;
}

/**
 * Report result from /api/reports/{tender_id}
 */
export interface ReportResult {
  status: string;
  tender_id: string;
  risk_level: string;
  risk_score: number;
  generated_at: string;
  evidence_count: number;
  recommendations: string[];
  sections: Record<string, string>;
  report_text: string;
  timestamp: string;
}

/**
 * Health check response from GET /api/health
 */
export interface HealthResponse {
  status: string;
  version: string;
  uptime: number;
  models: {
    xgboost: string;
    isolation_forest: string;
  };
  config_hash: string;
  config: Record<string, unknown>;
}

/**
 * Config injection types (CRITICAL for competition)
 */
export interface RuntimeConfig {
  procurement_scope?: ProcurementScope;
  institution_filter?: string[];
  risk_threshold?: number;
  year_range?: [number, number];
  anomaly_method?: AnomalyMethod;
  output_format?: OutputFormat;
  custom_params?: Record<string, unknown>;
}

export interface InjectionRequest {
  procurement_scope?: ProcurementScope;
  institution_filter?: string[];
  risk_threshold?: number;
  year_range?: [number, number];
  anomaly_method?: AnomalyMethod;
  output_format?: OutputFormat;
  custom_params?: Record<string, unknown>;
}

export interface InjectionResponse {
  success: boolean;
  old_values: Record<string, unknown>;
  new_values: Record<string, unknown>;
  validation_errors?: string[];
  injected_at: string;
}

export interface ConfigLogResponse {
  injection_log: Array<{
    timestamp: string;
    changes: Record<string, unknown>;
  }>;
  total_injections: number;
}
