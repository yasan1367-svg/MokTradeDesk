export function formatEquityDate(value: string): string {
  if (value === 'شروع') return value;
  const datePart = value.slice(0, 10);
  const date = new Date(`${datePart}T12:00:00`);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString('fa-IR');
}