import type {
  ChatReply,
  Health,
  NewsItem,
  Position,
  PriceBar,
  Run,
  RunEvent,
  SearchResult,
  Stock,
} from '../types';

export async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  });
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      message = typeof body.detail === 'string' ? body.detail : message;
    } catch {
      /* use HTTP status */
    }
    throw new Error(message);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
const post = <T>(path: string, body: unknown) =>
  request<T>(path, { method: 'POST', body: JSON.stringify(body) });
export const api = {
  health: () => request<Health>('/health'),
  overview: () => request<Stock[]>('/markets/overview'),
  search: (query: string) => request<SearchResult[]>(`/stocks/search?q=${encodeURIComponent(query)}`),
  stock: (symbol: string) => request<Stock>(`/stocks/${encodeURIComponent(symbol)}`),
  history: (symbol: string) => request<PriceBar[]>(`/stocks/${encodeURIComponent(symbol)}/history?range=1y`),
  watchlist: () => request<{ symbol: string }[]>('/watchlist'),
  watch: (symbol: string) => post('/watchlist', { symbol }),
  unwatch: (symbol: string) => request(`/watchlist/${encodeURIComponent(symbol)}`, { method: 'DELETE' }),
  positions: () => request<Position[]>('/positions'),
  position: (position: { symbol: string; shares: number; average_cost: number; currency: string }) =>
    post('/positions', position),
  removePosition: (id: number) => request(`/positions/${id}`, { method: 'DELETE' }),
  runResearch: (symbol: string, industry_slug?: string) =>
    post<Run>('/research-runs', { symbol, industry_slug }),
  runs: () => request<Run[]>('/research-runs'),
  run: (id: string) => request<Run>(`/research-runs/${encodeURIComponent(id)}`),
  events: (id: string) => request<RunEvent[]>(`/research-runs/${encodeURIComponent(id)}/events`),
  chat: (symbol: string, message: string) => post<ChatReply>('/chat', { symbol, message }),
  summarizeNews: () => request<ChatReply>('/intelligence/news/summary', { method: 'POST' }),
  news: () =>
    request<{ mode: string; items: NewsItem[]; gaps: string[]; fetched_at: string }>('/intelligence/news'),
};
