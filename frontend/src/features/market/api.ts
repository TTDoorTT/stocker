import { request } from '../../shared/api/client';
import type { PriceBar, SearchResult, Stock } from './types';
export const marketApi = {
  overview: () => request<Stock[]>('/markets/overview'),
  search: (query: string) => request<SearchResult[]>(`/stocks/search?q=${encodeURIComponent(query)}`),
  stock: (symbol: string) => request<Stock>(`/stocks/${encodeURIComponent(symbol)}`),
  history: (symbol: string) => request<PriceBar[]>(`/stocks/${encodeURIComponent(symbol)}/history?range=1y`),
};
