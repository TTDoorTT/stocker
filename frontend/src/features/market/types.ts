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

/** Typed stock-research candle contract from backend/app/contracts/stock_research.py. */
export type CandleRange = '1m' | '3m' | '6m' | '1y' | '2y' | '5y';
export type CandleInterval = '1d' | '1wk' | '1mo';
export interface CandleBar {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number | null;
  adjusted_close: number | null;
}
export interface CandleSeries {
  symbol: string;
  market: 'US' | 'CA';
  currency: 'USD' | 'CAD';
  mode: Mode;
  range: CandleRange;
  interval: CandleInterval;
  price_basis: 'provider_ohlc' | 'split_adjusted_ohlc' | 'fully_adjusted_ohlc';
  adjustment_note: string;
  source: {
    name: string;
    url: string;
    fetched_at: string;
    published_at: string | null;
    cached: boolean;
    fixture: boolean;
  };
  bars: CandleBar[];
  gaps: string[];
}
