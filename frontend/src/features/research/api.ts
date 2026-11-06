import { post, request } from '../../shared/api/client';
import type { ChatReply, Run, RunEvent } from './types';
export const researchApi = {
  runResearch: (symbol: string, industry_slug?: string) =>
    post<Run>('/research-runs', { symbol, industry_slug }),
  runs: () => request<Run[]>('/research-runs'),
  run: (id: string) => request<Run>(`/research-runs/${encodeURIComponent(id)}`),
  events: (id: string) => request<RunEvent[]>(`/research-runs/${encodeURIComponent(id)}/events`),
  chat: (symbol: string, message: string) => post<ChatReply>('/chat', { symbol, message }),
};
