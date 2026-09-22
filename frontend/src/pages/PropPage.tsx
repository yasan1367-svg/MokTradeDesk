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
  getPersonalAccounts,
  getPropAnalytics,
} from '../api/client';
import PropAnalytics from '../components/charts/PropAnalytics';

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
  if (type === 'stage_1') return { bg: 'bg-[#F1ECFF]', text: 'text-[#7959D6]', border: 'border-[#D5C8F5]' };
  if (type === 'stage_2') return { bg: 'bg-[#EDF3FF]', text: 'text-[#3F7CFF]', border: 'border-[#A9C1FA]' };
  return { bg: 'bg-[#E5F8F1]', text: 'text-[#13AE81]', border: 'border-[#A8E6CF]' };
};

const getStatusBadge = (status: string) => {
  const styles: Record<string, { bg: string, text: string, label: string }> = {
    active: { bg: 'bg-[#EDF3FF]', text: 'text-[#3F7CFF]', label: '🟢 فعال' },
    passed: { bg: 'bg-[#E5F8F1]', text: 'text-[#13AE81]', label: '✅ پاس‌شده' },
    failed: { bg: 'bg-[#FFEDF0]', text: 'text-[#E45D72]', label: '❌ فیل‌شده' },
    closed: { bg: 'bg-[#F5F7FB]', text: 'text-[#6B7A94]', label: '⚫ بسته‌شده' },
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
  const [personalAccounts, setPersonalAccounts] = useState<any[]>([]);
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
  });

  const [showFailModal, setShowFailModal] = useState(false);
  const [failingStage, setFailingStage] = useState<Stage | null>(null);
  const [failReason, setFailReason] = useState('max_daily_dd_exceeded');
  const [failDetails, setFailDetails] = useState('');

  const [propAnalytics, setPropAnalytics] = useState<any>(null);
  const [showAnalytics, setShowAnalytics] = useState(false);

    const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [modalError, setModalError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
    loadPersonalAccounts();
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

  const loadPersonalAccounts = async () => {
    try {
      const res = await getPersonalAccounts();
      setPersonalAccounts(res.data);
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
      });
      setSuccessMessage('قوانین مرحله ذخیره شد');
      setEditingStage(null);
      if (selectedAccount) await loadAccountDetail(selectedAccount.id);
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'خطا در ذخیره قوانین');
    }
  };

  const handleWithdraw = async (stageId: number) => {
    const amountStr = prompt('مبلغ برداشت (دلار):');
    if (!amountStr) return;
    const amount = parseFloat(amountStr);
    if (isNaN(amount) || amount <= 0) return;

    let targetAccountId: number | null = null;
    if (personalAccounts.length > 0) {
      const accountChoice = prompt(
        `پول به کدام اکانت واریز شود؟\n${personalAccounts.map((a, i) => `${i + 1}: ${a.name}`).join('\n')}\n0: خارج از سیستم (نقدی)`,
        '0'
      );
      const choiceNum = parseInt(accountChoice || '0');
      if (choiceNum > 0 && choiceNum <= personalAccounts.length) {
        targetAccountId = personalAccounts[choiceNum - 1].id;
      }
    }

    try {
      await withdrawFromStage(stageId, amount, undefined, targetAccountId || undefined);
      setSuccessMessage(`${amount} دلار برداشت شد`);
      if (selectedAccount) await loadAccountDetail(selectedAccount.id);
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'خطا در برداشت');
    }
  };

  return (
    <div className="space-y-6">
      {error && (
        <div className="bg-[#FFEDF0] border border-[#F0A6B2] text-[#E45D72] p-4 rounded-[14px] text-sm font-semibold shadow-sm">
          ❌ {error}
          <button onClick={() => setError(null)} className="float-left text-xs font-bold">✕</button>
        </div>
      )}
      {successMessage && (
        <div className="bg-[#E5F8F1] border border-[#A8E6CF] text-[#13AE81] p-4 rounded-[14px] text-sm font-semibold shadow-sm">
          ✅ {successMessage}
        </div>
      )}

      {/* دکمه‌ها */}
      <div className="flex gap-3 flex-wrap">
        <button
          onClick={() => setShowFirmForm(!showFirmForm)}
          className="text-white px-6 py-3 rounded-[12px] text-sm font-extrabold transition-all shadow-[0_6px_16px_rgba(63,124,255,0.3)] hover:shadow-[0_10px_24px_rgba(63,124,255,0.4)] hover:-translate-y-0.5"
          style={{ background: 'linear-gradient(135deg, #3F7CFF, #5B8DEF)' }}
        >
          ➕ شرکت پراپ جدید
        </button>
        <button
          onClick={() => setShowAccountForm(!showAccountForm)}
          disabled={firms.length === 0}
          className="text-white px-6 py-3 rounded-[12px] text-sm font-extrabold transition-all shadow-[0_6px_16px_rgba(19,174,129,0.3)] hover:shadow-[0_10px_24px_rgba(19,174,129,0.4)] hover:-translate-y-0.5 disabled:opacity-40 disabled:cursor-not-allowed"
          style={{ background: 'linear-gradient(135deg, #13AE81, #4DD9A9)' }}
        >
          ➕ اکانت پراپ جدید
        </button>
        <button
          onClick={loadAnalytics}
          className="bg-white border-2 border-[#E5EBF3] text-[#6B7A94] hover:border-[#A9C1FA] hover:text-[#3F7CFF] px-6 py-3 rounded-[12px] text-sm font-extrabold transition-all shadow-sm"
        >
          📊 گزارش تحلیلی
        </button>
      </div>

      {/* گزارش تحلیلی */}
      {showAnalytics && propAnalytics && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-5">
            <div className="bg-white border border-[#E5EBF3] rounded-[22px] p-5 shadow-md">
              <div className="text-[12px] text-[#6B7A94] font-bold mb-2">📊 کل مراحل</div>
              <div className="text-[28px] font-extrabold text-[#1A2B47]">{propAnalytics.summary.total_stages}</div>
            </div>
            <div className="bg-[#E5F8F1] border border-[#A8E6CF] rounded-[22px] p-5 shadow-md">
              <div className="text-[12px] text-[#6B7A94] font-bold mb-2">✅ پاس‌شده</div>
              <div className="text-[28px] font-extrabold text-[#13AE81]">{propAnalytics.summary.passed_count}</div>
            </div>
            <div className="bg-[#FFEDF0] border border-[#F0A6B2] rounded-[22px] p-5 shadow-md">
              <div className="text-[12px] text-[#6B7A94] font-bold mb-2">❌ فیل‌شده</div>
              <div className="text-[28px] font-extrabold text-[#E45D72]">{propAnalytics.summary.failed_count}</div>
            </div>
            <div className="bg-[#EDF3FF] border border-[#A9C1FA] rounded-[22px] p-5 shadow-md">
              <div className="text-[12px] text-[#6B7A94] font-bold mb-2">📈 نرخ پاس</div>
              <div className="text-[28px] font-extrabold text-[#3F7CFF]">{propAnalytics.summary.pass_rate}٪</div>
            </div>
          </div>

          <PropAnalytics data={propAnalytics} />

          <div className="flex justify-end">
            <button
              onClick={() => setShowAnalytics(false)}
              className="bg-white border-2 border-[#E5EBF3] text-[#6B7A94] hover:border-[#A9C1FA] px-5 py-2.5 rounded-[12px] text-[12px] font-bold transition-all"
            >
              ✕ بستن گزارش
            </button>
          </div>
        </>
      )}

      {/* فرم شرکت */}
      {showFirmForm && (
        <div className="bg-white border-2 border-[#3F7CFF] rounded-[22px] p-6 shadow-lg">
          <div className="flex items-center gap-3 mb-6 pb-4 border-b border-[#E5EBF3]">
            <div className="w-11 h-11 rounded-[14px] flex items-center justify-center text-xl text-white"
              style={{ background: 'linear-gradient(135deg, #3F7CFF, #5B8DEF)' }}>
              🏢
            </div>
            <div>
              <h3 className="text-lg font-extrabold text-[#1A2B47]">شرکت پراپ جدید</h3>
              <p className="text-[12px] text-[#6B7A94] mt-0.5">نام شرکت را وارد کنید</p>
            </div>
          </div>
          <div className="mb-5">
            <label className="text-[13px] text-[#1A2B47] font-bold block mb-2">
              نام شرکت <span className="text-[#E45D72]">*</span>
            </label>
            <input
              type="text"
              value={firmName}
              onChange={(e) => setFirmName(e.target.value)}
              placeholder="مثلاً FTMO"
              className="w-full bg-[#F8FAFF] border-2 border-[#E5EBF3] rounded-[12px] px-5 py-3.5 text-[#1A2B47] text-sm font-semibold focus:border-[#3F7CFF] focus:bg-white focus:outline-none focus:ring-4 focus:ring-[#EDF3FF] transition-all"
            />
          </div>
          <div className="flex gap-3 pt-4 border-t border-[#E5EBF3]">
            <button
              onClick={handleCreateFirm}
              className="text-white px-7 py-3 rounded-[12px] text-sm font-extrabold"
              style={{ background: 'linear-gradient(135deg, #13AE81, #4DD9A9)' }}
            >
              💾 ذخیره
            </button>
            <button
              onClick={() => setShowFirmForm(false)}
              className="bg-white border-2 border-[#E5EBF3] hover:border-[#A9C1FA] text-[#6B7A94] px-7 py-3 rounded-[12px] text-sm font-bold transition-all"
            >
              ✕ لغو
            </button>
          </div>
        </div>
      )}

      {/* فرم اکانت */}
      {showAccountForm && (
        <div className="bg-white border-2 border-[#13AE81] rounded-[22px] p-6 shadow-lg">
          <div className="flex items-center gap-3 mb-6 pb-4 border-b border-[#E5EBF3]">
            <div className="w-11 h-11 rounded-[14px] flex items-center justify-center text-xl text-white"
              style={{ background: 'linear-gradient(135deg, #13AE81, #4DD9A9)' }}>
              🏦
            </div>
            <div>
              <h3 className="text-lg font-extrabold text-[#1A2B47]">اکانت پراپ جدید</h3>
              <p className="text-[12px] text-[#6B7A94] mt-0.5">مشخصات و قوانین مرحله ۱ را وارد کنید</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-5">
            <div>
              <label className="text-[13px] text-[#1A2B47] font-bold block mb-2">شرکت <span className="text-[#E45D72]">*</span></label>
              <select
                value={selectedFirmId || ''}
                onChange={(e) => setSelectedFirmId(Number(e.target.value))}
                className="w-full bg-[#F8FAFF] border-2 border-[#E5EBF3] rounded-[12px] px-4 py-3 text-[#1A2B47] text-sm font-bold focus:border-[#13AE81] focus:bg-white focus:outline-none cursor-pointer"
              >
                <option value="">— انتخاب —</option>
                {firms.map((f) => (
                  <option key={f.id} value={f.id}>{f.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-[13px] text-[#1A2B47] font-bold block mb-2">برچسب <span className="text-[#E45D72]">*</span></label>
              <input
                type="text"
                value={accountLabel}
                onChange={(e) => setAccountLabel(e.target.value)}
                placeholder="مثلاً Challenge 1"
                className="w-full bg-[#F8FAFF] border-2 border-[#E5EBF3] rounded-[12px] px-4 py-3 text-[#1A2B47] text-sm font-semibold focus:border-[#13AE81] focus:bg-white focus:outline-none"
              />
            </div>
            <div>
              <label className="text-[13px] text-[#1A2B47] font-bold block mb-2">شماره اکانت</label>
              <input
                type="text"
                value={accountNumber}
                onChange={(e) => setAccountNumber(e.target.value)}
                placeholder="اختیاری"
                className="w-full bg-[#F8FAFF] border-2 border-[#E5EBF3] rounded-[12px] px-4 py-3 text-[#1A2B47] text-sm font-semibold focus:border-[#13AE81] focus:bg-white focus:outline-none"
              />
            </div>
          </div>

                    <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-5">
            <div>
              <label className="text-[12px] text-[#6B7A94] font-bold block mb-1.5">موجودی اولیه ($)</label>
              <input type="number" value={initialBalance} onChange={(e) => setInitialBalance(e.target.value)}
                className="w-full bg-[#F8FAFF] border-2 border-[#E5EBF3] rounded-[10px] px-3 py-2.5 text-[#1A2B47] text-sm font-bold focus:border-[#13AE81] focus:outline-none" />
            </div>
            <div>
              <label className="text-[12px] text-[#6B7A94] font-bold block mb-1.5">هدف سود (%)</label>
              <input type="number" step="0.1" value={profitTargetPercent} onChange={(e) => setProfitTargetPercent(e.target.value)}
                className="w-full bg-[#F8FAFF] border-2 border-[#E5EBF3] rounded-[10px] px-3 py-2.5 text-[#1A2B47] text-sm font-bold focus:border-[#13AE81] focus:outline-none" />
              <div className="text-[10px] text-[#13AE81] font-bold mt-1">
                = {((parseFloat(profitTargetPercent) || 0) / 100 * (parseFloat(initialBalance) || 0)).toFixed(0)} $
              </div>
            </div>
            <div>
              <label className="text-[12px] text-[#6B7A94] font-bold block mb-1.5">DD روزانه (%)</label>
              <input type="number" step="0.1" value={maxDailyDdPercent} onChange={(e) => setMaxDailyDdPercent(e.target.value)}
                className="w-full bg-[#F8FAFF] border-2 border-[#E5EBF3] rounded-[10px] px-3 py-2.5 text-[#1A2B47] text-sm font-bold focus:border-[#13AE81] focus:outline-none" />
              <div className="text-[10px] text-[#E45D72] font-bold mt-1">
                = {((parseFloat(maxDailyDdPercent) || 0) / 100 * (parseFloat(initialBalance) || 0)).toFixed(0)} $
              </div>
            </div>
            <div>
              <label className="text-[12px] text-[#6B7A94] font-bold block mb-1.5">DD کلی (%)</label>
              <input type="number" step="0.1" value={maxTotalDdPercent} onChange={(e) => setMaxTotalDdPercent(e.target.value)}
                className="w-full bg-[#F8FAFF] border-2 border-[#E5EBF3] rounded-[10px] px-3 py-2.5 text-[#1A2B47] text-sm font-bold focus:border-[#13AE81] focus:outline-none" />
              <div className="text-[10px] text-[#E45D72] font-bold mt-1">
                = {((parseFloat(maxTotalDdPercent) || 0) / 100 * (parseFloat(initialBalance) || 0)).toFixed(0)} $
              </div>
            </div>
            <div>
              <label className="text-[12px] text-[#6B7A94] font-bold block mb-1.5">حداقل روزها</label>
              <input type="number" value={minTradingDays} onChange={(e) => setMinTradingDays(e.target.value)}
                className="w-full bg-[#F8FAFF] border-2 border-[#E5EBF3] rounded-[10px] px-3 py-2.5 text-[#1A2B47] text-sm font-bold focus:border-[#13AE81] focus:outline-none" />
            </div>
          </div>

          <div className="flex gap-3 pt-4 border-t border-[#E5EBF3]">
            <button onClick={handleCreateAccount}
              className="text-white px-7 py-3 rounded-[12px] text-sm font-extrabold"
              style={{ background: 'linear-gradient(135deg, #13AE81, #4DD9A9)' }}>
              💾 ذخیره اکانت
            </button>
            <button onClick={() => setShowAccountForm(false)}
              className="bg-white border-2 border-[#E5EBF3] hover:border-[#A9C1FA] text-[#6B7A94] px-7 py-3 rounded-[12px] text-sm font-bold transition-all">
              ✕ لغو
            </button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* شرکت‌ها */}
        <div className="lg:col-span-1">
          <div className="bg-white border border-[#E5EBF3] rounded-[22px] p-6 shadow-md">
            <div className="flex items-center gap-3 mb-5 pb-4 border-b border-[#E5EBF3]">
              <div className="w-11 h-11 rounded-[14px] bg-[#EDF3FF] flex items-center justify-center text-xl">🏢</div>
              <div>
                <h3 className="text-base font-extrabold text-[#1A2B47]">شرکت‌های پراپ</h3>
                <p className="text-[12px] text-[#6B7A94] mt-0.5">{firms.length} شرکت</p>
              </div>
            </div>

            {firms.length === 0 ? (
              <div className="text-[#9AA8BF] text-sm text-center py-8">شرکتی وجود ندارد</div>
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
                          isExpanded ? 'bg-[#EDF3FF] border-[#3F7CFF]' : 'bg-white border-[#E5EBF3] hover:border-[#A9C1FA]'
                        }`}
                      >
                        <span className="text-[15px] font-extrabold text-[#1A2B47]">🏢 {firm.name}</span>
                        <span className="text-[11px] text-[#6B7A94] font-bold">
                          {firmAccounts.length} اکانت {isExpanded ? '▼' : '◀'}
                        </span>
                      </button>

                      {isExpanded && (
                        <div className="mt-2 mr-3 space-y-1.5">
                          {firmAccounts.length === 0 ? (
                            <div className="text-[#9AA8BF] text-[12px] py-3 text-center bg-[#F8FAFF] rounded-[10px]">
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
                                      ? 'bg-[#3F7CFF] text-white shadow-[0_4px_12px_rgba(63,124,255,0.3)]'
                                      : 'bg-[#F8FAFF] border border-[#E5EBF3] hover:border-[#A9C1FA]'
                                  }`}
                                >
                                  <div className={`text-[13px] font-bold ${isSelected ? 'text-white' : 'text-[#1A2B47]'}`}>
                                    📁 {acc.account_label}
                                  </div>
                                  <div className={`text-[11px] mt-1 ${isSelected ? 'text-white/80' : 'text-[#6B7A94]'}`}>
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
            <div className="bg-white border border-[#E5EBF3] rounded-[22px] p-6 shadow-md">
              <div className="flex items-center gap-3 mb-5 pb-4 border-b border-[#E5EBF3]">
                <div className="w-11 h-11 rounded-[14px] flex items-center justify-center text-xl text-white"
                  style={{ background: 'linear-gradient(135deg, #3F7CFF, #5B8DEF)' }}>🔍</div>
                <div>
                  <h3 className="text-base font-extrabold text-[#1A2B47]">
                    {accountDetail.account_label} — {accountDetail.firm_name}
                  </h3>
                  <p className="text-[12px] text-[#6B7A94] mt-0.5">{accountDetail.stages.length} مرحله</p>
                </div>
              </div>

              <div className="space-y-5">
                {accountDetail.stages.map((stage: Stage) => {
                  const stageColor = getStageColor(stage.stage_type);
                  return (
                    <div key={stage.id} className={`rounded-[18px] border-2 p-5 ${stageColor.border} ${stageColor.bg}`}>
                      <div className="flex justify-between items-center mb-5 flex-wrap gap-3">
                        <div className="flex items-center gap-3">
                          <span className="text-xl font-extrabold text-[#1A2B47]">{getStageTypeLabel(stage.stage_type)}</span>
                          {getStatusBadge(stage.status)}
                        </div>
                        <div className="flex gap-2 flex-wrap">
  <button
    onClick={() => handleOpenProgressModal(stage)}
    className="bg-white border border-[#E5EBF3] text-[#1A2B47] hover:border-[#13AE81] hover:text-[#13AE81] px-4 py-2 rounded-[10px] text-[12px] font-bold transition-all shadow-sm"
  >
    📊 وضعیت کنونی
  </button>
  <button
    onClick={() => loadStageTrades(stage.id)}
    className="bg-white border border-[#E5EBF3] text-[#1A2B47] hover:border-[#3F7CFF] hover:text-[#3F7CFF] px-4 py-2 rounded-[10px] text-[12px] font-bold transition-all shadow-sm"
  >
    📋 معاملات
  </button>
  <button
    onClick={() => startEditStage(stage)}
    className="bg-white border border-[#E5EBF3] text-[#1A2B47] hover:border-[#7959D6] hover:text-[#7959D6] px-4 py-2 rounded-[10px] text-[12px] font-bold transition-all shadow-sm"
  >
    ✏️ ویرایش قوانین
  </button>
  {stage.status === 'active' && stage.stage_type !== 'funded_real' && (
    <>
      <button
        onClick={() => handleOpenPassModal(stage)}
        className="text-white px-4 py-2 rounded-[10px] text-[12px] font-extrabold shadow-[0_4px_12px_rgba(19,174,129,0.3)]"
        style={{ background: 'linear-gradient(135deg, #13AE81, #4DD9A9)' }}
      >
        ✅ بررسی و پاس
      </button>
      <button
        onClick={() => handleOpenFailModal(stage)}
        className="text-white px-4 py-2 rounded-[10px] text-[12px] font-extrabold shadow-[0_4px_12px_rgba(228,93,114,0.3)]"
        style={{ background: 'linear-gradient(135deg, #E45D72, #F0A6B2)' }}
      >
        ❌ فیل
      </button>
    </>
  )}
  {stage.stage_type === 'funded_real' && stage.status !== 'failed' && stage.status !== 'closed' && (
    <>
      <button
        onClick={() => handleWithdraw(stage.id)}
        className="text-white px-4 py-2 rounded-[10px] text-[12px] font-extrabold shadow-[0_4px_12px_rgba(63,124,255,0.3)]"
        style={{ background: 'linear-gradient(135deg, #3F7CFF, #5B8DEF)' }}
      >
        💰 برداشت
      </button>
      <button
        onClick={() => handleOpenFailModal(stage)}
        className="text-white px-4 py-2 rounded-[10px] text-[12px] font-extrabold"
        style={{ background: 'linear-gradient(135deg, #E45D72, #F0A6B2)' }}
      >
        ❌ فیل
      </button>
    </>
  )}
</div>
                      </div>

                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        {stage.initial_balance !== null && (
                          <div className="bg-white rounded-[12px] p-3 border border-white/60">
                            <div className="text-[10px] text-[#6B7A94] font-bold mb-1">موجودی اولیه</div>
                            <div className="text-[16px] font-extrabold text-[#1A2B47]">${stage.initial_balance}</div>
                          </div>
                        )}
                        {stage.profit_target !== null && stage.profit_target > 0 && (
                          <div className="bg-white rounded-[12px] p-3 border border-white/60">
                            <div className="text-[10px] text-[#6B7A94] font-bold mb-1">هدف سود</div>
                            <div className="text-[16px] font-extrabold text-[#13AE81]">${stage.profit_target}</div>
                          </div>
                        )}
                        {stage.max_daily_dd !== null && stage.max_daily_dd > 0 && (
                          <div className="bg-white rounded-[12px] p-3 border border-white/60">
                            <div className="text-[10px] text-[#6B7A94] font-bold mb-1">DD روزانه</div>
                            <div className="text-[16px] font-extrabold text-[#E45D72]">${stage.max_daily_dd}</div>
                          </div>
                        )}
                        {stage.max_total_dd !== null && stage.max_total_dd > 0 && (
                          <div className="bg-white rounded-[12px] p-3 border border-white/60">
                            <div className="text-[10px] text-[#6B7A94] font-bold mb-1">DD کلی</div>
                            <div className="text-[16px] font-extrabold text-[#E45D72]">${stage.max_total_dd}</div>
                          </div>
                        )}
                        {stage.stage_type === 'funded_real' && (
                          <>
                            <div className="bg-white rounded-[12px] p-3 border border-white/60">
                              <div className="text-[10px] text-[#6B7A94] font-bold mb-1">سود جاری</div>
                              <div className={`text-[16px] font-extrabold ${stage.current_profit >= 0 ? 'text-[#13AE81]' : 'text-[#E45D72]'}`}>
                                ${stage.current_profit?.toFixed(2)}
                              </div>
                            </div>
                            <div className="bg-white rounded-[12px] p-3 border border-white/60">
                              <div className="text-[10px] text-[#6B7A94] font-bold mb-1">کل برداشت</div>
                              <div className="text-[16px] font-extrabold text-[#3F7CFF]">${stage.total_withdrawn?.toFixed(2)}</div>
                            </div>
                          </>
                        )}
                      </div>

                      {stage.failure_reason && (
                        <div className="mt-4 bg-[#FFEDF0] border border-[#F0A6B2] text-[#E45D72] p-3 rounded-[12px] text-[12px] font-bold">
                          ❌ دلیل فیل: {stage.failure_reason}
                          {stage.failure_details && ` — ${stage.failure_details}`}
                        </div>
                      )}

                      {editingStage === stage.id && (
                        <div className="mt-5 bg-white border-2 border-[#7959D6] rounded-[14px] p-5">
                          <h4 className="text-[14px] font-extrabold text-[#1A2B47] mb-4">✏️ ویرایش قوانین مرحله</h4>
                          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-4">
                                                        <div>
                              <label className="text-[11px] text-[#6B7A94] font-bold block mb-1.5">هدف سود (%)</label>
                              <input type="number" step="0.1" value={editRules.profit_target_percent}
                                onChange={(e) => setEditRules({ ...editRules, profit_target_percent: e.target.value })}
                                className="w-full bg-[#F8FAFF] border-2 border-[#E5EBF3] rounded-[10px] px-3 py-2 text-[#1A2B47] text-sm font-bold focus:border-[#7959D6] focus:outline-none" />
                              <div className="text-[10px] text-[#13AE81] font-bold mt-1">
                                = {((parseFloat(editRules.profit_target_percent) || 0) / 100 * (parseFloat(editRules.initial_balance) || 0)).toFixed(0)} $
                              </div>
                            </div>
                            <div>
                              <label className="text-[11px] text-[#6B7A94] font-bold block mb-1.5">DD روزانه (%)</label>
                              <input type="number" step="0.1" value={editRules.max_daily_dd_percent}
                                onChange={(e) => setEditRules({ ...editRules, max_daily_dd_percent: e.target.value })}
                                className="w-full bg-[#F8FAFF] border-2 border-[#E5EBF3] rounded-[10px] px-3 py-2 text-[#1A2B47] text-sm font-bold focus:border-[#7959D6] focus:outline-none" />
                              <div className="text-[10px] text-[#E45D72] font-bold mt-1">
                                = {((parseFloat(editRules.max_daily_dd_percent) || 0) / 100 * (parseFloat(editRules.initial_balance) || 0)).toFixed(0)} $
                              </div>
                            </div>
                            <div>
                              <label className="text-[11px] text-[#6B7A94] font-bold block mb-1.5">DD کلی (%)</label>
                              <input type="number" step="0.1" value={editRules.max_total_dd_percent}
                                onChange={(e) => setEditRules({ ...editRules, max_total_dd_percent: e.target.value })}
                                className="w-full bg-[#F8FAFF] border-2 border-[#E5EBF3] rounded-[10px] px-3 py-2 text-[#1A2B47] text-sm font-bold focus:border-[#7959D6] focus:outline-none" />
                              <div className="text-[10px] text-[#E45D72] font-bold mt-1">
                                = {((parseFloat(editRules.max_total_dd_percent) || 0) / 100 * (parseFloat(editRules.initial_balance) || 0)).toFixed(0)} $
                              </div>
                            </div>
                            <div>
                              <label className="text-[11px] text-[#6B7A94] font-bold block mb-1.5">حداقل روزها</label>
                              <input type="number" value={editRules.min_trading_days}
                                onChange={(e) => setEditRules({ ...editRules, min_trading_days: e.target.value })}
                                className="w-full bg-[#F8FAFF] border-2 border-[#E5EBF3] rounded-[10px] px-3 py-2 text-[#1A2B47] text-sm font-bold focus:border-[#7959D6] focus:outline-none" />
                            </div>
                            <div>
                              <label className="text-[11px] text-[#6B7A94] font-bold block mb-1.5">موجودی اولیه ($)</label>
                              <input type="number" value={editRules.initial_balance}
                                onChange={(e) => setEditRules({ ...editRules, initial_balance: e.target.value })}
                                className="w-full bg-[#F8FAFF] border-2 border-[#E5EBF3] rounded-[10px] px-3 py-2 text-[#1A2B47] text-sm font-bold focus:border-[#7959D6] focus:outline-none" />
                            </div>
                            {stage.stage_type === 'funded_real' && (
                              <div>
                                <label className="text-[11px] text-[#6B7A94] font-bold block mb-1.5">درصد سهم کاربر</label>
                                <input type="number" value={editRules.profit_share_percentage}
                                  onChange={(e) => setEditRules({ ...editRules, profit_share_percentage: e.target.value })}
                                  className="w-full bg-[#F8FAFF] border-2 border-[#E5EBF3] rounded-[10px] px-3 py-2 text-[#1A2B47] text-sm font-bold focus:border-[#7959D6] focus:outline-none" />
                              </div>
                            )}
                          </div>
                          <div className="flex gap-2">
                            <button onClick={() => handleSaveStageRules(stage.id)}
                              className="text-white px-5 py-2.5 rounded-[10px] text-[12px] font-extrabold"
                              style={{ background: 'linear-gradient(135deg, #13AE81, #4DD9A9)' }}>
                              💾 ذخیره
                            </button>
                            <button onClick={cancelEditStage}
                              className="bg-white border-2 border-[#E5EBF3] text-[#6B7A94] px-5 py-2.5 rounded-[10px] text-[12px] font-bold">
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
          ) : (
            <div className="bg-white border border-[#E5EBF3] rounded-[22px] p-12 shadow-md text-center">
              <div className="text-6xl mb-4">🏢</div>
              <div className="text-[15px] font-bold text-[#1A2B47]">یک اکانت را از لیست انتخاب کنید</div>
              <div className="text-[12px] text-[#9AA8BF] mt-2">تا جزئیات مراحل آن را ببینید</div>
            </div>
          )}
        </div>
      </div>

      {/* مودال معاملات مرحله */}
      {selectedStage && stageTrades.length > 0 && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-[22px] max-w-4xl w-full max-h-[85vh] overflow-hidden shadow-2xl">
            <div className="flex justify-between items-center p-6 border-b border-[#E5EBF3]">
              <div className="flex items-center gap-3">
                <div className="w-11 h-11 rounded-[14px] bg-[#EDF3FF] flex items-center justify-center text-xl">📋</div>
                <div>
                  <h3 className="text-base font-extrabold text-[#1A2B47]">معاملات مرحله</h3>
                  <p className="text-[12px] text-[#6B7A94] mt-0.5">{stageTrades.length} معامله</p>
                </div>
              </div>
              <button onClick={() => { setSelectedStage(null); setStageTrades([]); }}
                className="text-[#6B7A94] hover:text-[#E45D72] text-xl font-bold w-9 h-9 rounded-lg hover:bg-[#FFEDF0] transition-all">✕</button>
            </div>

            <div className="overflow-y-auto max-h-[calc(85vh-100px)] p-6">
              <div className="overflow-x-auto rounded-[14px] border border-[#E5EBF3]">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-[#F5F7FB]">
                      <th className="text-right px-4 py-3.5 text-[11px] text-[#6B7A94] font-extrabold rounded-r-[14px]">#</th>
                      <th className="text-right px-4 py-3.5 text-[11px] text-[#6B7A94] font-extrabold">نماد</th>
                      <th className="text-right px-4 py-3.5 text-[11px] text-[#6B7A94] font-extrabold">جهت</th>
                      <th className="text-right px-4 py-3.5 text-[11px] text-[#6B7A94] font-extrabold">حجم</th>
                      <th className="text-right px-4 py-3.5 text-[11px] text-[#6B7A94] font-extrabold">سود/زیان</th>
                      <th className="text-right px-4 py-3.5 text-[11px] text-[#6B7A94] font-extrabold rounded-l-[14px]">تاریخ</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stageTrades.map((t, idx) => (
                      <tr key={t.id} className="border-b border-[#E5EBF3] hover:bg-[#F8FAFF] transition-colors">
                        <td className="px-4 py-3 text-[#6B7A94] text-[12px] font-semibold">{idx + 1}</td>
                        <td className="px-4 py-3 font-extrabold text-[#1A2B47] text-[13px]">{t.symbol}</td>
                        <td className={`px-4 py-3 font-bold text-[13px] ${t.direction === 'buy' ? 'text-[#13AE81]' : 'text-[#E45D72]'}`}>
                          {t.direction === 'buy' ? 'خرید' : 'فروش'}
                        </td>
                        <td className="px-4 py-3 text-[#1A2B47] font-semibold text-[13px]">{t.size}</td>
                        <td className={`px-4 py-3 font-extrabold text-[13px] ${t.pnl >= 0 ? 'text-[#13AE81]' : 'text-[#E45D72]'}`}>
                          {t.pnl >= 0 ? '+' : ''}{t.pnl?.toFixed(2)} $
                        </td>
                        <td className="px-4 py-3 text-[#6B7A94] text-[12px] font-medium">
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
          <div className="bg-white rounded-[22px] max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl">
            <div className="flex justify-between items-center p-6 border-b border-[#E5EBF3]">
              <div className="flex items-center gap-3">
                <div className="w-11 h-11 rounded-[14px] flex items-center justify-center text-xl text-white"
                  style={{ background: 'linear-gradient(135deg, #13AE81, #4DD9A9)' }}>✅</div>
                <div>
                  <h3 className="text-base font-extrabold text-[#1A2B47]">
                    بررسی و پاس مرحله {passingStage.stage_type === 'stage_1' ? 'اول' : 'دوم'}
                  </h3>
                  <p className="text-[12px] text-[#6B7A94] mt-0.5">اطلاعات پیشرفت و قوانین مرحله‌ی بعدی</p>
                </div>
              </div>
              <button onClick={() => setShowPassModal(false)} className="text-[#6B7A94] text-xl w-9 h-9 rounded-lg hover:bg-[#F5F7FB]">✕</button>
            </div>
            <div className="p-6 space-y-4">
              {modalError && (
                <div className="bg-[#FFEDF0] border-2 border-[#F0A6B2] text-[#E45D72] p-4 rounded-[14px] text-[14px] font-bold">
                  ❌ {modalError}
                </div>
              )}

              <div className={`rounded-[14px] p-4 border-2 ${
                passProgress.suggested_status === 'ready_to_pass'
                  ? 'bg-[#E5F8F1] border-[#A8E6CF]'
                  : passProgress.suggested_status === 'failed_daily_dd' || passProgress.suggested_status === 'failed_total_dd'
                  ? 'bg-[#FFEDF0] border-[#F0A6B2]'
                  : 'bg-[#EDF3FF] border-[#A9C1FA]'
              }`}>
                <div className="font-extrabold text-[15px] text-[#1A2B47] mb-1">
                  {passProgress.suggested_status === 'ready_to_pass' && '✅ آماده‌ی پاس کردن'}
                  {passProgress.suggested_status === 'failed_daily_dd' && '❌ DD روزانه نقض شده'}
                  {passProgress.suggested_status === 'failed_total_dd' && '❌ DD کلی نقض شده'}
                  {passProgress.suggested_status === 'in_progress' && '⏳ در حال پیشرفت'}
                </div>
                <div className="text-[12px] text-[#6B7A94] font-semibold">
                  {passProgress.total_trades} معامله | سود فعلی: {passProgress.current_profit} $
                </div>
              </div>

              <div className="space-y-3">
                <div className="bg-[#F8FAFF] border border-[#E5EBF3] rounded-[14px] p-4">
                  <div className="flex justify-between mb-2">
                    <span className="text-[13px] text-[#1A2B47] font-bold">🎯 هدف سود</span>
                    <span className={`font-extrabold text-[14px] ${passProgress.target_reached ? 'text-[#13AE81]' : 'text-[#1A2B47]'}`}>
                      {passProgress.current_profit} $ / {passProgress.profit_target} $
                    </span>
                  </div>
                  <div className="h-2 bg-white rounded-full overflow-hidden">
                    <div className={`h-full rounded-full ${passProgress.target_reached ? 'bg-gradient-to-r from-[#13AE81] to-[#4DD9A9]' : 'bg-gradient-to-r from-[#3F7CFF] to-[#5B8DEF]'}`}
                      style={{ width: `${Math.min(passProgress.profit_progress_percent, 100)}%` }} />
                  </div>
                </div>

                <div className="bg-[#F8FAFF] border border-[#E5EBF3] rounded-[14px] p-4">
                  <div className="flex justify-between mb-2">
                    <span className="text-[13px] text-[#1A2B47] font-bold">⚠️ DD روزانه</span>
                    <span className={`font-extrabold text-[14px] ${passProgress.daily_dd_violated ? 'text-[#E45D72]' : 'text-[#1A2B47]'}`}>
                      {passProgress.max_daily_loss} $ / {passProgress.max_daily_dd_limit} $
                    </span>
                  </div>
                  <div className="h-2 bg-white rounded-full overflow-hidden">
                    <div className={`h-full rounded-full ${passProgress.daily_dd_violated ? 'bg-gradient-to-r from-[#E45D72] to-[#F0A6B2]' : 'bg-gradient-to-r from-[#3F7CFF] to-[#5B8DEF]'}`}
                      style={{ width: `${Math.min(passProgress.daily_dd_progress_percent, 100)}%` }} />
                  </div>
                </div>

                <div className="bg-[#F8FAFF] border border-[#E5EBF3] rounded-[14px] p-4">
                  <div className="flex justify-between mb-2">
                    <span className="text-[13px] text-[#1A2B47] font-bold">📉 DD کلی</span>
                    <span className={`font-extrabold text-[14px] ${passProgress.total_dd_violated ? 'text-[#E45D72]' : 'text-[#1A2B47]'}`}>
                      {passProgress.max_total_dd} $ / {passProgress.max_total_dd_limit} $
                    </span>
                  </div>
                  <div className="h-2 bg-white rounded-full overflow-hidden">
                    <div className={`h-full rounded-full ${passProgress.total_dd_violated ? 'bg-gradient-to-r from-[#E45D72] to-[#F0A6B2]' : 'bg-gradient-to-r from-[#3F7CFF] to-[#5B8DEF]'}`}
                      style={{ width: `${Math.min(passProgress.total_dd_progress_percent, 100)}%` }} />
                  </div>
                </div>

                <div className="bg-[#F8FAFF] border border-[#E5EBF3] rounded-[14px] p-4 flex justify-between items-center">
                  <span className="text-[13px] text-[#1A2B47] font-bold">📅 روزهای معاملاتی</span>
                  <span className={`font-extrabold text-[15px] ${passProgress.days_met ? 'text-[#13AE81]' : 'text-[#1A2B47]'}`}>
                    {passProgress.trading_days} / {passProgress.min_trading_days}
                  </span>
                </div>
              </div>

              {passProgress.suggested_status !== 'failed_daily_dd' && passProgress.suggested_status !== 'failed_total_dd' && (
                <div className="pt-4 border-t border-[#E5EBF3]">
                  <h4 className="text-[14px] font-extrabold text-[#1A2B47] mb-4">⚙️ قوانین مرحله‌ی بعدی</h4>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
  <label className="text-[11px] text-[#6B7A94] font-bold block mb-1.5">هدف سود (%)</label>
  <input type="number" step="0.1" value={nextStageRules.profit_target_percent}
    onChange={(e) => setNextStageRules({ ...nextStageRules, profit_target_percent: e.target.value })}
    className="w-full bg-[#F8FAFF] border-2 border-[#E5EBF3] rounded-[10px] px-3 py-2.5 text-[#1A2B47] text-sm font-bold focus:border-[#13AE81] focus:outline-none" />
  <div className="text-[10px] text-[#13AE81] font-bold mt-1">
    = {((parseFloat(nextStageRules.profit_target_percent) || 0) / 100 * (parseFloat(nextStageRules.initial_balance) || 0)).toFixed(0)} $
  </div>
</div>
<div>
  <label className="text-[11px] text-[#6B7A94] font-bold block mb-1.5">DD روزانه (%)</label>
  <input type="number" step="0.1" value={nextStageRules.max_daily_dd_percent}
    onChange={(e) => setNextStageRules({ ...nextStageRules, max_daily_dd_percent: e.target.value })}
    className="w-full bg-[#F8FAFF] border-2 border-[#E5EBF3] rounded-[10px] px-3 py-2.5 text-[#1A2B47] text-sm font-bold focus:border-[#13AE81] focus:outline-none" />
  <div className="text-[10px] text-[#E45D72] font-bold mt-1">
    = {((parseFloat(nextStageRules.max_daily_dd_percent) || 0) / 100 * (parseFloat(nextStageRules.initial_balance) || 0)).toFixed(0)} $
  </div>
</div>
<div>
  <label className="text-[11px] text-[#6B7A94] font-bold block mb-1.5">DD کلی (%)</label>
  <input type="number" step="0.1" value={nextStageRules.max_total_dd_percent}
    onChange={(e) => setNextStageRules({ ...nextStageRules, max_total_dd_percent: e.target.value })}
    className="w-full bg-[#F8FAFF] border-2 border-[#E5EBF3] rounded-[10px] px-3 py-2.5 text-[#1A2B47] text-sm font-bold focus:border-[#13AE81] focus:outline-none" />
  <div className="text-[10px] text-[#E45D72] font-bold mt-1">
    = {((parseFloat(nextStageRules.max_total_dd_percent) || 0) / 100 * (parseFloat(nextStageRules.initial_balance) || 0)).toFixed(0)} $
  </div>
</div>
                    <div>
                      <label className="text-[11px] text-[#6B7A94] font-bold block mb-1.5">حداقل روزها</label>
                      <input type="number" value={nextStageRules.min_trading_days}
                        onChange={(e) => setNextStageRules({ ...nextStageRules, min_trading_days: e.target.value })}
                        className="w-full bg-[#F8FAFF] border-2 border-[#E5EBF3] rounded-[10px] px-3 py-2.5 text-[#1A2B47] text-sm font-bold focus:border-[#13AE81] focus:outline-none" />
                    </div>
                    <div>
                      <label className="text-[11px] text-[#6B7A94] font-bold block mb-1.5">موجودی اولیه ($)</label>
                      <input type="number" value={nextStageRules.initial_balance}
                        onChange={(e) => setNextStageRules({ ...nextStageRules, initial_balance: e.target.value })}
                        className="w-full bg-[#F8FAFF] border-2 border-[#E5EBF3] rounded-[10px] px-3 py-2.5 text-[#1A2B47] text-sm font-bold focus:border-[#13AE81] focus:outline-none" />
                    </div>
                    {passingStage.stage_type === 'stage_2' && (
                      <div>
                        <label className="text-[11px] text-[#6B7A94] font-bold block mb-1.5">درصد سهم کاربر</label>
                        <input type="number" value={nextStageRules.profit_share_percentage}
                          onChange={(e) => setNextStageRules({ ...nextStageRules, profit_share_percentage: e.target.value })}
                          className="w-full bg-[#F8FAFF] border-2 border-[#E5EBF3] rounded-[10px] px-3 py-2.5 text-[#1A2B47] text-sm font-bold focus:border-[#13AE81] focus:outline-none" />
                      </div>
                    )}
                  </div>
                </div>
              )}

              <div className="flex gap-3 pt-4 border-t border-[#E5EBF3]">
                <button onClick={handleConfirmPass}
                  disabled={passProgress.suggested_status === 'failed_daily_dd' || passProgress.suggested_status === 'failed_total_dd'}
                  className="flex-1 text-white py-3 rounded-[12px] font-extrabold text-sm shadow-[0_6px_16px_rgba(19,174,129,0.3)] disabled:opacity-40 disabled:cursor-not-allowed"
                  style={{ background: 'linear-gradient(135deg, #13AE81, #4DD9A9)' }}>
                  ✅ تأیید و پاس
                </button>
                <button onClick={() => setShowPassModal(false)}
                  className="bg-white border-2 border-[#E5EBF3] text-[#6B7A94] px-7 py-3 rounded-[12px] font-bold text-sm hover:border-[#A9C1FA]">
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
          <div className="bg-white rounded-[22px] max-w-md w-full shadow-2xl">
            <div className="flex justify-between items-center p-6 border-b border-[#E5EBF3]">
              <div className="flex items-center gap-3">
                <div className="w-11 h-11 rounded-[14px] flex items-center justify-center text-xl text-white"
                  style={{ background: 'linear-gradient(135deg, #E45D72, #F0A6B2)' }}>❌</div>
                <div>
                  <h3 className="text-base font-extrabold text-[#1A2B47]">فیل کردن مرحله</h3>
                  <p className="text-[12px] text-[#6B7A94] mt-0.5">دلیل را انتخاب کنید</p>
                </div>
              </div>
              <button onClick={() => setShowFailModal(false)} className="text-[#6B7A94] text-xl">✕</button>
            </div>

            <div className="p-6 space-y-4">
              <div>
                <label className="text-[13px] text-[#1A2B47] font-bold block mb-2">دلیل فیل شدن</label>
                <select
                  value={failReason}
                  onChange={(e) => setFailReason(e.target.value)}
                  className="w-full bg-[#F8FAFF] border-2 border-[#E5EBF3] rounded-[12px] px-4 py-3 text-[#1A2B47] text-sm font-bold focus:border-[#E45D72] focus:outline-none cursor-pointer"
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
                <label className="text-[13px] text-[#1A2B47] font-bold block mb-2">توضیحات (اختیاری)</label>
                <textarea
                  value={failDetails}
                  onChange={(e) => setFailDetails(e.target.value)}
                  placeholder="توضیحات بیشتر..."
                  rows={3}
                  className="w-full bg-[#F8FAFF] border-2 border-[#E5EBF3] rounded-[12px] px-4 py-3 text-[#1A2B47] text-sm font-medium focus:border-[#E45D72] focus:outline-none resize-none"
                />
              </div>

              <div className="flex gap-3 pt-4 border-t border-[#E5EBF3]">
                <button onClick={handleConfirmFail}
                  className="flex-1 text-white py-3 rounded-[12px] font-extrabold text-sm"
                  style={{ background: 'linear-gradient(135deg, #E45D72, #F0A6B2)' }}>
                  ❌ تأیید فیل
                </button>
                <button onClick={() => setShowFailModal(false)}
                  className="bg-white border-2 border-[#E5EBF3] text-[#6B7A94] px-6 py-3 rounded-[12px] font-bold text-sm">
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
          <div className="bg-white rounded-[22px] max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl">
            <div className="flex justify-between items-center p-6 border-b border-[#E5EBF3]">
              <div className="flex items-center gap-3">
                <div className="w-11 h-11 rounded-[14px] flex items-center justify-center text-xl text-white"
                  style={{ background: 'linear-gradient(135deg, #13AE81, #4DD9A9)' }}>
                  📊
                </div>
                <div>
                  <h3 className="text-base font-extrabold text-[#1A2B47]">
                    وضعیت کنونی {getStageTypeLabel(progressStage.stage_type)}
                  </h3>
                  <p className="text-[12px] text-[#6B7A94] mt-0.5">
                    {stageProgressData.total_trades} معامله ثبت‌شده
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowProgressModal(false)}
                className="text-[#6B7A94] text-xl w-9 h-9 rounded-lg hover:bg-[#F5F7FB]"
              >
                ✕
              </button>
            </div>

            <div className="p-6 space-y-4">
              {/* وضعیت */}
              <div className={`rounded-[14px] p-4 border-2 ${
                progressStage.status === 'passed'
                  ? 'bg-[#E5F8F1] border-[#A8E6CF]'
                  : progressStage.status === 'failed'
                  ? 'bg-[#FFEDF0] border-[#F0A6B2]'
                  : stageProgressData.suggested_status === 'ready_to_pass'
                  ? 'bg-[#E5F8F1] border-[#A8E6CF]'
                  : 'bg-[#EDF3FF] border-[#A9C1FA]'
              }`}>
                <div className="font-extrabold text-[15px] text-[#1A2B47] mb-1">
                  {progressStage.status === 'passed' && '✅ این مرحله پاس شده است'}
                  {progressStage.status === 'failed' && '❌ این مرحله فیل شده است'}
                  {progressStage.status === 'active' && stageProgressData.suggested_status === 'ready_to_pass' && '✅ آماده‌ی پاس کردن'}
                  {progressStage.status === 'active' && stageProgressData.suggested_status === 'in_progress' && '⏳ در حال پیشرفت'}
                  {progressStage.status === 'active' && stageProgressData.suggested_status === 'failed_daily_dd' && '❌ DD روزانه نقض شده'}
                  {progressStage.status === 'active' && stageProgressData.suggested_status === 'failed_total_dd' && '❌ DD کلی نقض شده'}
                </div>
                <div className="text-[12px] text-[#6B7A94] font-semibold">
                  سود فعلی: <span className="text-[#13AE81] font-extrabold">{stageProgressData.current_profit} $</span>
                </div>
              </div>

              {/* هدف سود */}
              <div className="bg-[#F8FAFF] border border-[#E5EBF3] rounded-[14px] p-4">
                <div className="flex justify-between mb-2">
                  <span className="text-[13px] text-[#1A2B47] font-bold">🎯 هدف سود</span>
                  <span className={`font-extrabold text-[14px] ${stageProgressData.target_reached ? 'text-[#13AE81]' : 'text-[#1A2B47]'}`}>
                    {stageProgressData.current_profit} $ / {stageProgressData.profit_target} $
                  </span>
                </div>
                <div className="h-2 bg-white rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${stageProgressData.target_reached ? 'bg-gradient-to-r from-[#13AE81] to-[#4DD9A9]' : 'bg-gradient-to-r from-[#3F7CFF] to-[#5B8DEF]'}`}
                    style={{ width: `${Math.min(stageProgressData.profit_progress_percent, 100)}%` }}
                  />
                </div>
              </div>

              {/* DD روزانه */}
              <div className="bg-[#F8FAFF] border border-[#E5EBF3] rounded-[14px] p-4">
                <div className="flex justify-between mb-2">
                  <span className="text-[13px] text-[#1A2B47] font-bold">⚠️ DD روزانه</span>
                  <span className={`font-extrabold text-[14px] ${stageProgressData.daily_dd_violated ? 'text-[#E45D72]' : 'text-[#1A2B47]'}`}>
                    {stageProgressData.max_daily_loss} $ / {stageProgressData.max_daily_dd_limit} $
                  </span>
                </div>
                <div className="h-2 bg-white rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${stageProgressData.daily_dd_violated ? 'bg-gradient-to-r from-[#E45D72] to-[#F0A6B2]' : 'bg-gradient-to-r from-[#3F7CFF] to-[#5B8DEF]'}`}
                    style={{ width: `${Math.min(stageProgressData.daily_dd_progress_percent, 100)}%` }}
                  />
                </div>
              </div>

              {/* DD کلی */}
              <div className="bg-[#F8FAFF] border border-[#E5EBF3] rounded-[14px] p-4">
                <div className="flex justify-between mb-2">
                  <span className="text-[13px] text-[#1A2B47] font-bold">📉 DD کلی</span>
                  <span className={`font-extrabold text-[14px] ${stageProgressData.total_dd_violated ? 'text-[#E45D72]' : 'text-[#1A2B47]'}`}>
                    {stageProgressData.max_total_dd} $ / {stageProgressData.max_total_dd_limit} $
                  </span>
                </div>
                <div className="h-2 bg-white rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${stageProgressData.total_dd_violated ? 'bg-gradient-to-r from-[#E45D72] to-[#F0A6B2]' : 'bg-gradient-to-r from-[#3F7CFF] to-[#5B8DEF]'}`}
                    style={{ width: `${Math.min(stageProgressData.total_dd_progress_percent, 100)}%` }}
                  />
                </div>
              </div>

              {/* روزهای معاملاتی */}
              <div className="bg-[#F8FAFF] border border-[#E5EBF3] rounded-[14px] p-4 flex justify-between items-center">
                <span className="text-[13px] text-[#1A2B47] font-bold">📅 روزهای معاملاتی</span>
                <span className={`font-extrabold text-[15px] ${stageProgressData.days_met ? 'text-[#13AE81]' : 'text-[#1A2B47]'}`}>
                  {stageProgressData.trading_days} / {stageProgressData.min_trading_days}
                </span>
              </div>

              {/* دکمه‌ی بستن */}
              <div className="pt-4 border-t border-[#E5EBF3]">
                <button
                  onClick={() => setShowProgressModal(false)}
                  className="w-full bg-white border-2 border-[#E5EBF3] text-[#6B7A94] hover:border-[#A9C1FA] py-3 rounded-[12px] font-bold text-sm transition-all"
                >
                  ✕ بستن
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}