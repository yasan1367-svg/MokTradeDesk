interface AnalysisTableProps {
  title: string;
  icon?: string;
  data: Record<string, any>;
  firstColumnLabel: string;
}

function renderIntervalKey(key: string) {
  const match = key.match(/^(.*?)(\s*\[(.*?)\])?$/);
  if (!match || !match[3]) {
    return <span>{key}</span>;
  }
  const name = match[1];
  const label = match[3];
  const isOutside = label === 'خارج' || label === 'Outside';
  const badgeClass =
    label === 'A'
      ? 'bg-[var(--profit-soft)] text-[var(--profit)]'
      : label === 'B'
      ? 'bg-[var(--accent-soft)] text-[var(--accent)]'
      : label === 'C'
      ? 'bg-[var(--bg-input)] text-[var(--text-muted)]'
      : isOutside
      ? 'bg-[var(--warning-soft)] text-[var(--warning-strong)] border border-[var(--warning-border)]'
      : 'bg-[var(--bg-input)] text-[var(--text-secondary)]';

  return (
    <div className="flex items-center gap-2">
      <span>{name}</span>
      <span className={`inline-flex items-center px-2 py-0.5 rounded-[6px] text-[11px] font-extrabold ${badgeClass}`}>
        {isOutside ? 'خارج از بازه' : label}
      </span>
    </div>
  );
}

export default function AnalysisTable({ title, icon, data, firstColumnLabel }: AnalysisTableProps) {
  const entries = Object.entries(data);

  if (entries.length === 0) {
    return (
      <div className="glass-card p-6">
        <h3 className="text-[var(--text-primary)] font-bold mb-4">
          {icon} {title}
        </h3>
        <div className="text-[var(--text-secondary)] text-sm text-center py-4">
          داده‌ای برای نمایش وجود ندارد
        </div>
      </div>
    );
  }

  return (
    <div className="glass-card p-6">
      <h3 className="text-[var(--text-primary)] font-bold mb-4">
        {icon} {title}
      </h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-[var(--text-secondary)] border-b border-[var(--border-subtle)]">
              <th className="text-right py-2">{firstColumnLabel}</th>
              <th className="text-right py-2">معاملات</th>
              <th className="text-right py-2">برد</th>
              <th className="text-right py-2">باخت</th>
              <th className="text-right py-2">نرخ برد</th>
              <th className="text-right py-2">سود خالص</th>
              <th className="text-right py-2">فاکتور سود</th>
            </tr>
          </thead>
          <tbody>
            {entries.map(([key, value]: [string, any]) => {
              const isOutside = key.includes('[خارج]');
              return (
                <tr
                  key={key}
                  className={`border-b transition-colors ${
                    isOutside
                      ? 'border-[var(--warning-border)]/40 bg-[var(--warning-soft)]/20 hover:bg-[var(--warning-soft)]/30'
                      : 'border-card-border/50 hover:bg-card/50'
                  }`}
                >
                  <td className="py-2 text-[var(--text-primary)] font-bold">
                    {renderIntervalKey(key)}
                  </td>
                  <td className="py-2 text-[var(--text-primary)]">{value.total_trades}</td>
                  <td className="py-2 text-[var(--profit)]">{value.wins}</td>
                  <td className="py-2 text-[var(--loss)]">{value.losses}</td>
                  <td className="py-2 text-[var(--text-primary)]">{value.win_rate}٪</td>
                  <td className={`py-2 font-bold ${value.net_pnl >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
                    {value.net_pnl >= 0 ? '+' : ''}{value.net_pnl} USDT
                  </td>
                  <td className="py-2 text-[var(--accent)]">{value.profit_factor}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
