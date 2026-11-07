import type { FinancialMetricName, FinancialPeriod } from './types';

/** The backend owns financial arithmetic; this helper only scales plotted observations. */
export function quarterSeries(periods: FinancialPeriod[], metric: FinancialMetricName) {
  return [...periods]
    .filter((period) => period.period_kind === 'standalone_quarter' && period.fiscal_quarter)
    .sort((a, b) => a.period_end.localeCompare(b.period_end))
    .slice(-8)
    .map((period) => ({
      id: period.period_id,
      label: `${period.fiscal_quarter} FY${period.fiscal_year}`,
      date: period.period_end,
      value: period.metrics[metric]?.value ?? null,
      status: period.metrics[metric]?.status ?? 'unavailable',
    }));
}

export function chartGeometry(values: Array<number | null>) {
  const present = values.filter((value): value is number => value !== null && Number.isFinite(value));
  if (!present.length) return null;
  const minimum = Math.min(0, ...present);
  const maximum = Math.max(0, ...present);
  const span = maximum - minimum || 1;
  const plotTop = 20;
  const plotBottom = 192;
  const y = (value: number) => plotTop + ((maximum - value) / span) * (plotBottom - plotTop);
  return { minimum, maximum, y, baseline: y(0), top: plotTop, bottom: plotBottom };
}

export function formatFinancial(value: number | null, metric: FinancialMetricName, currency: string) {
  if (value === null || !Number.isFinite(value)) return 'Unavailable';
  const unit = metric === 'diluted_eps' ? `${currency}/share` : currency;
  const abs = Math.abs(value);
  const scale = abs >= 1e12 ? 1e12 : abs >= 1e9 ? 1e9 : abs >= 1e6 ? 1e6 : 1;
  const suffix = scale === 1e12 ? 'T' : scale === 1e9 ? 'B' : scale === 1e6 ? 'M' : '';
  const amount = (value / scale).toLocaleString('en-US', {
    minimumFractionDigits: scale === 1 ? (metric === 'diluted_eps' ? 2 : 0) : 1,
    maximumFractionDigits: scale === 1 ? (metric === 'diluted_eps' ? 2 : 2) : 2,
  });
  return `${amount}${suffix} ${unit}`;
}
