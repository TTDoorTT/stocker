/** UI-only data mapping. The backend owns trading calendars, eligibility and returns. */
import type { EventStudyResponse, EventWindow } from './types';

export interface DriftPoint {
  day: number;
  value: number;
}

const DAYS = Array.from({ length: 26 }, (_, index) => index - 5);

export function eventPath(event: EventWindow): DriftPoint[] {
  if (!event.eligible) return [];
  const points: DriftPoint[] = [];
  for (const day of DAYS) {
    const value = event.excess_returns[String(day)];
    if (typeof value !== 'number' || !Number.isFinite(value)) return [];
    points.push({ day, value });
  }
  return points;
}

/** Never display an aggregate when the API has withheld summary statistics. */
export function meanPath(study: EventStudyResponse): DriftPoint[] {
  if (!study.summary?.length || study.eligible_event_count < study.minimum_sample) return [];
  const eligible = study.events.filter((event) => event.eligible);
  if (eligible.length !== study.eligible_event_count) return [];
  const paths = eligible.map(eventPath);
  if (paths.some((path) => path.length !== DAYS.length)) return [];
  return DAYS.map((day, index) => ({
    day,
    value: paths.reduce((sum, path) => sum + path[index].value, 0) / paths.length,
  }));
}

export function driftBounds(points: DriftPoint[]): { minimum: number; maximum: number } | null {
  if (!points.length || points.some((point) => !Number.isFinite(point.value))) return null;
  const values = points.map((point) => point.value);
  const low = Math.min(0, ...values);
  const high = Math.max(0, ...values);
  const span = Math.max(high - low, 0.5);
  const padding = span * 0.1;
  return { minimum: low - padding, maximum: high + padding };
}

export function formatDrift(value: number | null | undefined): string {
  if (typeof value !== 'number' || !Number.isFinite(value)) return '—';
  return `${value > 0 ? '+' : ''}${value.toFixed(2)} pp`;
}

export function formatPositiveShare(value: number | null | undefined): string {
  if (typeof value !== 'number' || !Number.isFinite(value)) return '—';
  return `${(value * 100).toFixed(1)}%`;
}
