import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';

interface WinLossPieChartProps {
  wins: number;
  losses: number;
  height?: number;
}

export default function WinLossPieChart({ wins, losses, height = 200 }: WinLossPieChartProps) {
  const data = [
    { name: 'برد', value: wins, color: 'var(--profit)' },
    { name: 'باخت', value: losses, color: 'var(--loss)' },
  ];

  if (wins === 0 && losses === 0) {
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
          innerRadius={50}
          outerRadius={80}
          paddingAngle={5}
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
          formatter={(value: any, name: any) => [`${value} معامله`, name]}
        />
        <Legend wrapperStyle={{ fontSize: '12px', color: 'var(--text-primary)' }} />
      </PieChart>
    </ResponsiveContainer>
  );
}