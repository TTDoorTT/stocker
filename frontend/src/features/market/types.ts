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

/** Read-only contracts from backend/app/contracts/stock_research.py. */
export type FinancialMetricName =
  | 'revenue'
  | 'net_income'
  | 'diluted_eps'
  | 'operating_cash_flow'
  | 'gross_profit';
export interface FinancialSource {
  name: string;
  url: string;
  fetched_at: string;
  published_at: string | null;
  cached: boolean;
  fixture: boolean;
}
export interface FinancialMetric {
  value: number | null;
  unit: string;
  status: 'as_reported' | 'derived' | 'unavailable';
  evidence_ids: string[];
  calculation_id?: string | null;
  reason?: string | null;
}
export interface FinancialPeriod {
  period_id: string;
  fiscal_year: number;
  fiscal_quarter: 'Q1' | 'Q2' | 'Q3' | 'Q4' | null;
  period_kind: 'standalone_quarter' | 'ytd' | 'annual';
  period_start: string;
  period_end: string;
  filed_on: string;
  form: '10-K' | '10-Q';
  accession: string;
  metrics: Partial<Record<FinancialMetricName, FinancialMetric>>;
  source: FinancialSource;
}
export interface FinancialTTM {
  value: number | null;
  unit: string;
  status: 'available' | 'unavailable';
  input_period_ids: string[];
  calculation_id?: string | null;
  reason?: string | null;
}
export interface FinancialTrendsResponse {
  symbol: string;
  market: 'US' | 'CA';
  currency: 'USD' | 'CAD';
  mode: Mode;
  frequency: 'quarterly' | 'annual';
  periods: FinancialPeriod[];
  ttm: Partial<Record<FinancialMetricName, FinancialTTM>>;
  sources: FinancialSource[];
  gaps: string[];
}

/** Finnhub dated earnings calendar response; no inferred release timestamp. */
export interface UpcomingEarnings {
  scheduled_date: string;
  date_status: 'estimated' | 'confirmed';
  timing: 'before_open' | 'after_close' | 'during_session' | 'unknown';
  fiscal_year: number | null;
  fiscal_quarter: 'Q1' | 'Q2' | 'Q3' | 'Q4' | null;
  eps_estimate: number | null;
  eps_estimate_basis: 'gaap_diluted' | 'gaap_basic' | 'adjusted' | null;
  revenue_estimate: number | null;
  source: FinancialSource;
}
export interface EarningsRecord {
  event_id: string;
  fiscal_year: number;
  fiscal_quarter: 'Q1' | 'Q2' | 'Q3' | 'Q4';
  reported_on: string;
  actual_eps: number | null;
  actual_basis: 'gaap_diluted' | 'gaap_basic' | 'adjusted' | null;
  estimate_eps: number | null;
  estimate_basis: 'gaap_diluted' | 'gaap_basic' | 'adjusted' | null;
  surprise_pct: number | null;
  actual_revenue: number | null;
  estimate_revenue: number | null;
  revenue_surprise_pct: number | null;
  source: FinancialSource;
}
export interface EarningsResponse {
  symbol: string;
  market: 'US' | 'CA';
  currency: 'USD' | 'CAD';
  mode: Mode;
  upcoming: UpcomingEarnings | null;
  history: EarningsRecord[];
  sources: FinancialSource[];
  gaps: string[];
}
