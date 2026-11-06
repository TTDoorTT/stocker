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
export interface Calculation {
  calculation_id?: string;
  id?: string;
  metric?: string;
  value?: number | null;
  unit?: string;
  reason?: string | null;
  [key: string]: unknown;
}
