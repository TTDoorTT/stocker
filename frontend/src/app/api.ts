import { post, request } from '../shared/api/client';
import type { Health } from '../shared/types';
export type AIStatus = {
  base_url: string;
  model_id: string;
  has_api_key: boolean;
  configured: boolean;
  source: 'saved' | 'environment';
};
export type AIInput = { base_url: string; model_id: string; api_key: string | null };
export const appApi = {
  ai: () => request<AIStatus>('/settings/ai'),
  saveAI: (body: AIInput) => post<AIStatus>('/settings/ai', body),
  testAI: (body: AIInput) => post<{ ok: boolean; message: string }>('/settings/ai/test', body),
  resetAI: () => request<AIStatus>('/settings/ai', { method: 'DELETE' }),
  health: () => request<Health>('/health'),
};
