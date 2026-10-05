import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

interface ComparisonBarChartProps {
  items: any[];
  metric: 'win_rate' | 'profit_factor' | 'net_pnl' | 'max_dd';
  height?: number;
}

export default function ComparisonBarChart({ items, metric, height = 250 }: ComparisonBarChartProps) {
  const metricLabels: Record<string, string> = {
    win_rate: 'نرخ برد (٪)',
    profit_factor: 'فاکتور سود',
    net_pnl: 'سود خالص (USDT )',
    max_dd: 'حداکثر DD (USDT )',
  };

  const data = items.map((item) => ({
    name: item.version_name,
    value: item[metric],
    strategy: item.strategy_name,
  }));

  const colors = ['var(--accent)', 'var(--purple)', 'var(--profit)', 'var(--warning)', 'var(--loss)'];

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 20, right: 20, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
        <XAxis
          dataKey="name"
          stroke="var(--text-secondary)"
          style={{ fontSize: '11px', fontFamily: 'Vazirmatn', fontWeight: 'bold' }}
          tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
        />
        <YAxis
          stroke="var(--text-secondary)"
          style={{ fontSize: '11px', fontFamily: 'Vazirmatn' }}
          tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
        />
        <Tooltip
          contentStyle={{
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border-accent)',
            borderRadius: '8px',
            padding: '8px 12px',
            boxShadow: '0 4px 16px rgba(0,0,0,0.15)',
            color: 'var(--text-primary)',
            fontSize: '12px',
          }}
          formatter={(value: any) => [value, metricLabels[metric]]}
        />
        <Bar dataKey="value" radius={[6, 6, 0, 0]} opacity={0.85} activeBar={{ opacity: 1 }}>
          {data.map((_, index) => (
            <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
