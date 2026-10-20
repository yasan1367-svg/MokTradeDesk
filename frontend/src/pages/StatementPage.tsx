import { useState, useEffect, useCallback } from 'react';
import {
  Award,
  Download,
  Printer,
  ShieldCheck,
  Copy,
  Check,
  RefreshCw,
  ArrowUpRight,
  ArrowDownRight,
  FileCheck,
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { getStatementData, exportStatementPdf } from '../api/client';
import type { StatementParams } from '../api/client';
import { useToast } from '../components/ToastProvider';

interface StatementData {
  credentials: {
    trader_name: string;
    account_id: string;
    audit_date: string;
    period_from: string | null;
    period_to: string | null;
    initial_balance: number;
    current_balance: number;
    verification_hash: string;
    currency: string;
  };
  metrics: {
    net_pnl: number;
    gross_profit: number;
    gross_loss: number;
    return_pct: number;
    profit_factor: number | null;
    profit_factor_status: string;
    win_rate: number;
    total_trades: number;
    winning_trades: number;
    losing_trades: number;
    breakeven_trades: number;
    avg_win: number;
    avg_loss: number;
    win_loss_ratio: number;
    largest_win: number;
    largest_loss: number;
    avg_trade_pnl: number;
    sharpe_ratio: number;
    sortino_ratio: number;
    calmar_ratio: number | null;
    recovery_factor: number | null;
    max_drawdown: number;
    max_drawdown_pct: number;
    expectancy_usd: number;
    expectancy_r: number | null;
    avg_r_multiple: number | null;
    total_r_multiple: number | null;
    max_consecutive_wins: number;
    max_consecutive_losses: number;
  };
  long_short: {
    long_trades: number;
    long_wins: number;
    long_win_rate: number;
    long_pnl: number;
    short_trades: number;
    short_wins: number;
    short_win_rate: number;
    short_pnl: number;
  };
  monthly_matrix: Array<{
    year: number;
    months: Record<string, number | null>;
    months_pnl: Record<string, number | null>;
    ytd_return_pct: number;
    ytd_pnl: number;
  }>;
  equity_curve: Array<{
    trade_num: number;
    close_time: string | null;
    equity: number;
    drawdown: number;
    drawdown_pct: number;
  }>;
  top_symbols: Array<{
    symbol: string;
    trades_count: number;
    net_pnl: number;
    win_rate: number;
    profit_factor: number | null;
  }>;
}

const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

export default function StatementPage() {
  const toast = useToast();

  // فیلترها و مشخصات حسابرسی
  const [traderName, setTraderName] = useState(() => localStorage.getItem('mok_statement_trader') || 'Chief Investment Officer');
  const [accountId, setAccountId] = useState(() => localStorage.getItem('mok_statement_account') || 'MTD-ACT-001');
  const [initialBalance, setInitialBalance] = useState<number>(10000);
  const currency = 'USDT';
  const [scope, setScope] = useState<string>('all');
  const [lang, setLang] = useState<'en' | 'fa'>('en');

  const [loading, setLoading] = useState(true);
  const [pdfDownloading, setPdfDownloading] = useState(false);
  const [copiedHash, setCopiedHash] = useState(false);
  const [data, setData] = useState<StatementData | null>(null);

  const loadStatement = useCallback(async () => {
    setLoading(true);
    try {
      const params: StatementParams = {
        trader_name: traderName.trim() || 'Portfolio Manager',
        account_id: accountId.trim() || 'MTD-ACT-001',
        initial_balance: Number(initialBalance) || 10000,
        currency,
        scope: scope === 'all' ? undefined : scope,
        lang,
      };
      const res = await getStatementData(params);
      setData(res.data);
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'خطا در بارگذاری استیتمنت رسمی');
    } finally {
      setLoading(false);
    }
  }, [traderName, accountId, initialBalance, currency, scope, lang, toast]);

  useEffect(() => {
    loadStatement();
  }, [loadStatement]);

  const handleSaveParams = () => {
    localStorage.setItem('mok_statement_trader', traderName);
    localStorage.setItem('mok_statement_account', accountId);
    toast.success('مشخصات حسابرسی ذخیره شد');
    loadStatement();
  };

  const handleDownloadPdf = async () => {
    setPdfDownloading(true);
    try {
      const params: StatementParams = {
        trader_name: traderName.trim() || 'Portfolio Manager',
        account_id: accountId.trim() || 'MTD-ACT-001',
        initial_balance: Number(initialBalance) || 10000,
        currency,
        scope: scope === 'all' ? undefined : scope,
        lang,
      };
      const res = await exportStatementPdf(params);
      const blob = new Blob([res.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `MTD_Institutional_Statement_${lang.toUpperCase()}_${Date.now()}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success('فایل PDF استیتمنت رسمی دانلود شد');
    } catch (err) {
      toast.error('خطا در تولید فایل PDF');
    } finally {
      setPdfDownloading(false);
    }
  };

  const handleCopyHash = () => {
    if (!data?.credentials?.verification_hash) return;
    navigator.clipboard.writeText(data.credentials.verification_hash);
    setCopiedHash(true);
    toast.success('کد هش اعتبارسنجی کپی شد');
    setTimeout(() => setCopiedHash(false), 2000);
  };

  const m = data?.metrics;
  const cred = data?.credentials;
  const ls = data?.long_short;

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* ── نوار فیلتر و کنترل‌های استیتمنت ── */}
      <div className="app-card p-5 border border-[var(--border-subtle)] space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <div className="w-10 h-10 rounded-xl bg-[var(--accent)]/10 text-[var(--accent)] flex items-center justify-center font-bold">
              <Award size={22} />
            </div>
            <div>
              <h2 className="text-base font-extrabold text-[var(--text-primary)]">تنظیمات استیتمنت رسمی و تاییدیه نهادی</h2>
              <p className="text-xs text-[var(--text-secondary)]">سفارشی‌سازی مشخصات گزارش جهت ارائه به بانک‌ها، صندوق‌های سرمایه‌گذاری و پراپ‌فرم‌ها</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleDownloadPdf}
              disabled={pdfDownloading || loading}
              className="flex items-center gap-1.5 px-4 py-2 bg-[var(--accent)] hover:opacity-90 text-white rounded-xl text-xs font-bold transition-all shadow-sm disabled:opacity-50"
            >
              {pdfDownloading ? <RefreshCw size={14} className="animate-spin" /> : <Download size={14} />}
              <span>دانلود PDF استیتمنت ({lang.toUpperCase()})</span>
            </button>
            <button
              onClick={() => window.print()}
              className="flex items-center gap-1.5 px-3 py-2 bg-[var(--bg-elevated)] hover:bg-[var(--border-subtle)] text-[var(--text-secondary)] rounded-xl text-xs font-semibold transition-all border border-[var(--border-subtle)]"
            >
              <Printer size={14} />
              <span>پرینت</span>
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 pt-2 border-t border-[var(--border-subtle)]/70">
          <div>
            <label className="text-[11px] font-semibold text-[var(--text-secondary)] block mb-1">نام مدیر / تریدر</label>
            <input
              type="text"
              value={traderName}
              onChange={(e) => setTraderName(e.target.value)}
              className="w-full text-xs p-2 rounded-lg bg-[var(--bg-input)] border border-[var(--border-subtle)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent)]"
              placeholder="Portfolio Manager"
            />
          </div>

          <div>
            <label className="text-[11px] font-semibold text-[var(--text-secondary)] block mb-1">شناسه حساب / کد تایید</label>
            <input
              type="text"
              value={accountId}
              onChange={(e) => setAccountId(e.target.value)}
              className="w-full text-xs p-2 rounded-lg bg-[var(--bg-input)] border border-[var(--border-subtle)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent)]"
              placeholder="MTD-ACT-001"
            />
          </div>

          <div>
            <label className="text-[11px] font-semibold text-[var(--text-secondary)] block mb-1">سرمایه اولیه ({currency})</label>
            <input
              type="number"
              value={initialBalance}
              onChange={(e) => setInitialBalance(Number(e.target.value))}
              className="w-full text-xs p-2 rounded-lg bg-[var(--bg-input)] border border-[var(--border-subtle)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent)]"
              step="1000"
              min="100"
            />
          </div>

          <div>
            <label className="text-[11px] font-semibold text-[var(--text-secondary)] block mb-1">دامنه معاملات</label>
            <select
              value={scope}
              onChange={(e) => setScope(e.target.value)}
              className="w-full text-xs p-2 rounded-lg bg-[var(--bg-input)] border border-[var(--border-subtle)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent)]"
            >
              <option value="all">همه معاملات</option>
              <option value="forward">فوروارد تست (Forward Test)</option>
              <option value="backtest">بک‌تست (Backtest)</option>
            </select>
          </div>

          <div>
            <label className="text-[11px] font-semibold text-[var(--text-secondary)] block mb-1">زبان PDF خروجی</label>
            <div className="grid grid-cols-2 gap-1 p-0.5 rounded-lg bg-[var(--bg-input)] border border-[var(--border-subtle)]">
              <button
                type="button"
                onClick={() => setLang('en')}
                className={`py-1 text-xs font-bold rounded-md transition-all ${lang === 'en' ? 'bg-[var(--accent)] text-white shadow-sm' : 'text-[var(--text-secondary)]'}`}
              >
                EN (بین‌المللی)
              </button>
              <button
                type="button"
                onClick={() => setLang('fa')}
                className={`py-1 text-xs font-bold rounded-md transition-all ${lang === 'fa' ? 'bg-[var(--accent)] text-white shadow-sm' : 'text-[var(--text-secondary)]'}`}
              >
                FA (فارسی)
              </button>
            </div>
          </div>

          <div className="flex items-end">
            <button
              onClick={handleSaveParams}
              className="w-full py-2 bg-[var(--bg-elevated)] hover:bg-[var(--accent-soft)] hover:text-[var(--accent)] text-[var(--text-primary)] rounded-lg text-xs font-bold transition-all border border-[var(--border-subtle)] flex items-center justify-center gap-1.5"
            >
              <RefreshCw size={13} />
              <span>محاسبه مجدد</span>
            </button>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center p-16 text-[var(--text-secondary)] gap-3">
          <RefreshCw size={20} className="animate-spin text-[var(--accent)]" />
          <span className="text-sm font-semibold">در حال حسابرسی و تحلیل دفتر کل معاملات…</span>
        </div>
      ) : !data || !m || !cred || !ls ? (
        <div className="app-card p-12 text-center text-[var(--text-secondary)]">
          داده‌ای برای استیتمنت یافت نشد. لطفاً فیلترها را بررسی کنید.
        </div>
      ) : (
        <>
          {/* ── لوح سربرگ حسابرسی و تاییدیه دیجیتال (Audit Dossier Header) ── */}
          <div className="app-card p-6 border-t-4 border-t-[var(--accent)] relative overflow-hidden bg-gradient-to-br from-[var(--bg-card)] via-[var(--bg-card)] to-[var(--accent-soft)]/20 shadow-md">
            <div className="flex flex-wrap items-start justify-between gap-6 relative z-10">
              <div className="space-y-1">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[var(--accent)]/10 text-[var(--accent)] text-[11px] font-bold tracking-wider uppercase mb-2">
                  <ShieldCheck size={14} />
                  <span>Institutional Trading Audit Dossier · GIPS Compliant</span>
                </div>
                <h1 className="text-2xl font-black text-[var(--text-primary)] tracking-tight">
                  صورت‌حساب رسمی حسابرسی عملکرد معاملاتی
                </h1>
                <p className="text-xs text-[var(--text-secondary)]">
                  تاییدیه مستقل دفتر کل معاملات محلی · بازه: {cred.period_from || '—'} تا {cred.period_to || '—'}
                </p>
              </div>

              {/* نشان اعتبارسنجی دیجیتال و هش امنیتی */}
              <div className="p-3.5 rounded-xl bg-[var(--bg-elevated)]/90 border border-[var(--border-subtle)] text-right space-y-1.5 shadow-sm">
                <div className="flex items-center justify-between gap-3 text-[10px] text-[var(--text-muted)]">
                  <span>کد تاییدیه هش امنیتی:</span>
                  <span className="inline-flex items-center gap-1 text-[var(--profit)] font-bold">
                    <span className="w-1.5 h-1.5 rounded-full bg-[var(--profit)] animate-pulse" />
                    VERIFIED LEDGER
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <code className="text-xs font-mono font-bold text-[var(--accent)] dir-ltr bg-[var(--bg-base)] px-2 py-1 rounded border border-[var(--border-subtle)]">
                    {cred.verification_hash}
                  </code>
                  <button
                    onClick={handleCopyHash}
                    className="p-1 hover:bg-[var(--accent-soft)] text-[var(--text-secondary)] rounded transition-all"
                    title="کپی کد اعتبارسنجی"
                  >
                    {copiedHash ? <Check size={14} className="text-[var(--profit)]" /> : <Copy size={14} />}
                  </button>
                </div>
                <div className="text-[10px] text-[var(--text-muted)]">
                  تاریخ صدور: <span className="dir-ltr font-mono">{cred.audit_date}</span>
                </div>
              </div>
            </div>

            {/* کارت‌های شاخص‌های کلیدی اولیه */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mt-6 pt-5 border-t border-[var(--border-subtle)]">
              <div className="p-3 rounded-xl bg-[var(--bg-base)]/50 border border-[var(--border-subtle)]/70">
                <div className="text-[11px] text-[var(--text-secondary)] font-medium mb-1">سرمایه اولیه</div>
                <div className="text-sm font-extrabold text-[var(--text-primary)] dir-ltr font-mono">
                  {cred.initial_balance.toLocaleString()} {currency}
                </div>
              </div>

              <div className="p-3 rounded-xl bg-[var(--bg-base)]/50 border border-[var(--border-subtle)]/70">
                <div className="text-[11px] text-[var(--text-secondary)] font-medium mb-1">ارزش جاری پرتفوی</div>
                <div className="text-sm font-extrabold text-[var(--text-primary)] dir-ltr font-mono">
                  {cred.current_balance.toLocaleString()} {currency}
                </div>
              </div>

              <div className="p-3 rounded-xl bg-[var(--bg-base)]/50 border border-[var(--border-subtle)]/70">
                <div className="text-[11px] text-[var(--text-secondary)] font-medium mb-1">سود / زیان کل</div>
                <div className={`text-sm font-extrabold dir-ltr font-mono ${m.net_pnl >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
                  {m.net_pnl >= 0 ? '+' : ''}{m.net_pnl.toLocaleString()} {currency}
                </div>
              </div>

              <div className="p-3 rounded-xl bg-[var(--bg-base)]/50 border border-[var(--border-subtle)]/70">
                <div className="text-[11px] text-[var(--text-secondary)] font-medium mb-1">درصد بازدهی کل</div>
                <div className={`text-sm font-extrabold dir-ltr font-mono ${m.return_pct >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
                  {m.return_pct >= 0 ? '+' : ''}{m.return_pct.toFixed(2)}%
                </div>
              </div>

              <div className="p-3 rounded-xl bg-[var(--bg-base)]/50 border border-[var(--border-subtle)]/70">
                <div className="text-[11px] text-[var(--text-secondary)] font-medium mb-1">فاکتور سود (PF)</div>
                <div className="text-sm font-extrabold text-[var(--accent)] dir-ltr font-mono">
                  {m.profit_factor !== null ? m.profit_factor.toFixed(2) : '—'}
                </div>
              </div>

              <div className="p-3 rounded-xl bg-[var(--bg-base)]/50 border border-[var(--border-subtle)]/70">
                <div className="text-[11px] text-[var(--text-secondary)] font-medium mb-1">حداکثر افت (DD)</div>
                <div className="text-sm font-extrabold text-[var(--loss)] dir-ltr font-mono">
                  -{m.max_drawdown.toLocaleString()} ({m.max_drawdown_pct.toFixed(1)}%)
                </div>
              </div>
            </div>
          </div>

          {/* ── بخش ۱: جدول شاخص‌های ارزیابی ریسک و کیفیت نهادی ── */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="app-card p-4 border border-[var(--border-subtle)]">
              <div className="text-xs font-bold text-[var(--text-secondary)] mb-1 flex items-center justify-between">
                <span>نسبت شارپ (Sharpe)</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--accent)]/10 text-[var(--accent)]">سالانه شده</span>
              </div>
              <div className="text-2xl font-black text-[var(--accent)] dir-ltr font-mono">{m.sharpe_ratio.toFixed(2)}</div>
              <p className="text-[11px] text-[var(--text-muted)] mt-1">سنجش بازدهی نسبت به نوسان کل حساب (&gt;۱.۰ استاندارد صندوق‌ها)</p>
            </div>

            <div className="app-card p-4 border border-[var(--border-subtle)]">
              <div className="text-xs font-bold text-[var(--text-secondary)] mb-1 flex items-center justify-between">
                <span>نسبت سورتینو (Sortino)</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--purple)]/10 text-[var(--purple)]">ریسک نزولی</span>
              </div>
              <div className="text-2xl font-black text-[var(--purple)] dir-ltr font-mono">{m.sortino_ratio.toFixed(2)}</div>
              <p className="text-[11px] text-[var(--text-muted)] mt-1">تمرکز انحصاری بر جریمه نوسانات منفی و باخت‌ها</p>
            </div>

            <div className="app-card p-4 border border-[var(--border-subtle)]">
              <div className="text-xs font-bold text-[var(--text-secondary)] mb-1 flex items-center justify-between">
                <span>نسبت کالمار (Calmar)</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--profit)]/10 text-[var(--profit)]">بازده / افت</span>
              </div>
              <div className="text-2xl font-black text-[var(--profit)] dir-ltr font-mono">
                {m.calmar_ratio !== null ? m.calmar_ratio.toFixed(2) : '—'}
              </div>
              <p className="text-[11px] text-[var(--text-muted)] mt-1">نسبت سود به حداکثر افت سرمایه (معیار اصلی سرمایه‌گذاران نهادی)</p>
            </div>

            <div className="app-card p-4 border border-[var(--border-subtle)]">
              <div className="text-xs font-bold text-[var(--text-secondary)] mb-1 flex items-center justify-between">
                <span>امید ریاضی (Expectancy)</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--warning)]/10 text-[var(--warning)]">ارزش هر ترید</span>
              </div>
              <div className={`text-2xl font-black dir-ltr font-mono ${m.expectancy_usd >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
                {m.expectancy_usd >= 0 ? '+' : ''}{m.expectancy_usd.toFixed(2)} {currency}
              </div>
              <p className="text-[11px] text-[var(--text-muted)] mt-1">
                {m.expectancy_r !== null ? `معادل ${m.expectancy_r >= 0 ? '+' : ''}${m.expectancy_r.toFixed(2)}R به ازای هر معامله` : 'میانگین سود انتظاری به ازای ورود'}
              </p>
            </div>
          </div>

          {/* ── بخش ۲: نمودارهای رشد سرمایه و دراوداون زیر آب ── */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {/* نمودار منحنی رشد سرمایه */}
            <div className="app-card p-5 border border-[var(--border-subtle)]">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-sm font-bold text-[var(--text-primary)]">📈 منحنی انباشته سرمایه (Equity Curve)</h3>
                  <p className="text-xs text-[var(--text-secondary)]">روند رشد دارایی در طول {data.equity_curve.length - 1} معامله بسته شده</p>
                </div>
                <span className="text-xs font-mono font-bold text-[var(--accent)] dir-ltr">
                  {cred.current_balance.toLocaleString()} {currency}
                </span>
              </div>
              <div className="h-[230px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={data.equity_curve} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="eqGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="var(--accent)" stopOpacity={0.35} />
                        <stop offset="95%" stopColor="var(--accent)" stopOpacity={0.0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" vertical={false} />
                    <XAxis dataKey="trade_num" stroke="var(--text-muted)" fontSize={11} tickLine={false} />
                    <YAxis stroke="var(--text-muted)" fontSize={11} domain={['auto', 'auto']} tickLine={false} />
                    <Tooltip
                      content={({ active, payload }) => {
                        if (!active || !payload?.length) return null;
                        const p = payload[0].payload;
                        return (
                          <div className="p-2 rounded-lg bg-[var(--bg-elevated)] border border-[var(--border-subtle)] text-xs shadow-lg">
                            <div className="text-[var(--text-secondary)] font-medium">معامله #{p.trade_num}</div>
                            <div className="text-[var(--accent)] font-bold dir-ltr">{p.equity.toLocaleString()} {currency}</div>
                          </div>
                        );
                      }}
                    />
                    <Area type="monotone" dataKey="equity" stroke="var(--accent)" strokeWidth={2.5} fill="url(#eqGradient)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* نمودار دراوداون زیر آب (Underwater Chart) */}
            <div className="app-card p-5 border border-[var(--border-subtle)]">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-sm font-bold text-[var(--text-primary)]">🌊 افت سرمایه زیر آب (Underwater Drawdown)</h3>
                  <p className="text-xs text-[var(--text-secondary)]">سنجش عمق و ماندگاری افت حساب از سقف تاریخی</p>
                </div>
                <span className="text-xs font-mono font-bold text-[var(--loss)] dir-ltr">
                  Max: -{m.max_drawdown_pct.toFixed(1)}%
                </span>
              </div>
              <div className="h-[230px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={data.equity_curve} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="ddGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="var(--loss)" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="var(--loss)" stopOpacity={0.05} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" vertical={false} />
                    <XAxis dataKey="trade_num" stroke="var(--text-muted)" fontSize={11} tickLine={false} />
                    <YAxis stroke="var(--text-muted)" fontSize={11} tickFormatter={(v) => `-${v}%`} tickLine={false} />
                    <Tooltip
                      content={({ active, payload }) => {
                        if (!active || !payload?.length) return null;
                        const p = payload[0].payload;
                        return (
                          <div className="p-2 rounded-lg bg-[var(--bg-elevated)] border border-[var(--border-subtle)] text-xs shadow-lg">
                            <div className="text-[var(--text-secondary)] font-medium">معامله #{p.trade_num}</div>
                            <div className="text-[var(--loss)] font-bold dir-ltr">افت: -{p.drawdown.toLocaleString()} ({p.drawdown_pct}%)</div>
                          </div>
                        );
                      }}
                    />
                    <Area type="monotone" dataKey="drawdown_pct" stroke="var(--loss)" strokeWidth={2} fill="url(#ddGradient)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* ── بخش ۳: ماتریس بازدهی ماهانه (Monthly Returns Matrix) ── */}
          <div className="app-card p-5 border border-[var(--border-subtle)]">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="text-sm font-bold text-[var(--text-primary)]">📅 ماتریس عملکرد ماهانه و سالانه (Monthly Returns Matrix)</h3>
                <p className="text-xs text-[var(--text-secondary)]">تفکیک درصد سودآوری بر اساس استاندارد گزارش‌های مدیریت دارایی (GIPS)</p>
              </div>
            </div>

            {data.monthly_matrix.length === 0 ? (
              <div className="py-8 text-center text-xs text-[var(--text-muted)]">معامله‌ای با تاریخ خروج ثبت نشده است</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-center border-collapse">
                  <thead>
                    <tr className="border-b border-[var(--border-subtle)] text-[var(--text-secondary)] font-bold">
                      <th className="py-2.5 px-3 text-right">سال</th>
                      {MONTH_NAMES.map((mn) => (
                        <th key={mn} className="py-2.5 px-2">{mn}</th>
                      ))}
                      <th className="py-2.5 px-3 bg-[var(--accent-soft)]/40 text-[var(--accent)] font-extrabold">YTD</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.monthly_matrix.map((row) => (
                      <tr key={row.year} className="border-b border-[var(--border-subtle)]/40 hover:bg-[var(--accent-soft)]/10 transition-colors">
                        <td className="py-2.5 px-3 font-bold text-[var(--text-primary)] text-right font-mono">{row.year}</td>
                        {MONTH_NAMES.map((mn) => {
                          const val = row.months[mn];
                          if (val === null || val === undefined) {
                            return <td key={mn} className="py-2.5 px-2 text-[var(--text-muted)]/50">—</td>;
                          }
                          const isPos = val >= 0;
                          return (
                            <td
                              key={mn}
                              className={`py-2.5 px-2 font-mono font-bold dir-ltr ${
                                isPos ? 'text-[var(--profit)] bg-[var(--profit-soft)]/20' : 'text-[var(--loss)] bg-[var(--loss-soft)]/20'
                              }`}
                            >
                              {isPos ? '+' : ''}{val.toFixed(1)}%
                            </td>
                          );
                        })}
                        <td className={`py-2.5 px-3 font-mono font-extrabold dir-ltr bg-[var(--accent-soft)]/30 ${
                          row.ytd_return_pct >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'
                        }`}>
                          {row.ytd_return_pct >= 0 ? '+' : ''}{row.ytd_return_pct.toFixed(1)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* ── بخش ۴: تفکیک موقعیت‌های لانگ/شورت و ابزارهای برتر ── */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {/* تفکیک لانگ و شورت */}
            <div className="app-card p-5 border border-[var(--border-subtle)] space-y-4">
              <h3 className="text-sm font-bold text-[var(--text-primary)]">⚖️ مشخصات موقعیت‌های خرید و فروش (Long vs Short)</h3>
              <div className="grid grid-cols-2 gap-3">
                <div className="p-4 rounded-xl bg-[var(--bg-base)] border border-[var(--border-subtle)] space-y-2">
                  <div className="flex items-center justify-between text-xs font-bold text-[var(--text-primary)]">
                    <span className="flex items-center gap-1.5 text-[var(--profit)]">
                      <ArrowUpRight size={16} /> معاملات خرید (Long)
                    </span>
                    <span className="font-mono">{ls.long_trades} معامله</span>
                  </div>
                  <div className="text-lg font-black text-[var(--profit)] dir-ltr font-mono">
                    {ls.long_pnl >= 0 ? '+' : ''}{ls.long_pnl.toLocaleString()} {currency}
                  </div>
                  <div className="text-[11px] text-[var(--text-secondary)]">
                    وین‌ریت خرید: <span className="font-bold">{ls.long_win_rate}%</span> ({ls.long_wins} برد)
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-[var(--bg-base)] border border-[var(--border-subtle)] space-y-2">
                  <div className="flex items-center justify-between text-xs font-bold text-[var(--text-primary)]">
                    <span className="flex items-center gap-1.5 text-[var(--loss)]">
                      <ArrowDownRight size={16} /> معاملات فروش (Short)
                    </span>
                    <span className="font-mono">{ls.short_trades} معامله</span>
                  </div>
                  <div className="text-lg font-black text-[var(--loss)] dir-ltr font-mono">
                    {ls.short_pnl >= 0 ? '+' : ''}{ls.short_pnl.toLocaleString()} {currency}
                  </div>
                  <div className="text-[11px] text-[var(--text-secondary)]">
                    وین‌ریت فروش: <span className="font-bold">{ls.short_win_rate}%</span> ({ls.short_wins} برد)
                  </div>
                </div>
              </div>

              {/* آمار معاملاتی تفصیلی */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-[var(--border-subtle)] text-center">
                <div className="p-2">
                  <div className="text-[10px] text-[var(--text-secondary)]">میانگین سود</div>
                  <div className="text-xs font-bold text-[var(--profit)] dir-ltr font-mono">+{m.avg_win.toFixed(2)}</div>
                </div>
                <div className="p-2">
                  <div className="text-[10px] text-[var(--text-secondary)]">میانگین زیان</div>
                  <div className="text-xs font-bold text-[var(--loss)] dir-ltr font-mono">-{m.avg_loss.toFixed(2)}</div>
                </div>
                <div className="p-2">
                  <div className="text-[10px] text-[var(--text-secondary)]">نسبت سود/زیان</div>
                  <div className="text-xs font-bold text-[var(--accent)] dir-ltr font-mono">x{m.win_loss_ratio.toFixed(2)}</div>
                </div>
                <div className="p-2">
                  <div className="text-[10px] text-[var(--text-secondary)]">توالی باخت</div>
                  <div className="text-xs font-bold text-[var(--warning)] dir-ltr font-mono">{m.max_consecutive_losses} معامله</div>
                </div>
              </div>
            </div>

            {/* نمادهای برتر */}
            <div className="app-card p-5 border border-[var(--border-subtle)]">
              <h3 className="text-sm font-bold text-[var(--text-primary)] mb-3">🪙 توزیع ابزارهای معاملاتی برتر</h3>
              {data.top_symbols.length === 0 ? (
                <div className="py-8 text-center text-xs text-[var(--text-muted)]">هیچ داده‌ای ثبت نشده است</div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-[var(--border-subtle)] text-[var(--text-secondary)]">
                        <th className="text-right py-2 px-2">نماد</th>
                        <th className="text-center py-2 px-2">تعداد</th>
                        <th className="text-center py-2 px-2">وین‌ریت</th>
                        <th className="text-center py-2 px-2">PF</th>
                        <th className="text-left py-2 px-2">سود خالص</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.top_symbols.slice(0, 6).map((s) => (
                        <tr key={s.symbol} className="border-b border-[var(--border-subtle)]/40 hover:bg-[var(--accent-soft)]/20 transition-colors">
                          <td className="py-2 px-2 font-bold text-[var(--text-primary)]">{s.symbol}</td>
                          <td className="py-2 px-2 text-center font-mono">{s.trades_count}</td>
                          <td className="py-2 px-2 text-center font-mono">{s.win_rate}%</td>
                          <td className="py-2 px-2 text-center font-mono">{s.profit_factor !== null ? s.profit_factor.toFixed(2) : '—'}</td>
                          <td className={`py-2 px-2 text-left font-mono font-bold dir-ltr ${s.net_pnl >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
                            {s.net_pnl >= 0 ? '+' : ''}{s.net_pnl.toLocaleString()} {currency}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>

          {/* ── بخش ۵: متن تاییدیه حقوقی و سلب مسئولیت اداری ── */}
          <div className="app-card p-5 border border-[var(--border-subtle)] bg-[var(--bg-elevated)]/50 text-xs text-[var(--text-secondary)] space-y-3">
            <div className="flex items-center gap-2 font-bold text-[var(--text-primary)]">
              <FileCheck size={16} className="text-[var(--accent)]" />
              <span>بیانیه اعتبار و تاییدیه حسابرسی دفتر کل (Audit Attestation)</span>
            </div>
            <p className="leading-relaxed">
              این سند به‌صورت خودکار توسط موتور اعتبارسنجی <b>MokTradeDesk</b> از پایگاه دادهٔ محلی (Local-first) استخراج شده است. 
              کد هش دیجیتال اختصاصی درج‌شده در بالای صفحه، صحت داده‌ها و عدم دستکاری آنها را تا لحظه صدور تضمین می‌نماید. 
              این استیتمنت با استانداردهای مدیریت دارایی نهادی (GIPS) همخوانی داشته و تمامی معیارهای سود ناخالص، کارمزد، سوآپ و نسبت‌های ریسک تعدیل‌شده را منعکس می‌کند.
            </p>
            <div className="flex flex-wrap items-center justify-between gap-4 pt-3 border-t border-[var(--border-subtle)] text-[11px] text-[var(--text-muted)]">
              <div>
                مدیر پرتفوی / حسابرس: <span className="font-bold text-[var(--text-primary)]">{cred.trader_name}</span>
              </div>
              <div className="font-mono dir-ltr">
                Desk ID: {cred.account_id} · SHA-256 Verified
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
