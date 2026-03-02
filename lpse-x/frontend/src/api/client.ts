/// <reference types="vite/client" />
import axios from 'axios'
import type {
  HealthResponse,
  InjectionRequest,
  InjectionResponse,
  ConfigLogResponse,
  RiskPrediction,
  XAIResponse,
  DicePrecomputeResponse,
  DiceStatusResponse,
  GraphResponse,
  VendorCommunityResponse,
  ReportResult,
  TenderListResponse,
  TenderDetailResponse,
} from '../types/models'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
  timeout: 30000,
})

// ============================================================================
// Health
// ============================================================================

export async function getHealth(): Promise<HealthResponse> {
  const response = await apiClient.get<HealthResponse>('/api/health')
  return response.data
}

// ============================================================================
// Config / Dynamic Injection (CRITICAL for competition)
// ============================================================================

export async function injectConfig(params: InjectionRequest): Promise<InjectionResponse> {
  const response = await apiClient.put<InjectionResponse>('/api/config/inject', params)
  return response.data
}

export async function getConfig(): Promise<Record<string, unknown>> {
  const response = await apiClient.get<Record<string, unknown>>('/api/config')
  return response.data
}

export async function getConfigLog(): Promise<ConfigLogResponse> {
  const response = await apiClient.get<ConfigLogResponse>('/api/config/log')
  return response.data
}

// ============================================================================
// Inference
// ============================================================================

export interface PredictRequest {
  tender_id: string
  features: Record<string, number>
  icw_raw_score?: number
  tender_metadata?: Record<string, unknown>
}

export async function predictTender(request: PredictRequest): Promise<RiskPrediction> {
  const response = await apiClient.post<RiskPrediction>('/api/predict', request)
  return response.data
}

// ============================================================================
// XAI / Oracle Sandwich
// ============================================================================

export interface XaiRequest {
  features: Record<string, number>
  amount_values?: number[]
}

export async function getXaiExplanation(
  tenderId: string,
  request: XaiRequest,
): Promise<XAIResponse> {
  const response = await apiClient.post<XAIResponse>(`/api/xai/${tenderId}`, request)
  return response.data
}

export async function precomputeDice(
  tenderId: string,
  features: Record<string, number>,
  nCfs = 3,
): Promise<DicePrecomputeResponse> {
  const response = await apiClient.post<DicePrecomputeResponse>('/api/xai/dice/precompute', {
    tender_id: tenderId,
    features,
    n_cfs: nCfs,
  })
  return response.data
}

export async function getDiceStatus(tenderId: string): Promise<DiceStatusResponse> {
  const response = await apiClient.get<DiceStatusResponse>(
    `/api/xai/dice/status/${tenderId}`,
  )
  return response.data
}

// ============================================================================
// Graph (Cartel)
// ============================================================================

export async function getGraphCommunities(
  minCommunitySize = 2,
  topN = 10,
): Promise<GraphResponse> {
  const response = await apiClient.get<GraphResponse>('/api/graph', {
    params: { min_community_size: minCommunitySize, top_n: topN },
  })
  return response.data
}

export async function getVendorCommunity(vendorId: string): Promise<VendorCommunityResponse> {
  const response = await apiClient.get<VendorCommunityResponse>(
    `/api/graph/vendor/${vendorId}`,
  )
  return response.data
}

// ============================================================================
// Reports
// ============================================================================

export async function getReport(tenderId: string): Promise<ReportResult> {
  const response = await apiClient.get<ReportResult>(`/api/reports/${tenderId}`)
  return response.data
}

export async function generateReport(
  tenderId: string,
  oracleResult?: Record<string, unknown>,
  tenderData?: Record<string, unknown>,
): Promise<ReportResult> {
  const response = await apiClient.post<ReportResult>(`/api/reports/${tenderId}`, {
    oracle_result: oracleResult,
    tender_data: tenderData,
  })
  return response.data
}

// ============================================================================
// Tenders
// ============================================================================

export interface ListTendersParams {
  page?: number
  page_size?: number
  risk_level?: string
}

export async function listTenders(params?: ListTendersParams): Promise<TenderListResponse> {
  const response = await apiClient.get<TenderListResponse>('/api/tenders', { params })
  return response.data
}

export async function getTender(tenderId: string): Promise<TenderDetailResponse> {
  const response = await apiClient.get<TenderDetailResponse>(`/api/tenders/${tenderId}`)
  return response.data
}

export default apiClient
