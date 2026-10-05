import { useCallback, useEffect, useMemo, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from 'recharts';
import EmptyState from '../components/ui/EmptyState';
import PersianDateInput from '../components/PersianDateInput';
import { RiskSkeleton } from '../components/Skeleton';
import { useToast } from '../components/ToastProvider';
import {
  getPropPayouts,
  getPropPayoutsStats,
  createPropPayout,
  updatePropPayout,
  updatePropPayoutStatus,
  createPropPayoutTransfer,
  deletePropPayout,
  getBrokerCashMovements,
  getBrokerCashMovementStats,
  createBrokerCashMovement,
  updateBrokerCashMovement,
  deleteBrokerCashMovement,
  getPropFirms,
  getAllPropStages,
  getFinanceAccountsForDestination,
  getPersonalTradingAccounts,
} from '../api/client';
import { gregorianToJalali } from '../utils/jalali';

type Tab = 'prop' | 'broker';

// فاز ۳۳ — چرخهٔ عمر برداشت
const STATUS_META: Record<string, { label: string; cls: string; icon: string }> = {
  requested: { label: 'درخواست‌شده', icon: '🕐', cls: 'bg-[var(--bg-elevated)] text-[var(--text-secondary)] border-[var(--border-subtle)]' },
  approved: { label: 'تأییدشده', icon: '✅', cls: 'bg-[var(--accent)]/15 text-[var(--accent)] border-[var(--accent)]/30' },
  processing: { label: 'در حال پردازش', icon: '⏳', cls: 'bg-[var(--warning)]/15 text-[var(--warning)] border-[var(--warning)]/30' },
  received: { label: 'دریافت‌شده', icon: '💰', cls: 'bg-[var(--profit)]/15 text-[var(--profit)] border-[var(--profit)]/30' },
  cancelled: { label: 'لغوشده', icon: '🚫', cls: 'bg-[var(--loss)]/15 text-[var(--loss)] border-[var(--loss)]/30' },
};

const STATUS_ACTION_LABEL: Record<string, string> = {
  approved: 'تأیید',
  processing: 'پردازش',
  received: 'دریافت',
  cancelled: 'لغو',
};

function StatusBadge({ status }: { status?: string | null }) {
  if (!status) return <span className="text-[var(--text-muted)]">—</span>;
  const m = STATUS_META[status];
  if (!m) return <span className="text-[var(--text-secondary)]">{status}</span>;
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full border text-[11px] font-bold whitespace-nowrap ${m.cls}`}>
      {m.icon} {m.label}
    </span>
  );
}

/** تاریخ میلادی ISO → شمسی (YYYY/MM/DD) */
function faDate(iso?: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return '—';
  const [jy, jm, jd] = gregorianToJalali(d.getFullYear(), d.getMonth() + 1, d.getDate());
  return `${jy}/${String(jm).padStart(2, '0')}/${String(jd).padStart(2, '0')}`;
}

const inputCls =
  'w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[12px] px-4 py-2.5 text-[var(--text-primary)] text-sm focus:border-[var(--accent)] focus:outline-none';

function StatCard({ icon, label, value, tone = 'accent' }: { icon: string; label: string; value: string; tone?: 'accent' | 'profit' | 'purple' }) {
  const grad = {
    accent: 'linear-gradient(135deg, var(--accent), var(--accent-strong))',
    profit: 'linear-gradient(135deg, var(--profit), var(--profit-border))',
    purple: 'linear-gradient(135deg, var(--purple), var(--purple-light))',
  }[tone];
  return (
    <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-5 shadow-md">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-[12px] flex items-center justify-center text-lg text-white" style={{ background: grad }}>
          {icon}
        </div>
        <div className="min-w-0">
          <div className="text-[11px] text-[var(--text-secondary)] font-bold">{label}</div>
          <div className="text-lg font-extrabold text-[var(--text-primary)] truncate">{value}</div>
        </div>
      </div>
    </div>
  );
}

export default function PayoutHistoryPage() {
  const toast = useToast();

  const [tab, setTab] = useState<Tab>('prop');
  const [loading, setLoading] = useState(true);
  const [rows, setRows] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);

  // فیلترها
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [currency, setCurrency] = useState('');
  const [firmId, setFirmId] = useState<string>('');
  const [firms, setFirms] = useState<any[]>([]);

  // فرم ثبت برداشت جدید
  const [showForm, setShowForm] = useState(false);
  const [editingBrokerId, setEditingBrokerId] = useState<number | null>(null);
  const [editingPropId, setEditingPropId] = useState<number | null>(null);
  const [stages, setStages] = useState<any[]>([]);
  const [destAccounts, setDestAccounts] = useState<any[]>([]);
  const [tradingAccounts, setTradingAccounts] = useState<any[]>([]);
  const [saving, setSaving] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);

  // فاز ۳۳ — انتقال بین‌حسابی (Trust Wallet → Exchange → IRR → Bank Card)
  const [transferRow, setTransferRow] = useState<any | null>(null);
  const [transferSaving, setTransferSaving] = useState(false);
  const [transferForm, setTransferForm] = useState({
    from_account_id: '', to_account_id: '', amount: '', currency: '', date: '', note: '',
  });
  const [form, setForm] = useState({ prop_stage_id: '', amount: '', destination_account_id: '', withdrawal_date: '', note: '' });
  const [brokerForm, setBrokerForm] = useState({
    direction: 'withdrawal_from_broker' as 'deposit_to_broker' | 'withdrawal_from_broker',
    personal_trading_account_id: '', financial_account_id: '', amount: '', date: '', note: '',
  });

  const params = useMemo(
    () => ({
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
      currency: currency || undefined,
      firm_id: tab === 'prop' && firmId ? Number(firmId) : undefined,
    }),
    [dateFrom, dateTo, currency, firmId, tab],
  );

  const load = useCallback(async () => {
    setLoading(true);
    try {
      if (tab === 'prop') {
        const [list, st] = await Promise.all([getPropPayouts(params), getPropPayoutsStats(params)]);
        setRows(list.data || []);
        setStats(st.data || null);
      } else {
        const [list, st] = await Promise.all([getBrokerCashMovements(params), getBrokerCashMovementStats(params)]);
        setRows(list.data || []);
        setStats(st.data || null);
      }
    } catch {
      toast.error('خطا در بارگذاری تاریخچهٔ برداشت‌ها');
    } finally {
      setLoading(false);
    }
  }, [tab, params, toast]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (tab === 'prop') {
      getPropFirms().then((r) => setFirms(r.data || [])).catch(() => {});
      getAllPropStages().then((r) => setStages(r.data || [])).catch(() => {});
      getFinanceAccountsForDestination().then((r) => setDestAccounts(r.data || [])).catch(() => {});
    } else {
      getPersonalTradingAccounts().then((r) => setTradingAccounts(r.data || [])).catch(() => {});
      getFinanceAccountsForDestination().then((r) => setDestAccounts(r.data || [])).catch(() => {});
    }
  }, [tab]);

  const handleSubmit = async () => {
    if (!form.prop_stage_id || !form.amount || !form.destination_account_id) {
      toast.warning('مرحله، مبلغ و حساب مقصد الزامی است');
      return;
    }
    const amount = Number(form.amount);
    if (!Number.isFinite(amount) || amount <= 0) {
      toast.warning('مبلغ باید عددی مثبت باشد');
      return;
    }
    setSaving(true);
    try {
      const payload = {
        amount,
        destination_account_id: Number(form.destination_account_id),
        currency: destAccounts.find((account: any) => String(account.id) === form.destination_account_id)?.currency,
        withdrawal_date: form.withdrawal_date || undefined,
        note: form.note,
      };
      if (editingPropId !== null) {
        await updatePropPayout(editingPropId, payload);
      } else {
        await createPropPayout({ ...payload, prop_stage_id: Number(form.prop_stage_id) });
      }
      toast.success(editingPropId !== null ? 'برداشت و اثر مالی آن اصلاح شد' : 'برداشت با موفقیت ثبت شد');
      setShowForm(false);
      setEditingPropId(null);
      setForm({ prop_stage_id: '', amount: '', destination_account_id: '', withdrawal_date: '', note: '' });
      load();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'خطا در ذخیره برداشت');
    } finally {
      setSaving(false);
    }
  };

  const openPropEdit = (row: any) => {
    setEditingPropId(row.id);
    setForm({
      prop_stage_id: String(row.prop_stage_id),
      amount: String(row.amount),
      destination_account_id: String(row.destination_account_id),
      withdrawal_date: row.withdrawal_date || '',
      note: row.note || '',
    });
    setShowForm(true);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleDelete = async (id: number) => {
    try {
      if (isProp) {
        await deletePropPayout(id);
        toast.success('برداشت پراپ حذف شد');
      } else {
        await deleteBrokerCashMovement(id);
        toast.success('گردش بروکر حذف شد و موجودی‌ها برگشت خورد');
      }
      load();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'خطا در حذف برداشت');
    }
  };

  const handleBrokerSubmit = async () => {
    if (!brokerForm.personal_trading_account_id || !brokerForm.financial_account_id || !brokerForm.amount) {
      toast.warning('حساب بروکر، حساب مالی و مبلغ الزامی است');
      return;
    }
    const amount = Number(brokerForm.amount);
    if (!Number.isFinite(amount) || amount <= 0) {
      toast.warning('مبلغ باید عددی مثبت باشد');
      return;
    }
    setSaving(true);
    try {
      const payload = {
        direction: brokerForm.direction,
        personal_trading_account_id: Number(brokerForm.personal_trading_account_id),
        financial_account_id: Number(brokerForm.financial_account_id),
        amount,
        date: brokerForm.date || undefined,
        note: brokerForm.note,
      };
      if (editingBrokerId !== null) {
        await updateBrokerCashMovement(editingBrokerId, payload);
      } else {
        await createBrokerCashMovement(payload);
      }
      toast.success(editingBrokerId !== null ? 'گردش بروکر و موجودی هر دو حساب اصلاح شد' : brokerForm.direction === 'deposit_to_broker' ? 'واریز به بروکر ثبت شد' : 'برداشت از بروکر ثبت شد');
      setShowForm(false);
      setEditingBrokerId(null);
      setBrokerForm({ ...brokerForm, amount: '', financial_account_id: '', date: '', note: '' });
      load();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'خطا در ثبت گردش بروکر');
    } finally {
      setSaving(false);
    }
  };

  const openBrokerEdit = (row: any) => {
    setEditingBrokerId(row.id);
    setBrokerForm({
      direction: row.direction,
      personal_trading_account_id: String(row.personal_trading_account_id),
      financial_account_id: String(row.financial_account_id),
      amount: String(row.amount),
      date: row.date || '',
      note: row.note || '',
    });
    setShowForm(true);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // فاز ۳۳ — تغییر وضعیت برداشت (REQUESTED → APPROVED → PROCESSING → RECEIVED / CANCELLED)
  const handleAdvance = async (id: number, status: string) => {
    if (
      status === 'received' &&
      !window.confirm('با ثبت «دریافت»، موجودی حساب مقصد به‌روز می‌شود؛ فقط اگر مقصد حساب بانکی باشد در گزارش درآمد می‌آید. ادامه؟')
    ) {
      return;
    }
    setBusyId(id);
    try {
      await updatePropPayoutStatus(id, status);
      toast.success(`وضعیت به «${STATUS_META[status]?.label || status}» تغییر کرد`);
      load();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'خطا در تغییر وضعیت برداشت');
    } finally {
      setBusyId(null);
    }
  };

  // فاز ۳۳ — باز کردن فرم انتقال برای یک برداشت دریافت‌شده
  const openTransfer = (row: any) => {
    setTransferRow(row);
    setTransferForm({
      from_account_id: String(row.destination_account_id ?? ''),
      to_account_id: '',
      amount: String(row.amount ?? ''),
      currency: row.currency || 'USDT',
      date: '',
      note: '',
    });
  };

  const handleTransferSubmit = async () => {
    if (!transferRow) return;
    if (!transferForm.to_account_id || !transferForm.amount) {
      toast.warning('حساب مقصد و مبلغ الزامی است');
      return;
    }
    if (transferForm.from_account_id && transferForm.from_account_id === transferForm.to_account_id) {
      toast.warning('حساب مبدأ و مقصد باید متفاوت باشند');
      return;
    }
    setTransferSaving(true);
    try {
      await createPropPayoutTransfer(transferRow.id, {
        to_account_id: Number(transferForm.to_account_id),
        from_account_id: transferForm.from_account_id ? Number(transferForm.from_account_id) : undefined,
        amount: Number(transferForm.amount),
        currency: transferForm.currency || undefined,
        date: transferForm.date || undefined,
        note: transferForm.note || undefined,
      });
      const destination = destAccounts.find((account: any) => account.id === Number(transferForm.to_account_id));
      const source = destAccounts.find((account: any) => account.id === Number(transferForm.from_account_id || transferRow.destination_account_id));
      toast.success(destination?.type === 'bank' && source?.type !== 'bank' ? 'انتقال ثبت شد؛ مبلغ واریزی به بانک در گزارش درآمد می‌آید' : 'انتقال بین حساب‌ها ثبت شد');
      setTransferRow(null);
      load();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'خطا در ثبت انتقال');
    } finally {
      setTransferSaving(false);
    }
  };

  const isProp = tab === 'prop';
  // حساب‌های مالی مجاز برای انتقال (بدون حساب‌های پراپ)
  const transferAccounts = (destAccounts || []).filter((a: any) => a.type !== 'prop');
  const selectedTradingAccount = tradingAccounts.find(
    (a: any) => String(a.id) === brokerForm.personal_trading_account_id,
  );
  const brokerFinancialAccounts = transferAccounts.filter(
    (a: any) => !selectedTradingAccount || a.currency === selectedTradingAccount.currency,
  );
  const chartData = (stats?.monthly || []).map((m: any) => ({
    name: m.month, amount: m.amount, deposits: m.deposits, withdrawals: m.withdrawals,
  }));
  const money = (v: any) => `${currency || 'USDT'} ${Number(v || 0).toLocaleString('en-US', { maximumFractionDigits: 2 })}`;

  return (
    <div className="space-y-6">
      {/* هدر */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-[14px] flex items-center justify-center text-2xl text-white"
               style={{ background: 'linear-gradient(135deg, var(--accent), var(--accent-strong))' }}>💸</div>
          <div>
            <h2 className="text-2xl font-extrabold text-[var(--text-primary)]">{isProp ? 'تاریخچهٔ برداشت‌های پراپ' : 'گردش مالی بروکر'}</h2>
            <p className="text-xs text-[var(--text-secondary)] mt-0.5">پراپ و بروکر — آمار و تاریخچهٔ کامل</p>
          </div>
        </div>
        <button
          onClick={() => {
            setEditingBrokerId(null);
            setEditingPropId(null);
            setForm({ prop_stage_id: '', amount: '', destination_account_id: '', withdrawal_date: '', note: '' });
            setBrokerForm({ ...brokerForm, amount: '', financial_account_id: '', date: '', note: '' });
            setShowForm((value) => editingBrokerId !== null || editingPropId !== null || !value);
          }}
          className="text-white px-5 py-3 rounded-[12px] text-sm font-extrabold shadow-[0_6px_16px_rgba(19,174,129,0.3)] hover:-translate-y-0.5 transition-all"
          style={{ background: 'linear-gradient(135deg, var(--profit), var(--profit-border))' }}
        >
          {isProp ? '➕ ثبت برداشت جدید' : '➕ ثبت گردش بروکر'}
        </button>
      </div>

      {/* تب‌ها */}
      <div className="flex gap-2 bg-[var(--bg-elevated)] p-1.5 rounded-[14px] w-fit">
        {([['prop', '🏢 پراپ'], ['broker', '📈 گردش بروکر']] as [Tab, string][]).map(([k, label]) => (
          <button
            key={k}
            onClick={() => { setTab(k); setShowForm(false); setEditingBrokerId(null); setEditingPropId(null); }}
            className={`px-5 py-2 rounded-[10px] text-sm font-extrabold transition-all ${
              tab === k ? 'bg-[var(--accent)] text-white' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* فرم ثبت برداشت پراپ */}
      {isProp && showForm && (
        <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-6 shadow-md">
          <div className="flex items-center gap-3 mb-5 pb-4 border-b border-[var(--border-subtle)]">
            <div className="w-11 h-11 rounded-[14px] flex items-center justify-center text-xl text-white"
                 style={{ background: 'linear-gradient(135deg, var(--profit), var(--profit-border))' }}>➕</div>
            <h3 className="text-lg font-extrabold text-[var(--text-primary)]">{editingPropId !== null ? 'ویرایش برداشت پراپ' : 'ثبت برداشت جدید'}</h3>
            <span className="text-[11px] text-[var(--text-muted)]">{editingPropId !== null ? 'اصلاح برداشت دریافت‌شده، موجودی مقصد و گزارش درآمد را هم اصلاح می‌کند.' : 'وضعیت اولیه: «درخواست‌شده» — تأیید → پردازش → دریافت'}</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            <div>
              <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">🏢 مرحله (رییل)</label>
              <select className={inputCls} value={form.prop_stage_id} disabled={editingPropId !== null}
                      onChange={(e) => setForm({ ...form, prop_stage_id: e.target.value })}>
                <option value="">انتخاب مرحله…</option>
                {stages.filter((s: any) => s.stage_type === 'funded_real').map((s: any) => (
                  <option key={s.id} value={s.id}>{s.display_name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">💵 مبلغ واقعی دریافتی</label>
              <input type="number" min="0.01" step="any" className={inputCls} value={form.amount} placeholder="مثلاً 500"
                     onChange={(e) => setForm({ ...form, amount: e.target.value })} />
            </div>
            <div>
              <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">🏦 حساب مقصد</label>
              <select className={inputCls} value={form.destination_account_id}
                      onChange={(e) => setForm({ ...form, destination_account_id: e.target.value })}>
                <option value="">انتخاب حساب…</option>
                {destAccounts.map((a: any) => (
                  <option key={a.id} value={a.id}>{a.name} ({a.currency})</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">📅 تاریخ برداشت (شمسی)</label>
              <PersianDateInput value={form.withdrawal_date} onChange={(iso) => setForm({ ...form, withdrawal_date: iso })} />
            </div>
            <div className="md:col-span-2">
              <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">📝 توضیحات</label>
              <input className={inputCls} value={form.note} placeholder="اختیاری"
                     onChange={(e) => setForm({ ...form, note: e.target.value })} />
            </div>
          </div>
          <div className="flex justify-end gap-3 mt-6">
            <button onClick={() => setShowForm(false)}
                    className="px-5 py-3 rounded-[12px] text-sm font-extrabold bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] text-[var(--text-secondary)]">
              انصراف
            </button>
            <button onClick={handleSubmit} disabled={saving}
                    className="text-white px-7 py-3 rounded-[12px] text-sm font-extrabold shadow-[0_6px_16px_rgba(19,174,129,0.3)] disabled:opacity-50"
                    style={{ background: 'linear-gradient(135deg, var(--profit), var(--profit-border))' }}>
              {saving ? '⏳ در حال ذخیره…' : editingPropId !== null ? 'ذخیرهٔ اصلاحات' : '💾 ثبت برداشت'}
            </button>
          </div>
        </div>
      )}

      {!isProp && showForm && (
        <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-6 shadow-md">
          <div className="flex items-center gap-3 mb-5 pb-4 border-b border-[var(--border-subtle)]">
            <div className="w-11 h-11 rounded-[14px] flex items-center justify-center text-xl text-white"
                 style={{ background: 'linear-gradient(135deg, var(--accent), var(--accent-strong))' }}>🔁</div>
            <div>
              <h3 className="text-lg font-extrabold text-[var(--text-primary)]">{editingBrokerId !== null ? 'ویرایش گردش پول بروکر' : 'ثبت گردش پول بروکر'}</h3>
              <p className="text-[11px] text-[var(--text-secondary)]">موجودی هر دو حساب هم‌زمان به‌روز می‌شود؛ ارزها باید یکسان باشند.</p>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            <div>
              <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">نوع گردش</label>
              <select className={inputCls} value={brokerForm.direction}
                      onChange={(e) => setBrokerForm({ ...brokerForm, direction: e.target.value as typeof brokerForm.direction, financial_account_id: '' })}>
                <option value="withdrawal_from_broker">برداشت از بروکر به حساب مالی</option>
                <option value="deposit_to_broker">واریز از حساب مالی به بروکر</option>
              </select>
            </div>
            <div>
              <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">حساب معاملاتی بروکر</label>
              <select className={inputCls} value={brokerForm.personal_trading_account_id}
                      onChange={(e) => setBrokerForm({ ...brokerForm, personal_trading_account_id: e.target.value, financial_account_id: '' })}>
                <option value="">انتخاب حساب…</option>
                {tradingAccounts.filter((a: any) => a.is_active).map((a: any) => (
                  <option key={a.id} value={a.id}>{a.broker_name} — {a.account_label || a.account_number} ({a.currency})</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">
                {brokerForm.direction === 'deposit_to_broker' ? 'حساب مالی مبدأ' : 'حساب مالی مقصد'}
              </label>
              <select className={inputCls} value={brokerForm.financial_account_id}
                      onChange={(e) => setBrokerForm({ ...brokerForm, financial_account_id: e.target.value })}>
                <option value="">انتخاب حساب…</option>
                {brokerFinancialAccounts.map((a: any) => (
                  <option key={a.id} value={a.id}>{a.name} ({a.currency})</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">مبلغ ({selectedTradingAccount?.currency || '—'})</label>
              <input type="number" min="0.01" step="any" className={inputCls} value={brokerForm.amount} placeholder="مثلاً 250"
                     onChange={(e) => setBrokerForm({ ...brokerForm, amount: e.target.value })} />
            </div>
            <div>
              <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">تاریخ گردش (شمسی)</label>
              <PersianDateInput value={brokerForm.date} onChange={(iso) => setBrokerForm({ ...brokerForm, date: iso })} />
            </div>
            <div>
              <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">توضیحات</label>
              <input className={inputCls} value={brokerForm.note} placeholder="اختیاری"
                     onChange={(e) => setBrokerForm({ ...brokerForm, note: e.target.value })} />
            </div>
          </div>
          <div className="flex justify-end gap-3 mt-6">
            <button onClick={() => setShowForm(false)}
                    className="px-5 py-3 rounded-[12px] text-sm font-extrabold bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] text-[var(--text-secondary)]">
              انصراف
            </button>
            <button onClick={handleBrokerSubmit} disabled={saving || tradingAccounts.length === 0}
                    className="text-white px-7 py-3 rounded-[12px] text-sm font-extrabold shadow-[0_6px_16px_rgba(19,174,129,0.3)] disabled:opacity-50"
                    style={{ background: 'linear-gradient(135deg, var(--profit), var(--profit-border))' }}>
              {saving ? '⏳ در حال ذخیره…' : editingBrokerId !== null ? 'ذخیرهٔ اصلاحات' : 'ثبت گردش'}
            </button>
          </div>
        </div>
      )}

      {/* فیلترها */}
      <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-5 shadow-md">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <label className="text-[12px] text-[var(--text-secondary)] font-bold block mb-2">📅 از تاریخ (شمسی)</label>
            <PersianDateInput value={dateFrom} onChange={setDateFrom} />
          </div>
          <div>
            <label className="text-[12px] text-[var(--text-secondary)] font-bold block mb-2">📅 تا تاریخ (شمسی)</label>
            <PersianDateInput value={dateTo} onChange={setDateTo} />
          </div>
          <div>
            <label className="text-[12px] text-[var(--text-secondary)] font-bold block mb-2">💱 ارز</label>
            <select className={inputCls} value={currency} onChange={(e) => setCurrency(e.target.value)}>
              <option value="">پیش‌فرض: USDT</option>
              <option value="USDT">USDT</option>
              <option value="IRR">IRR</option>
            </select>
          </div>
          {isProp && (
            <div>
              <label className="text-[12px] text-[var(--text-secondary)] font-bold block mb-2">🏢 شرکت پراپ</label>
              <select className={inputCls} value={firmId} onChange={(e) => setFirmId(e.target.value)}>
                <option value="">همه</option>
                {firms.map((f: any) => <option key={f.id} value={f.id}>{f.name}</option>)}
              </select>
            </div>
          )}
        </div>
        {(dateFrom || dateTo || currency || firmId) && (
          <div className="flex justify-end mt-4">
            <button onClick={() => { setDateFrom(''); setDateTo(''); setCurrency(''); setFirmId(''); }}
                    className="text-xs font-bold text-[var(--accent)] hover:underline">
              ✖ پاک کردن فیلترها
            </button>
          </div>
        )}
      </div>

      {/* محتوا */}
      {loading ? (
        <RiskSkeleton />
      ) : (
        <>
          {/* آمار */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
            <StatCard icon="💵" label={isProp ? 'مجموع برداشت‌ها' : 'واریز به بروکر'} value={money(isProp ? stats?.total : stats?.total_deposits)} />
            <StatCard icon="🏧" label={isProp ? 'تعداد برداشت‌ها' : 'برداشت از بروکر'} value={isProp ? String(stats?.count ?? 0) : money(stats?.total_withdrawals)} tone="purple" />
            <StatCard icon="📊" label={isProp ? 'میانگین برداشت' : 'تعداد گردش‌ها'} value={isProp ? money(stats?.average) : String(stats?.count ?? 0)} tone="profit" />
            <StatCard icon="🏆" label={isProp ? 'بزرگ‌ترین برداشت' : 'بزرگ‌ترین گردش'} value={money(stats?.largest)} />
          </div>

          {/* نمودار برداشت‌ها در طول زمان */}
          {chartData.length > 0 && (
            <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-6 shadow-md">
              <h3 className="text-base font-extrabold text-[var(--text-primary)] mb-4">{isProp ? '📈 برداشت‌ها در طول زمان' : '🔄 واریز و برداشت بروکر در طول زمان'}</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
                    <XAxis dataKey="name" tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} />
                    <YAxis tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} />
                    <Tooltip contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 12, color: 'var(--text-primary)' }} />
                    {isProp ? (
                      <Bar dataKey="amount" fill="var(--accent)" radius={[6, 6, 0, 0]} />
                    ) : (
                      <>
                        <Legend />
                        <Bar dataKey="deposits" name="واریز به بروکر" fill="var(--profit)" radius={[6, 6, 0, 0]} />
                        <Bar dataKey="withdrawals" name="برداشت از بروکر" fill="var(--loss)" radius={[6, 6, 0, 0]} />
                      </>
                    )}
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* مقایسه پراپ/بروکر */}
          {(isProp ? stats?.by_firm : stats?.by_account)?.length > 0 && (
            <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-6 shadow-md">
              <h3 className="text-base font-extrabold text-[var(--text-primary)] mb-4">
                {isProp ? '🏢 مقایسهٔ شرکت‌های پراپ' : '📈 مقایسهٔ حساب‌های بروکر'}
              </h3>
              <div className="flex flex-wrap gap-3">
                {(isProp ? stats.by_firm : stats.by_account).map((x: any, i: number) => (
                  <div key={i} className="bg-[var(--bg-elevated)] border border-[var(--border-subtle)] rounded-[14px] px-4 py-3">
                    <div className="text-[12px] font-bold text-[var(--text-primary)]">{x.name}</div>
                    <div className="text-[13px] font-extrabold text-[var(--profit)]">{money(x.amount)}</div>
                    <div className="text-[11px] text-[var(--text-muted)]">{x.count} {isProp ? 'برداشت' : 'گردش'}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* جدول */}
          <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] shadow-md overflow-hidden">
            {rows.length === 0 ? (
              <EmptyState
                icon="💸"
                title={isProp ? 'برداشتی ثبت نشده' : 'گردشی ثبت نشده'}
                description={isProp ? 'با ثبت اولین برداشت، این جدول پر می‌شود' : 'واریز یا برداشت بروکر را ثبت کن تا در این جدول نمایش داده شود'}
              />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-[var(--border-subtle)] text-[var(--text-secondary)]">
                      <th className="text-right py-3 px-4">تاریخ</th>
                      {!isProp && <th className="text-right py-3 px-4">نوع گردش</th>}
                      <th className="text-right py-3 px-4">مبلغ</th>
                      {isProp && <th className="text-right py-3 px-4">وضعیت</th>}
                      <th className="text-right py-3 px-4">{isProp ? 'پراپ' : 'حساب بروکر'}</th>
                      {isProp && <th className="text-right py-3 px-4">مرحله</th>}
                      <th className="text-right py-3 px-4">{isProp ? 'حساب مقصد' : 'حساب مالی'}</th>
                      <th className="text-right py-3 px-4">توضیحات</th>
                      <th className="text-right py-3 px-4">عملیات</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((r: any) => (
                      <tr
                        key={r.id}
                        className="border-b border-[var(--border-subtle)]/50 hover:bg-[var(--accent-soft)]/30 transition-colors"
                      >
                        <td className="py-3 px-4 text-[var(--text-secondary)] text-[12px]">
                          {faDate(r.withdrawal_date || r.date)}
                        </td>
                        {!isProp && (
                          <td className={`py-3 px-4 font-bold ${r.direction === 'deposit_to_broker' ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
                            {r.direction === 'deposit_to_broker' ? 'واریز به بروکر' : 'برداشت از بروکر'}
                          </td>
                        )}
                        <td className={`py-3 px-4 font-extrabold ${!isProp && r.direction === 'withdrawal_from_broker' ? 'text-[var(--loss)]' : 'text-[var(--profit)]'}`}>
                          {money(r.amount)}
                        </td>
                        {isProp && (
                          <td className="py-3 px-4"><StatusBadge status={r.status} /></td>
                        )}
                        <td className="py-3 px-4 text-[var(--text-primary)]">
                          {isProp ? (r.firm_name || '—') : `${r.broker_name || '—'} — ${r.personal_account_name || ''}`}
                        </td>
                        {isProp && (
                          <td className="py-3 px-4 text-[var(--text-secondary)]">{r.stage_type || '—'}</td>
                        )}
                        <td className="py-3 px-4 text-[var(--text-secondary)]">
                          {isProp ? (r.destination_account_name || '—') : (r.financial_account_name || '—')}
                        </td>
                        <td className="py-3 px-4 text-[var(--text-secondary)] truncate max-w-[200px]">
                          {r.note || r.description || '—'}
                        </td>
                        <td className="py-3 px-4">
                            <div className="flex items-center gap-2">
                              {(
                                <button
                                  onClick={() => isProp ? openPropEdit(r) : openBrokerEdit(r)}
                                  disabled={saving}
                                  title="ویرایش گردش و اصلاح موجودی هر دو حساب"
                                  className="text-xs font-bold text-[var(--accent)] hover:underline disabled:opacity-40"
                                >
                                  ✏️
                                </button>
                              )}
                              {isProp && (r.allowed_transitions || []).map((s: string) => (
                                <button
                                  key={s}
                                  disabled={busyId === r.id}
                                  onClick={() => handleAdvance(r.id, s)}
                                  title={`تغییر وضعیت به ${STATUS_META[s]?.label || s}`}
                                  className={`text-[11px] font-bold px-2.5 py-1 rounded-[8px] border transition-all disabled:opacity-40 ${
                                    s === 'cancelled'
                                      ? 'text-[var(--loss)] border-[var(--loss)]/40 hover:bg-[var(--loss)]/10'
                                      : s === 'received'
                                      ? 'text-[var(--profit)] border-[var(--profit)]/40 hover:bg-[var(--profit)]/10'
                                      : 'text-[var(--accent)] border-[var(--accent)]/40 hover:bg-[var(--accent-soft)]'
                                  }`}
                                >
                                  {busyId === r.id ? '…' : STATUS_ACTION_LABEL[s] || s}
                                </button>
                              ))}
                              {isProp && r.status === 'received' && (
                                <button
                                  onClick={() => openTransfer(r)}
                                  title="ثبت انتقال بین‌حسابی"
                                  className="text-xs font-bold text-[var(--purple)] hover:underline"
                                >
                                  🔄
                                </button>
                              )}
                              <button
                                onClick={() => handleDelete(r.id)}
                                title="حذف"
                                className="text-xs font-bold text-[var(--loss)] hover:underline"
                              >
                                🗑️
                              </button>
                            </div>
                          </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
      {/* فاز ۳۳ — Modal انتقال بین‌حسابی (درآمد نیست) */}
      {transferRow && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
          onClick={() => setTransferRow(null)}
        >
          <div
            className="w-full max-w-xl bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-6 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-3">
              <div
                className="w-11 h-11 rounded-[14px] flex items-center justify-center text-xl text-white"
                style={{ background: 'linear-gradient(135deg, var(--purple), var(--purple-light))' }}
              >
                🔄
              </div>
              <div>
                <h3 className="text-lg font-extrabold text-[var(--text-primary)]">ثبت انتقال بین‌حسابی</h3>
                <p className="text-[11px] text-[var(--text-muted)]">
                  انتقال از کیف‌پول یا صرافی به بانک در گزارش درآمد می‌آید؛ انتقال بین دو حساب بانکی درآمد تازه نیست.
                </p>
              </div>
            </div>

            <div className="text-[11px] text-[var(--text-secondary)] bg-[var(--accent-soft)] rounded-[10px] px-3 py-2 my-4">
              زنجیرهٔ نمونه: Prop → Trust Wallet → Exchange → IRR → Bank Card
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">📤 حساب مبدأ</label>
                <select
                  className={inputCls}
                  value={transferForm.from_account_id}
                  onChange={(e) => setTransferForm({ ...transferForm, from_account_id: e.target.value })}
                >
                  <option value="">— (حساب مقصد همان برداشت)</option>
                  {transferAccounts.map((a: any) => (
                    <option key={a.id} value={a.id}>{a.name} ({a.currency})</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">📥 حساب مقصد</label>
                <select
                  className={inputCls}
                  value={transferForm.to_account_id}
                  onChange={(e) => setTransferForm({ ...transferForm, to_account_id: e.target.value })}
                >
                  <option value="">انتخاب حساب…</option>
                  {transferAccounts.map((a: any) => (
                    <option key={a.id} value={a.id}>{a.name} ({a.currency})</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">💵 مبلغ</label>
                <input
                  type="number"
                  className={inputCls}
                  value={transferForm.amount}
                  placeholder="مثلاً 500"
                  onChange={(e) => setTransferForm({ ...transferForm, amount: e.target.value })}
                />
              </div>
              <div>
                <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">💱 ارز</label>
                <select
                  className={inputCls}
                  value={transferForm.currency}
                  onChange={(e) => setTransferForm({ ...transferForm, currency: e.target.value })}
                >
                  <option value="USDT">USDT</option>
                  <option value="IRR">IRR</option>
                </select>
              </div>
              <div className="md:col-span-2">
                <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">📅 تاریخ انتقال (شمسی)</label>
                <PersianDateInput
                  value={transferForm.date}
                  onChange={(iso) => setTransferForm({ ...transferForm, date: iso })}
                />
              </div>
              <div className="md:col-span-2">
                <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">📝 توضیحات</label>
                <input
                  className={inputCls}
                  value={transferForm.note}
                  placeholder="اختیاری"
                  onChange={(e) => setTransferForm({ ...transferForm, note: e.target.value })}
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setTransferRow(null)}
                className="px-5 py-3 rounded-[12px] text-sm font-extrabold bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] text-[var(--text-secondary)]"
              >
                انصراف
              </button>
              <button
                onClick={handleTransferSubmit}
                disabled={transferSaving}
                className="text-white px-7 py-3 rounded-[12px] text-sm font-extrabold shadow-[0_6px_16px_rgba(99,102,241,0.3)] disabled:opacity-50"
                style={{ background: 'linear-gradient(135deg, var(--purple), var(--purple-light))' }}
              >
                {transferSaving ? '⏳ در حال ثبت…' : '🔄 ثبت انتقال'}
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}




