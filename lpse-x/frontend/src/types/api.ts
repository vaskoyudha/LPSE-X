/**
 * LPSE-X API Response Types
 * Shared API contract definitions for frontend consumption
 */

import {
  GraphCommunity,
  InvestigationReport,
  RiskPrediction,
  TenderRecord,
  XAIExplanation,
} from "./models";

/**
 * Standard API response wrapper for single items
 */
export interface ApiResponse<T> {
  data: T;
  total?: number;
  page?: number;
  page_size?: number;
}

/**
 * Standard error response from API
 */
export interface ApiError {
  detail: string;
  status_code: number;
}

/**
 * Paginated response for list endpoints
 */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pages: number;
}

/**
 * Tender with prediction and explanation (common response)
 */
export interface TenderWithPrediction {
  tender: TenderRecord;
  prediction: RiskPrediction;
  explanation?: XAIExplanation;
}

/**
 * Search/list tenders response
 */
export interface TendersListResponse extends PaginatedResponse<TenderWithPrediction> {}

/**
 * Risk summary statistics
 */
export interface RiskSummary {
  total_tenders: number;
  risk_distribution: {
    aman: number;
    perlu_pantauan: number;
    risiko_tinggi: number;
    risiko_kritis: number;
  };
  average_score: number;
  critical_count: number;
}

/**
 * Cartel detection results
 */
export interface CartelDetectionResponse {
  communities: GraphCommunity[];
  total_detected: number;
  high_risk_count: number;
}

/**
 * Report generation response
 */
export interface ReportGenerationResponse {
  report_id: string;
  tender_id: string;
  status: "generated" | "queued" | "failed";
  report?: InvestigationReport;
  error?: string;
}

/**
 * Dashboard stats response
 */
export interface DashboardStats {
  summary: RiskSummary;
  recent_high_risk: TenderWithPrediction[];
  detected_communities: GraphCommunity[];
  last_updated: string;
}
