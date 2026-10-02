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
        <XAxis dataKey="name" stroke="var(--text-muted)" style={{ fontSize: '11px' }} tick={{ fill: 'var(--text-muted)' }} />
        <YAxis stroke="var(--text-muted)" style={{ fontSize: '10px' }} tick={{ fill: 'var(--text-muted)' }} />
        <Tooltip
          contentStyle={{
            backgroundColor: '#14141E',
            border: '1px solid #2A2A3A',
            borderRadius: '12px',
            color: '#F0F0F5',
            fontSize: '12px',
          }}
          formatter={(value: any) => [
            metric === 'win_rate' ? `${value}%` : `${value} USDT `,
            metric === 'win_rate' ? 'نرخ برد' : 'سود خالص',
          ]}
        />
        <Bar dataKey="value" radius={[8, 8, 0, 0]} fill="#6C63FF" />
      </BarChart>
    </ResponsiveContainer>
  );
}
