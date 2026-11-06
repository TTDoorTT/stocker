import type { Calculation, Evidence, Mode } from '../../shared/types';
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
