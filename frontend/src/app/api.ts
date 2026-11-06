import { request } from '../shared/api/client';
import type { Health } from '../shared/types/index';
export const appApi = {
  health: () => request<Health>('/health'),
};
