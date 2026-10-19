import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface WeekdayBarChartProps {
  data: Record<string, any>;
  metric?: 'win_rate' | 'net_pnl';
  height?: number;
}

export default function WeekdayBarChart({ data, metric = 'win_rate', height = 200 }: WeekdayBarChartProps) {
  const weekdayLabels: Record<string, string> = {
    Saturday: 'شنبه',
    Sunday: 'یک‌شنبه',
    Monday: 'دوشنبه',
    Tuesday: 'سه‌شنبه',
    Wednesday: 'چهارشنبه',
    Thursday: 'پنج‌شنبه',
    Friday: 'جمعه',
  };

  const order = ['Saturday', 'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];

  const chartData = order
    .filter((day) => data[day])
    .map((day) => ({
      name: weekdayLabels[day] || day,
      value: data[day][metric] || 0,
    }));

  if (chartData.length === 0) {
    return (
      <div className="text-[var(--text-secondary)] text-center py-8 text-sm">
        داده‌ای برای نمایش وجود ندارد
      </div>
    );
  }

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
            metric === 'win_rate' ? `${value}%` : `${value} USDT `,
            metric === 'win_rate' ? 'نرخ برد' : 'سود خالص',
          ]}
        />
        <Bar dataKey="value" radius={[6, 6, 0, 0]} fill="var(--purple)" opacity={0.85} activeBar={{ opacity: 1 }} />
      </BarChart>
    </ResponsiveContainer>
  );
}
