import type { Mode, NewsItem, Quote } from '../../shared/types';
export interface Signal {
  series_id: string;
  name: string;
  value: number | null;
  unit: string;
  observation_date?: string;
  source_url: string;
  source_name: string;
  fetched_at: string;
  stale: boolean;
  status: string;
  observations: { date: string; value: number }[];
  gaps: string[];
}
export interface Review {
  mode: Mode;
  as_of: string;
  proxies: {
    symbol: string;
    name: string;
    quote: Quote | null;
    daily_return_pct: number | null;
    gaps: string[];
  }[];
  news: NewsItem[];
  gaps: string[];
  session: string;
  coverage: string;
}
export interface Industry {
  slug: string;
  name: string;
  prompt: string;
  symbols: string[];
  gaps: string[];
}
