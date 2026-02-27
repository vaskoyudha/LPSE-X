/**
 * LPSE-X TypeScript Models — Mirror of Python Pydantic schemas
 * Ensures frontend type safety and API contract validation
 */

// ============================================================================
// ENUMS (CRITICAL FOR COMPETITION)
// ============================================================================

export type RiskLevel = "Aman" | "Perlu Pantauan" | "Risiko Tinggi" | "Risiko Kritis";

export type ProcurementScope = "konstruksi" | "barang" | "jasa_konsultansi" | "jasa_lainnya";

export type AnomalyMethod = "isolation_forest" | "xgboost" | "ensemble";

export type OutputFormat = "dashboard" | "api_json" | "audit_report";

// ============================================================================
// DATA MODELS
// ============================================================================

/**
 * OCDS-format tender record with OCP red flags.
 * Minimum schema; can be extended via ocds_data field.
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
 * Risk prediction result from ML models with disagreement tracking.
 */
export interface RiskPrediction {
  tender_id: string;
  risk_level: RiskLevel;
  score: number;
  model_scores: Record<string, number>;
  disagreement_flag: boolean;
  predicted_at?: string;
}

/**
 * Oracle Sandwich: 5-layer explainability for a single prediction.
 * All layers are optional (computed on demand).
 */
export interface XAIExplanation {
  tender_id: string;
  
  // Layer 1: SHAP (Global Feature Importance)
  shap_values?: Record<string, number>;
  shap_base_value?: number;
  
  // Layer 2: DiCE (Local Counterfactuals)
  dice_counterfactuals?: Record<string, unknown>[];
  
  // Layer 3: Anchors (Rule-based Explanations)
  anchor_rules?: string[];
  anchor_precision?: number;
  anchor_coverage?: number;
  
  // Layer 4: Leiden (Graph Community Detection)
  leiden_community_id?: number;
  leiden_community_size?: number;
  
  // Layer 5: Benford (Statistical Forensics)
  benford_result?: Record<string, unknown>;
  
  generated_at?: string;
}

/**
 * Cartel network: detected vendor community from Leiden algorithm.
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

/**
 * CRITICAL: All 7 injectable parameters (competition rules).
 * Must accept partial updates via PUT /api/config/inject.
 * custom_params is wildcard for judge-injected unknown parameters.
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

/**
 * Auto-generated pre-investigation report (Bahasa Indonesia, IIA 2025 standards).
 */
export interface InvestigationReport {
  report_id: string;
  tender_id: string;
  risk_level: RiskLevel;
  findings?: string[];
  recommendations?: string[];
  template_version?: string;
  generated_at?: string;
  evidence_summary?: string;
}

/**
 * Request body for PUT /api/config/inject.
 * All fields optional (partial config updates).
 */
export interface InjectionRequest {
  procurement_scope?: ProcurementScope;
  institution_filter?: string[];
  risk_threshold?: number;
  year_range?: [number, number];
  anomaly_method?: AnomalyMethod;
  output_format?: OutputFormat;
  custom_params?: Record<string, unknown>;
}

/**
 * Response from PUT /api/config/inject.
 */
export interface InjectionResponse {
  success: boolean;
  old_values: Record<string, unknown>;
  new_values: Record<string, unknown>;
  validation_errors?: string[];
  injected_at: string;
}
