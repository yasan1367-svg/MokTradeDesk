import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

interface SessionBarChartProps {
  data: Record<string, any>;
  metric?: 'win_rate' | 'net_pnl' | 'total_trades';
  height?: number;
}

export default function SessionBarChart({ data, metric = 'win_rate', height = 200 }: SessionBarChartProps) {
  const sessionLabels: Record<string, string> = {
    Early: 'ابتدای روز',
    'London Only': 'فقط لندن',
    'London+NY': 'لندن + نیویورک',
    'NY Only': 'فقط نیویورک',
    Outside: 'خارج از بازه',
  };

  const chartData = Object.entries(data).map(([key, value]: [string, any]) => ({
    key,
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

  const colors: Record<string, string> = {
    Early: 'var(--profit)',
    'London Only': 'var(--purple)',
    'London+NY': 'var(--warning)',
    'NY Only': 'var(--accent)',
    Outside: 'var(--text-secondary)',
  };

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
        <XAxis dataKey="name" stroke="var(--text-secondary)" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
        <YAxis stroke="var(--text-secondary)" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
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
          formatter={(value: any) => [
            metric === 'win_rate' ? `${value}%` : metric === 'net_pnl' ? `${value} USDT ` : value,
            metric === 'win_rate' ? 'نرخ برد' : metric === 'net_pnl' ? 'سود خالص' : 'معاملات',
          ]}
        />
        <Bar dataKey="value" radius={[6, 6, 0, 0]} opacity={0.85} activeBar={{ opacity: 1 }}>
          {chartData.map((entry) => (
            <Cell key={entry.key} fill={colors[entry.key] || 'var(--text-secondary)'} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
