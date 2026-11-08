import type { Mode, NewsItem, Quote } from '../../shared/types';
import type { ChatReply } from '../research/types';

export interface RSSArticle {
  headline: string;
  source_name: string;
  source_url: string;
  published_at: string;
  fetched_at: string;
}

export interface RSSNewsResponse {
  category: string;
  categories: { key: string; name: string; count: number }[];
  items: RSSArticle[];
  sources_total: number;
  sources_ok: number;
  sources_failed: number;
  last_refreshed: string | null;
  refreshing: boolean;
  error: string;
}

export interface SavedRSSHighlights {
  category: string;
  saved: boolean;
  generated_at: string | null;
  model_id: string | null;
  stale: boolean;
  result: ChatReply | null;
}

export interface FilingEvidenceCoverage {
  selected_issuers: string[];
  represented_issuers: string[];
  missing_issuers: string[];
  accepted_excerpts: number;
  limitation: string;
}

export interface SavedIndustrySection {
  industry_slug: string;
  section: IndustrySectionKey;
  saved: boolean;
  generated_at: string | null;
  model_id: string | null;
  stale: boolean;
  result: (ChatReply & { filing_coverage?: FilingEvidenceCoverage }) | null;
}

export type IndustrySectionKey = 'overview' | 'technology' | 'supply-chain' | 'competition' | 'outlook';

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
  research_status: 'guided_only' | 'limited_pilot';
  ai_sections: IndustrySectionKey[];
  research_coverage: string;
}

export interface FilingExcerpt {
  symbol: string;
  form: string;
  filed: string;
  matched_term: string;
  text: string;
  source_name: string;
  source_url: string;
  fetched_at: string;
  cached: boolean;
}

export interface FilingExcerptsResponse {
  industry: string;
  year: number;
  mode: 'fixtures' | 'live';
  excerpts: FilingExcerpt[];
  gaps: string[];
  coverage: string;
}
