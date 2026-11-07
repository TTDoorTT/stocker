import { request } from '../../shared/api/client';
import type { Mode, NewsItem } from '../../shared/types';
import type { ChatReply } from '../research/types';
import type {
  Industry,
  IndustrySectionKey,
  Review,
  RSSNewsResponse,
  SavedIndustrySection,
  SavedRSSHighlights,
  Signal,
} from './types';

export const intelligenceApi = {
  rss: (category: string) =>
    request<RSSNewsResponse>(`/intelligence/rss?category=${encodeURIComponent(category)}`),
  refreshRSS: () => request<RSSNewsResponse>('/intelligence/rss/refresh', { method: 'POST' }),
  savedRSSHighlights: (category: string) =>
    request<SavedRSSHighlights>(`/intelligence/rss/highlights?category=${encodeURIComponent(category)}`),
  rssHighlights: (category: string) =>
    request<ChatReply>('/intelligence/rss/highlights', {
      method: 'POST',
      body: JSON.stringify({ category }),
    }),
  signals: () => request<{ mode: Mode; items: Signal[]; gaps: string[] }>('/intelligence/signals'),
  dailyReview: () => request<Review>('/daily-review'),
  industries: () => request<Industry[]>('/industries'),
  industry: (slug: string) => request<Industry>(`/industries/${encodeURIComponent(slug)}`),
  savedIndustrySection: (slug: string, section: IndustrySectionKey) =>
    request<SavedIndustrySection>(`/industries/${encodeURIComponent(slug)}/sections/${section}`),
  generateIndustrySection: (slug: string, section: IndustrySectionKey) =>
    request<SavedIndustrySection>(`/industries/${encodeURIComponent(slug)}/sections/${section}/generate`, {
      method: 'POST',
    }),
  summarizeNews: () => request<ChatReply>('/intelligence/news/summary', { method: 'POST' }),
  news: () =>
    request<{ mode: string; items: NewsItem[]; gaps: string[]; fetched_at: string }>('/intelligence/news'),
};

// Only feature API modules may use the generic HTTP client.
export function fetchIndustryEvidence<T>(year: number): Promise<T> {
  return request<T>(`/industries/ai-computing/evidence?year=${year}`);
}
