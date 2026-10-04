import { useState, useEffect } from 'react';
import {
  getPropFirms,
  createPropFirm,
  getPropAccounts,
  createPropAccount,
  getPropAccountDetail,
  failStage,
  withdrawFromStage,
  getStageTrades,
  checkPassReady,
  passStageWithRules,
  updateStageRules,
  getPropAnalytics,
  getFirmDefaultRules,
  getPropAlerts,
  markAlertRead,
  generatePropAlerts,
  getFinanceAccountsForDestination,
} from '../api/client';
import PropAnalytics from '../components/charts/PropAnalytics';
import PersianDateInput from '../components/PersianDateInput';
import Toast from '../components/Toast';

interface Firm {
  id: number;
  name: string;
  accounts_count?: number;
}

interface Account {
  id: number;
  account_label: string;
  firm_id: number;
  firm_name: string;
  currency: string;
  stages_count: number;
}

interface Stage {
  id: number;
  stage_type: string;
  status: string;
  start_date: string;
  end_date: string | null;
  profit_target: number | null;
  max_daily_dd: number | null;
  max_total_dd: number | null;
  min_trading_days: number | null;
  initial_balance: number | null;
  dd_basis: 'balance' | 'equity';
  daily_dd_mode: 'static' | 'trailing';
  total_dd_mode: 'static' | 'trailing';
  final_balance: number | null;
  current_profit: number;
  total_withdrawn: number;
  profit_share_percentage: number | null;
  failure_reason: string | null;
  failure_details: string | null;
}

const getStageTypeLabel = (type: string) => {
  if (type === 'stage_1') return '🥇 مرحله ۱';
  if (type === 'stage_2') return '🥈 مرحله ۲';
  if (type === 'funded_real') return '💰 رییل';
  return type;
};

const getStageColor = (type: string) => {
  if (type === 'stage_1') return { bg: 'bg-[var(--purple-soft)]', text: 'text-[var(--purple)]', border: 'border-[var(--purple-border)]' };
  if (type === 'stage_2') return { bg: 'bg-[var(--accent-soft)]', text: 'text-[var(--accent)]', border: 'border-[var(--border-accent)]' };
  return { bg: 'bg-[var(--profit-soft)]', text: 'text-[var(--profit)]', border: 'border-[var(--profit-border)]' };
};

const getStatusBadge = (status: string) => {
  const styles: Record<string, { bg: string, text: string, label: string }> = {
    active: { bg: 'bg-[var(--accent-soft)]', text: 'text-[var(--accent)]', label: '🟢 فعال' },
    passed: { bg: 'bg-[var(--profit-soft)]', text: 'text-[var(--profit)]', label: '✅ پاس‌شده' },
    failed: { bg: 'bg-[var(--loss-soft)]', text: 'text-[var(--loss)]', label: '❌ فیل‌شده' },
    closed: { bg: 'bg-[var(--bg-elevated)]', text: 'text-[var(--text-secondary)]', label: '⚫ بسته‌شده' },
  };
  const style = styles[status] || styles.closed;
  return (
    <span className={`text-[11px] font-bold px-3 py-1 rounded-full ${style.bg} ${style.text}`}>
      {style.label}
    </span>
  );
};

export default function PropPage() {
  const [firms, setFirms] = useState<Firm[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [destinationAccounts, setDestinationAccounts] = useState<any[]>([]);
  const [selectedAccount, setSelectedAccount] = useState<Account | null>(null);
  const [accountDetail, setAccountDetail] = useState<any>(null);
  const [expandedFirms, setExpandedFirms] = useState<number[]>([]);

  const [showFirmForm, setShowFirmForm] = useState(false);
  const [showAccountForm, setShowAccountForm] = useState(false);
  const [firmName, setFirmName] = useState('');
  const [selectedFirmId, setSelectedFirmId] = useState<number | null>(null);
  const [accountLabel, setAccountLabel] = useState('');
  const [accountNumber, setAccountNumber] = useState('');

    const [initialBalance, setInitialBalance] = useState('10000');
  const [profitTargetPercent, setProfitTargetPercent] = useState('8');
  const [maxDailyDdPercent, setMaxDailyDdPercent] = useState('5');
  const [maxTotalDdPercent, setMaxTotalDdPercent] = useState('10');
  const [minTradingDays, setMinTradingDays] = useState('5');
  const [stageTrades, setStageTrades] = useState<any[]>([]);
  const [selectedStage, setSelectedStage] = useState<number | null>(null);

  const [showPassModal, setShowPassModal] = useState(false);
  const [passingStage, setPassingStage] = useState<Stage | null>(null);
  const [passProgress, setPassProgress] = useState<any>(null);
  const [nextStageRules, setNextStageRules] = useState({
  profit_target_percent: '',
  max_daily_dd_percent: '',
  max_total_dd_percent: '',
  min_trading_days: '',
  initial_balance: '',
  profit_share_percentage: '',
  dd_basis: 'balance' as 'balance' | 'equity',
  daily_dd_mode: 'static' as 'static' | 'trailing',
  total_dd_mode: 'static' as 'static' | 'trailing',
});
const [showProgressModal, setShowProgressModal] = useState(false);
const [progressStage, setProgressStage] = useState<Stage | null>(null);
const [stageProgressData, setStageProgressData] = useState<any>(null);
  const [editingStage, setEditingStage] = useState<number | null>(null);
    const [editRules, setEditRules] = useState({
    profit_target_percent: '',
    max_daily_dd_percent: '',
    max_total_dd_percent: '',
    min_trading_days: '',
    initial_balance: '',
    profit_share_percentage: '',
    dd_basis: 'balance' as 'balance' | 'equity',
    daily_dd_mode: 'static' as 'static' | 'trailing',
    total_dd_mode: 'static' as 'static' | 'trailing',
  });

  const [showFailModal, setShowFailModal] = useState(false);
  const [failingStage, setFailingStage] = useState<Stage | null>(null);
  const [failReason, setFailReason] = useState('max_daily_dd_exceeded');
  const [failDetails, setFailDetails] = useState('');

  const [propAnalytics, setPropAnalytics] = useState<any>(null);
  const [showAnalytics, setShowAnalytics] = useState(false);
const [alerts, setAlerts] = useState<any[]>([]);
  const [showAlerts, setShowAlerts] = useState(false);
  const [alertLoading, setAlertLoading] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [modalError, setModalError] = useState<string | null>(null);

  // فاز ۳۸.۵: stateهای «یکپارچگی با مالی» (createFinanceAccount / financeInfo / loadingDetail)
  // حذف شدند — بک‌اند این پل را در فاز ۲۸ حذف کرده بود و همهٔ آن مسیرها ۴۰۴/بی‌اثر بودند.

  // 🆕 فاز ۵.۱ — Modal برداشت
  const [showWithdrawModal, setShowWithdrawModal] = useState(false);
  const [withdrawingStage, setWithdrawingStage] = useState<Stage | null>(null);
  const [withdrawAmount, setWithdrawAmount] = useState('');
  const [withdrawDate, setWithdrawDate] = useState(new Date().toISOString().slice(0, 10));
  const [withdrawDestinationId, setWithdrawDestinationId] = useState<number | ''>('');
  const [withdrawNote, setWithdrawNote] = useState('');

  useEffect(() => {
    loadData();
    loadDestinationAccounts();
  }, []);

  const loadData = async () => {
    try {
      const [firmsRes, accountsRes] = await Promise.all([
        getPropFirms(),
        getPropAccounts(),
      ]);
      setFirms(firmsRes.data);
      setAccounts(accountsRes.data);
      const firmIds = firmsRes.data.map((f: Firm) => f.id);
      setExpandedFirms(firmIds);
    } catch (err) {
      console.error('خطا:', err);
    }
  };

  // 🆕 فاز ۵.۱ — حساب‌های مالی مجاز به‌عنوان مقصد برداشت (type !== prop)
  const loadDestinationAccounts = async () => {
    try {
      const res = await getFinanceAccountsForDestination();
      setDestinationAccounts((res.data || []).filter((a: any) => a.type !== 'prop'));
    } catch (err) {
      console.error('خطا:', err);
    }
  };

  const loadAnalytics = async () => {
    try {
      const res = await getPropAnalytics();
      setPropAnalytics(res.data);
      setShowAnalytics(true);
    } catch (err) {
      console.error('خطا:', err);
    }
  };

  const loadAccountDetail = async (accountId: number) => {
    try {
      const res = await getPropAccountDetail(accountId);
      setAccountDetail(res.data);
    } catch (err) {
      console.error('خطا:', err);
    }
  };

  const loadStageTrades = async (stageId: number) => {
    try {
      const res = await getStageTrades(stageId);
      setStageTrades(res.data);
      setSelectedStage(stageId);
    } catch (err) {
      console.error('خطا:', err);
    }
  };

  const handleSelectAccount = (account: Account) => {
    setSelectedAccount(account);
    loadAccountDetail(account.id);
  };

  const toggleFirm = (firmId: number) => {
    if (expandedFirms.includes(firmId)) {
      setExpandedFirms(expandedFirms.filter((id) => id !== firmId));
    } else {
      setExpandedFirms([...expandedFirms, firmId]);
    }
  };

  const handleCreateFirm = async () => {
    if (!firmName.trim()) return;
    try {
      await createPropFirm({ name: firmName, default_profit_share: 80 });
      setFirmName('');
      setShowFirmForm(false);
      await loadData();
      setSuccessMessage('شرکت پراپ ساخته شد');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'خطا در ساخت شرکت');
    }
  };
const loadAlerts = async (stageId?: number) => {
    setAlertLoading(true);
    try {
      const params: any = { unread_only: true };
      if (stageId) params.stage_id = stageId;
      const res = await getPropAlerts(params);
      setAlerts(res.data);
    } catch { /* silent */ }
    finally { setAlertLoading(false); }
  };

    const handleCreateAccount = async () => {
    if (!selectedFirmId || !accountLabel.trim()) return;
    try {
      const initialBalanceNum = parseFloat(initialBalance) || 10000;
      const profitTargetAmount = (parseFloat(profitTargetPercent) || 0) / 100 * initialBalanceNum;
      const maxDailyDdAmount = (parseFloat(maxDailyDdPercent) || 0) / 100 * initialBalanceNum;
      const maxTotalDdAmount = (parseFloat(maxTotalDdPercent) || 0) / 100 * initialBalanceNum;

      await createPropAccount({
        prop_firm_id: selectedFirmId,
        account_label: accountLabel,
        account_number: accountNumber,
        initial_balance: initialBalanceNum,
        profit_target: profitTargetAmount,
        max_daily_dd: maxDailyDdAmount,
        max_total_dd: maxTotalDdAmount,
        min_trading_days: parseInt(minTradingDays) || 5,
      });
      setAccountLabel('');
      setAccountNumber('');
      setShowAccountForm(false);
      await loadData();
      await loadDestinationAccounts();
      // فاز ۳۸.۵: پیام ساده — «ساخت خودکار حساب مالی» در فاز ۲۸ حذف شد
      setSuccessMessage('اکانت پراپ ساخته شد');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'خطا در ساخت اکانت');
    }
  };

    const handleOpenPassModal = async (stage: Stage) => {
    setModalError(null);
    try {
      const res = await checkPassReady(stage.id);
      setPassProgress(res.data);
      setPassingStage(stage);
      setNextStageRules({
        profit_target_percent: '',
        max_daily_dd_percent: '',
        max_total_dd_percent: '',
        min_trading_days: '',
        initial_balance: (stage.final_balance || stage.initial_balance || 10000).toString(),
        profit_share_percentage: stage.stage_type === 'stage_2' ? '80' : '',
        dd_basis: 'balance',
        daily_dd_mode: 'static',
        total_dd_mode: 'static',
      });
      setShowPassModal(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'خطا در بررسی مرحله');
    }
  };
   const handleOpenProgressModal = async (stage: Stage) => {
  try {
    const res = await checkPassReady(stage.id);
    setStageProgressData(res.data);
    setProgressStage(stage);
    setShowProgressModal(true);
  } catch (err: any) {
    setError(err.response?.data?.detail || 'خطا در بررسی مرحله');
  }
};
     const handleConfirmPass = async () => {
    if (!passingStage || !passProgress) return;
    setModalError(null);
    try {
      const finalBalance = (passingStage.initial_balance || 0) + (passProgress.current_profit || 0);
      const nextInitialBalance = nextStageRules.initial_balance
  ? parseFloat(nextStageRules.initial_balance)
  : finalBalance;

await passStageWithRules(
  passingStage.id,
  finalBalance,
  {
    profit_target: nextStageRules.profit_target_percent
      ? (parseFloat(nextStageRules.profit_target_percent) / 100) * nextInitialBalance
      : undefined,
    max_daily_dd: nextStageRules.max_daily_dd_percent
      ? (parseFloat(nextStageRules.max_daily_dd_percent) / 100) * nextInitialBalance
      : undefined,
    max_total_dd: nextStageRules.max_total_dd_percent
      ? (parseFloat(nextStageRules.max_total_dd_percent) / 100) * nextInitialBalance
      : undefined,
    min_trading_days: nextStageRules.min_trading_days ? parseInt(nextStageRules.min_trading_days) : undefined,
    initial_balance: nextStageRules.initial_balance ? parseFloat(nextStageRules.initial_balance) : undefined,
    profit_share_percentage: nextStageRules.profit_share_percentage ? parseFloat(nextStageRules.profit_share_percentage) : undefined,
    dd_basis: nextStageRules.dd_basis,
    daily_dd_mode: nextStageRules.daily_dd_mode,
    total_dd_mode: nextStageRules.total_dd_mode,
  }
);
      setSuccessMessage('مرحله با موفقیت پاس شد. مرحله‌ی بعدی ایجاد شد.');
      setShowPassModal(false);
      if (selectedAccount) await loadAccountDetail(selectedAccount.id);
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: any) {
                 setModalError(err.response?.data?.detail || 'خطا در پاس کردن');
    }
  };

  const handleOpenFailModal = (stage: Stage) => {
    setFailingStage(stage);
    setFailReason('max_daily_dd_exceeded');
    setFailDetails('');
    setShowFailModal(true);
  };

  const handleConfirmFail = async () => {
    if (!failingStage) return;
    try {
      await failStage(failingStage.id, failReason, failDetails);
      setSuccessMessage('مرحله فیل شد');
      setShowFailModal(false);
      if (selectedAccount) await loadAccountDetail(selectedAccount.id);
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'خطا در فیل کردن مرحله');
    }
  };

    const startEditStage = (stage: Stage) => {
    setEditingStage(stage.id);
    const initial = stage.initial_balance || 10000;
    setEditRules({
      profit_target_percent: stage.profit_target
        ? ((stage.profit_target / initial) * 100).toFixed(2)
        : '',
      max_daily_dd_percent: stage.max_daily_dd
        ? ((stage.max_daily_dd / initial) * 100).toFixed(2)
        : '',
      max_total_dd_percent: stage.max_total_dd
        ? ((stage.max_total_dd / initial) * 100).toFixed(2)
        : '',
      min_trading_days: stage.min_trading_days?.toString() || '',
      initial_balance: stage.initial_balance?.toString() || '',
      profit_share_percentage: stage.profit_share_percentage?.toString() || '',
      dd_basis: stage.dd_basis || 'balance',
      daily_dd_mode: stage.daily_dd_mode || 'static',
      total_dd_mode: stage.total_dd_mode || 'static',
    });
  };


  const cancelEditStage = () => {
    setEditingStage(null);
  };

    const handleSaveStageRules = async (stageId: number) => {
    try {
      const initialBalanceNum = parseFloat(editRules.initial_balance) || 10000;

      await updateStageRules(stageId, {
        profit_target: editRules.profit_target_percent
          ? (parseFloat(editRules.profit_target_percent) / 100) * initialBalanceNum
          : undefined,
        max_daily_dd: editRules.max_daily_dd_percent
          ? (parseFloat(editRules.max_daily_dd_percent) / 100) * initialBalanceNum
          : undefined,
        max_total_dd: editRules.max_total_dd_percent
          ? (parseFloat(editRules.max_total_dd_percent) / 100) * initialBalanceNum
          : undefined,
        min_trading_days: editRules.min_trading_days ? parseInt(editRules.min_trading_days) : undefined,
        initial_balance: editRules.initial_balance ? parseFloat(editRules.initial_balance) : undefined,
        profit_share_percentage: editRules.profit_share_percentage ? parseFloat(editRules.profit_share_percentage) : undefined,
        dd_basis: editRules.dd_basis,
        daily_dd_mode: editRules.daily_dd_mode,
        total_dd_mode: editRules.total_dd_mode,
      });
      setSuccessMessage('قوانین مرحله ذخیره شد');
      setEditingStage(null);
      if (selectedAccount) await loadAccountDetail(selectedAccount.id);
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'خطا در ذخیره قوانین');
    }
  };

  // 🆕 فاز ۵.۱ — باز کردن Modal برداشت (جایگزین prompt)
  const handleWithdraw = (stage: Stage) => {
    setWithdrawingStage(stage);
    setWithdrawAmount('');
    setWithdrawDate(new Date().toISOString().slice(0, 10));
    setWithdrawDestinationId(destinationAccounts.length === 1 ? destinationAccounts[0].id : '');
    setWithdrawNote('');
    setModalError(null);
    setShowWithdrawModal(true);
  };

  // 🆕 فاز ۵.۱ — تأیید برداشت و ثبت تراکنش مالی
  const handleConfirmWithdraw = async () => {
    if (!withdrawingStage) return;
    const amount = parseFloat(withdrawAmount);
    if (isNaN(amount) || amount <= 0) {
      setModalError('مبلغ برداشت باید عددی مثبت باشد');
      return;
    }
    if (!withdrawDestinationId) {
      setModalError('انتخاب حساب مقصد الزامی است');
      return;
    }
    try {
      await withdrawFromStage(withdrawingStage.id, {
        amount,
        destination_account_id: Number(withdrawDestinationId),
        withdrawal_date: withdrawDate || undefined,
        note: withdrawNote || undefined,
      });
      setShowWithdrawModal(false);
      setSuccessMessage(`${amount} دلار برداشت شد و به حساب مقصد واریز شد`);
      await loadDestinationAccounts();
      if (selectedAccount) await loadAccountDetail(selectedAccount.id);
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setModalError(err.response?.data?.detail || 'خطا در برداشت');
    }
  };

  return (
    <div className="space-y-6">
      {/* 🆕 فاز ۵.۱ — Toast برای پیام‌های موفقیت/خطا */}
      {error && <Toast message={error} type="error" onClose={() => setError(null)} />}
      {successMessage && (
        <Toast message={successMessage} type="success" onClose={() => setSuccessMessage(null)} />
      )}

      {/* دکمه‌ها */}
      <div className="flex gap-3 flex-wrap">
        <button
          onClick={() => setShowFirmForm(!showFirmForm)}
          className="text-white px-6 py-3 rounded-[12px] text-sm font-extrabold transition-all shadow-[0_6px_16px_rgba(63,124,255,0.3)] hover:shadow-[0_10px_24px_rgba(63,124,255,0.4)] hover:-translate-y-0.5"
          style={{ background: 'linear-gradient(135deg, var(--accent), var(--accent-strong))' }}
        >
          ➕ شرکت پراپ جدید
        </button>
        <button
          onClick={() => setShowAccountForm(!showAccountForm)}
          disabled={firms.length === 0}
          className="text-white px-6 py-3 rounded-[12px] text-sm font-extrabold transition-all shadow-[0_6px_16px_rgba(19,174,129,0.3)] hover:shadow-[0_10px_24px_rgba(19,174,129,0.4)] hover:-translate-y-0.5 disabled:opacity-40 disabled:cursor-not-allowed"
          style={{ background: 'linear-gradient(135deg, var(--profit), var(--profit-border))' }}
        >
          ➕ اکانت پراپ جدید
        </button>
        <button
          onClick={loadAnalytics}
          className="bg-[var(--bg-card)] border-2 border-[var(--border-subtle)] text-[var(--text-secondary)] hover:border-[var(--border-accent)] hover:text-[var(--accent)] px-6 py-3 rounded-[12px] text-sm font-extrabold transition-all shadow-sm"
        >
          📊 گزارش تحلیلی
        </button>
      </div>

      {/* گزارش تحلیلی */}
      {showAnalytics && propAnalytics && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-5">
            <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-5 shadow-md">
              <div className="text-[12px] text-[var(--text-secondary)] font-bold mb-2">📊 کل مراحل</div>
              <div className="text-[28px] font-extrabold text-[var(--text-primary)]">{propAnalytics.summary.total_stages}</div>
            </div>
            <div className="bg-[var(--profit-soft)] border border-[var(--profit-border)] rounded-[22px] p-5 shadow-md">
              <div className="text-[12px] text-[var(--text-secondary)] font-bold mb-2">✅ پاس‌شده</div>
              <div className="text-[28px] font-extrabold text-[var(--profit)]">{propAnalytics.summary.passed_count}</div>
            </div>
            <div className="bg-[var(--loss-soft)] border border-[var(--loss-border)] rounded-[22px] p-5 shadow-md">
              <div className="text-[12px] text-[var(--text-secondary)] font-bold mb-2">❌ فیل‌شده</div>
              <div className="text-[28px] font-extrabold text-[var(--loss)]">{propAnalytics.summary.failed_count}</div>
            </div>
            <div className="bg-[var(--accent-soft)] border border-[var(--border-accent)] rounded-[22px] p-5 shadow-md">
              <div className="text-[12px] text-[var(--text-secondary)] font-bold mb-2">📈 نرخ پاس</div>
              <div className="text-[28px] font-extrabold text-[var(--accent)]">{propAnalytics.summary.pass_rate}٪</div>
            </div>
          </div>

          <PropAnalytics data={propAnalytics} />

          <div className="flex justify-end">
            <button
              onClick={() => setShowAnalytics(false)}
              className="bg-[var(--bg-card)] border-2 border-[var(--border-subtle)] text-[var(--text-secondary)] hover:border-[var(--border-accent)] px-5 py-2.5 rounded-[12px] text-[12px] font-bold transition-all"
            >
              ✕ بستن گزارش
            </button>
          </div>
        </>
      )}

      {/* فرم شرکت */}
      {showFirmForm && (
        <div className="bg-[var(--bg-card)] border-2 border-[var(--accent)] rounded-[22px] p-6 shadow-lg">
          <div className="flex items-center gap-3 mb-6 pb-4 border-b border-[var(--border-subtle)]">
            <div className="w-11 h-11 rounded-[14px] flex items-center justify-center text-xl text-white"
              style={{ background: 'linear-gradient(135deg, var(--accent), var(--accent-strong))' }}>
              🏢
            </div>
            <div>
              <h3 className="text-lg font-extrabold text-[var(--text-primary)]">شرکت پراپ جدید</h3>
              <p className="text-[12px] text-[var(--text-secondary)] mt-0.5">نام شرکت را وارد کنید</p>
            </div>
          </div>
          <div className="mb-5">
            <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">
              نام شرکت <span className="text-[var(--loss)]">*</span>
            </label>
            <input
              type="text"
              value={firmName}
              onChange={(e) => setFirmName(e.target.value)}
              placeholder="مثلاً FTMO"
              className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[12px] px-5 py-3.5 text-[var(--text-primary)] text-sm font-semibold focus:border-[var(--accent)] focus:bg-[var(--bg-card)] focus:outline-none focus:ring-4 focus:ring-[var(--accent-soft)] transition-all"
            />
          </div>
          <div className="flex gap-3 pt-4 border-t border-[var(--border-subtle)]">
            <button
              onClick={handleCreateFirm}
              className="text-white px-7 py-3 rounded-[12px] text-sm font-extrabold"
              style={{ background: 'linear-gradient(135deg, var(--profit), var(--profit-border))' }}
            >
              💾 ذخیره
            </button>
            <button
              onClick={() => setShowFirmForm(false)}
              className="bg-[var(--bg-card)] border-2 border-[var(--border-subtle)] hover:border-[var(--border-accent)] text-[var(--text-secondary)] px-7 py-3 rounded-[12px] text-sm font-bold transition-all"
            >
              ✕ لغو
            </button>
          </div>
        </div>
      )}

      {/* فرم اکانت */}
      {showAccountForm && (
        <div className="bg-[var(--bg-card)] border-2 border-[var(--profit)] rounded-[22px] p-6 shadow-lg">
          <div className="flex items-center gap-3 mb-6 pb-4 border-b border-[var(--border-subtle)]">
            <div className="w-11 h-11 rounded-[14px] flex items-center justify-center text-xl text-white"
              style={{ background: 'linear-gradient(135deg, var(--profit), var(--profit-border))' }}>
              🏦
            </div>
            <div>
              <h3 className="text-lg font-extrabold text-[var(--text-primary)]">اکانت پراپ جدید</h3>
              <p className="text-[12px] text-[var(--text-secondary)] mt-0.5">مشخصات و قوانین مرحله ۱ را وارد کنید</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-5">
            <div>
              <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">شرکت <span className="text-[var(--loss)]">*</span></label>
              <select
                value={selectedFirmId || ''}
                onChange={async (e) => {
                  const firmId = Number(e.target.value);
                  setSelectedFirmId(firmId);
                  // بارگذاری قوانین پیش‌فرض شرکت
                  if (firmId) {
                    try {
                      const res = await getFirmDefaultRules(firmId);
                      const rules = res.data;
                      // stage_1 پیش‌فرض
                      const s1 = rules.find((r: any) => r.stage_type === 'stage_1') || rules[0];
                      if (s1) {
                        const bal = parseFloat(initialBalance) || 10000;
                        setProfitTargetPercent(((s1.profit_target || 0) / bal * 100).toFixed(1));
                        setMaxDailyDdPercent(((s1.max_daily_dd || 0) / bal * 100).toFixed(1));
                        setMaxTotalDdPercent(((s1.max_total_dd || 0) / bal * 100).toFixed(1));
                        if (s1.min_trading_days) setMinTradingDays(String(s1.min_trading_days));
                      }
                    } catch { /* silent */ }
                  }
                }}
                className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[12px] px-4 py-3 text-[var(--text-primary)] text-sm font-bold focus:border-[var(--profit)] focus:bg-[var(--bg-card)] focus:outline-none cursor-pointer"
              >
                <option value="">— انتخاب —</option>
                {firms.map((f) => (
                  <option key={f.id} value={f.id}>{f.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">برچسب <span className="text-[var(--loss)]">*</span></label>
              <input
                type="text"
                value={accountLabel}
                onChange={(e) => setAccountLabel(e.target.value)}
                placeholder="مثلاً Challenge 1"
                className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[12px] px-4 py-3 text-[var(--text-primary)] text-sm font-semibold focus:border-[var(--profit)] focus:bg-[var(--bg-card)] focus:outline-none"
              />
            </div>
            <div>
              <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">شماره اکانت</label>
              <input
                type="text"
                value={accountNumber}
                onChange={(e) => setAccountNumber(e.target.value)}
                placeholder="اختیاری"
                className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[12px] px-4 py-3 text-[var(--text-primary)] text-sm font-semibold focus:border-[var(--profit)] focus:bg-[var(--bg-card)] focus:outline-none"
              />
            </div>
          </div>

                    <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-5">
            <div>
              <label className="text-[12px] text-[var(--text-secondary)] font-bold block mb-1.5">موجودی اولیه (USDT )</label>
              <input type="number" value={initialBalance} onChange={(e) => setInitialBalance(e.target.value)}
                className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[10px] px-3 py-2.5 text-[var(--text-primary)] text-sm font-bold focus:border-[var(--profit)] focus:outline-none" />
            </div>
            <div>
              <label className="text-[12px] text-[var(--text-secondary)] font-bold block mb-1.5">هدف سود (%)</label>
              <input type="number" step="0.1" value={profitTargetPercent} onChange={(e) => setProfitTargetPercent(e.target.value)}
                className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[10px] px-3 py-2.5 text-[var(--text-primary)] text-sm font-bold focus:border-[var(--profit)] focus:outline-none" />
              <div className="text-[10px] text-[var(--profit)] font-bold mt-1">
                = {((parseFloat(profitTargetPercent) || 0) / 100 * (parseFloat(initialBalance) || 0)).toFixed(0)} USDT
              </div>
            </div>
            <div>
              <label className="text-[12px] text-[var(--text-secondary)] font-bold block mb-1.5">DD روزانه (%)</label>
              <input type="number" step="0.1" value={maxDailyDdPercent} onChange={(e) => setMaxDailyDdPercent(e.target.value)}
                className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[10px] px-3 py-2.5 text-[var(--text-primary)] text-sm font-bold focus:border-[var(--profit)] focus:outline-none" />
              <div className="text-[10px] text-[var(--loss)] font-bold mt-1">
                = {((parseFloat(maxDailyDdPercent) || 0) / 100 * (parseFloat(initialBalance) || 0)).toFixed(0)} USDT
              </div>
            </div>
            <div>
              <label className="text-[12px] text-[var(--text-secondary)] font-bold block mb-1.5">DD کلی (%)</label>
              <input type="number" step="0.1" value={maxTotalDdPercent} onChange={(e) => setMaxTotalDdPercent(e.target.value)}
                className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[10px] px-3 py-2.5 text-[var(--text-primary)] text-sm font-bold focus:border-[var(--profit)] focus:outline-none" />
              <div className="text-[10px] text-[var(--loss)] font-bold mt-1">
                = {((parseFloat(maxTotalDdPercent) || 0) / 100 * (parseFloat(initialBalance) || 0)).toFixed(0)} USDT
              </div>
            </div>
            <div>
              <label className="text-[12px] text-[var(--text-secondary)] font-bold block mb-1.5">حداقل روزها</label>
              <input type="number" value={minTradingDays} onChange={(e) => setMinTradingDays(e.target.value)}
                className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[10px] px-3 py-2.5 text-[var(--text-primary)] text-sm font-bold focus:border-[var(--profit)] focus:outline-none" />
            </div>
          </div>

          {/* فاز ۳۸.۵: checkbox «ساخت خودکار حساب مالی» حذف شد
              (بک‌اند از فاز ۲۸ این فیلد را نمی‌پذیرد و پل پراپ↔مالی حذف شده است) */}

          <div className="flex gap-3 pt-4 border-t border-[var(--border-subtle)]">
            <button onClick={handleCreateAccount}
              className="text-white px-7 py-3 rounded-[12px] text-sm font-extrabold"
              style={{ background: 'linear-gradient(135deg, var(--profit), var(--profit-border))' }}>
              💾 ذخیره اکانت
            </button>
            <button onClick={() => setShowAccountForm(false)}
              className="bg-[var(--bg-card)] border-2 border-[var(--border-subtle)] hover:border-[var(--border-accent)] text-[var(--text-secondary)] px-7 py-3 rounded-[12px] text-sm font-bold transition-all">
              ✕ لغو
            </button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* شرکت‌ها */}
        <div className="lg:col-span-1">
          <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-6 shadow-md">
            <div className="flex items-center gap-3 mb-5 pb-4 border-b border-[var(--border-subtle)]">
              <div className="w-11 h-11 rounded-[14px] bg-[var(--accent-soft)] flex items-center justify-center text-xl">🏢</div>
              <div>
                <h3 className="text-base font-extrabold text-[var(--text-primary)]">شرکت‌های پراپ</h3>
                <p className="text-[12px] text-[var(--text-secondary)] mt-0.5">{firms.length} شرکت</p>
              </div>
            </div>

            {firms.length === 0 ? (
              <div className="text-[var(--text-muted)] text-sm text-center py-8">شرکتی وجود ندارد</div>
            ) : (
              <div className="space-y-2">
                {firms.map((firm) => {
                  const firmAccounts = accounts.filter((a) => a.firm_id === firm.id);
                  const isExpanded = expandedFirms.includes(firm.id);

                  return (
                    <div key={firm.id}>
                      <button
                        onClick={() => toggleFirm(firm.id)}
                        className={`w-full text-right p-3.5 rounded-[14px] border-2 transition-all flex justify-between items-center ${
                          isExpanded ? 'bg-[var(--accent-soft)] border-[var(--accent)]' : 'bg-[var(--bg-card)] border-[var(--border-subtle)] hover:border-[var(--border-accent)]'
                        }`}
                      >
                        <span className="text-[15px] font-extrabold text-[var(--text-primary)]">🏢 {firm.name}</span>
                        <span className="text-[11px] text-[var(--text-secondary)] font-bold">
                          {firmAccounts.length} اکانت {isExpanded ? '▼' : '◀'}
                        </span>
                      </button>

                      {isExpanded && (
                        <div className="mt-2 mr-3 space-y-1.5">
                          {firmAccounts.length === 0 ? (
                            <div className="text-[var(--text-muted)] text-[12px] py-3 text-center bg-[var(--bg-input)] rounded-[10px]">
                              اکانتی ندارد
                            </div>
                          ) : (
                            firmAccounts.map((acc) => {
                              const isSelected = selectedAccount?.id === acc.id;
                              return (
                                <button
                                  key={acc.id}
                                  onClick={() => handleSelectAccount(acc)}
                                  className={`w-full text-right p-3 rounded-[12px] transition-all ${
                                    isSelected
                                      ? 'bg-[var(--accent)] text-white shadow-[0_4px_12px_rgba(63,124,255,0.3)]'
                                      : 'bg-[var(--bg-input)] border border-[var(--border-subtle)] hover:border-[var(--border-accent)]'
                                  }`}
                                >
                                  <div className={`text-[13px] font-bold ${isSelected ? 'text-white' : 'text-[var(--text-primary)]'}`}>
                                    📁 {acc.account_label}
                                  </div>
                                  <div className={`text-[11px] mt-1 ${isSelected ? 'text-white/80' : 'text-[var(--text-secondary)]'}`}>
                                    {acc.stages_count} مرحله
                                  </div>
                                </button>
                              );
                            })
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* جزئیات */}
        <div className="lg:col-span-2">
          {accountDetail ? (
            <div>
              <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-6 shadow-md">
              <div className="flex items-center gap-3 mb-5 pb-4 border-b border-[var(--border-subtle)]">
                <div className="w-11 h-11 rounded-[14px] flex items-center justify-center text-xl text-white"
                  style={{ background: 'linear-gradient(135deg, var(--accent), var(--accent-strong))' }}>🔍</div>
                <div>
                  <h3 className="text-base font-extrabold text-[var(--text-primary)]">
                    {accountDetail.account_label} — {accountDetail.firm_name}
                  </h3>
                  <p className="text-[12px] text-[var(--text-secondary)] mt-0.5">{accountDetail.stages.length} مرحله</p>
                </div>
              </div>

              {/* فاز ۳۸.۵: پنل «حساب مالی متناظر» حذف شد — endpoint آن در فاز ۲۸ حذف شده بود
                  و همیشه «حساب مالی متصل نیست» نشان می‌داد (کد مرده). */}

              <div className="space-y-5">
                {accountDetail.stages.map((stage: Stage) => {
                  const stageColor = getStageColor(stage.stage_type);
                  return (
                    <div key={stage.id} className={`rounded-[18px] border-2 p-5 ${stageColor.border} ${stageColor.bg}`}>
                      <div className="flex justify-between items-center mb-5 flex-wrap gap-3">
                        <div className="flex items-center gap-3">
                          <span className="text-xl font-extrabold text-[var(--text-primary)]">{getStageTypeLabel(stage.stage_type)}</span>
                          {getStatusBadge(stage.status)}
                        </div>
                        <div className="flex gap-2 flex-wrap">
  <button
    onClick={() => handleOpenProgressModal(stage)}
    className="bg-[var(--bg-card)] border border-[var(--border-subtle)] text-[var(--text-primary)] hover:border-[var(--profit)] hover:text-[var(--profit)] px-4 py-2 rounded-[10px] text-[12px] font-bold transition-all shadow-sm"
  >
    📊 وضعیت کنونی
  </button>
  <button
    onClick={() => loadStageTrades(stage.id)}
    className="bg-[var(--bg-card)] border border-[var(--border-subtle)] text-[var(--text-primary)] hover:border-[var(--accent)] hover:text-[var(--accent)] px-4 py-2 rounded-[10px] text-[12px] font-bold transition-all shadow-sm"
  >
    📋 معاملات
  </button>
  <button
    onClick={() => startEditStage(stage)}
    className="bg-[var(--bg-card)] border border-[var(--border-subtle)] text-[var(--text-primary)] hover:border-[var(--purple)] hover:text-[var(--purple)] px-4 py-2 rounded-[10px] text-[12px] font-bold transition-all shadow-sm"
  >
    ✏️ ویرایش قوانین
  </button>
  {stage.status === 'active' && stage.stage_type !== 'funded_real' && (
    <>
      <button
        onClick={() => handleOpenPassModal(stage)}
        className="text-white px-4 py-2 rounded-[10px] text-[12px] font-extrabold shadow-[0_4px_12px_rgba(19,174,129,0.3)]"
        style={{ background: 'linear-gradient(135deg, var(--profit), var(--profit-border))' }}
      >
        ✅ بررسی و پاس
      </button>
      <button
        onClick={() => handleOpenFailModal(stage)}
        className="text-white px-4 py-2 rounded-[10px] text-[12px] font-extrabold shadow-[0_4px_12px_rgba(228,93,114,0.3)]"
        style={{ background: 'linear-gradient(135deg, var(--loss), var(--loss-border))' }}
      >
        ❌ فیل
      </button>
    </>
  )}
  {stage.stage_type === 'funded_real' && stage.status !== 'failed' && stage.status !== 'closed' && (
    <>
      <button
        onClick={() => handleWithdraw(stage)}
        className="text-white px-4 py-2 rounded-[10px] text-[12px] font-extrabold shadow-[0_4px_12px_rgba(63,124,255,0.3)]"
        style={{ background: 'linear-gradient(135deg, var(--accent), var(--accent-strong))' }}
      >
        💰 برداشت
      </button>
      <button
        onClick={() => handleOpenFailModal(stage)}
        className="text-white px-4 py-2 rounded-[10px] text-[12px] font-extrabold"
        style={{ background: 'linear-gradient(135deg, var(--loss), var(--loss-border))' }}
      >
        ❌ فیل
      </button>
    </>
  )}
</div>
                      </div>

                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        {stage.initial_balance !== null && (
                          <div className="bg-[var(--bg-card)] rounded-[12px] p-3 border border-white/60">
                            <div className="text-[10px] text-[var(--text-secondary)] font-bold mb-1">موجودی اولیه</div>
                            <div className="text-[16px] font-extrabold text-[var(--text-primary)]">${stage.initial_balance}</div>
                          </div>
                        )}
                        {stage.profit_target !== null && stage.profit_target > 0 && (
                          <div className="bg-[var(--bg-card)] rounded-[12px] p-3 border border-white/60">
                            <div className="text-[10px] text-[var(--text-secondary)] font-bold mb-1">هدف سود</div>
                            <div className="text-[16px] font-extrabold text-[var(--profit)]">${stage.profit_target}</div>
                          </div>
                        )}
                        {stage.max_daily_dd !== null && stage.max_daily_dd > 0 && (
                          <div className="bg-[var(--bg-card)] rounded-[12px] p-3 border border-white/60">
                            <div className="text-[10px] text-[var(--text-secondary)] font-bold mb-1">DD روزانه</div>
                            <div className="text-[16px] font-extrabold text-[var(--loss)]">${stage.max_daily_dd}</div>
                          </div>
                        )}
                        {stage.max_total_dd !== null && stage.max_total_dd > 0 && (
                          <div className="bg-[var(--bg-card)] rounded-[12px] p-3 border border-white/60">
                            <div className="text-[10px] text-[var(--text-secondary)] font-bold mb-1">DD کلی</div>
                            <div className="text-[16px] font-extrabold text-[var(--loss)]">${stage.max_total_dd}</div>
                          </div>
                        )}
                        {stage.stage_type === 'funded_real' && (
                          <>
                            <div className="bg-[var(--bg-card)] rounded-[12px] p-3 border border-white/60">
                              <div className="text-[10px] text-[var(--text-secondary)] font-bold mb-1">سود جاری</div>
                              <div className={`text-[16px] font-extrabold ${stage.current_profit >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
                                ${stage.current_profit?.toFixed(2)}
                              </div>
                            </div>
                            <div className="bg-[var(--bg-card)] rounded-[12px] p-3 border border-white/60">
                              <div className="text-[10px] text-[var(--text-secondary)] font-bold mb-1">کل برداشت</div>
                              <div className="text-[16px] font-extrabold text-[var(--accent)]">${stage.total_withdrawn?.toFixed(2)}</div>
                            </div>
                          </>
                        )}
                      </div>

                      {stage.failure_reason && (
                        <div className="mt-4 bg-[var(--loss-soft)] border border-[var(--loss-border)] text-[var(--loss)] p-3 rounded-[12px] text-[12px] font-bold">
                          ❌ دلیل فیل: {stage.failure_reason}
                          {stage.failure_details && ` — ${stage.failure_details}`}
                        </div>
                      )}

                      {editingStage === stage.id && (
                        <div className="mt-5 bg-[var(--bg-card)] border-2 border-[var(--purple)] rounded-[14px] p-5">
                          <h4 className="text-[14px] font-extrabold text-[var(--text-primary)] mb-4">✏️ ویرایش قوانین مرحله</h4>
                          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-4">
                                                        <div>
                              <label className="text-[11px] text-[var(--text-secondary)] font-bold block mb-1.5">هدف سود (%)</label>
                              <input type="number" step="0.1" value={editRules.profit_target_percent}
                                onChange={(e) => setEditRules({ ...editRules, profit_target_percent: e.target.value })}
                                className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[10px] px-3 py-2 text-[var(--text-primary)] text-sm font-bold focus:border-[var(--purple)] focus:outline-none" />
                              <div className="text-[10px] text-[var(--profit)] font-bold mt-1">
                                = {((parseFloat(editRules.profit_target_percent) || 0) / 100 * (parseFloat(editRules.initial_balance) || 0)).toFixed(0)} USDT
                              </div>
                            </div>
                            <div>
                              <label className="text-[11px] text-[var(--text-secondary)] font-bold block mb-1.5">DD روزانه (%)</label>
                              <input type="number" step="0.1" value={editRules.max_daily_dd_percent}
                                onChange={(e) => setEditRules({ ...editRules, max_daily_dd_percent: e.target.value })}
                                className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[10px] px-3 py-2 text-[var(--text-primary)] text-sm font-bold focus:border-[var(--purple)] focus:outline-none" />
                              <div className="text-[10px] text-[var(--loss)] font-bold mt-1">
                                = {((parseFloat(editRules.max_daily_dd_percent) || 0) / 100 * (parseFloat(editRules.initial_balance) || 0)).toFixed(0)} USDT
                              </div>
                            </div>
                            <div>
                              <label className="text-[11px] text-[var(--text-secondary)] font-bold block mb-1.5">DD کلی (%)</label>
                              <input type="number" step="0.1" value={editRules.max_total_dd_percent}
                                onChange={(e) => setEditRules({ ...editRules, max_total_dd_percent: e.target.value })}
                                className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[10px] px-3 py-2 text-[var(--text-primary)] text-sm font-bold focus:border-[var(--purple)] focus:outline-none" />
                              <div className="text-[10px] text-[var(--loss)] font-bold mt-1">
                                = {((parseFloat(editRules.max_total_dd_percent) || 0) / 100 * (parseFloat(editRules.initial_balance) || 0)).toFixed(0)} USDT
                              </div>
                            </div>
                            <div>
                              <label className="text-[11px] text-[var(--text-secondary)] font-bold block mb-1.5">حداقل روزها</label>
                              <input type="number" value={editRules.min_trading_days}
                                onChange={(e) => setEditRules({ ...editRules, min_trading_days: e.target.value })}
                                className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[10px] px-3 py-2 text-[var(--text-primary)] text-sm font-bold focus:border-[var(--purple)] focus:outline-none" />
                            </div>
                            <div>
                              <label className="text-[11px] text-[var(--text-secondary)] font-bold block mb-1.5">موجودی اولیه (USDT )</label>
                              <input type="number" value={editRules.initial_balance}
                                onChange={(e) => setEditRules({ ...editRules, initial_balance: e.target.value })}
                                className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[10px] px-3 py-2 text-[var(--text-primary)] text-sm font-bold focus:border-[var(--purple)] focus:outline-none" />
                            </div>
                            <div>
                              <label className="text-[11px] text-[var(--text-secondary)] font-bold block mb-1.5">مبنای DD</label>
                              <select value={editRules.dd_basis}
                                onChange={(e) => setEditRules({ ...editRules, dd_basis: e.target.value as 'balance' | 'equity' })}
                                className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[10px] px-3 py-2 text-[var(--text-primary)] text-sm font-bold">
                                <option value="balance">Balance — معاملات بسته</option>
                                <option value="equity">Equity — با سود/زیان شناور</option>
                              </select>
                            </div>
                            <div>
                              <label className="text-[11px] text-[var(--text-secondary)] font-bold block mb-1.5">مدل DD روزانه</label>
                              <select value={editRules.daily_dd_mode}
                                onChange={(e) => setEditRules({ ...editRules, daily_dd_mode: e.target.value as 'static' | 'trailing' })}
                                className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[10px] px-3 py-2 text-[var(--text-primary)] text-sm font-bold">
                                <option value="static">Static — خالص زیان روز</option>
                                <option value="trailing">Trailing — افت از سقف روز</option>
                              </select>
                            </div>
                            <div>
                              <label className="text-[11px] text-[var(--text-secondary)] font-bold block mb-1.5">مدل DD کلی</label>
                              <select value={editRules.total_dd_mode}
                                onChange={(e) => setEditRules({ ...editRules, total_dd_mode: e.target.value as 'static' | 'trailing' })}
                                className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[10px] px-3 py-2 text-[var(--text-primary)] text-sm font-bold">
                                <option value="static">Static — از موجودی اولیه</option>
                                <option value="trailing">Trailing — از سقف حساب</option>
                              </select>
                            </div>
                            {stage.stage_type === 'funded_real' && (
                              <div>
                                <label className="text-[11px] text-[var(--text-secondary)] font-bold block mb-1.5">درصد سهم کاربر</label>
                                <input type="number" value={editRules.profit_share_percentage}
                                  onChange={(e) => setEditRules({ ...editRules, profit_share_percentage: e.target.value })}
                                  className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[10px] px-3 py-2 text-[var(--text-primary)] text-sm font-bold focus:border-[var(--purple)] focus:outline-none" />
                              </div>
                            )}
                          </div>
                          <div className="flex gap-2">
                            <button onClick={() => handleSaveStageRules(stage.id)}
                              className="text-white px-5 py-2.5 rounded-[10px] text-[12px] font-extrabold"
                              style={{ background: 'linear-gradient(135deg, var(--profit), var(--profit-border))' }}>
                              💾 ذخیره
                            </button>
                            <button onClick={cancelEditStage}
                              className="bg-[var(--bg-card)] border-2 border-[var(--border-subtle)] text-[var(--text-secondary)] px-5 py-2.5 rounded-[10px] text-[12px] font-bold">
                              ✕ لغو
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
<div className="mt-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <span className="text-base">🔔</span>
                    <h3 className="text-base font-extrabold text-[var(--text-primary)]">هشدارها</h3>
                    {alerts.filter(a => !a.is_read).length > 0 && (
                      <span className="bg-[var(--loss)] text-white text-[10px] font-bold px-2 py-0.5 rounded-full">
                        {alerts.filter(a => !a.is_read).length}
                      </span>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => { loadAlerts(); setShowAlerts(true); }}
                      className="bg-[var(--accent-soft)] text-[var(--accent)] hover:bg-[var(--accent)] hover:text-white px-4 py-2 rounded-[10px] text-[12px] font-bold transition-all"
                    >
                      🔄 بارگذاری
                    </button>
                    <button
                      onClick={async () => {
                        try {
                          await generatePropAlerts();
                          await loadAlerts();
                        } catch { /* silent */ }
                      }}
                      className="bg-[var(--warning-soft-alt)] text-[var(--warning)] hover:bg-[var(--warning)] hover:text-white px-4 py-2 rounded-[10px] text-[12px] font-bold transition-all"
                    >
                      ⚡ بررسی خودکار
                    </button>
                  </div>
                </div>

                {alertLoading && (
                  <div className="text-[var(--text-muted)] text-xs text-center py-4 animate-pulse">⏳ در حال بررسی...</div>
                )}

                {!alertLoading && showAlerts && alerts.length === 0 && (
                  <div className="text-[var(--text-muted)] text-xs text-center py-6">✅ هیچ هشدار فعالی وجود ندارد</div>
                )}

                {!alertLoading && showAlerts && alerts.length > 0 && (
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {alerts.map((alert) => {
                      const isWarning = alert.message.includes('⚠️');
                      const isDanger = alert.message.includes('🚨');
                      const isSuccess = alert.message.includes('🎯');
                      const bgColor = isDanger ? 'bg-[var(--loss-soft)]' : isWarning ? 'bg-[var(--warning-soft-alt)]' : isSuccess ? 'bg-[var(--profit-soft)]' : 'bg-[var(--bg-input)]';
                      const borderColor = isDanger ? 'border-[var(--loss-border)]' : isWarning ? 'border-[var(--warning-border)]' : isSuccess ? 'border-[var(--profit-border)]' : 'border-[var(--border-subtle)]';
                      return (
                        <div key={alert.id} className={`${bgColor} border ${borderColor} rounded-[12px] px-4 py-3 flex items-center justify-between`}>
                          <span className={`text-[12px] font-medium ${isDanger ? 'text-[var(--loss)]' : isWarning ? 'text-[var(--warning)]' : isSuccess ? 'text-[var(--profit)]' : 'text-[var(--text-secondary)]'}`}>
                            {alert.message}
                          </span>
                          <button
                            onClick={async () => {
                              try {
                                await markAlertRead(alert.id);
                                await loadAlerts();
                              } catch { /* silent */ }
                            }}
                            className={`text-[11px] px-3 py-1 rounded-full font-bold transition-all ${alert.is_read ? 'bg-[var(--border-subtle)] text-[var(--text-secondary)]' : 'bg-[var(--bg-card)] text-[var(--accent)] hover:bg-[var(--accent-soft)]'}`}
                          >
                            {alert.is_read ? '✓ خوانده‌شده' : '✓ علامت'}
                          </button>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-12 shadow-md text-center">
              <div className="text-6xl mb-4">🏢</div>
              <div className="text-[15px] font-bold text-[var(--text-primary)]">یک اکانت را از لیست انتخاب کنید</div>
              <div className="text-[12px] text-[var(--text-muted)] mt-2">تا جزئیات مراحل آن را ببینید</div>
            </div>
          )}
        </div>
      </div>

      {/* مودال معاملات مرحله */}
      {selectedStage && stageTrades.length > 0 && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-[var(--bg-card)] rounded-[22px] max-w-4xl w-full max-h-[85vh] overflow-hidden shadow-2xl">
            <div className="flex justify-between items-center p-6 border-b border-[var(--border-subtle)]">
              <div className="flex items-center gap-3">
                <div className="w-11 h-11 rounded-[14px] bg-[var(--accent-soft)] flex items-center justify-center text-xl">📋</div>
                <div>
                  <h3 className="text-base font-extrabold text-[var(--text-primary)]">معاملات مرحله</h3>
                  <p className="text-[12px] text-[var(--text-secondary)] mt-0.5">{stageTrades.length} معامله</p>
                </div>
              </div>
              <button onClick={() => { setSelectedStage(null); setStageTrades([]); }}
                className="text-[var(--text-secondary)] hover:text-[var(--loss)] text-xl font-bold w-9 h-9 rounded-lg hover:bg-[var(--loss-soft)] transition-all">✕</button>
            </div>

            <div className="overflow-y-auto max-h-[calc(85vh-100px)] p-6">
              <div className="overflow-x-auto rounded-[14px] border border-[var(--border-subtle)]">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-[var(--bg-elevated)]">
                      <th className="text-right px-4 py-3.5 text-[11px] text-[var(--text-secondary)] font-extrabold rounded-r-[14px]">#</th>
                      <th className="text-right px-4 py-3.5 text-[11px] text-[var(--text-secondary)] font-extrabold">نماد</th>
                      <th className="text-right px-4 py-3.5 text-[11px] text-[var(--text-secondary)] font-extrabold">جهت</th>
                      <th className="text-right px-4 py-3.5 text-[11px] text-[var(--text-secondary)] font-extrabold">حجم</th>
                      <th className="text-right px-4 py-3.5 text-[11px] text-[var(--text-secondary)] font-extrabold">سود/زیان</th>
                      <th className="text-right px-4 py-3.5 text-[11px] text-[var(--text-secondary)] font-extrabold rounded-l-[14px]">تاریخ</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stageTrades.map((t, idx) => (
                      <tr key={t.id} className="border-b border-[var(--border-subtle)] hover:bg-[var(--bg-input)] transition-colors">
                        <td className="px-4 py-3 text-[var(--text-secondary)] text-[12px] font-semibold">{idx + 1}</td>
                        <td className="px-4 py-3 font-extrabold text-[var(--text-primary)] text-[13px]">{t.symbol}</td>
                        <td className={`px-4 py-3 font-bold text-[13px] ${t.direction === 'buy' ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
                          {t.direction === 'buy' ? 'خرید' : 'فروش'}
                        </td>
                        <td className="px-4 py-3 text-[var(--text-primary)] font-semibold text-[13px]">{t.size}</td>
                        <td className={`px-4 py-3 font-extrabold text-[13px] ${t.pnl >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
                          {t.pnl >= 0 ? '+' : ''}{t.pnl?.toFixed(2)} USDT
                        </td>
                        <td className="px-4 py-3 text-[var(--text-secondary)] text-[12px] font-medium">
                          {t.close_time ? new Date(t.close_time).toLocaleDateString('fa-IR') : '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* مودال Pass */}
      {showPassModal && passingStage && passProgress && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-[var(--bg-card)] rounded-[22px] max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl">
            <div className="flex justify-between items-center p-6 border-b border-[var(--border-subtle)]">
              <div className="flex items-center gap-3">
                <div className="w-11 h-11 rounded-[14px] flex items-center justify-center text-xl text-white"
                  style={{ background: 'linear-gradient(135deg, var(--profit), var(--profit-border))' }}>✅</div>
                <div>
                  <h3 className="text-base font-extrabold text-[var(--text-primary)]">
                    بررسی و پاس مرحله {passingStage.stage_type === 'stage_1' ? 'اول' : 'دوم'}
                  </h3>
                  <p className="text-[12px] text-[var(--text-secondary)] mt-0.5">اطلاعات پیشرفت و قوانین مرحله‌ی بعدی</p>
                </div>
              </div>
              <button onClick={() => setShowPassModal(false)} className="text-[var(--text-secondary)] text-xl w-9 h-9 rounded-lg hover:bg-[var(--bg-elevated)]">✕</button>
            </div>
            <div className="p-6 space-y-4">
              {modalError && (
                <div className="bg-[var(--loss-soft)] border-2 border-[var(--loss-border)] text-[var(--loss)] p-4 rounded-[14px] text-[14px] font-bold">
                  ❌ {modalError}
                </div>
              )}

              <div className={`rounded-[14px] p-4 border-2 ${
                passProgress.suggested_status === 'ready_to_pass'
                  ? 'bg-[var(--profit-soft)] border-[var(--profit-border)]'
                  : passProgress.suggested_status === 'failed_daily_dd' || passProgress.suggested_status === 'failed_total_dd'
                  ? 'bg-[var(--loss-soft)] border-[var(--loss-border)]'
                  : 'bg-[var(--accent-soft)] border-[var(--border-accent)]'
              }`}>
                <div className="font-extrabold text-[15px] text-[var(--text-primary)] mb-1">
                  {passProgress.suggested_status === 'ready_to_pass' && '✅ آماده‌ی پاس کردن'}
                  {passProgress.suggested_status === 'failed_daily_dd' && '❌ DD روزانه نقض شده'}
                  {passProgress.suggested_status === 'failed_total_dd' && '❌ DD کلی نقض شده'}
                  {passProgress.suggested_status === 'in_progress' && '⏳ در حال پیشرفت'}
                </div>
                <div className="text-[12px] text-[var(--text-secondary)] font-semibold">
                  {passProgress.total_trades} معامله | سود فعلی: {passProgress.current_profit} USDT
                </div>
              </div>

              <div className="space-y-3">
                <div className="bg-[var(--bg-input)] border border-[var(--border-subtle)] rounded-[14px] p-4">
                  <div className="flex justify-between mb-2">
                    <span className="text-[13px] text-[var(--text-primary)] font-bold">🎯 هدف سود</span>
                    <span className={`font-extrabold text-[14px] ${passProgress.target_reached ? 'text-[var(--profit)]' : 'text-[var(--text-primary)]'}`}>
                      {passProgress.current_profit} USDT  / {passProgress.profit_target} USDT
                    </span>
                  </div>
                  <div className="h-2 bg-[var(--bg-card)] rounded-full overflow-hidden">
                    <div className={`h-full rounded-full ${passProgress.target_reached ? 'bg-gradient-to-r from-[var(--profit)] to-[var(--profit-border)]' : 'bg-gradient-to-r from-[var(--accent)] to-[var(--accent-strong)]'}`}
                      style={{ width: `${Math.min(passProgress.profit_progress_percent, 100)}%` }} />
                  </div>
                </div>

                <div className="bg-[var(--bg-input)] border border-[var(--border-subtle)] rounded-[14px] p-4">
                  <div className="flex justify-between mb-2">
                    <span className="text-[13px] text-[var(--text-primary)] font-bold">⚠️ DD روزانه</span>
                    <span className={`font-extrabold text-[14px] ${passProgress.daily_dd_violated ? 'text-[var(--loss)]' : 'text-[var(--text-primary)]'}`}>
                      {passProgress.max_daily_loss} USDT  / {passProgress.max_daily_dd_limit} USDT
                    </span>
                  </div>
                  <div className="h-2 bg-[var(--bg-card)] rounded-full overflow-hidden">
                    <div className={`h-full rounded-full ${passProgress.daily_dd_violated ? 'bg-gradient-to-r from-[var(--loss)] to-[var(--loss-border)]' : 'bg-gradient-to-r from-[var(--accent)] to-[var(--accent-strong)]'}`}
                      style={{ width: `${Math.min(passProgress.daily_dd_progress_percent, 100)}%` }} />
                  </div>
                </div>

                <div className="bg-[var(--bg-input)] border border-[var(--border-subtle)] rounded-[14px] p-4">
                  <div className="flex justify-between mb-2">
                    <span className="text-[13px] text-[var(--text-primary)] font-bold">📉 DD کلی</span>
                    <span className={`font-extrabold text-[14px] ${passProgress.total_dd_violated ? 'text-[var(--loss)]' : 'text-[var(--text-primary)]'}`}>
                      {passProgress.max_total_dd} USDT  / {passProgress.max_total_dd_limit} USDT
                    </span>
                  </div>
                  <div className="h-2 bg-[var(--bg-card)] rounded-full overflow-hidden">
                    <div className={`h-full rounded-full ${passProgress.total_dd_violated ? 'bg-gradient-to-r from-[var(--loss)] to-[var(--loss-border)]' : 'bg-gradient-to-r from-[var(--accent)] to-[var(--accent-strong)]'}`}
                      style={{ width: `${Math.min(passProgress.total_dd_progress_percent, 100)}%` }} />
                  </div>
                </div>

                <div className="bg-[var(--bg-input)] border border-[var(--border-subtle)] rounded-[14px] p-4 flex justify-between items-center">
                  <span className="text-[13px] text-[var(--text-primary)] font-bold">📅 روزهای معاملاتی</span>
                  <span className={`font-extrabold text-[15px] ${passProgress.days_met ? 'text-[var(--profit)]' : 'text-[var(--text-primary)]'}`}>
                    {passProgress.trading_days} / {passProgress.min_trading_days}
                  </span>
                </div>
              </div>

              {passProgress.suggested_status !== 'failed_daily_dd' && passProgress.suggested_status !== 'failed_total_dd' && (
                <div className="pt-4 border-t border-[var(--border-subtle)]">
                  <h4 className="text-[14px] font-extrabold text-[var(--text-primary)] mb-4">⚙️ قوانین مرحله‌ی بعدی</h4>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
  <label className="text-[11px] text-[var(--text-secondary)] font-bold block mb-1.5">هدف سود (%)</label>
  <input type="number" step="0.1" value={nextStageRules.profit_target_percent}
    onChange={(e) => setNextStageRules({ ...nextStageRules, profit_target_percent: e.target.value })}
    className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[10px] px-3 py-2.5 text-[var(--text-primary)] text-sm font-bold focus:border-[var(--profit)] focus:outline-none" />
  <div className="text-[10px] text-[var(--profit)] font-bold mt-1">
    = {((parseFloat(nextStageRules.profit_target_percent) || 0) / 100 * (parseFloat(nextStageRules.initial_balance) || 0)).toFixed(0)} USDT
  </div>
</div>
<div>
  <label className="text-[11px] text-[var(--text-secondary)] font-bold block mb-1.5">DD روزانه (%)</label>
  <input type="number" step="0.1" value={nextStageRules.max_daily_dd_percent}
    onChange={(e) => setNextStageRules({ ...nextStageRules, max_daily_dd_percent: e.target.value })}
    className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[10px] px-3 py-2.5 text-[var(--text-primary)] text-sm font-bold focus:border-[var(--profit)] focus:outline-none" />
  <div className="text-[10px] text-[var(--loss)] font-bold mt-1">
    = {((parseFloat(nextStageRules.max_daily_dd_percent) || 0) / 100 * (parseFloat(nextStageRules.initial_balance) || 0)).toFixed(0)} USDT
  </div>
</div>
<div>
  <label className="text-[11px] text-[var(--text-secondary)] font-bold block mb-1.5">DD کلی (%)</label>
  <input type="number" step="0.1" value={nextStageRules.max_total_dd_percent}
    onChange={(e) => setNextStageRules({ ...nextStageRules, max_total_dd_percent: e.target.value })}
    className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[10px] px-3 py-2.5 text-[var(--text-primary)] text-sm font-bold focus:border-[var(--profit)] focus:outline-none" />
  <div className="text-[10px] text-[var(--loss)] font-bold mt-1">
    = {((parseFloat(nextStageRules.max_total_dd_percent) || 0) / 100 * (parseFloat(nextStageRules.initial_balance) || 0)).toFixed(0)} USDT
  </div>
</div>
                    <div>
                      <label className="text-[11px] text-[var(--text-secondary)] font-bold block mb-1.5">حداقل روزها</label>
                      <input type="number" value={nextStageRules.min_trading_days}
                        onChange={(e) => setNextStageRules({ ...nextStageRules, min_trading_days: e.target.value })}
                        className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[10px] px-3 py-2.5 text-[var(--text-primary)] text-sm font-bold focus:border-[var(--profit)] focus:outline-none" />
                    </div>
                    <div>
                      <label className="text-[11px] text-[var(--text-secondary)] font-bold block mb-1.5">موجودی اولیه (USDT )</label>
                      <input type="number" value={nextStageRules.initial_balance}
                        onChange={(e) => setNextStageRules({ ...nextStageRules, initial_balance: e.target.value })}
                        className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[10px] px-3 py-2.5 text-[var(--text-primary)] text-sm font-bold focus:border-[var(--profit)] focus:outline-none" />
                    </div>
                    <div>
                      <label className="text-[11px] text-[var(--text-secondary)] font-bold block mb-1.5">مبنای DD</label>
                      <select value={nextStageRules.dd_basis}
                        onChange={(e) => setNextStageRules({ ...nextStageRules, dd_basis: e.target.value as 'balance' | 'equity' })}
                        className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[10px] px-3 py-2.5 text-[var(--text-primary)] text-sm font-bold">
                        <option value="balance">Balance — معاملات بسته</option>
                        <option value="equity">Equity — با شناور</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-[11px] text-[var(--text-secondary)] font-bold block mb-1.5">مدل DD روزانه</label>
                      <select value={nextStageRules.daily_dd_mode}
                        onChange={(e) => setNextStageRules({ ...nextStageRules, daily_dd_mode: e.target.value as 'static' | 'trailing' })}
                        className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[10px] px-3 py-2.5 text-[var(--text-primary)] text-sm font-bold">
                        <option value="static">Static</option>
                        <option value="trailing">Trailing</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-[11px] text-[var(--text-secondary)] font-bold block mb-1.5">مدل DD کلی</label>
                      <select value={nextStageRules.total_dd_mode}
                        onChange={(e) => setNextStageRules({ ...nextStageRules, total_dd_mode: e.target.value as 'static' | 'trailing' })}
                        className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[10px] px-3 py-2.5 text-[var(--text-primary)] text-sm font-bold">
                        <option value="static">Static</option>
                        <option value="trailing">Trailing</option>
                      </select>
                    </div>
                    {passingStage.stage_type === 'stage_2' && (
                      <div>
                        <label className="text-[11px] text-[var(--text-secondary)] font-bold block mb-1.5">درصد سهم کاربر</label>
                        <input type="number" value={nextStageRules.profit_share_percentage}
                          onChange={(e) => setNextStageRules({ ...nextStageRules, profit_share_percentage: e.target.value })}
                          className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[10px] px-3 py-2.5 text-[var(--text-primary)] text-sm font-bold focus:border-[var(--profit)] focus:outline-none" />
                      </div>
                    )}
                  </div>
                </div>
              )}

              <div className="flex gap-3 pt-4 border-t border-[var(--border-subtle)]">
                <button onClick={handleConfirmPass}
                  disabled={!passProgress.ready_to_pass}
                  className="flex-1 text-white py-3 rounded-[12px] font-extrabold text-sm shadow-[0_6px_16px_rgba(19,174,129,0.3)] disabled:opacity-40 disabled:cursor-not-allowed"
                  style={{ background: 'linear-gradient(135deg, var(--profit), var(--profit-border))' }}>
                  ✅ تأیید و پاس
                </button>
                <button onClick={() => setShowPassModal(false)}
                  className="bg-[var(--bg-card)] border-2 border-[var(--border-subtle)] text-[var(--text-secondary)] px-7 py-3 rounded-[12px] font-bold text-sm hover:border-[var(--border-accent)]">
                  ✕ لغو
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* مودال Fail */}
      {showFailModal && failingStage && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-[var(--bg-card)] rounded-[22px] max-w-md w-full shadow-2xl">
            <div className="flex justify-between items-center p-6 border-b border-[var(--border-subtle)]">
              <div className="flex items-center gap-3">
                <div className="w-11 h-11 rounded-[14px] flex items-center justify-center text-xl text-white"
                  style={{ background: 'linear-gradient(135deg, var(--loss), var(--loss-border))' }}>❌</div>
                <div>
                  <h3 className="text-base font-extrabold text-[var(--text-primary)]">فیل کردن مرحله</h3>
                  <p className="text-[12px] text-[var(--text-secondary)] mt-0.5">دلیل را انتخاب کنید</p>
                </div>
              </div>
              <button onClick={() => setShowFailModal(false)} className="text-[var(--text-secondary)] text-xl">✕</button>
            </div>

            <div className="p-6 space-y-4">
              <div>
                <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">دلیل فیل شدن</label>
                <select
                  value={failReason}
                  onChange={(e) => setFailReason(e.target.value)}
                  className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[12px] px-4 py-3 text-[var(--text-primary)] text-sm font-bold focus:border-[var(--loss)] focus:outline-none cursor-pointer"
                >
                  <option value="max_daily_dd_exceeded">نقض DD روزانه</option>
                  <option value="max_total_dd_exceeded">نقض DD کلی</option>
                  <option value="profit_target_not_met">عدم رسیدن به هدف سود</option>
                  <option value="min_trading_days_not_met">کمبود روزهای معاملاتی</option>
                  <option value="rule_violation">نقض قانون</option>
                  <option value="manual">فیل دستی</option>
                  <option value="other">سایر</option>
                </select>
              </div>

              <div>
                <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">توضیحات (اختیاری)</label>
                <textarea
                  value={failDetails}
                  onChange={(e) => setFailDetails(e.target.value)}
                  placeholder="توضیحات بیشتر..."
                  rows={3}
                  className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[12px] px-4 py-3 text-[var(--text-primary)] text-sm font-medium focus:border-[var(--loss)] focus:outline-none resize-none"
                />
              </div>

              <div className="flex gap-3 pt-4 border-t border-[var(--border-subtle)]">
                <button onClick={handleConfirmFail}
                  className="flex-1 text-white py-3 rounded-[12px] font-extrabold text-sm"
                  style={{ background: 'linear-gradient(135deg, var(--loss), var(--loss-border))' }}>
                  ❌ تأیید فیل
                </button>
                <button onClick={() => setShowFailModal(false)}
                  className="bg-[var(--bg-card)] border-2 border-[var(--border-subtle)] text-[var(--text-secondary)] px-6 py-3 rounded-[12px] font-bold text-sm">
                  ✕ لغو
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
            {/* ═════════════════════════════════════════════
          مودال وضعیت کنونی
      ═════════════════════════════════════════════ */}
      {showProgressModal && progressStage && stageProgressData && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-[var(--bg-card)] rounded-[22px] max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl">
            <div className="flex justify-between items-center p-6 border-b border-[var(--border-subtle)]">
              <div className="flex items-center gap-3">
                <div className="w-11 h-11 rounded-[14px] flex items-center justify-center text-xl text-white"
                  style={{ background: 'linear-gradient(135deg, var(--profit), var(--profit-border))' }}>
                  📊
                </div>
                <div>
                  <h3 className="text-base font-extrabold text-[var(--text-primary)]">
                    وضعیت کنونی {getStageTypeLabel(progressStage.stage_type)}
                  </h3>
                  <p className="text-[12px] text-[var(--text-secondary)] mt-0.5">
                    {stageProgressData.total_trades} معامله ثبت‌شده
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowProgressModal(false)}
                className="text-[var(--text-secondary)] text-xl w-9 h-9 rounded-lg hover:bg-[var(--bg-elevated)]"
              >
                ✕
              </button>
            </div>

            <div className="p-6 space-y-4">
              {/* وضعیت */}
              <div className={`rounded-[14px] p-4 border-2 ${
                progressStage.status === 'passed'
                  ? 'bg-[var(--profit-soft)] border-[var(--profit-border)]'
                  : progressStage.status === 'failed'
                  ? 'bg-[var(--loss-soft)] border-[var(--loss-border)]'
                  : stageProgressData.suggested_status === 'ready_to_pass'
                  ? 'bg-[var(--profit-soft)] border-[var(--profit-border)]'
                  : 'bg-[var(--accent-soft)] border-[var(--border-accent)]'
              }`}>
                <div className="font-extrabold text-[15px] text-[var(--text-primary)] mb-1">
                  {progressStage.status === 'passed' && '✅ این مرحله پاس شده است'}
                  {progressStage.status === 'failed' && '❌ این مرحله فیل شده است'}
                  {progressStage.status === 'active' && stageProgressData.suggested_status === 'ready_to_pass' && '✅ آماده‌ی پاس کردن'}
                  {progressStage.status === 'active' && stageProgressData.suggested_status === 'in_progress' && '⏳ در حال پیشرفت'}
                  {progressStage.status === 'active' && stageProgressData.suggested_status === 'failed_daily_dd' && '❌ DD روزانه نقض شده'}
                  {progressStage.status === 'active' && stageProgressData.suggested_status === 'failed_total_dd' && '❌ DD کلی نقض شده'}
                </div>
                <div className="text-[12px] text-[var(--text-secondary)] font-semibold">
                  سود فعلی: <span className="text-[var(--profit)] font-extrabold">{stageProgressData.current_profit} USDT </span>
                </div>
              </div>

              {/* هدف سود */}
              <div className="bg-[var(--bg-input)] border border-[var(--border-subtle)] rounded-[14px] p-4">
                <div className="flex justify-between mb-2">
                  <span className="text-[13px] text-[var(--text-primary)] font-bold">🎯 هدف سود</span>
                  <span className={`font-extrabold text-[14px] ${stageProgressData.target_reached ? 'text-[var(--profit)]' : 'text-[var(--text-primary)]'}`}>
                    {stageProgressData.current_profit} USDT  / {stageProgressData.profit_target} USDT
                  </span>
                </div>
                <div className="h-2 bg-[var(--bg-card)] rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${stageProgressData.target_reached ? 'bg-gradient-to-r from-[var(--profit)] to-[var(--profit-border)]' : 'bg-gradient-to-r from-[var(--accent)] to-[var(--accent-strong)]'}`}
                    style={{ width: `${Math.min(stageProgressData.profit_progress_percent, 100)}%` }}
                  />
                </div>
              </div>

              {/* DD روزانه */}
              <div className="bg-[var(--bg-input)] border border-[var(--border-subtle)] rounded-[14px] p-4">
                <div className="flex justify-between mb-2">
                  <span className="text-[13px] text-[var(--text-primary)] font-bold">⚠️ DD روزانه</span>
                  <span className={`font-extrabold text-[14px] ${stageProgressData.daily_dd_violated ? 'text-[var(--loss)]' : 'text-[var(--text-primary)]'}`}>
                    {stageProgressData.max_daily_loss} USDT  / {stageProgressData.max_daily_dd_limit} USDT
                  </span>
                </div>
                <div className="h-2 bg-[var(--bg-card)] rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${stageProgressData.daily_dd_violated ? 'bg-gradient-to-r from-[var(--loss)] to-[var(--loss-border)]' : 'bg-gradient-to-r from-[var(--accent)] to-[var(--accent-strong)]'}`}
                    style={{ width: `${Math.min(stageProgressData.daily_dd_progress_percent, 100)}%` }}
                  />
                </div>
              </div>

              {/* DD کلی */}
              <div className="bg-[var(--bg-input)] border border-[var(--border-subtle)] rounded-[14px] p-4">
                <div className="flex justify-between mb-2">
                  <span className="text-[13px] text-[var(--text-primary)] font-bold">📉 DD کلی</span>
                  <span className={`font-extrabold text-[14px] ${stageProgressData.total_dd_violated ? 'text-[var(--loss)]' : 'text-[var(--text-primary)]'}`}>
                    {stageProgressData.max_total_dd} USDT  / {stageProgressData.max_total_dd_limit} USDT
                  </span>
                </div>
                <div className="h-2 bg-[var(--bg-card)] rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${stageProgressData.total_dd_violated ? 'bg-gradient-to-r from-[var(--loss)] to-[var(--loss-border)]' : 'bg-gradient-to-r from-[var(--accent)] to-[var(--accent-strong)]'}`}
                    style={{ width: `${Math.min(stageProgressData.total_dd_progress_percent, 100)}%` }}
                  />
                </div>
              </div>

              {/* روزهای معاملاتی */}
              <div className="bg-[var(--bg-input)] border border-[var(--border-subtle)] rounded-[14px] p-4 flex justify-between items-center">
                <span className="text-[13px] text-[var(--text-primary)] font-bold">📅 روزهای معاملاتی</span>
                <span className={`font-extrabold text-[15px] ${stageProgressData.days_met ? 'text-[var(--profit)]' : 'text-[var(--text-primary)]'}`}>
                  {stageProgressData.trading_days} / {stageProgressData.min_trading_days}
                </span>
              </div>

              {/* دکمه‌ی بستن */}
              <div className="pt-4 border-t border-[var(--border-subtle)]">
                <button
                  onClick={() => setShowProgressModal(false)}
                  className="w-full bg-[var(--bg-card)] border-2 border-[var(--border-subtle)] text-[var(--text-secondary)] hover:border-[var(--border-accent)] py-3 rounded-[12px] font-bold text-sm transition-all"
                >
                  ✕ بستن
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ═════════════════════════════════════════════
          🆕 فاز ۵.۱ — مودال برداشت
      ═════════════════════════════════════════════ */}
      {showWithdrawModal && withdrawingStage && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-[var(--bg-card)] rounded-[22px] max-w-lg w-full max-h-[90vh] overflow-y-auto shadow-2xl">
            <div className="flex justify-between items-center p-6 border-b border-[var(--border-subtle)]">
              <div className="flex items-center gap-3">
                <div className="w-11 h-11 rounded-[14px] flex items-center justify-center text-xl text-white"
                  style={{ background: 'linear-gradient(135deg, var(--accent), var(--accent-strong))' }}>
                  💰
                </div>
                <div>
                  <h3 className="text-base font-extrabold text-[var(--text-primary)]">برداشت از پراپ</h3>
                  <p className="text-[12px] text-[var(--text-secondary)] mt-0.5">
                    {getStageTypeLabel(withdrawingStage.stage_type)} — سود فعلی:{' '}
                    {withdrawingStage.current_profit?.toFixed(0)} USDT
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowWithdrawModal(false)}
                className="text-[var(--text-secondary)] text-xl w-9 h-9 rounded-lg hover:bg-[var(--bg-elevated)]"
              >
                ✕
              </button>
            </div>

            <div className="p-6 space-y-4">
              {modalError && (
                <div className="bg-[var(--loss-soft)] border border-[var(--loss-border)] text-[var(--loss)] p-3 rounded-[12px] text-[13px] font-semibold">
                  ❌ {modalError}
                </div>
              )}

              <div>
                <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">
                  مبلغ برداشت (دلار) <span className="text-[var(--loss)]">*</span>
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={withdrawAmount}
                  onChange={(e) => setWithdrawAmount(e.target.value)}
                  placeholder="مثلاً 500"
                  className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[12px] px-4 py-3 text-[var(--text-primary)] text-sm font-bold focus:border-[var(--accent)] focus:outline-none"
                />
              </div>

              <PersianDateInput
                label="تاریخ برداشت"
                value={withdrawDate}
                onChange={setWithdrawDate}
              />

              <div>
                <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">
                  حساب مقصد <span className="text-[var(--loss)]">*</span>
                </label>
                <select
                  value={withdrawDestinationId}
                  onChange={(e) =>
                    setWithdrawDestinationId(e.target.value ? Number(e.target.value) : '')
                  }
                  className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[12px] px-4 py-3 text-[var(--text-primary)] text-sm font-bold focus:border-[var(--accent)] focus:outline-none cursor-pointer"
                >
                  <option value="">— انتخاب حساب —</option>
                  {destinationAccounts.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.name} ({a.currency}) — {a.balance?.toLocaleString()}
                    </option>
                  ))}
                </select>
                {destinationAccounts.length === 0 && (
                  <div className="text-[11px] text-[var(--loss)] font-bold mt-1.5">
                    ⚠️ حساب مالی مقصدی وجود ندارد. ابتدا در صفحه «مالی» یک حساب
                    بانکی/صرافی/کیف‌پول/بروکر بسازید.
                  </div>
                )}
              </div>

              <div>
                <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">توضیحات</label>
                <input
                  type="text"
                  value={withdrawNote}
                  onChange={(e) => setWithdrawNote(e.target.value)}
                  placeholder="اختیاری"
                  className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[12px] px-4 py-3 text-[var(--text-primary)] text-sm font-semibold focus:border-[var(--accent)] focus:outline-none"
                />
              </div>
            </div>

            <div className="flex gap-3 p-6 pt-0">
              <button
                onClick={handleConfirmWithdraw}
                className="flex-1 text-white px-7 py-3 rounded-[12px] text-sm font-extrabold shadow-[0_6px_16px_rgba(63,124,255,0.3)]"
                style={{ background: 'linear-gradient(135deg, var(--accent), var(--accent-strong))' }}
              >
                💾 ثبت برداشت
              </button>
              <button
                onClick={() => setShowWithdrawModal(false)}
                className="bg-[var(--bg-card)] border-2 border-[var(--border-subtle)] hover:border-[var(--border-accent)] text-[var(--text-secondary)] px-7 py-3 rounded-[12px] text-sm font-bold transition-all"
              >
                ✕ لغو
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
