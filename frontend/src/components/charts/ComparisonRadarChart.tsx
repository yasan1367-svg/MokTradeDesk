import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import { measuredProfitFactor } from '../../utils/comparisonChartData';

export function buildRadarData(items: any[]) {
  const measured = items.map((item) => ({
    ...item,
    profit_factor: measuredProfitFactor(item.profit_factor, item.profit_factor_status),
  }));
  const finitePf = measured.flatMap((item) => item.profit_factor === null ? [] : [item.profit_factor]);
  const maxWinRate = Math.max(...measured.map((i) => i.win_rate), 1);
  const maxPF = Math.max(...finitePf, 1);
  const maxDD = Math.max(...measured.map((i) => i.max_dd), 1);
  const maxScore = Math.max(...measured.map((i) => i.health_score), 1);
  const metrics = [
    { key: 'win_rate', label: 'نرخ برد', max: maxWinRate },
    ...(finitePf.length ? [{ key: 'profit_factor', label: 'فاکتور سود', max: maxPF }] : []),
    { key: 'health_score', label: 'Score', max: maxScore },
    { key: 'dd_inverse', label: 'کم بودن DD', max: maxDD },
  ];
  return metrics.map((m) => {
    const point: Record<string, string | number | null> = { metric: m.label };
    measured.forEach((item) => {
      if (m.key === 'profit_factor' && item.profit_factor === null) {
        point[`version_${item.version_id}`] = null;
      } else {
        const original = m.key === 'dd_inverse' ? item.max_dd : item[m.key];
        const value = m.key === 'dd_inverse'
            ? ((m.max - item.max_dd) / m.max) * 100
            : (Math.max(0, Number(original ?? 0)) / m.max) * 100;
        point[`version_${item.version_id}`] = Math.round(value);
        point[`original_${item.version_id}`] = Number(original ?? 0);
      }
    });
    return point;
  });
}

interface ComparisonRadarChartProps {
  items: any[];
  height?: number;
}

export default function ComparisonRadarChart({ items, height = 400 }: ComparisonRadarChartProps) {
  const data = buildRadarData(items);

  const colors = ['var(--accent)', 'var(--purple)', 'var(--profit)', 'var(--warning)', 'var(--loss)'];

  return (
    <ResponsiveContainer width="100%" height={height}>
      <RadarChart data={data} cx="50%" cy="50%" outerRadius="70%">
        <PolarGrid stroke="var(--border-subtle)" />
        <PolarAngleAxis
          dataKey="metric"
          tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
          style={{ fontSize: '11px', fontFamily: 'Vazirmatn', fontWeight: 'bold', fill: 'var(--text-secondary)' }}
        />
        <PolarRadiusAxis
          angle={90}
          domain={[0, 100]}
          tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
          style={{ fontSize: '11px', fill: 'var(--text-secondary)' }}
        />
        {items.map((item, index) => (
          <Radar
            key={item.version_id}
            name={`${item.version_name} (#${item.version_id})`}
            dataKey={`version_${item.version_id}`}
            stroke={colors[index % colors.length]}
            fill={colors[index % colors.length]}
            fillOpacity={0.25}
            strokeWidth={2}
          />
        ))}
        <Tooltip
          formatter={(value, _name, entry) => {
            const dataKey = String(entry.dataKey);
            const id = dataKey.replace('version_', '');
            const original = (entry.payload as Record<string, unknown>)[`original_${id}`];
            const axis = String(entry.payload.metric);
            const unit = axis === 'نرخ برد' ? '%' : axis === 'فاکتور سود' ? 'ratio' : axis === 'Score' ? '/100' : 'USDT';
            return [`${String(value)} / 100 (مقدار اصلی: ${String(original)} ${unit})`, itemLabel(items, Number(id))];
          }}
          contentStyle={{
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border-accent)',
            borderRadius: '8px',
            padding: '8px 12px',
            boxShadow: '0 4px 16px rgba(0,0,0,0.15)',
            color: 'var(--text-primary)',
            fontSize: '12px',
          }}
        />
          <Legend
          wrapperStyle={{ fontSize: '12px', color: 'var(--text-primary)', fontWeight: 'bold', paddingTop: '10px' }}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}

function itemLabel(items: any[], id: number) {
  const item = items.find((candidate) => candidate.version_id === id);
  return item ? `${item.version_name} (#${id})` : `نسخه #${id}`;
}