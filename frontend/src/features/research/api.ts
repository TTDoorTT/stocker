import { post, request } from '../../shared/api/client';
import type { ChatReply, ResearchStrategy, Run, RunEvent } from './types';
export const researchApi = {
  runResearch: (symbol: string, industry_slug?: string, strategy?: ResearchStrategy) =>
    post<Run>('/research-runs', {
      symbol,
      ...(industry_slug ? { industry_slug } : {}),
      ...(strategy ? { strategy } : {}),
    }),
  cancelRun: (id: string) => post<Run>(`/research-runs/${encodeURIComponent(id)}/cancel`, {}),
  deleteRun: (id: string) =>
    request<{ deleted: boolean; run_id: string }>(`/research-runs/${encodeURIComponent(id)}`, {
      method: 'DELETE',
    }),
  runs: () => request<Run[]>('/research-runs'),
  run: (id: string) => request<Run>(`/research-runs/${encodeURIComponent(id)}`),
  events: (id: string) => request<RunEvent[]>(`/research-runs/${encodeURIComponent(id)}/events`),
  chat: (symbol: string, message: string) => post<ChatReply>('/chat', { symbol, message }),
};
