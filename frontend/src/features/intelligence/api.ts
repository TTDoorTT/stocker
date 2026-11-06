import { request } from '../../shared/api/client';
import type { Mode, NewsItem } from '../../shared/types';
import type { ChatReply } from '../research/types';
import type { Industry, Review, Signal } from './types';
export const intelligenceApi = {
  signals: () => request<{ mode: Mode; items: Signal[]; gaps: string[] }>('/intelligence/signals'),
  dailyReview: () => request<Review>('/daily-review'),
  industries: () => request<Industry[]>('/industries'),
  summarizeNews: () => request<ChatReply>('/intelligence/news/summary', { method: 'POST' }),
  news: () =>
    request<{ mode: string; items: NewsItem[]; gaps: string[]; fetched_at: string }>('/intelligence/news'),
};
