import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

interface ComparisonBarChartProps {
  items: any[];
  metric: 'win_rate' | 'profit_factor' | 'net_pnl' | 'max_dd';
  height?: number;
}

export default function ComparisonBarChart({ items, metric, height = 250 }: ComparisonBarChartProps) {
  const metricLabels: Record<string, string> = {
    win_rate: 'نرخ برد (٪)',
    profit_factor: 'فاکتور سود',
    net_pnl: 'سود خالص ($)',
    max_dd: 'حداکثر DD ($)',
  };

  const data = items.map((item) => ({
    name: item.version_name,
    value: item[metric],
    strategy: item.strategy_name,
  }));

  const colors = ['#3F7CFF', '#7959D6', '#13AE81', '#D99B25', '#E45D72'];

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 20, right: 20, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#E5EBF3" />
        <XAxis
          dataKey="name"
          stroke="#6B7A94"
          style={{ fontSize: '11px', fontFamily: 'Vazirmatn', fontWeight: 'bold' }}
          tick={{ fill: '#1A2B47' }}
        />
        <YAxis
          stroke="#6B7A94"
          style={{ fontSize: '11px', fontFamily: 'Vazirmatn' }}
          tick={{ fill: '#6B7A94' }}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#FFFFFF',
            border: '2px solid #E5EBF3',
            borderRadius: '12px',
            color: '#1A2B47',
            fontSize: '12px',
            fontWeight: 'bold',
            boxShadow: '0 6px 16px rgba(25,50,85,0.08)',
          }}
          formatter={(value: any) => [value, metricLabels[metric]]}
        />
        <Bar dataKey="value" radius={[8, 8, 0, 0]}>
          {data.map((_, index) => (
            <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}