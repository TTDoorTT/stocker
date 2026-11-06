export function formatNumber(value: unknown, maximumFractionDigits = 2) {
  return typeof value === 'number' && Number.isFinite(value)
    ? new Intl.NumberFormat('en-US', { maximumFractionDigits }).format(value)
    : 'Unavailable';
}
export function money(value: unknown, currency = 'USD') {
  return typeof value === 'number' && Number.isFinite(value)
    ? new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(value)
    : 'Unavailable';
}
export function dateTime(value?: string | null) {
  if (!value) return 'Unavailable';
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : date.toLocaleString();
}
