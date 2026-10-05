import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip, Legend } from 'recharts';

interface ComparisonRadarChartProps {
  items: any[];
  height?: number;
}

export default function ComparisonRadarChart({ items, height = 400 }: ComparisonRadarChartProps) {
  // نرمال‌سازی هر متریک بین 0 و 100
  const maxWinRate = Math.max(...items.map((i) => i.win_rate), 1);
  const maxPF = Math.max(...items.map((i) => i.profit_factor), 1);
  const maxPnL = Math.max(...items.map((i) => Math.abs(i.net_pnl)), 1);
  const maxDD = Math.max(...items.map((i) => i.max_dd), 1);
  const maxScore = Math.max(...items.map((i) => i.health_score), 1);

  const metrics = [
    { key: 'win_rate', label: 'نرخ برد', max: maxWinRate },
    { key: 'profit_factor', label: 'فاکتور سود', max: maxPF },
    { key: 'net_pnl', label: 'سود خالص', max: maxPnL },
    { key: 'health_score', label: 'Health Score', max: maxScore },
    { key: 'dd_inverse', label: 'کم بودن DD', max: maxDD },
  ];

  const data = metrics.map((m) => {
    const dataPoint: any = { metric: m.label };
    items.forEach((item) => {
      let value = 0;
      if (m.key === 'dd_inverse') {
        value = ((m.max - item.max_dd) / m.max) * 100;
      } else {
        value = (item[m.key] / m.max) * 100;
      }
      dataPoint[item.version_name] = Math.round(value);
    });
    return dataPoint;
  });

  const colors = ['var(--accent)', 'var(--purple)', 'var(--profit)', 'var(--warning)', 'var(--loss)'];

  return (
    <ResponsiveContainer width="100%" height={height}>
      <RadarChart data={data} cx="50%" cy="50%" outerRadius="70%">
        <PolarGrid stroke="var(--border-subtle)" />
        <PolarAngleAxis
          dataKey="metric"
          tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
          style={{ fontSize: '11px', fontFamily: 'Vazirmatn', fontWeight: 'bold', fill: 'var(--text-secondary)' }}
        />
        <PolarRadiusAxis
          angle={90}
          domain={[0, 100]}
          tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
          style={{ fontSize: '11px', fill: 'var(--text-secondary)' }}
        />
        {items.map((item, index) => (
          <Radar
            key={item.version_id}
            name={item.version_name}
            dataKey={item.version_name}
            stroke={colors[index % colors.length]}
            fill={colors[index % colors.length]}
            fillOpacity={0.25}
            strokeWidth={2}
          />
        ))}
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
        />
        <Legend
          wrapperStyle={{ fontSize: '12px', color: 'var(--text-primary)', fontWeight: 'bold', paddingTop: '10px' }}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}