import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';

interface PropAnalyticsProps {
  data: any;
}

const FAILURE_LABELS: Record<string, string> = {
  max_daily_dd_exceeded: 'نقض DD روزانه',
  max_total_dd_exceeded: 'نقض DD کلی',
  profit_target_not_met: 'عدم رسیدن به هدف',
  min_trading_days_not_met: 'کمبود روزها',
  rule_violation: 'نقض قانون',
  manual: 'فیل دستی',
  other: 'سایر',
};

const STAGE_LABELS: Record<string, string> = {
  stage_1: 'مرحله ۱',
  stage_2: 'مرحله ۲',
  funded_real: 'رییل',
};

export default function PropAnalytics({ data }: PropAnalyticsProps) {
  if (!data) return null;

  // داده‌ی دلایل فیل‌شدن
  const failureData = Object.entries(data.failure_reasons || {}).map(([key, value]) => ({
    name: FAILURE_LABELS[key] || key,
    value: value as number,
  }));

  // داده‌ی مقایسه‌ی مراحل
  const stageData = Object.entries(data.by_type || {}).map(([key, value]: [string, any]) => ({
    name: STAGE_LABELS[key] || key,
    passed: value.passed,
    failed: value.failed,
    active: value.active,
  }));

  const FAILURE_COLORS = ['var(--loss)', 'var(--loss-border)', 'var(--warning)', 'var(--purple)', 'var(--accent)', 'var(--profit)', 'var(--text-secondary)'];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* نمودار دلایل فیل‌شدن */}
      <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-6 shadow-md">
        <div className="flex items-center gap-3 mb-5 pb-4 border-b border-[var(--border-subtle)]">
          <div className="w-11 h-11 rounded-[14px] bg-[var(--loss-soft)] flex items-center justify-center text-xl">
            ⚠️
          </div>
          <div>
            <h3 className="text-base font-extrabold text-[var(--text-primary)]">دلایل فیل‌شدن</h3>
            <p className="text-[12px] text-[var(--text-secondary)] mt-0.5">تفکیک بر اساس دلیل</p>
          </div>
        </div>

        {failureData.length === 0 ? (
          <div className="text-[var(--text-muted)] text-sm text-center py-12">
            هنوز چالشی فیل نشده است
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie
                data={failureData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={90}
                paddingAngle={3}
                dataKey="value"
              >
                {failureData.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={FAILURE_COLORS[index % FAILURE_COLORS.length]} />
                ))}
              </Pie>
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
                formatter={(value: any) => [`${value} بار`, 'تعداد']}
              />
              <Legend
                wrapperStyle={{ fontSize: '11px', color: 'var(--text-primary)', fontWeight: 'bold' }}
              />
            </PieChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* نمودار مقایسه‌ی مراحل */}
      <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-6 shadow-md">
        <div className="flex items-center gap-3 mb-5 pb-4 border-b border-[var(--border-subtle)]">
          <div className="w-11 h-11 rounded-[14px] bg-[var(--accent-soft)] flex items-center justify-center text-xl">
            📊
          </div>
          <div>
            <h3 className="text-base font-extrabold text-[var(--text-primary)]">وضعیت مراحل</h3>
            <p className="text-[12px] text-[var(--text-secondary)] mt-0.5">پاس‌شده، فیل‌شده، فعال</p>
          </div>
        </div>

        {stageData.length === 0 ? (
          <div className="text-[var(--text-muted)] text-sm text-center py-12">
            داده‌ای وجود ندارد
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={stageData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
              <XAxis
                dataKey="name"
                stroke="var(--text-secondary)"
                style={{ fontSize: '11px', fontFamily: 'Vazirmatn', fontWeight: 'bold' }}
                tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
              />
              <YAxis
                stroke="var(--text-secondary)"
                style={{ fontSize: '11px', fontFamily: 'Vazirmatn' }}
                tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
              />
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
              <Bar dataKey="passed" fill="var(--profit)" radius={[6, 6, 0, 0]} opacity={0.85} activeBar={{ opacity: 1 }} name="پاس‌شده" />
              <Bar dataKey="active" fill="var(--accent)" radius={[6, 6, 0, 0]} opacity={0.85} activeBar={{ opacity: 1 }} name="فعال" />
              <Bar dataKey="failed" fill="var(--loss)" radius={[6, 6, 0, 0]} opacity={0.85} activeBar={{ opacity: 1 }} name="فیل‌شده" />
              <Legend
                wrapperStyle={{ fontSize: '11px', color: 'var(--text-primary)', fontWeight: 'bold' }}
              />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}