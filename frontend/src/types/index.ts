export type Mode = 'fixtures' | 'live';
export interface Health {
  status: string;
  mode?: Mode;
  model_configured?: boolean;
  model_id?: string;
  missing_configuration?: string[];
}
export interface Evidence {
  evidence_id: string;
  symbol: string;
  field: string;
  value: number | string | null;
  unit: string;
  currency: string | null;
  period: string;
  source_name: string;
  source_url: string;
  published_at: string | null;
  fetched_at: string;
  fixture?: boolean;
  cached?: boolean;
  missing_reason?: string | null;
}
export interface Quote {
  price: number;
  previous_close: number | null;
  timestamp: string;
  source_url: string;
  source_name: string;
  stale: boolean;
  delayed: boolean;
  cached?: boolean;
  fetched_at?: string;
}
export interface NewsItem {
  headline: string;
  source_url: string;
  source_name?: string;
  fetched_at?: string;
  cached?: boolean;
  published_at: string | null;
  symbols?: string[];
  summary?: string;
}
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
export interface Position {
  id: number;
  symbol: string;
  shares: number;
  average_cost: number;
  currency: string;
  quote_price: number | null;
  unrealized_pnl: number | null;
  mode?: Mode;
  quote?: Quote | null;
  gaps?: string[];
}
export interface Stage {
  stage: string;
  attempt: number;
  status: string;
  input_evidence_ids?: string[];
  input?: unknown;
  output?: { summary?: string; gaps?: unknown[]; [key: string]: unknown } | null;
  validation_errors: string[];
  started_at?: string;
  finished_at?: string;
}
export interface Calculation {
  calculation_id?: string;
  id?: string;
  metric?: string;
  value?: number | null;
  unit?: string;
  reason?: string | null;
  [key: string]: unknown;
}
export interface Run {
  run_id: string;
  symbol: string;
  status: string;
  model_id: string;
  mode: Mode;
  started_at: string;
  finished_at?: string | null;
  stages: Stage[];
  evidence: Evidence[];
  calculations: Calculation[];
  report?: string | null;
  gaps: string[];
  error?: string;
}
export interface RunEvent {
  id: number;
  event: string;
  stage?: string;
  at?: string;
  timestamp?: string;
  [key: string]: unknown;
}
export interface ChatReply {
  answer: string;
  evidence: Evidence[];
  mode: Mode;
  gaps: string[];
}
