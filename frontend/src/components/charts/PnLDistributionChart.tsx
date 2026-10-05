import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';

interface PnLDistributionChartProps {
  trades?: any[];
  height?: number;
  /** سطل‌های آماده از endpoint داشبورد: [{range, count}] */
  data?: { range: string; count: number }[];
}

export default function PnLDistributionChart({ trades = [], height = 250, data: buckets }: PnLDistributionChartProps) {
  // حالت ۱ (داشبورد): سطل‌های آماده → نمودار میله‌ای توزیع
  if (buckets && buckets.length > 0) {
    if (!buckets.some((b) => b.count > 0)) {
      return (
        <div className="text-[var(--text-secondary)] text-center py-8 text-sm">
          داده‌ای برای نمایش وجود ندارد
        </div>
      );
    }
    const barColors = ['var(--loss)', 'var(--loss)', 'var(--loss-border)', 'var(--loss-border)', 'var(--profit-border)', 'var(--profit-border)', 'var(--profit)', 'var(--profit)'];
    return (
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={buckets} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
          <XAxis
            dataKey="range"
            tick={{ fontSize: 10, fontFamily: 'Vazirmatn', fill: 'var(--text-secondary)' }}
            stroke="var(--text-secondary)"
          />
          <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} stroke="var(--text-secondary)" />
          <Tooltip
            contentStyle={{
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '12px',
              color: 'var(--text-primary)',
              fontSize: '12px',
              direction: 'rtl',
            }}
            formatter={(value: any) => [`${value} معامله`, 'تعداد']}
          />
          <Bar dataKey="count" radius={[6, 6, 0, 0]}>
            {buckets.map((_, index) => (
              <Cell key={`bucket-${index}`} fill={barColors[index % barColors.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    );
  }

  // حالت ۲ (سازگاری — AnalysisPage): توزیع بر حسب نماد
  const bySymbol: Record<string, number> = {};
  trades.forEach((t) => {
    if (!t.symbol) return;
    const pnl = Math.abs(t.pnl || 0);
    bySymbol[t.symbol] = (bySymbol[t.symbol] || 0) + pnl;
  });

  const colors = ['var(--purple)', 'var(--profit)', 'var(--warning)', 'var(--loss)', 'var(--accent)', 'var(--purple-light)'];

  const data = Object.entries(bySymbol).map(([symbol, value], idx) => ({
    name: symbol,
    value: Math.round(value * 100) / 100,
    color: colors[idx % colors.length],
  }));

  if (data.length === 0) {
    return (
      <div className="text-[var(--text-secondary)] text-center py-8 text-sm">
        داده‌ای برای نمایش وجود ندارد
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={60}
          outerRadius={90}
          paddingAngle={3}
          dataKey="value"
        >
          {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{
            backgroundColor: 'var(--bg-elevated)',
            border: '1px solid var(--border-medium)',
            borderRadius: '12px',
            color: 'var(--text-primary)',
            fontSize: '12px',
          }}
          formatter={(value: any) => [`${value} USDT `, 'مجموع']}
        />
        <Legend wrapperStyle={{ fontSize: '11px', color: 'var(--text-primary)' }} />
      </PieChart>
    </ResponsiveContainer>
  );
}
