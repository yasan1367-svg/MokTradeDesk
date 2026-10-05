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
          style={{ fontSize: '13px', fontFamily: 'Vazirmatn', fontWeight: 'bold', fill: 'var(--text-primary)' }}
        />
        <PolarRadiusAxis
          angle={90}
          domain={[0, 100]}
          style={{ fontSize: '10px', fill: 'var(--text-muted)' }}
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
            backgroundColor: 'var(--bg-card)',
            border: '2px solid var(--border-subtle)',
            borderRadius: '12px',
            color: 'var(--text-primary)',
            fontSize: '12px',
            fontWeight: 'bold',
            boxShadow: '0 6px 16px rgba(25,50,85,0.08)',
          }}
        />
        <Legend
          wrapperStyle={{ fontSize: '12px', color: 'var(--text-primary)', fontWeight: 'bold', paddingTop: '10px' }}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}