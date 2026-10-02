import { useState, useEffect } from 'react';
import Skeleton from '../components/Skeleton';
import PersianDateInput from '../components/PersianDateInput';
import AccountForm from '../components/AccountForm';
import TransactionForm from '../components/TransactionForm';
import FinancialAssetBalances from '../components/FinancialAssetBalances';
import type { FinancialAssets } from '../api/client';
import CategoryForm from '../components/CategoryForm';
import {
  getFinanceAccounts,
  createFinanceAccount,
  updateFinanceAccount,
  deleteFinanceAccount,
  getFinanceCategories,
  createFinanceCategory,
  updateFinanceCategory,
  deleteFinanceCategory,
  getFinanceTransactions,
  createFinanceTransaction,
  updateFinanceTransaction,
  deleteFinanceTransaction,
  seedFinanceCategories,
  getFinanceSummary,
  getFinanceAccountStats,
  getAccountReconcile,
  getFinanceWithdrawalStats,
  getFinanceCashflow,
  getFinanceDistribution,
  getFinanceMonthlyReport,
  getFinanceCategoryBreakdown,
  getFinanceAccountComparison,
  getFinanceProfitLoss,
  getSpendableAssets,
  getRealPnl,
  getNetProfit,
  getMoneyFlow,
  getFinanceExpenses,
  getMoneyCycle,
  getFinancialCalendar,
  api,
} from '../api/client';

import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend, BarChart, Bar,
} from 'recharts';

import { currentJalaliYear, JALALI_MONTHS_FA } from '../utils/jalali';
import EmptyState from '../components/ui/EmptyState';
import ConfirmDialog from '../components/ui/ConfirmDialog';
import InfoTooltip from '../components/ui/Tooltip';
import { useToast } from '../components/ToastProvider';

type Tab = 'accounts' | 'transactions' | 'categories' | 'reports' | 'advanced'
  | 'real' | 'moneyflow' | 'expenses' | 'cycle' | 'calendar' | 'wallets';

type Account = {
  id: number; name: string; type: string; currency: string;
  balance: number; card_number?: string; created_at?: string;
  // فاز ۳۸.۵: `broker_name`/`prop_firm_name`/`prop_firm_id` حذف شدند (فیلد منسوخهٔ فاز ۲۸)
};

type Category = {
  id: number; name: string; type: string;
  color?: string; icon?: string; created_at?: string;
};

type Transaction = {
  id: number; account_id: number; account_name?: string;
  category_id?: number | null; category_name?: string;
  amount: number; currency: string; date: string;
  description?: string; type: string;
  from_account_id?: number | null; to_account_id?: number | null;
  created_at?: string;
};

const ACCOUNT_TYPE_LABELS: Record<string, string> = {
  bank: '🏦', exchange: '🔄', crypto_wallet: '₿',
  card: '💳', cash: '💵', trust_wallet: '🤝',   // فاز ۳۸.۲
  // فاز ۳۸.۵: `broker`/`prop` حذف شدند (از فاز ۲۸ در AccountType وجود ندارند)
};

const ACCOUNT_TYPE_NAMES: Record<string, string> = {
  bank: 'بانک', exchange: 'صرافی', crypto_wallet: 'کیف‌پول دیجیتال',
  card: 'کارت بانکی', cash: 'پول نقد', trust_wallet: 'کیف پول Trust',  // فاز ۳۸.۲
  // فاز ۳۸.۵: `broker`/`prop` حذف شدند (از فاز ۲۸ در AccountType وجود ندارند)
};

const TRANSACTION_TYPE_STYLES: Record<string, { bg: string; text: string }> = {
  deposit: { bg: 'bg-[#22c55e]/10', text: 'text-[#22c55e]' },
  withdrawal: { bg: 'bg-[#ef4444]/10', text: 'text-[#ef4444]' },
  transfer: { bg: 'bg-[#8b5cf6]/10', text: 'text-[#8b5cf6]' },  // فاز ۳۸.۴: جایگزین `exchange`
  profit: { bg: 'bg-[#10b981]/10', text: 'text-[#10b981]' },
  loss: { bg: 'bg-[#f97316]/10', text: 'text-[#f97316]' },
  fee: { bg: 'bg-[#eab308]/10', text: 'text-[#eab308]' },
  purchase: { bg: 'bg-[#ec4899]/10', text: 'text-[#ec4899]' },
};

// برچسب و رنگ فارسی انواع تراکنش (برای نمودار دایره‌ای)
const TRANSACTION_TYPE_LABELS: Record<string, string> = {
  deposit: 'واریز', withdrawal: 'برداشت', transfer: 'انتقال',
  profit: 'سود', loss: 'ضرر', fee: 'کارمزد', purchase: 'خرید',
  deposit_to_broker: 'واریز به بروکر', withdrawal_from_broker: 'برداشت از بروکر',
};

const TRANSACTION_TYPE_COLORS: Record<string, string> = {
  deposit: '#22c55e', withdrawal: '#ef4444', transfer: '#8b5cf6',  // فاز ۳۸.۴: exchange → transfer
  profit: '#10b981', loss: '#f97316', fee: '#eab308', purchase: '#ec4899',
};

const FALLBACK_COLORS = ['#3F7CFF', '#6366f1', '#14b8a6', '#a855f7', '#f43f5e'];

export default function FinancePage() {
  const [tab, setTab] = useState<Tab>('accounts');
  const [loading, setLoading] = useState(true);
  const toast = useToast();
  const [pendingDelete, setPendingDelete] = useState<{
    message: string;
    onConfirm: () => Promise<void>;
  } | null>(null);

  // Accounts state
  const [accounts, setAccounts] = useState<Account[]>([]);
  // فاز ۴۵.۹ — نتیجهٔ مغایرت‌یابی هر حساب (delta != 0 ⇒ هشدار)
  const [reconcileMap, setReconcileMap] = useState<Record<number, any>>({});
  const [showAccountForm, setShowAccountForm] = useState(false);
  const [editAccount, setEditAccount] = useState<Account | null>(null);
  const [accountFormScope, setAccountFormScope] = useState<'accounts' | 'wallets'>('accounts');

  // Categories state
  const [categories, setCategories] = useState<Category[]>([]);
  const [showCategoryForm, setShowCategoryForm] = useState(false);
  const [editCategory, setEditCategory] = useState<Category | null>(null);

  // Transactions state
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [showTransactionForm, setShowTransactionForm] = useState(false);
  const [editTransaction, setEditTransaction] = useState<Transaction | null>(null);
  const [filterDateFrom, setFilterDateFrom] = useState('');
  const [filterDateTo, setFilterDateTo] = useState('');
  const [filterAccountId, setFilterAccountId] = useState<number | ''>('');
  const [filterType, setFilterType] = useState('');
  const [filterCategoryId, setFilterCategoryId] = useState<number | ''>('');

  // Reports state
  const [summary, setSummary] = useState<{
    assets_by_currency: Record<string, number>;
    total_income: number;
    total_expense: number;
    total_transfers: number;
    transaction_count: number;
  } | null>(null);
  const [cashflow, setCashflow] = useState<Array<{
    month: string; year: number; month_num: number; income: number; expense: number;
  }>>([]);
  const [withdrawalStats, setWithdrawalStats] = useState<{
    total_withdrawals: number;
    prop_withdrawals: number;
    broker_withdrawals: number;
    withdrawal_count: number;
    history: Array<{
      id: number | string; kind: 'prop' | 'broker'; amount: number; currency: string; date: string;
      description?: string; account_id: number; account_name?: string;
    }>;
  } | null>(null);
  const [accountStats, setAccountStats] = useState<Record<number, any>>({});
  const [distribution, setDistribution] = useState<Array<{
    type: string; count: number; total_amount: number;
  }>>([]);

  // Advanced Reports state (فاز ۱۱)
  const [advYear, setAdvYear] = useState<number>(currentJalaliYear());
  const [advMonth, setAdvMonth] = useState<number | ''>('');
  const [advAccountId, setAdvAccountId] = useState<number | ''>('');
  const [monthlyReport, setMonthlyReport] = useState<{
    year: number;
    months: Array<{ month_num: number; month_name: string; income: number; expense: number; net: number }>;
  } | null>(null);
  const [categoryBreakdown, setCategoryBreakdown] = useState<{
    total_income: number;
    total_expense: number;
    items: Array<{
      category_id: number | null; category_name: string; color?: string | null;
      icon?: string | null; type: string; total: number; percent: number; count: number;
    }>;
  } | null>(null);
  const [accountComparison, setAccountComparison] = useState<Array<{
    id: number; name: string; type: string; currency: string; balance: number;
    total_income: number; total_expense: number; net: number; transaction_count: number;
  }>>([]);
  const [profitLoss, setProfitLoss] = useState<{
    total_income: number; total_expense: number; net_profit: number; margin: number; year: number;
    yearly: Array<{ year: number; income: number; expense: number; net: number }>;
    monthly: Array<{ month_num: number; month_name: string; net: number; cumulative: number }>;
    trend: Array<{ label: string; net: number; cumulative: number }>;
  } | null>(null);

  // فاز ۲۲ — گزارش‌های مالی جدید
  const [spendableAssets, setSpendableAssets] = useState<FinancialAssets | null>(null);
  const [realPnl, setRealPnl] = useState<any>(null);
  const [netProfit, setNetProfit] = useState<any>(null);
  const [moneyFlow, setMoneyFlow] = useState<Array<any>>([]);
  const [expenses, setExpenses] = useState<any>(null);
  const [moneyCycle, setMoneyCycle] = useState<any>(null);
  const [calendar, setCalendar] = useState<Array<any>>([]);
  // فاز ۴۴.۵ — ارز فعال گزارش‌های مالی
  const [currency, setCurrency] = useState<'USDT' | 'IRR'>('USDT');

  // Load functions
  const loadAccounts = async () => {
    const { data } = await getFinanceAccounts();
    setAccounts(data);
    // فاز ۴۵.۹ — مغایرت‌یابی هر حساب
    try {
      const pairs = await Promise.all(
        (data as any[]).map(async (a) => {
          try { return [a.id, (await getAccountReconcile(a.id)).data]; }
          catch { return [a.id, null]; }
        }),
      );
      setReconcileMap(Object.fromEntries(pairs.filter(([, v]) => v)) as Record<number, any>);
    } catch { /* silent */ }
  };
  const loadCategories = async () => {
    const { data } = await getFinanceCategories();
    setCategories(data);
  };
  const loadTransactions = async () => {
    const params: Record<string, any> = {};
    if (filterDateFrom) params.date_from = filterDateFrom;
    if (filterDateTo) params.date_to = filterDateTo;
    if (filterAccountId) params.account_id = filterAccountId;
    if (filterType) params.type = filterType;
    if (filterCategoryId) params.category_id = filterCategoryId;
    const { data } = await getFinanceTransactions(params);
    setTransactions(data);
  };

  const loadReports = async () => {
    try {
      const [sumRes, flowRes, wdRes] = await Promise.all([
        getFinanceSummary({ currency }),
        getFinanceCashflow({ currency }),
        getFinanceWithdrawalStats({ currency }),
      ]);
      setSummary(sumRes.data);
      setCashflow(flowRes.data);
      setWithdrawalStats(wdRes.data);

      // توزیع تراکنش‌ها بر اساس نوع
      const distRes = await getFinanceDistribution({
        date_from: filterDateFrom || undefined,
        date_to: filterDateTo || undefined,
      });
      setDistribution(distRes.data);

      // دریافت آمار هر حساب
      const accts = accounts.length > 0 ? accounts : (await getFinanceAccounts()).data;
      const statsMap: Record<number, any> = {};
      await Promise.all(
        accts.map(async (a: any) => {
          try {
            const { data } = await getFinanceAccountStats(a.id);
            statsMap[a.id] = data;
          } catch { /* ignore */ }
        })
      );
      setAccountStats(statsMap);
    } catch (err: any) {
      // فاز ۵۳.۶.۲: خطا دیگر بی‌صدا نیست
      toast.error(err?.response?.data?.detail || 'خطا در بارگذاری گزارش‌های مالی');
    }
  };

  const loadAdvancedReports = async () => {
    try {
      const y = advYear || undefined;
      const m = advMonth || undefined;
      const acc = advAccountId || undefined;
      const [monthlyRes, catRes, accRes, plRes] = await Promise.all([
        getFinanceMonthlyReport({ year: y, account_id: acc, currency }),
        getFinanceCategoryBreakdown({ year: y, month: m, account_id: acc, currency }),
        getFinanceAccountComparison({ year: y, month: m }),
        getFinanceProfitLoss({ year: y, account_id: acc, currency }),
      ]);
      setMonthlyReport(monthlyRes.data);
      setCategoryBreakdown(catRes.data);
      setAccountComparison(accRes.data);
      setProfitLoss(plRes.data);
    } catch (err: any) {
      // فاز ۵۳.۶.۲: خطا دیگر بی‌صدا نیست
      toast.error(err?.response?.data?.detail || 'خطا در بارگذاری گزارش‌های پیشرفته');
    }
  };

  const loadAll = async () => {
    setLoading(true);
    try {
      await Promise.all([loadAccounts(), loadCategories(), loadTransactions()]);
      if (tab === 'reports') await loadReports();
    } finally {
      setLoading(false);
    }
  };

  // فاز ۲۲ — بارگذاری همهٔ گزارش‌های جدید
  const loadPhase22 = async () => {
    try {
      const [spRes, rpRes, npRes, mfRes, exRes, mcRes, calRes] = await Promise.all([
        getSpendableAssets(),
        getRealPnl({ currency }),
        getNetProfit({ currency }),
        getMoneyFlow(),
        getFinanceExpenses({ currency }),
        getMoneyCycle({ currency }),
        getFinancialCalendar(),
      ]);
      setSpendableAssets(spRes.data);
      setRealPnl(rpRes.data);
      setNetProfit(npRes.data);
      setMoneyFlow(mfRes.data.flows || []);
      setExpenses(exRes.data);
      setMoneyCycle(mcRes.data);
      setCalendar(calRes.data.days || []);
    } catch (err: any) {
      // فاز ۵۳.۶.۲: خطا دیگر بی‌صدا نیست
      toast.error(err?.response?.data?.detail || 'خطا در بارگذاری گزارش‌های مالی');
    }
  };

  useEffect(() => { loadAll(); }, []);
  useEffect(() => {
    if (tab === 'transactions') loadTransactions();
    if (tab === 'reports') loadReports();
    if (tab === 'advanced') loadAdvancedReports();
    if ((['real', 'moneyflow', 'expenses', 'cycle', 'calendar'] as Tab[]).includes(tab)) loadPhase22();
  },
    [tab, filterDateFrom, filterDateTo, filterAccountId, filterType, filterCategoryId, advYear, advMonth, advAccountId, currency]);

  const showSuccess = (msg: string) => toast.success(msg);
  const walletAccountTypes = ['exchange', 'trust_wallet', 'crypto_wallet'];
  const walletAccounts = accounts.filter((account) => walletAccountTypes.includes(account.type));

  const saveAccount = async (data: Record<string, any>) => {
    if (editAccount) {
      await updateFinanceAccount(editAccount.id, data);
      showSuccess(accountFormScope === 'wallets' ? 'کیف پول به‌روزرسانی شد' : 'حساب به‌روزرسانی شد');
    } else {
      await createFinanceAccount(data as any);
      showSuccess(accountFormScope === 'wallets' ? 'کیف پول ساخته شد' : 'حساب ساخته شد');
    }
    setShowAccountForm(false);
    setEditAccount(null);
    await loadAccounts();
  };

  const accountFormPanel = showAccountForm ? (
    <AccountForm
      mode={editAccount ? 'edit' : 'create'}
      initialData={editAccount ?? undefined}
      allowedTypes={accountFormScope === 'wallets' ? walletAccountTypes : undefined}
      defaultType={accountFormScope === 'wallets' ? 'trust_wallet' : undefined}
      onSave={saveAccount}
      onCancel={() => { setShowAccountForm(false); setEditAccount(null); }}
    />
  ) : null;

  const TABS: { key: Tab; icon: string; label: string }[] = [
    { key: 'accounts', icon: '🏦', label: 'حساب‌ها' },
    { key: 'wallets', icon: '👛', label: 'کیف‌پول‌ها' },
    { key: 'transactions', icon: '💳', label: 'تراکنش‌ها' },
    { key: 'categories', icon: '🏷️', label: 'دسته‌بندی‌ها' },
    { key: 'reports', icon: '📊', label: 'گزارش‌ها' },
    { key: 'advanced', icon: '📈', label: 'گزارش‌های پیشرفته' },
    { key: 'real', icon: '💰', label: 'سود/زیان Real' },
    { key: 'moneyflow', icon: '🔀', label: 'جریان پول' },
    { key: 'expenses', icon: '🧾', label: 'هزینه‌ها' },
    { key: 'cycle', icon: '♻️', label: 'چرخهٔ پول' },
    { key: 'calendar', icon: '🗓️', label: 'تقویم مالی' },
  ];

  if (loading) return <FinanceSkeleton />;

  return (
    <div>
      {/* Global Confirm Dialog */}
      <ConfirmDialog
        open={!!pendingDelete}
        title="تأیید حذف"
        message={pendingDelete?.message ?? ''}
        confirmLabel="حذف"
        cancelLabel="انصراف"
        danger
        onConfirm={() => { const p = pendingDelete; setPendingDelete(null); p?.onConfirm(); }}
        onCancel={() => setPendingDelete(null)}
      />

      {/* Tabs */}
      <div className="flex gap-2 mb-6 border-b border-[var(--border-subtle)] pb-3 overflow-x-auto flex-wrap">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-5 py-2.5 rounded-xl text-sm font-bold transition-all whitespace-nowrap ${
              tab === t.key
                ? 'text-white shadow-[0_4px_12px_rgba(63,124,255,0.3)]'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-card)]'
            }`}
            style={tab === t.key ? { background: 'linear-gradient(135deg, #3F7CFF, #5B8DEF)' } : {}}
          >
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {/* گزارش‌ها بر اساس IRR یا USDT فیلتر می‌شوند. */}
      {(['reports', 'advanced', 'real', 'expenses', 'cycle'] as Tab[]).includes(tab) && (
        <div className="flex items-center gap-2 mb-5 flex-wrap">
          <span className="text-xs font-bold text-[var(--text-secondary)]">💱 ارز:</span>
          {(['USDT', 'IRR'] as const).map((c) => (
            <button
              key={c}
              onClick={() => setCurrency(c)}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
                currency === c
                  ? 'text-white shadow-[0_4px_12px_rgba(63,124,255,0.3)]'
                  : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-card)]'
              }`}
              style={currency === c ? { background: 'linear-gradient(135deg, #3F7CFF, #5B8DEF)' } : {}}
            >
              {c}
            </button>
          ))}
        </div>
      )}

      {/* ═══ Accounts Tab ═══ */}
      {tab === 'accounts' && (
        <>
          <div className="flex gap-3 mb-6 flex-wrap">
            <button onClick={() => {
              setEditAccount(null);
              setAccountFormScope('accounts');
              setShowAccountForm(!(showAccountForm && accountFormScope === 'accounts'));
            }}
              className="text-white px-6 py-3 rounded-[12px] text-sm font-extrabold shadow-[0_6px_16px_rgba(63,124,255,0.3)] hover:shadow-[0_10px_24px_rgba(63,124,255,0.4)] hover:-translate-y-0.5 transition-all"
              style={{ background: 'linear-gradient(135deg, #3F7CFF, #5B8DEF)' }}>
              🆕 حساب جدید
            </button>
            <button onClick={async () => {
              try {
                const res = await api.post('/api/finance/sync/trades');
                toast.toast(res.data.message || 'همگام‌سازی انجام شد', 'success');
              } catch { toast.toast('خطا در همگام‌سازی', 'error'); }
            }}
              className="text-white px-6 py-3 rounded-[12px] text-sm font-extrabold shadow-[0_6px_16px_rgba(34,197,94,0.3)] hover:shadow-[0_10px_24px_rgba(34,197,94,0.4)] hover:-translate-y-0.5 transition-all"
              style={{ background: 'linear-gradient(135deg, #22C55E, #4ADE80)' }}>
              🔄 همگام‌سازی معاملات
            </button>
          </div>

          {accountFormScope === 'accounts' && accountFormPanel}

          {accounts.length === 0 ? (
            <EmptyState
              icon="🏦"
              title="هیچ حسابی ثبت نشده"
              description="برای شروع، یک حساب جدید ایجاد کنید"
              actionLabel="حساب جدید"
              onAction={() => { setAccountFormScope('accounts'); setShowAccountForm(true); setEditAccount(null); }}
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {accounts.map((a) => (
                <div key={a.id} className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-5 transition-all hover:shadow-lg hover:border-[var(--border-accent)]">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <div className="text-lg font-extrabold text-[var(--text-primary)]">{a.name}</div>
                      <div className="text-xs text-[var(--text-secondary)] mt-1">
                        {ACCOUNT_TYPE_LABELS[a.type] || '❓'} {ACCOUNT_TYPE_NAMES[a.type] || a.type} • {a.currency}
                      </div>
                    </div>
                    <div className="flex gap-1">
                      <InfoTooltip content="ویرایش حساب">
                        <button onClick={() => { setAccountFormScope('accounts'); setEditAccount(a); setShowAccountForm(true); }}
                          className="w-8 h-8 rounded-lg bg-[var(--bg-base)] text-[var(--text-secondary)] hover:text-[var(--accent)] hover:bg-[var(--accent-soft)] transition-all flex items-center justify-center text-sm">✏️</button>
                      </InfoTooltip>
                      <InfoTooltip content="حذف حساب">
                        <button onClick={() => setPendingDelete({ message: `حساب «${a.name}» حذف شود؟`, onConfirm: async () => {
                          try {
                            await deleteFinanceAccount(a.id);
                            showSuccess('حساب آرشیو شد');
                            await loadAccounts();
                          } catch (err: any) {
                            // فاز ۴۵.۳: حساب دارای تراکنش/موجودی صفر نیست ⇒ 409
                            toast.toast(err?.response?.data?.detail || 'حذف حساب ممکن نشد', 'error');
                          }
                        } })}
                          className="w-8 h-8 rounded-lg bg-[var(--bg-base)] text-[var(--text-secondary)] hover:text-red-500 hover:bg-red-500/10 transition-all flex items-center justify-center text-sm">🗑️</button>
                      </InfoTooltip>
                    </div>
                  </div>
                  <div className="text-2xl font-black text-[var(--text-primary)] flex items-center gap-2">
                    {a.balance?.toLocaleString() ?? '0'} <span className="text-xs font-bold text-[var(--text-secondary)]">{a.currency}</span>
                    {/* فاز ۴۵.۹: هشدار مغایرت دفتر کل */}
                    {reconcileMap[a.id] && !reconcileMap[a.id].is_balanced && (
                      <InfoTooltip content={`مغایرت دفتر کل: ${reconcileMap[a.id].delta} (باید صفر باشد)`}>
                        <span className="text-base cursor-help" style={{ color: 'var(--warning, #D99B25)' }}>🟠</span>
                      </InfoTooltip>
                    )}
                  </div>
                  {a.card_number && <div className="text-xs text-[var(--text-secondary)] mt-2 font-mono">💳 {a.card_number}</div>}
                </div>
              ))}
            </div>
          )}
        </>
      )}
      {tab === 'wallets' && (
        <>
          <div className="flex items-start justify-between gap-4 flex-wrap mb-5">
            <div>
              <h2 className="text-lg font-extrabold text-[var(--text-primary)]">کیف‌پول‌ها و حساب‌های صرافی</h2>
              <p className="text-xs text-[var(--text-secondary)] mt-1">
                برای صرافی، حساب جداگانهٔ IRR و USDT بساز. برنامه تبدیل ارز انجام نمی‌دهد.
              </p>
            </div>
            <button
              onClick={() => {
                setEditAccount(null);
                setAccountFormScope('wallets');
                setShowAccountForm(!(showAccountForm && accountFormScope === 'wallets'));
              }}
              className="text-white px-6 py-3 rounded-[12px] text-sm font-extrabold shadow-[0_6px_16px_rgba(63,124,255,0.3)] hover:-translate-y-0.5 transition-all"
              style={{ background: 'linear-gradient(135deg, #3F7CFF, #5B8DEF)' }}
            >
              🆕 کیف‌پول یا حساب صرافی
            </button>
          </div>

          {accountFormScope === 'wallets' && accountFormPanel}

          {walletAccounts.length === 0 ? (
            <EmptyState
              icon="👛"
              title="هنوز کیف‌پول یا حساب صرافی ثبت نشده"
              description="Trust Wallet و کیف‌پول‌های دیگر فقط با USDT ثبت می‌شوند."
              actionLabel="ساخت کیف‌پول"
              onAction={() => {
                setEditAccount(null);
                setAccountFormScope('wallets');
                setShowAccountForm(true);
              }}
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {walletAccounts.map((account) => (
                <div key={account.id} className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-5 transition-all hover:shadow-lg hover:border-[var(--border-accent)]">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <div className="text-lg font-extrabold text-[var(--text-primary)]">{account.name}</div>
                      <div className="text-xs text-[var(--text-secondary)] mt-1">
                        {ACCOUNT_TYPE_LABELS[account.type] || '👛'} {ACCOUNT_TYPE_NAMES[account.type] || account.type} · {account.currency}
                      </div>
                    </div>
                    <div className="flex gap-1">
                      <InfoTooltip content="ویرایش حساب">
                        <button onClick={() => { setAccountFormScope('wallets'); setEditAccount(account); setShowAccountForm(true); }}
                          className="w-8 h-8 rounded-lg bg-[var(--bg-base)] text-[var(--text-secondary)] hover:text-[var(--accent)] hover:bg-[var(--accent-soft)] transition-all flex items-center justify-center text-sm">✏️</button>
                      </InfoTooltip>
                      <InfoTooltip content="حذف حساب">
                        <button onClick={() => setPendingDelete({ message: `حساب «${account.name}» حذف شود؟`, onConfirm: async () => {
                          try {
                            await deleteFinanceAccount(account.id);
                            showSuccess('حساب آرشیو شد');
                            await loadAccounts();
                          } catch (err: any) {
                            toast.toast(err?.response?.data?.detail || 'حذف حساب ممکن نشد', 'error');
                          }
                        } })}
                          className="w-8 h-8 rounded-lg bg-[var(--bg-base)] text-[var(--text-secondary)] hover:text-red-500 hover:bg-red-500/10 transition-all flex items-center justify-center text-sm">🗑️</button>
                      </InfoTooltip>
                    </div>
                  </div>
                  <div className="text-2xl font-black text-[var(--text-primary)]">
                    {account.balance?.toLocaleString() ?? '0'} <span className="text-xs font-bold text-[var(--text-secondary)]">{account.currency}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
      {/* ═══ Transactions Tab ═══ */}
      {tab === 'transactions' && (
        <>
          <div className="flex gap-3 mb-6 flex-wrap">
            <button onClick={() => { setShowTransactionForm(!showTransactionForm); setEditTransaction(null); }}
              className="text-white px-6 py-3 rounded-[12px] text-sm font-extrabold shadow-[0_6px_16px_rgba(63,124,255,0.3)] hover:shadow-[0_10px_24px_rgba(63,124,255,0.4)] hover:-translate-y-0.5 transition-all"
              style={{ background: 'linear-gradient(135deg, #3F7CFF, #5B8DEF)' }}>
              🆕 تراکنش جدید
            </button>
          </div>

          {showTransactionForm && (
            <TransactionForm
              mode={editTransaction ? 'edit' : 'create'}
              accounts={accounts}
              categories={categories}
              initialData={editTransaction ?? undefined}
              onSave={async (data) => {
                if (editTransaction) {
                  await updateFinanceTransaction(editTransaction.id, data);
                  showSuccess('تراکنش به‌روزرسانی شد');
                } else {
                  await createFinanceTransaction(data as any);
                  showSuccess('تراکنش ثبت شد');
                }
                setShowTransactionForm(false); setEditTransaction(null);
                await loadTransactions();
              }}
              onCancel={() => { setShowTransactionForm(false); setEditTransaction(null); }}
            />
          )}

          {/* Filters */}
          <div className="grid grid-cols-1 md:grid-cols-5 gap-3 mb-4 p-4 bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px]">
            <PersianDateInput label="از تاریخ" value={filterDateFrom} onChange={(v) => setFilterDateFrom(v)} />
            <PersianDateInput label="تا تاریخ" value={filterDateTo} onChange={(v) => setFilterDateTo(v)} />
            <div>
              <label className="text-[var(--text-secondary)] text-xs block mb-1">حساب</label>
              <select value={filterAccountId} onChange={(e) => setFilterAccountId(e.target.value ? parseInt(e.target.value) : '')}
                className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-4 py-3 text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none transition-all text-sm">
                <option value="">همه</option>
                {accounts.map((a) => (<option key={a.id} value={a.id}>{a.name}</option>))}
              </select>
            </div>
            <div>
              <label className="text-[var(--text-secondary)] text-xs block mb-1">نوع</label>
              <select value={filterType} onChange={(e) => setFilterType(e.target.value)}
                className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-4 py-3 text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none transition-all text-sm">
                <option value="">همه</option>
                <option value="deposit">💵 واریز</option>
                <option value="withdrawal">🏧 برداشت</option>
                <option value="transfer">🔄 انتقال</option>
                <option value="profit">📈 سود</option>
                <option value="loss">📉 ضرر</option>
                <option value="fee">💸 کارمزد</option>
                <option value="purchase">🛒 خرید</option>
              </select>
            </div>
            <div>
              <label className="text-[var(--text-secondary)] text-xs block mb-1">دسته‌بندی</label>
              <select value={filterCategoryId} onChange={(e) => setFilterCategoryId(e.target.value ? parseInt(e.target.value) : '')}
                className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-4 py-3 text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none transition-all text-sm">
                <option value="">همه</option>
                {categories.map((c) => (<option key={c.id} value={c.id}>{c.icon} {c.name}</option>))}
              </select>
            </div>
          </div>
          {transactions.length === 0 ? (
            <EmptyState
              icon="💳"
              title="هیچ تراکنشی یافت نشد"
              description="فیلترها را تغییر دهید یا تراکنش جدید ثبت کنید"
              actionLabel="تراکنش جدید"
              onAction={() => { setShowTransactionForm(true); setEditTransaction(null); }}
            />
          ) : (
            <div className="space-y-3">
              {transactions.map((t) => {
                const style = TRANSACTION_TYPE_STYLES[t.type] || { bg: 'bg-[#6B7A94]/10', text: 'text-[#6B7A94]' };
                return (
                  <div key={t.id} className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[18px] p-4 transition-all hover:shadow-md">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`px-2 py-0.5 rounded-lg text-[11px] font-bold ${style.bg} ${style.text}`}>{t.type}</span>
                          <span className="text-xs text-[var(--text-secondary)]">{t.account_name || `حساب ${t.account_id}`}</span>
                          {t.category_name && <span className="text-xs text-[var(--text-secondary)]">• {t.category_name}</span>}
                        </div>
                        {t.description && <div className="text-sm text-[var(--text-secondary)] truncate">{t.description}</div>}
                        <div className="text-xs text-[var(--text-secondary)] mt-1">{t.date?.split('T')[0]}</div>
                      </div>
                      <div className="text-left shrink-0">
                        <div className="text-lg font-black text-[var(--text-primary)]">{t.amount?.toLocaleString() ?? '0'}</div>
                        <div className="text-[10px] font-bold text-[var(--text-secondary)]">{t.currency}</div>
                      </div>
                      <div className="flex gap-1 shrink-0">
                        <InfoTooltip content="ویرایش تراکنش">
                          <button onClick={() => { setEditTransaction(t); setShowTransactionForm(true); }}
                            className="w-7 h-7 rounded-lg bg-[var(--bg-base)] text-[var(--text-secondary)] hover:text-[var(--accent)] hover:bg-[var(--accent-soft)] transition-all flex items-center justify-center text-xs">✏️</button>
                        </InfoTooltip>
                        <InfoTooltip content="حذف تراکنش">
                          <button onClick={() => setPendingDelete({ message: 'این تراکنش حذف شود؟', onConfirm: async () => { await deleteFinanceTransaction(t.id); showSuccess('تراکنش حذف شد'); await loadTransactions(); } })}
                            className="w-7 h-7 rounded-lg bg-[var(--bg-base)] text-[var(--text-secondary)] hover:text-red-500 hover:bg-red-500/10 transition-all flex items-center justify-center text-xs">🗑️</button>
                        </InfoTooltip>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
      {/* ═══ Categories Tab ═══ */}
      {tab === 'categories' && (
        <>
          <div className="flex gap-3 mb-6 flex-wrap">
            <button onClick={() => { setShowCategoryForm(!showCategoryForm); setEditCategory(null); }}
              className="text-white px-6 py-3 rounded-[12px] text-sm font-extrabold shadow-[0_6px_16px_rgba(63,124,255,0.3)] hover:shadow-[0_10px_24px_rgba(63,124,255,0.4)] hover:-translate-y-0.5 transition-all"
              style={{ background: 'linear-gradient(135deg, #3F7CFF, #5B8DEF)' }}>
              🆕 دسته‌بندی جدید
            </button>
            <button onClick={async () => { const { data } = await seedFinanceCategories(); showSuccess(data.message); await loadCategories(); }}
              className="px-6 py-3 rounded-[12px] text-sm font-bold transition-all border border-[var(--border-subtle)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--border-accent)]">
              🌱 دسته‌بندی‌های پیش‌فرض
            </button>
          </div>

          {showCategoryForm && (
            <CategoryForm
              mode={editCategory ? 'edit' : 'create'}
              initialData={editCategory ?? undefined}
              onSave={async (data) => {
                if (editCategory) {
                  await updateFinanceCategory(editCategory.id, data);
                  showSuccess('دسته‌بندی به‌روزرسانی شد');
                } else {
                  await createFinanceCategory(data as any);
                  showSuccess('دسته‌بندی ساخته شد');
                }
                setShowCategoryForm(false); setEditCategory(null);
                await loadCategories();
              }}
              onCancel={() => { setShowCategoryForm(false); setEditCategory(null); }}
            />
          )}

          {categories.length === 0 ? (
            <EmptyState
              icon="🏷️"
              title="هیچ دسته‌بندی‌ای ثبت نشده"
              description="دسته‌بندی جدید ایجاد کنید یا از دکمه «دسته‌بندی‌های پیش‌فرض» استفاده کنید"
              actionLabel="دسته‌بندی جدید"
              onAction={() => { setShowCategoryForm(true); setEditCategory(null); }}
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {categories.map((c) => (
                <div key={c.id} className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-5 transition-all hover:shadow-lg hover:border-[var(--border-accent)]">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl flex items-center justify-center text-lg"
                        style={{ backgroundColor: c.color ? c.color + '20' : '#3F7CFF20' }}>
                        {c.icon || '🏷️'}
                      </div>
                      <div>
                        <div className="text-base font-extrabold text-[var(--text-primary)]">{c.name}</div>
                        <div className="text-xs text-[var(--text-secondary)]">{c.type}</div>
                      </div>
                    </div>
                    <div className="flex gap-1">
                      <InfoTooltip content="ویرایش دسته‌بندی">
                        <button onClick={() => { setEditCategory(c); setShowCategoryForm(true); }}
                          className="w-8 h-8 rounded-lg bg-[var(--bg-base)] text-[var(--text-secondary)] hover:text-[var(--accent)] hover:bg-[var(--accent-soft)] transition-all flex items-center justify-center text-sm">✏️</button>
                      </InfoTooltip>
                      <InfoTooltip content="حذف دسته‌بندی">
                        <button onClick={() => setPendingDelete({ message: `دسته‌بندی «${c.name}» حذف شود؟`, onConfirm: async () => { await deleteFinanceCategory(c.id); showSuccess('دسته‌بندی حذف شد'); await loadCategories(); } })}
                          className="w-8 h-8 rounded-lg bg-[var(--bg-base)] text-[var(--text-secondary)] hover:text-red-500 hover:bg-red-500/10 transition-all flex items-center justify-center text-sm">🗑️</button>
                      </InfoTooltip>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* ═══ Reports Tab ═══ */}
      {tab === 'reports' && (
        <div className="space-y-6">
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-5">
              <div className="text-xs text-[var(--text-secondary)] mb-1">💰 مجموع دارایی‌ها</div>
              <div className="text-2xl font-extrabold text-[var(--text-primary)]">
                {summary ? Object.values(summary.assets_by_currency).reduce((a, b) => a + b, 0).toLocaleString() : '—'}
              </div>
              <div className="text-xs text-[var(--text-secondary)] mt-1">
                {summary ? Object.entries(summary.assets_by_currency).map(([c, v]) => `${v.toLocaleString()} ${c}`).join(' | ') : '...'}
              </div>
            </div>
            <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-5">
              <div className="text-xs text-[var(--text-secondary)] mb-1">📈 مجموع درآمد</div>
              <div className="text-2xl font-extrabold text-[#22c55e]">
                {summary ? summary.total_income.toLocaleString() : '—'}
              </div>
              <div className="text-xs text-[var(--text-secondary)] mt-1">تعداد تراکنش‌ها: {summary?.transaction_count ?? '—'}</div>
            </div>
            <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-5">
              <div className="text-xs text-[var(--text-secondary)] mb-1">📉 مجموع هزینه</div>
              <div className="text-2xl font-extrabold text-[#ef4444]">
                {summary ? summary.total_expense.toLocaleString() : '—'}
              </div>
              <div className="text-xs text-[var(--text-secondary)] mt-1">انتقال: {summary?.total_transfers.toLocaleString() ?? '—'}</div>
            </div>
            <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-5">
              <div className="text-xs text-[var(--text-secondary)] mb-1">🔄 برداشت‌ها</div>
              <div className="text-2xl font-extrabold text-[var(--text-primary)]">
                {withdrawalStats ? withdrawalStats.total_withdrawals.toLocaleString() : '—'}
              </div>
              <div className="text-xs text-[var(--text-secondary)] mt-1">
                پراپ: {withdrawalStats ? withdrawalStats.prop_withdrawals.toLocaleString() : '—'} | بروکر: {withdrawalStats ? withdrawalStats.broker_withdrawals.toLocaleString() : '—'}
              </div>
            </div>
          </div>

          {/* Charts Row */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Cash Flow Chart */}
            <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-5">
              <div className="text-sm font-extrabold text-[var(--text-primary)] mb-4">📊 جریان نقدی (درآمد vs هزینه)</div>
              {cashflow.length > 0 ? (
                <ResponsiveContainer width="100%" height={280}>
                  <LineChart data={cashflow}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
                    <XAxis dataKey="month" tick={{ fontSize: 11 }} stroke="var(--text-secondary)" />
                    <YAxis tick={{ fontSize: 11 }} stroke="var(--text-secondary)" />
                    <Tooltip contentStyle={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 12, color: 'var(--text-primary)', direction: 'rtl' }} />
                    <Line type="monotone" dataKey="income" stroke="#22c55e" strokeWidth={2} name="درآمد" dot={{ r: 3 }} />
                    <Line type="monotone" dataKey="expense" stroke="#ef4444" strokeWidth={2} name="هزینه" dot={{ r: 3 }} />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="text-center py-12 text-[var(--text-secondary)]">داده‌ای برای نمایش وجود ندارد</div>
              )}
            </div>
            {/* Pie Chart */}
            <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-5">
              <div className="text-sm font-extrabold text-[var(--text-primary)] mb-4">🥧 توزیع تراکنش‌ها بر اساس نوع</div>
              {distribution.length > 0 ? (
                <ResponsiveContainer width="100%" height={280}>
                  <PieChart>
                    <Pie
                      data={distribution.map((d, i) => ({
                        name: TRANSACTION_TYPE_LABELS[d.type] || d.type,
                        value: d.count,
                        count: d.count,
                        amount: d.total_amount,
                        fill: TRANSACTION_TYPE_COLORS[d.type] || FALLBACK_COLORS[i % FALLBACK_COLORS.length],
                      }))}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={90}
                      innerRadius={45}
                      paddingAngle={2}
                      label={(props: any) => `${props.name} ${((props.percent ?? 0) * 100).toFixed(0)}%`}
                      labelLine={false}
                    >
                      {distribution.map((d, i) => (
                        <Cell
                          key={d.type}
                          fill={TRANSACTION_TYPE_COLORS[d.type] || FALLBACK_COLORS[i % FALLBACK_COLORS.length]}
                        />
                      ))}
                    </Pie>
                    <Tooltip
                      content={({ active, payload }: any) => {
                        if (!active || !payload || !payload.length) return null;
                        const d = payload[0].payload;
                        return (
                          <div
                            className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-3 py-2 text-xs"
                            style={{ direction: 'rtl' }}
                          >
                            <div className="font-extrabold text-[var(--text-primary)] mb-1">{d.name}</div>
                            <div className="text-[var(--text-secondary)]">تعداد: {d.count}</div>
                            <div className="text-[var(--text-secondary)]">مجموع مبلغ: {d.amount.toLocaleString()}</div>
                          </div>
                        );
                      }}
                    />
                    <Legend
                      formatter={(value: any) => (
                        <span className="text-xs text-[var(--text-secondary)]">{value}</span>
                      )}
                    />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="text-center py-12 text-[var(--text-secondary)]">
                  <div className="text-4xl mb-3">🥧</div>
                  <div>داده‌ای برای نمایش وجود ندارد</div>
                </div>
              )}
            </div>
          </div>

          {/* Account Stats Table */}
          <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-5">
            <div className="text-sm font-extrabold text-[var(--text-primary)] mb-4">🏦 آمار هر حساب</div>
            {Object.keys(accountStats).length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-[var(--border-subtle)] text-[var(--text-secondary)]">
                      <th className="text-right py-3 px-3">حساب</th>
                      <th className="text-right py-3 px-3">نوع</th>
                      <th className="text-right py-3 px-3">ارز</th>
                      <th className="text-right py-3 px-3">موجودی</th>
                      <th className="text-right py-3 px-3">درآمد</th>
                      <th className="text-right py-3 px-3">هزینه</th>
                      <th className="text-right py-3 px-3">تعداد</th>
                      <th className="text-right py-3 px-3">آخرین تراکنش</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.values(accountStats).map((s: any) => (
                      <tr key={s.id} className="border-b border-[var(--border-subtle)]/50 hover:bg-[var(--accent-soft)]/30 transition-colors">
                        <td className="py-3 px-3 font-bold text-[var(--text-primary)]">{s.name}</td>
                        <td className="py-3 px-3 text-[var(--text-secondary)]">{ACCOUNT_TYPE_LABELS[s.type] || s.type}</td>
                        <td className="py-3 px-3 text-[var(--text-secondary)]">{s.currency}</td>
                        <td className="py-3 px-3 font-bold text-[var(--text-primary)]">{s.balance?.toLocaleString()}</td>
                        <td className="py-3 px-3 text-[#22c55e]">{s.total_income?.toLocaleString()}</td>
                        <td className="py-3 px-3 text-[#ef4444]">{s.total_expense?.toLocaleString()}</td>
                        <td className="py-3 px-3 text-[var(--text-secondary)]">{s.transaction_count}</td>
                        <td className="py-3 px-3 text-xs text-[var(--text-secondary)]">
                          {s.last_transaction ? (
                            <span className="flex flex-col">
                              <span>{s.last_transaction.amount?.toLocaleString()} {s.last_transaction.type}</span>
                              <span className="text-[10px]">{new Date(s.last_transaction.date).toLocaleDateString('fa-IR')}</span>
                            </span>
                          ) : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-center py-8 text-[var(--text-secondary)]">در حال بارگذاری...</div>
            )}
          </div>

          {/* Withdrawal Stats Table */}
          {withdrawalStats && (
            <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-5">
              <div className="flex items-center justify-between mb-4">
                <div className="text-sm font-extrabold text-[var(--text-primary)]">💸 تاریخچه برداشت‌ها</div>
                <div className="text-xs text-[var(--text-secondary)]">تعداد: {withdrawalStats.withdrawal_count}</div>
              </div>
              {withdrawalStats.history.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-[var(--border-subtle)] text-[var(--text-secondary)]">
                        <th className="text-right py-3 px-3">منبع</th>
                        <th className="text-right py-3 px-3">مبلغ</th>
                        <th className="text-right py-3 px-3">ارز</th>
                        <th className="text-right py-3 px-3">تاریخ</th>
                        <th className="text-right py-3 px-3">توضیحات</th>
                      </tr>
                    </thead>
                    <tbody>
                      {withdrawalStats.history.map((w) => (
                        <tr key={w.id} className="border-b border-[var(--border-subtle)]/50 hover:bg-[var(--accent-soft)]/30 transition-colors">
                          <td className="py-3 px-3 font-bold text-[var(--text-primary)]">{w.kind === 'prop' ? 'پراپ' : 'بروکر'} — {w.account_name || `#${w.account_id}`}</td>
                          <td className="py-3 px-3 text-[#ef4444] font-bold">{w.amount.toLocaleString()}</td>
                          <td className="py-3 px-3 text-[var(--text-secondary)]">{w.currency}</td>
                          <td className="py-3 px-3 text-xs text-[var(--text-secondary)]">{new Date(w.date).toLocaleDateString('fa-IR')}</td>
                          <td className="py-3 px-3 text-[var(--text-secondary)]">{w.description || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-center py-8 text-[var(--text-secondary)]">هیچ برداشتی ثبت نشده</div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ═══ Advanced Reports Tab (فاز ۱۱) ═══ */}
      {tab === 'advanced' && (
        <div className="space-y-6">
          {/* Filters */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 p-4 bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px]">
            <div>
              <label className="text-[var(--text-secondary)] text-xs block mb-1">سال (شمسی)</label>
              <select value={advYear} onChange={(e) => setAdvYear(parseInt(e.target.value))}
                className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-4 py-3 text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none transition-all text-sm">
                {(() => {
                  const years = new Set<number>([currentJalaliYear()]);
                  (profitLoss?.yearly || []).forEach((y) => years.add(y.year));
                  return Array.from(years).sort((a, b) => b - a).map((y) => (
                    <option key={y} value={y}>{y}</option>
                  ));
                })()}
              </select>
            </div>
            <div>
              <label className="text-[var(--text-secondary)] text-xs block mb-1">ماه (شمسی)</label>
              <select value={advMonth} onChange={(e) => setAdvMonth(e.target.value ? parseInt(e.target.value) : '')}
                className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-4 py-3 text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none transition-all text-sm">
                <option value="">همه ماه‌ها</option>
                {JALALI_MONTHS_FA.map((m, i) => (<option key={i} value={i + 1}>{m}</option>))}
              </select>
            </div>
            <div>
              <label className="text-[var(--text-secondary)] text-xs block mb-1">حساب</label>
              <select value={advAccountId} onChange={(e) => setAdvAccountId(e.target.value ? parseInt(e.target.value) : '')}
                className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-4 py-3 text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none transition-all text-sm">
                <option value="">همه</option>
                {accounts.map((a) => (<option key={a.id} value={a.id}>{a.name}</option>))}
              </select>
            </div>
          </div>

          {/* Net Profit Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-5">
              <div className="text-xs text-[var(--text-secondary)] mb-1">💵 سود خالص</div>
              <div className={`text-2xl font-extrabold ${(profitLoss?.net_profit ?? 0) >= 0 ? 'text-[#22c55e]' : 'text-[#ef4444]'}`}>
                {profitLoss ? profitLoss.net_profit.toLocaleString() : '—'}
              </div>
              <div className="text-xs text-[var(--text-secondary)] mt-1">سال {profitLoss?.year ?? advYear}</div>
            </div>
            <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-5">
              <div className="text-xs text-[var(--text-secondary)] mb-1">📈 کل درآمد</div>
              <div className="text-2xl font-extrabold text-[#22c55e]">{profitLoss ? profitLoss.total_income.toLocaleString() : '—'}</div>
            </div>
            <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-5">
              <div className="text-xs text-[var(--text-secondary)] mb-1">📉 کل هزینه</div>
              <div className="text-2xl font-extrabold text-[#ef4444]">{profitLoss ? profitLoss.total_expense.toLocaleString() : '—'}</div>
            </div>
            <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-5">
              <div className="text-xs text-[var(--text-secondary)] mb-1">📊 حاشیه سود</div>
              <div className="text-2xl font-extrabold text-[var(--text-primary)]">{profitLoss ? `${profitLoss.margin}%` : '—'}</div>
            </div>
          </div>
          {/* Monthly Bar Chart + P&L Trend */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-5">
              <div className="text-sm font-extrabold text-[var(--text-primary)] mb-4">📊 درآمد vs هزینه ماهانه ({monthlyReport?.year ?? advYear})</div>
              {monthlyReport && monthlyReport.months.some((m) => m.income || m.expense) ? (
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={monthlyReport.months}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
                    <XAxis dataKey="month_name" tick={{ fontSize: 10, fontFamily: 'Vazirmatn' }} stroke="var(--text-secondary)" />
                    <YAxis tick={{ fontSize: 11 }} stroke="var(--text-secondary)" />
                    <Tooltip contentStyle={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 12, color: 'var(--text-primary)', direction: 'rtl' }} />
                    <Legend formatter={(v: any) => <span className="text-xs text-[var(--text-secondary)]">{v}</span>} />
                    <Bar dataKey="income" fill="#22c55e" radius={[6, 6, 0, 0]} name="درآمد" />
                    <Bar dataKey="expense" fill="#ef4444" radius={[6, 6, 0, 0]} name="هزینه" />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="text-center py-12 text-[var(--text-secondary)]">داده‌ای برای نمایش وجود ندارد</div>
              )}
            </div>
            <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-5">
              <div className="text-sm font-extrabold text-[var(--text-primary)] mb-4">📈 روند سود و زیان ({profitLoss?.year ?? advYear})</div>
              {profitLoss && profitLoss.monthly.some((m) => m.net) ? (
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={profitLoss.monthly}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
                    <XAxis dataKey="month_name" tick={{ fontSize: 10, fontFamily: 'Vazirmatn' }} stroke="var(--text-secondary)" />
                    <YAxis tick={{ fontSize: 11 }} stroke="var(--text-secondary)" />
                    <Tooltip contentStyle={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 12, color: 'var(--text-primary)', direction: 'rtl' }} />
                    <Legend formatter={(v: any) => <span className="text-xs text-[var(--text-secondary)]">{v}</span>} />
                    <Line type="monotone" dataKey="cumulative" stroke="#3F7CFF" strokeWidth={2} name="تجمعی" dot={{ r: 3 }} />
                    <Line type="monotone" dataKey="net" stroke="#a855f7" strokeWidth={2} name="ماهانه" dot={{ r: 3 }} />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="text-center py-12 text-[var(--text-secondary)]">داده‌ای برای نمایش وجود ندارد</div>
              )}
            </div>
          </div>
          {/* Category Breakdown Pie + Account Comparison */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-5">
              <div className="text-sm font-extrabold text-[var(--text-primary)] mb-4">🥧 تفکیک دسته‌بندی</div>
              {categoryBreakdown && categoryBreakdown.items.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={categoryBreakdown.items.map((it, i) => ({
                        name: it.category_name,
                        value: it.total,
                        percent: it.percent,
                        fill: it.color || (it.type === 'income' ? '#22c55e' : FALLBACK_COLORS[i % FALLBACK_COLORS.length]),
                      }))}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={100}
                      label={(p: any) => `${p.percent}%`}
                    >
                      {categoryBreakdown.items.map((it, i) => (
                        <Cell key={i} fill={it.color || (it.type === 'income' ? '#22c55e' : FALLBACK_COLORS[i % FALLBACK_COLORS.length])} />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(value: any, name: any) => [`${Number(value).toLocaleString()}`, name]}
                      contentStyle={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 12, color: 'var(--text-primary)', direction: 'rtl', fontSize: 12 }}
                    />
                    <Legend formatter={(v: any) => <span className="text-xs text-[var(--text-secondary)]">{v}</span>} />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="text-center py-12 text-[var(--text-secondary)]">
                  <div className="text-4xl mb-3">🥧</div>
                  <div>داده‌ای برای نمایش وجود ندارد</div>
                </div>
              )}
            </div>
            <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-5">
              <div className="text-sm font-extrabold text-[var(--text-primary)] mb-4">🏦 مقایسه حساب‌ها</div>
              {accountComparison.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-[var(--border-subtle)] text-[var(--text-secondary)]">
                        <th className="text-right py-3 px-3">حساب</th>
                        <th className="text-right py-3 px-3">موجودی</th>
                        <th className="text-right py-3 px-3">درآمد</th>
                        <th className="text-right py-3 px-3">هزینه</th>
                        <th className="text-right py-3 px-3">خالص</th>
                      </tr>
                    </thead>
                    <tbody>
                      {accountComparison.map((s) => (
                        <tr key={s.id} className="border-b border-[var(--border-subtle)]/50 hover:bg-[var(--accent-soft)]/30 transition-colors">
                          <td className="py-3 px-3 font-bold text-[var(--text-primary)]">
                            {ACCOUNT_TYPE_LABELS[s.type] || '❓'} {s.name}
                            <span className="text-[10px] text-[var(--text-secondary)] mr-1">{s.currency}</span>
                          </td>
                          <td className="py-3 px-3 font-bold text-[var(--text-primary)]">{s.balance?.toLocaleString()}</td>
                          <td className="py-3 px-3 text-[#22c55e]">{s.total_income.toLocaleString()}</td>
                          <td className="py-3 px-3 text-[#ef4444]">{s.total_expense.toLocaleString()}</td>
                          <td className={`py-3 px-3 font-bold ${s.net >= 0 ? 'text-[#22c55e]' : 'text-[#ef4444]'}`}>{s.net.toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-center py-12 text-[var(--text-secondary)]">حسابی برای مقایسه وجود ندارد</div>
              )}
            </div>
          </div>
          {/* Yearly P&L Table */}
          {profitLoss && profitLoss.yearly.length > 0 && (
            <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-5">
              <div className="text-sm font-extrabold text-[var(--text-primary)] mb-4">📅 سود و زیان به تفکیک سال</div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-[var(--border-subtle)] text-[var(--text-secondary)]">
                      <th className="text-right py-3 px-3">سال (شمسی)</th>
                      <th className="text-right py-3 px-3">درآمد</th>
                      <th className="text-right py-3 px-3">هزینه</th>
                      <th className="text-right py-3 px-3">سود خالص</th>
                    </tr>
                  </thead>
                  <tbody>
                    {profitLoss.yearly.map((y) => (
                      <tr key={y.year} className="border-b border-[var(--border-subtle)]/50 hover:bg-[var(--accent-soft)]/30 transition-colors">
                        <td className="py-3 px-3 font-bold text-[var(--text-primary)]">{y.year}</td>
                        <td className="py-3 px-3 text-[#22c55e]">{y.income.toLocaleString()}</td>
                        <td className="py-3 px-3 text-[#ef4444]">{y.expense.toLocaleString()}</td>
                        <td className={`py-3 px-3 font-bold ${y.net >= 0 ? 'text-[#22c55e]' : 'text-[#ef4444]'}`}>{y.net.toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ═══ Real PnL Tab (فاز ۲۲.۱) ═══ */}
      {tab === 'real' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-5">
              <div className="text-xs text-[var(--text-secondary)] mb-1">🏢 مرحلهٔ ۳ پراپ</div>
              <div className={`text-2xl font-extrabold ${(realPnl?.prop_stage_3?.pnl ?? 0) >= 0 ? 'text-[#22c55e]' : 'text-[#ef4444]'}`}>
                {realPnl ? `${realPnl.prop_stage_3.pnl >= 0 ? '+' : ''}${realPnl.prop_stage_3.pnl.toLocaleString()}` : '—'} {realPnl?.currency || 'USDT'}
              </div>
              <div className="text-xs text-[var(--text-secondary)] mt-1">تعداد معاملات: {realPnl?.prop_stage_3?.trades ?? '—'}</div>
            </div>
            <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-5">
              <div className="text-xs text-[var(--text-secondary)] mb-1">📊 بروکر</div>
              <div className={`text-2xl font-extrabold ${(realPnl?.broker?.pnl ?? 0) >= 0 ? 'text-[#22c55e]' : 'text-[#ef4444]'}`}>
                {realPnl ? `${realPnl.broker.pnl >= 0 ? '+' : ''}${realPnl.broker.pnl.toLocaleString()}` : '—'} {realPnl?.currency || 'USDT'}
              </div>
              <div className="text-xs text-[var(--text-secondary)] mt-1">تعداد معاملات: {realPnl?.broker?.trades ?? '—'}</div>
            </div>
            <div className="bg-[var(--bg-card)] border border-[var(--border-accent)] rounded-[22px] p-5">
              <div className="text-xs text-[var(--text-secondary)] mb-1">Σ مجموع Real</div>
              <div className={`text-2xl font-black ${(realPnl?.total?.pnl ?? 0) >= 0 ? 'text-[#22c55e]' : 'text-[#ef4444]'}`}>
                {realPnl ? `${realPnl.total.pnl >= 0 ? '+' : ''}${realPnl.total.pnl.toLocaleString()}` : '—'} {realPnl?.currency || 'USDT'}
              </div>
              <div className="text-xs text-[var(--text-secondary)] mt-1">تعداد کل: {realPnl?.total?.trades ?? '—'}</div>
            </div>
          </div>

          <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-5">
            <div className="text-sm font-extrabold text-[var(--text-primary)] mb-4">💰 سود/زیان Real بر اساس منبع</div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--border-subtle)] text-[var(--text-secondary)]">
                    <th className="text-right py-3 px-3">منبع</th>
                    <th className="text-right py-3 px-3">سود/زیان (net_pnl)</th>
                    <th className="text-right py-3 px-3">تعداد معاملات</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    ['🏢 مرحلهٔ ۳ پراپ', realPnl?.prop_stage_3],
                    ['📊 بروکر', realPnl?.broker],
                    ['Σ مجموع', realPnl?.total],
                  ].map(([label, v]: any, i) => (
                    <tr key={i} className={`border-b border-[var(--border-subtle)]/50 ${i === 2 ? 'font-bold' : ''}`}>
                      <td className="py-3 px-3 text-[var(--text-primary)]">{label}</td>
                      <td className={`py-3 px-3 font-bold ${(v?.pnl ?? 0) >= 0 ? 'text-[#22c55e]' : 'text-[#ef4444]'}`}>
                        {v ? v.pnl.toLocaleString() : '—'}
                      </td>
                      <td className="py-3 px-3 text-[var(--text-secondary)]">{v?.trades ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* سود خالص (فاز ۲۲.۱) */}
          <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-5">
            <div className="text-sm font-extrabold text-[var(--text-primary)] mb-4">🧾 سود خالص</div>
            {netProfit ? (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-[var(--bg-elevated)] rounded-[14px] p-4">
                  <div className="text-[11px] text-[var(--text-secondary)] font-bold">سود Real</div>
                  <div className={`text-xl font-extrabold ${netProfit.real_pnl >= 0 ? 'text-[#22c55e]' : 'text-[#ef4444]'}`}>{netProfit.real_pnl.toLocaleString()} {netProfit.currency || 'USDT'}</div>
                </div>
                <div className="bg-[var(--bg-elevated)] rounded-[14px] p-4">
                  <div className="text-[11px] text-[var(--text-secondary)] font-bold">هزینه‌ها</div>
                  <div className="text-xl font-extrabold text-[#ef4444]">−{netProfit.expenses.toLocaleString()} {netProfit.currency || 'USDT'}</div>
                </div>
                <div className="bg-[var(--accent-soft)] rounded-[14px] p-4">
                  <div className="text-[11px] text-[var(--text-secondary)] font-bold">سود خالص</div>
                  <div className={`text-xl font-black ${netProfit.net_profit >= 0 ? 'text-[#22c55e]' : 'text-[#ef4444]'}`}>{netProfit.net_profit.toLocaleString()} {netProfit.currency || 'USDT'}</div>
                </div>
              </div>
            ) : (
              <div className="text-sm text-[var(--text-secondary)]">در حال بارگذاری…</div>
            )}
          </div>
        </div>
      )}

      {/* ═══ Money Flow Tab (فاز ۲۲.۲) ═══ */}
      {tab === 'moneyflow' && (
        <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-5">
          <div className="text-sm font-extrabold text-[var(--text-primary)] mb-4">🔀 جریان پول بین حساب‌ها</div>
          {spendableAssets && (
            <div className="mb-5">
              <FinancialAssetBalances assets={spendableAssets} />
            </div>
          )}
          {moneyFlow.length === 0 ? (
            <div className="text-center py-12 text-[var(--text-secondary)]">جریانی برای نمایش وجود ندارد</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--border-subtle)] text-[var(--text-secondary)]">
                    <th className="text-right py-3 px-3">از</th>
                    <th className="text-right py-3 px-3">به</th>
                    <th className="text-right py-3 px-3">مبلغ</th>
                    <th className="text-right py-3 px-3">ارز</th>
                    <th className="text-right py-3 px-3">نوع</th>
                    <th className="text-right py-3 px-3">تاریخ</th>
                  </tr>
                </thead>
                <tbody>
                  {moneyFlow.map((f, i) => (
                    <tr key={i} className="border-b border-[var(--border-subtle)]/50 hover:bg-[var(--accent-soft)]/30 transition-colors">
                      <td className="py-3 px-3 text-[var(--text-primary)]">{f.from_name || `${ACCOUNT_TYPE_LABELS[f.from] || ''} ${ACCOUNT_TYPE_NAMES[f.from] || f.from || '—'}`}</td>
                      <td className="py-3 px-3 text-[var(--text-primary)]">{f.to_name || `${ACCOUNT_TYPE_LABELS[f.to] || ''} ${ACCOUNT_TYPE_NAMES[f.to] || f.to || '—'}`}</td>
                      <td className="py-3 px-3 font-bold text-[var(--text-primary)]">{Number(f.amount).toLocaleString()}</td>
                      <td className="py-3 px-3 text-[var(--text-secondary)]">{f.currency}</td>
                      <td className="py-3 px-3"><span className="text-xs px-2 py-0.5 rounded-full bg-[var(--accent-soft)] text-[var(--accent)] font-bold">{TRANSACTION_TYPE_LABELS[f.type] || f.type}</span></td>
                      <td className="py-3 px-3 text-xs text-[var(--text-secondary)]">{f.date ? new Date(f.date).toLocaleDateString('fa-IR') : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ═══ Expenses Tab (فاز ۲۲.۲) ═══ */}
      {tab === 'expenses' && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {([
              ['prop_purchase', '🛒 خرید پراپ'],
              ['prop_subscription', '📄 اشتراک پراپ'],
              ['exchange_fee', '💱 کارمزد صرافی'],
              ['withdrawal_fee', '🏧 کارمزد برداشت'],
              ['other', '📦 سایر'],
              ['total', 'Σ مجموع'],
            ] as const).map(([key, label]) => (
              <div key={key} className={`bg-[var(--bg-card)] border rounded-[22px] p-4 ${key === 'total' ? 'border-[var(--border-accent)]' : 'border-[var(--border-subtle)]'}`}>
                <div className="text-[11px] text-[var(--text-secondary)] mb-1">{label}</div>
                <div className={`text-lg font-extrabold ${key === 'total' ? 'text-[var(--accent)]' : 'text-[#ef4444]'}`}>
                  {expenses ? Number(expenses[key] ?? 0).toLocaleString() : '—'} USDT
                </div>
              </div>
            ))}
          </div>

          <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-5">
            <div className="text-sm font-extrabold text-[var(--text-primary)] mb-4">🧾 تفکیک هزینه‌ها</div>
            {expenses && expenses.total > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={[
                  { name: 'خرید پراپ', value: expenses.prop_purchase },
                  { name: 'اشتراک پراپ', value: expenses.prop_subscription },
                  { name: 'کارمزد صرافی', value: expenses.exchange_fee },
                  { name: 'کارمزد برداشت', value: expenses.withdrawal_fee },
                  { name: 'سایر', value: expenses.other },
                ]}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
                  <XAxis dataKey="name" tick={{ fontSize: 11, fontFamily: 'Vazirmatn' }} stroke="var(--text-secondary)" />
                  <YAxis tick={{ fontSize: 11 }} stroke="var(--text-secondary)" />
                  <Tooltip contentStyle={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 12, color: 'var(--text-primary)', direction: 'rtl' }} formatter={(v: any) => [`${Number(v).toLocaleString()} USDT`, '']} />
                  <Bar dataKey="value" radius={[6, 6, 0, 0]} fill="#ef4444" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-center py-12 text-[var(--text-secondary)]">هزینه‌ای ثبت نشده</div>
            )}
          </div>
        </div>
      )}

      {/* ═══ Money Cycle Tab (فاز ۲۲.۲) ═══ */}
      {tab === 'cycle' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {([
            ['total_deposits', '💵 مجموع واریز', '#22c55e'],
            ['total_withdrawals', '🏧 مجموع برداشت', '#ef4444'],
            ['total_exchanges', '🔄 مجموع تبدیل', '#8b5cf6'],
            ['total_transfers', '🔀 مجموع انتقال', '#3F7CFF'],
            ['current_balance', '🏦 موجودی فعلی', '#13AE81'],
          ] as const).map(([key, label, color]) => (
            <div key={key} className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-6">
              <div className="text-xs text-[var(--text-secondary)] mb-2">{label}</div>
              <div className="text-2xl font-black" style={{ color }}>
                {moneyCycle ? Number(moneyCycle[key] ?? 0).toLocaleString() : '—'}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ═══ Financial Calendar Tab (فاز ۲۲.۳) ═══ */}
      {tab === 'calendar' && (
        <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-5">
          <div className="text-sm font-extrabold text-[var(--text-primary)] mb-4">🗓️ تقویم مالی (به تفکیک روز شمسی)</div>
          {calendar.length === 0 ? (
            <div className="text-center py-12 text-[var(--text-secondary)]">داده‌ای برای نمایش وجود ندارد</div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
              {calendar.map((d) => (
                <div key={d.date} className="rounded-[16px] p-3 border border-[var(--border-subtle)]"
                  style={{ background: d.pnl > 0 ? 'rgba(34,197,94,0.08)' : d.pnl < 0 ? 'rgba(239,68,68,0.08)' : 'var(--bg-elevated)' }}>
                  <div className="text-[11px] font-bold text-[var(--text-secondary)] mb-1">{d.date}</div>
                  <div className={`text-base font-extrabold ${d.pnl > 0 ? 'text-[#22c55e]' : d.pnl < 0 ? 'text-[#ef4444]' : 'text-[var(--text-primary)]'}`}>
                    {d.pnl >= 0 ? '+' : ''}{d.pnl.toLocaleString()} USDT
                  </div>
                  <div className="text-[10px] text-[var(--text-secondary)] mt-1">{d.trades} معامله</div>
                  {(d.deposits > 0 || d.withdrawals > 0) && (
                    <div className="text-[10px] mt-1 text-[var(--text-secondary)]">
                      {d.deposits > 0 && <span className="text-[#22c55e]">+{d.deposits.toLocaleString()} </span>}
                      {d.withdrawals > 0 && <span className="text-[#ef4444]">−{d.withdrawals.toLocaleString()}</span>}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

          </div>
  );
}


function FinanceSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex gap-2 mb-6 pb-3">
        <Skeleton variant="text" className="w-24 h-8 rounded-xl" count={4} />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }, (_, i) => (
          <div key={i} className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-5">
            <Skeleton variant="text" className="w-28 h-4 mb-3" />
            <Skeleton variant="text" className="w-20 h-8 mb-2" />
            <Skeleton variant="text" className="w-32 h-3" />
          </div>
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Skeleton variant="card" className="h-72" />
        <Skeleton variant="card" className="h-72" />
      </div>
      <Skeleton variant="card" className="h-48" />
    </div>
  );
}
