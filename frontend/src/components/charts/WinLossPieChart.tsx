import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';

interface WinLossPieChartProps {
  wins: number;
  losses: number;
  height?: number;
}

export default function WinLossPieChart({ wins, losses, height = 200 }: WinLossPieChartProps) {
  const data = [
    { name: 'برد', value: wins, color: '#00D4AA' },
    { name: 'باخت', value: losses, color: '#FF4D6D' },
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
            backgroundColor: '#14141E',
            border: '1px solid #2A2A3A',
            borderRadius: '12px',
            color: '#F0F0F5',
            fontSize: '12px',
          }}
          formatter={(value: any, name: any) => [`${value} معامله`, name]}
        />
        <Legend wrapperStyle={{ fontSize: '12px', color: '#F0F0F5' }} />
      </PieChart>
    </ResponsiveContainer>
  );
}