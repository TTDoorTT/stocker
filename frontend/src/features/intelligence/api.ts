import { request } from '../../shared/api/client';
import type { ChatReply, NewsItem } from '../../shared/types/index';
export const intelligenceApi = {
  summarizeNews: () => request<ChatReply>('/intelligence/news/summary', { method: 'POST' }),
  news: () =>
    request<{ mode: string; items: NewsItem[]; gaps: string[]; fetched_at: string }>('/intelligence/news'),
};
