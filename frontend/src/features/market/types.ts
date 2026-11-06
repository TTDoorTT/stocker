import type { Evidence, Mode, NewsItem, Quote } from '../../shared/types';
export interface Stock {
  symbol: string;
  name: string;
  market: string;
  currency: string;
  mode: Mode;
  profile: string;
  quote: Quote | null;
  facts: Evidence[];
  news: NewsItem[];
  evidence?: Evidence[];
  gaps: string[];
}
export interface SearchResult {
  symbol: string;
  name: string;
}
export interface PriceBar {
  currency?: string;
  limitations?: string[];
  date: string;
  close: number;
  source_name?: string;
  source_url?: string;
  fetched_at?: string;
  cached?: boolean;
}
