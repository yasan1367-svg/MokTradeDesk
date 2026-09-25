import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';

interface PnLDistributionChartProps {
  trades: any[];
  height?: number;
}

export default function PnLDistributionChart({ trades, height = 250 }: PnLDistributionChartProps) {
  const bySymbol: Record<string, number> = {};
  trades.forEach((t) => {
    if (!t.symbol) return;
    const pnl = Math.abs(t.pnl || 0);
    bySymbol[t.symbol] = (bySymbol[t.symbol] || 0) + pnl;
  });

  const colors = ['#6C63FF', '#00D4AA', '#FFB84D', '#FF4D6D', '#4DA6FF', '#B84DFF'];

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
            backgroundColor: '#14141E',
            border: '1px solid #2A2A3A',
            borderRadius: '12px',
            color: '#F0F0F5',
            fontSize: '12px',
          }}
          formatter={(value: any) => [`${value} $`, 'مجموع']}
        />
        <Legend wrapperStyle={{ fontSize: '11px', color: '#F0F0F5' }} />
      </PieChart>
    </ResponsiveContainer>
  );
}