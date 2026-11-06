import { post, request } from '../../shared/api/client';
import type { Position } from '../../shared/types/index';
export const portfolioApi = {
  watchlist: () => request<{ symbol: string }[]>('/watchlist'),
  watch: (symbol: string) => post('/watchlist', { symbol }),
  unwatch: (symbol: string) => request(`/watchlist/${encodeURIComponent(symbol)}`, { method: 'DELETE' }),
  positions: () => request<Position[]>('/positions'),
  position: (position: { symbol: string; shares: number; average_cost: number; currency: string }) =>
    post('/positions', position),
  removePosition: (id: number) => request(`/positions/${id}`, { method: 'DELETE' }),
};
