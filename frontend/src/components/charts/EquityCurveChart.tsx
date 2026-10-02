import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface EquityCurveChartProps {
  trades?: any[];
  initialBalance?: number;
  height?: number;
  /** سری آماده از endpoint داشبورد: [{date, equity}] */
  data?: { date: string; equity: number }[];
}

export default function EquityCurveChart({ trades = [], initialBalance = 0, height = 250, data: series }: EquityCurveChartProps) {
  let data: { index: number; date: string; equity: number; pnl?: number }[];

  if (series && series.length > 0) {
    // استفادهٔ مستقیم از equity_curve آمادهٔ بک‌اند
    data = series.map((p, idx) => ({ index: idx, date: p.date, equity: p.equity }));
  } else {
    const sorted = [...trades]
      .filter((t) => t.close_time)
      .sort((a, b) => new Date(a.close_time).getTime() - new Date(b.close_time).getTime());

    let equity = initialBalance;
    data = sorted.map((t, idx) => {
      equity += t.pnl || 0;
      return {
        index: idx + 1,
        date: new Date(t.close_time).toLocaleDateString('fa-IR'),
        equity: Math.round(equity * 100) / 100,
        pnl: t.pnl || 0,
      };
    });

    data.unshift({
      index: 0,
      date: 'شروع',
      equity: initialBalance,
      pnl: 0,
    });
  }

  if (data.length < 2) {
    return (
      <div className="text-[var(--text-secondary)] text-center py-8 text-sm">
        داده‌ای برای نمایش منحنی سرمایه وجود ندارد
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#00D4AA" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#00D4AA" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
        <XAxis
  dataKey="index"
  stroke="var(--text-secondary)"
  style={{ fontSize: '11px', fontFamily: 'Vazirmatn' }}
  tick={{ fill: 'var(--text-secondary)' }}
/>
<YAxis
  stroke="var(--text-secondary)"
  style={{ fontSize: '11px', fontFamily: 'Vazirmatn' }}
  tick={{ fill: 'var(--text-secondary)' }}
/>
        <Tooltip
          contentStyle={{
            backgroundColor: '#14141E',
            border: '1px solid #2A2A3A',
            borderRadius: '12px',
            color: '#F0F0F5',
            fontSize: '12px',
          }}
          formatter={(value: any) => [`${value} USDT `, 'سرمایه']}
          labelFormatter={(label) => `معامله #${label}`}
        />
        <Area
          type="monotone"
          dataKey="equity"
          stroke="#00D4AA"
          strokeWidth={2}
          fill="url(#equityGradient)"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
