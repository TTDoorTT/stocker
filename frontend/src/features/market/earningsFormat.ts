/** Display-only transformations: figures are returned by the backend, never inferred here. */
export function earningsAmount(value: number | null | undefined, currency: 'USD' | 'CAD'): string {
  if (value == null || !Number.isFinite(value)) return 'Unavailable';
  const absolute = Math.abs(value);
  const suffix = absolute >= 1e12 ? 'T' : absolute >= 1e9 ? 'B' : absolute >= 1e6 ? 'M' : null;
  const factor = suffix === 'T' ? 1e12 : suffix === 'B' ? 1e9 : suffix === 'M' ? 1e6 : 1;
  const digits = suffix ? 2 : 0;
  const number = new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value / factor);
  return suffix ? `${number}${suffix}` : number;
}

export function earningsEPS(value: number | null | undefined, currency: 'USD' | 'CAD'): string {
  if (value == null || !Number.isFinite(value)) return 'Unavailable';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 3,
  }).format(value);
}

export function earningsPercent(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return 'Unavailable';
  return `${value > 0 ? '+' : ''}${value.toFixed(2)}%`;
}

export function surpriseClass(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return '';
  return value > 0 ? 'is-positive' : value < 0 ? 'is-negative' : '';
}

export function calendarDate(date: string | null | undefined): string {
  if (!date || !/^\d{4}-\d{2}-\d{2}$/.test(date)) return 'Date unavailable';
  const instant = new Date(`${date}T12:00:00Z`);
  if (Number.isNaN(instant.getTime()) || instant.toISOString().slice(0, 10) !== date)
    return 'Date unavailable';
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    timeZone: 'UTC',
  }).format(instant);
}

export function earningsTiming(value: string): string {
  switch (value) {
    case 'before_open':
      return 'Before market open';
    case 'after_close':
      return 'After market close';
    case 'during_session':
      return 'During market session';
    default:
      return 'Release time unverified';
  }
}
