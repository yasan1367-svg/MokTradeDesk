import type { FinancialAssets } from '../api/client';

const ACCOUNT_LABELS = [
  ['broker', '📊 بروکر شخصی'],
  ['exchange', '🔄 صرافی'],
  ['trust_wallet', '₿ تراست ولت'],
  ['crypto_wallet', '🪙 کیف‌پول'],
  ['bank', '🏦 بانک'],
  ['card', '💳 کارت'],
  ['cash', '💵 نقد'],
] as const;

export default function FinancialAssetBalances({ assets }: { assets: FinancialAssets }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-[var(--text-secondary)] text-xs border-b border-[var(--border-subtle)]">
            <th className="py-2 text-right">محل نگهداری</th>
            <th className="py-2 text-left px-3">USDT</th>
            <th className="py-2 text-left">ریال</th>
          </tr>
        </thead>
        <tbody>
          {ACCOUNT_LABELS.map(([key, label]) => (
            <tr key={key} className="border-b border-[var(--border-subtle)]">
              <td className="py-2.5 text-[var(--text-secondary)] whitespace-nowrap">{label}</td>
              {(['USDT', 'IRR'] as const).map((currency) => (
                <td key={currency} className="py-2.5 text-left px-3 font-bold text-[var(--text-primary)] tabular-nums">
                  <span dir="ltr">{Number(assets.by_currency?.[currency]?.[key] ?? 0).toLocaleString('en-US')}</span>
                </td>
              ))}
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="font-extrabold text-[var(--accent)]">
            <td className="py-3">مجموع دارایی شخصی</td>
            <td className="py-3 text-left px-3 tabular-nums"><span dir="ltr">{Number(assets.total?.usdt ?? 0).toLocaleString('en-US')}</span></td>
            <td className="py-3 text-left tabular-nums"><span dir="ltr">{Number(assets.total?.irr ?? 0).toLocaleString('en-US')}</span></td>
          </tr>
        </tfoot>
      </table>
      <p className="text-xs text-[var(--text-secondary)] mt-2">
        سرمایه و سود دریافت‌نشدهٔ پراپ در این مجموع نیست. درآمد پس از رسیدن وجه به بانک ثبت می‌شود.
      </p>
    </div>
  );
}
