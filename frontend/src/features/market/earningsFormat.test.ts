import { describe, expect, it } from 'vitest';
import {
  calendarDate,
  earningsAmount,
  earningsEPS,
  earningsPercent,
  earningsTiming,
  surpriseClass,
} from './earningsFormat';

describe('display-only earnings formatting', () => {
  it('never fabricates missing or nonfinite financial values', () => {
    expect(earningsAmount(null, 'USD')).toBe('Unavailable');
    expect(earningsEPS(undefined, 'CAD')).toBe('Unavailable');
    expect(earningsPercent(Number.NaN)).toBe('Unavailable');
    expect(earningsPercent(0)).toBe('0.00%');
    expect(earningsAmount(0, 'CAD')).toContain('0');
  });

  it('handles positives, negatives, small EPS and scaled revenue', () => {
    expect(earningsPercent(4.1666667)).toBe('+4.17%');
    expect(earningsPercent(-3.5)).toBe('-3.50%');
    expect(earningsEPS(-0.245, 'USD')).toContain('0.245');
    expect(earningsAmount(1_250_000_000, 'USD')).toBe('$1.25B');
    expect(earningsAmount(-2_500_000, 'CAD')).toContain('2.50M');
    expect(surpriseClass(-0.1)).toBe('is-negative');
    expect(surpriseClass(null)).toBe('');
  });

  it('uses calendar-only dates without timezone shifts or inferred times', () => {
    expect(calendarDate('2026-11-07')).toBe('Nov 7, 2026');
    expect(calendarDate('2026-02-30')).toBe('Date unavailable');
    expect(earningsTiming('after_close')).toBe('After market close');
    expect(earningsTiming('unknown')).toBe('Release time unverified');
  });
});
