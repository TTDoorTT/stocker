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

// Shared short-lived cache: chart markers and Event Study reuse the same dated-events request.
// Errors are evicted immediately; this cache never contains event-study return calculations.
const earningsEventCache = new Map<string, { until: number; promise: Promise<EventsResponse> }>();

function cachedEarningsEvents(symbol: string): Promise<EventsResponse> {
  const key = symbol.trim().toUpperCase();
  const hit = earningsEventCache.get(key);
  if (hit && hit.until > Date.now()) return hit.promise;
  const promise = request<EventsResponse>(`/stocks/${encodeURIComponent(key)}/events`);
  earningsEventCache.set(key, { until: Date.now() + 5 * 60 * 1000, promise });
  void promise.catch(() => {
    if (earningsEventCache.get(key)?.promise === promise) earningsEventCache.delete(key);
  });
  if (earningsEventCache.size > 16) earningsEventCache.delete(earningsEventCache.keys().next().value!);
  return promise;
}

export const marketApi = {
  overview: () => request<Stock[]>('/markets/overview'),
  search: (query: string) => request<SearchResult[]>(`/stocks/search?q=${encodeURIComponent(query)}`),
  stock: (symbol: string) => request<Stock>(`/stocks/${encodeURIComponent(symbol)}`),
  history: (symbol: string) => request<PriceBar[]>(`/stocks/${encodeURIComponent(symbol)}/history?range=1y`),
  financialTrends: (symbol: string) =>
    request<FinancialTrendsResponse>(`/stocks/${encodeURIComponent(symbol)}/financial-trends`),
  earnings: (symbol: string) => request<EarningsResponse>(`/stocks/${encodeURIComponent(symbol)}/earnings`),
  events: (symbol: string) => cachedEarningsEvents(symbol),
  eventStudy: (symbol: string) =>
    request<EventStudyResponse>(`/stocks/${encodeURIComponent(symbol)}/event-study`),
  candles: (symbol: string, range: CandleRange, interval: CandleInterval) =>
    request<CandleSeries>(
      `/stocks/${encodeURIComponent(symbol)}/candles?range=${encodeURIComponent(range)}&interval=${encodeURIComponent(interval)}`,
    ),
};
