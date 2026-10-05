import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

interface SessionBarChartProps {
  data: Record<string, any>;
  metric?: 'win_rate' | 'net_pnl' | 'total_trades';
  height?: number;
}

export default function SessionBarChart({ data, metric = 'win_rate', height = 200 }: SessionBarChartProps) {
  const sessionLabels: Record<string, string> = {
    Asia: 'آسیا',
    Europe: 'اروپا',
    America: 'آمریکا',
    Other: 'سایر',
  };

  const chartData = Object.entries(data).map(([key, value]: [string, any]) => ({
    name: sessionLabels[key] || key,
    value: value[metric] || 0,
  }));

  if (chartData.length === 0) {
    return (
      <div className="text-[var(--text-secondary)] text-center py-8 text-sm">
        داده‌ای برای نمایش وجود ندارد
      </div>
    );
  }

  const colors = ['var(--profit)', 'var(--purple)', 'var(--warning)', 'var(--loss)'];

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
        <XAxis dataKey="name" stroke="var(--text-muted)" style={{ fontSize: '11px' }} tick={{ fill: 'var(--text-muted)' }} />
        <YAxis stroke="var(--text-muted)" style={{ fontSize: '10px' }} tick={{ fill: 'var(--text-muted)' }} />
        <Tooltip
          contentStyle={{
            backgroundColor: 'var(--bg-elevated)',
            border: '1px solid var(--border-medium)',
            borderRadius: '12px',
            color: 'var(--text-primary)',
            fontSize: '12px',
          }}
          formatter={(value: any) => [
            metric === 'win_rate' ? `${value}%` : metric === 'net_pnl' ? `${value} USDT ` : value,
            metric === 'win_rate' ? 'نرخ برد' : metric === 'net_pnl' ? 'سود خالص' : 'معاملات',
          ]}
        />
        <Bar dataKey="value" radius={[8, 8, 0, 0]}>
          {chartData.map((_, index) => (
            <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
