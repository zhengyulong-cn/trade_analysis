import axios from '@/api/axios'

export interface FractalPoint {
  index: number
  time: number
  price: number
  type: 'top' | 'bottom'
}

export interface FractalListResponse {
  symbol: string
  interval: number
  count: number
  fractals: FractalPoint[]
}

export const getFractalsApi = (params: { symbol: string; interval: number; limit?: number }) => {
  return axios.get<FractalListResponse>('/analysis/fractals', params) as unknown as Promise<FractalListResponse>
}
