/// <reference types="vite/client" />
import axios from 'axios'
import type { 
  InjectionRequest, 
  InjectionResponse, 
  RiskPrediction
} from '../types/models'
import type { 
  TendersListResponse,
  DashboardStats,
  TenderWithPrediction
} from '../types/api'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 30000,
})

export async function getTenders(page: number, pageSize: number): Promise<TendersListResponse> {
  const response = await apiClient.get<TendersListResponse>('/api/tenders', {
    params: { page, page_size: pageSize }
  })
  return response.data
}

export async function injectConfig(params: InjectionRequest): Promise<InjectionResponse> {
  const response = await apiClient.put<InjectionResponse>('/api/config/inject', params)
  return response.data
}

export async function getPrediction(tenderId: string): Promise<RiskPrediction> {
  const response = await apiClient.get<RiskPrediction>(`/api/predict/${tenderId}`)
  return response.data
}

export async function getDashboardStats(): Promise<DashboardStats> {
  const response = await apiClient.get<DashboardStats>('/api/dashboard/stats')
  return response.data
}

export async function getTenderDetail(tenderId: string): Promise<TenderWithPrediction> {
  const response = await apiClient.get<TenderWithPrediction>(`/api/tenders/${tenderId}`)
  return response.data
}

export default apiClient
