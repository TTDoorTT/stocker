import { request } from '../../shared/api/client';
import type {
  CandleInterval,
  CandleRange,
  CandleSeries,
  EarningsResponse,
  EventStudyResponse,
  EventsResponse,
  FinancialTrendsResponse,
  PriceBar,
  SearchResult,
  Stock,
} from './types';
export const marketApi = {
  overview: () => request<Stock[]>('/markets/overview'),
  search: (query: string) => request<SearchResult[]>(`/stocks/search?q=${encodeURIComponent(query)}`),
  stock: (symbol: string) => request<Stock>(`/stocks/${encodeURIComponent(symbol)}`),
  history: (symbol: string) => request<PriceBar[]>(`/stocks/${encodeURIComponent(symbol)}/history?range=1y`),
  financialTrends: (symbol: string) =>
    request<FinancialTrendsResponse>(`/stocks/${encodeURIComponent(symbol)}/financial-trends`),
  earnings: (symbol: string) => request<EarningsResponse>(`/stocks/${encodeURIComponent(symbol)}/earnings`),
  events: (symbol: string) => request<EventsResponse>(`/stocks/${encodeURIComponent(symbol)}/events`),
  eventStudy: (symbol: string) =>
    request<EventStudyResponse>(`/stocks/${encodeURIComponent(symbol)}/event-study`),
  candles: (symbol: string, range: CandleRange, interval: CandleInterval) =>
    request<CandleSeries>(
      `/stocks/${encodeURIComponent(symbol)}/candles?range=${encodeURIComponent(range)}&interval=${encodeURIComponent(interval)}`,
    ),
};
