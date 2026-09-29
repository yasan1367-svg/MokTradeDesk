import { useCallback, useEffect, useMemo, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import EmptyState from '../components/ui/EmptyState';
import PersianDateInput from '../components/PersianDateInput';
import { RiskSkeleton } from '../components/Skeleton';
import { useToast } from '../components/ToastProvider';
import {
  getPropPayouts,
  getPropPayoutsStats,
  createPropPayout,
  updatePropPayoutStatus,
  createPropPayoutTransfer,
  deletePropPayout,
  getBrokerPayouts,
  getBrokerPayoutsStats,
  getPropFirms,
  getAllPropStages,
  getFinanceAccountsForDestination,
} from '../api/client';
import { gregorianToJalali } from '../utils/jalali';

type Tab = 'prop' | 'broker';

// فاز ۳۳ — چرخهٔ عمر برداشت
const STATUS_META: Record<string, { label: string; cls: string; icon: string }> = {
  requested: { label: 'درخواست‌شده', icon: '🕐', cls: 'bg-[var(--bg-elevated)] text-[var(--text-secondary)] border-[var(--border-subtle)]' },
  approved: { label: 'تأییدشده', icon: '✅', cls: 'bg-[#3F7CFF]/15 text-[#3F7CFF] border-[#3F7CFF]/30' },
  processing: { label: 'در حال پردازش', icon: '⏳', cls: 'bg-[#F59E0B]/15 text-[#F59E0B] border-[#F59E0B]/30' },
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
    accent: 'linear-gradient(135deg, var(--accent), #5B8DEF)',
    profit: 'linear-gradient(135deg, var(--profit), #4DD9A9)',
    purple: 'linear-gradient(135deg, var(--purple), #A78BFA)',
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
  const [stages, setStages] = useState<any[]>([]);
  const [destAccounts, setDestAccounts] = useState<any[]>([]);
  const [saving, setSaving] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);

  // فاز ۳۳ — انتقال بین‌حسابی (Trust Wallet → Exchange → IRR → Bank Card)
  const [transferRow, setTransferRow] = useState<any | null>(null);
  const [transferSaving, setTransferSaving] = useState(false);
  const [transferForm, setTransferForm] = useState({
    from_account_id: '', to_account_id: '', amount: '', currency: '', date: '', note: '',
  });
  const [form, setForm] = useState({ prop_stage_id: '', amount: '', destination_account_id: '', withdrawal_date: '', note: '' });

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
        const [list, st] = await Promise.all([getBrokerPayouts(params), getBrokerPayoutsStats(params)]);
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
    if (tab !== 'prop') return;
    getPropFirms().then((r) => setFirms(r.data || [])).catch(() => {});
    getAllPropStages().then((r) => setStages(r.data || [])).catch(() => {});
    getFinanceAccountsForDestination().then((r) => setDestAccounts(r.data || [])).catch(() => {});
  }, [tab]);

  const handleSubmit = async () => {
    if (!form.prop_stage_id || !form.amount || !form.destination_account_id) {
      toast.warning('مرحله، مبلغ و حساب مقصد الزامی است');
      return;
    }
    setSaving(true);
    try {
      await createPropPayout({
        prop_stage_id: Number(form.prop_stage_id),
        amount: Number(form.amount),
        destination_account_id: Number(form.destination_account_id),
        withdrawal_date: form.withdrawal_date || undefined,
        note: form.note || undefined,
      });
      toast.success('برداشت با موفقیت ثبت شد');
      setShowForm(false);
      setForm({ prop_stage_id: '', amount: '', destination_account_id: '', withdrawal_date: '', note: '' });
      load();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'خطا در ثبت برداشت');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await deletePropPayout(id);
      toast.success('برداشت حذف شد');
      load();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'خطا در حذف برداشت');
    }
  };

  // فاز ۳۳ — تغییر وضعیت برداشت (REQUESTED → APPROVED → PROCESSING → RECEIVED / CANCELLED)
  const handleAdvance = async (id: number, status: string) => {
    if (
      status === 'received' &&
      !window.confirm('با ثبت «دریافت»، این مبلغ وارد حسابداری مالی (درآمد) می‌شود. ادامه؟')
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
      currency: row.currency || 'USD',
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
      toast.success('انتقال ثبت شد (درآمد نیست)');
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
  const chartData = (stats?.monthly || []).map((m: any) => ({ name: m.month, amount: m.amount }));
  const money = (v: any) => `$${Number(v || 0).toLocaleString('en-US', { maximumFractionDigits: 2 })}`;

  return (
    <div className="space-y-6">
      {/* هدر */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-[14px] flex items-center justify-center text-2xl text-white"
               style={{ background: 'linear-gradient(135deg, var(--accent), #5B8DEF)' }}>💸</div>
          <div>
            <h2 className="text-2xl font-extrabold text-[var(--text-primary)]">تاریخچهٔ برداشت‌ها</h2>
            <p className="text-xs text-[var(--text-secondary)] mt-0.5">پراپ و بروکر — آمار و تاریخچهٔ کامل</p>
          </div>
        </div>
        {isProp && (
          <button
            onClick={() => setShowForm((v) => !v)}
            className="text-white px-5 py-3 rounded-[12px] text-sm font-extrabold shadow-[0_6px_16px_rgba(19,174,129,0.3)] hover:-translate-y-0.5 transition-all"
            style={{ background: 'linear-gradient(135deg, var(--profit), #4DD9A9)' }}
          >
            ➕ ثبت برداشت جدید
          </button>
        )}
      </div>

      {/* تب‌ها */}
      <div className="flex gap-2 bg-[var(--bg-elevated)] p-1.5 rounded-[14px] w-fit">
        {([['prop', '🏢 پراپ'], ['broker', '📈 بروکر']] as [Tab, string][]).map(([k, label]) => (
          <button
            key={k}
            onClick={() => setTab(k)}
            className={`px-5 py-2 rounded-[10px] text-sm font-extrabold transition-all ${
              tab === k ? 'bg-[var(--accent)] text-white' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* فرم ثبت برداشت جدید (فقط پراپ) */}
      {isProp && showForm && (
        <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-6 shadow-md">
          <div className="flex items-center gap-3 mb-5 pb-4 border-b border-[var(--border-subtle)]">
            <div className="w-11 h-11 rounded-[14px] flex items-center justify-center text-xl text-white"
                 style={{ background: 'linear-gradient(135deg, var(--profit), #4DD9A9)' }}>➕</div>
            <h3 className="text-lg font-extrabold text-[var(--text-primary)]">ثبت برداشت جدید</h3>
            <span className="text-[11px] text-[var(--text-muted)]">وضعیت اولیه: «درخواست‌شده» — با دکمه‌های جدول → تأیید → پردازش → دریافت</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            <div>
              <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">🏢 مرحله (رییل)</label>
              <select className={inputCls} value={form.prop_stage_id}
                      onChange={(e) => setForm({ ...form, prop_stage_id: e.target.value })}>
                <option value="">انتخاب مرحله…</option>
                {stages.filter((s: any) => s.stage_type === 'funded_real').map((s: any) => (
                  <option key={s.id} value={s.id}>{s.display_name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">💵 مبلغ</label>
              <input type="number" className={inputCls} value={form.amount} placeholder="مثلاً 500"
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
                    style={{ background: 'linear-gradient(135deg, var(--profit), #4DD9A9)' }}>
              {saving ? '⏳ در حال ثبت…' : '💾 ثبت برداشت'}
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
              <option value="">همه</option>
              <option value="USD">USD</option>
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
            <StatCard icon="💵" label="مجموع برداشت‌ها" value={money(stats?.total)} />
            <StatCard icon="🔢" label="تعداد برداشت‌ها" value={String(stats?.count ?? 0)} tone="purple" />
            <StatCard icon="📊" label="میانگین برداشت" value={money(stats?.average)} tone="profit" />
            <StatCard icon="🏆" label="بزرگ‌ترین برداشت" value={money(stats?.largest)} />
          </div>

          {/* نمودار برداشت‌ها در طول زمان */}
          {chartData.length > 0 && (
            <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-6 shadow-md">
              <h3 className="text-base font-extrabold text-[var(--text-primary)] mb-4">📈 برداشت‌ها در طول زمان</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
                    <XAxis dataKey="name" tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} />
                    <YAxis tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} />
                    <Tooltip contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 12, color: 'var(--text-primary)' }} />
                    <Bar dataKey="amount" fill="var(--accent)" radius={[6, 6, 0, 0]} />
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
                    <div className="text-[11px] text-[var(--text-muted)]">{x.count} برداشت</div>
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
                title="برداشتی ثبت نشده"
                description="با ثبت اولین برداشت، این جدول پر می‌شود"
              />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-[var(--border-subtle)] text-[var(--text-secondary)]">
                      <th className="text-right py-3 px-4">تاریخ</th>
                      <th className="text-right py-3 px-4">مبلغ</th>
                      {isProp && <th className="text-right py-3 px-4">وضعیت</th>}
                      <th className="text-right py-3 px-4">{isProp ? 'پراپ' : 'بروکر'}</th>
                      {isProp && <th className="text-right py-3 px-4">مرحله</th>}
                      <th className="text-right py-3 px-4">حساب مقصد</th>
                      <th className="text-right py-3 px-4">توضیحات</th>
                      {isProp && <th className="text-right py-3 px-4">عملیات</th>}
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
                        <td className="py-3 px-4 font-extrabold text-[var(--profit)]">{money(r.amount)}</td>
                        {isProp && (
                          <td className="py-3 px-4"><StatusBadge status={r.status} /></td>
                        )}
                        <td className="py-3 px-4 text-[var(--text-primary)]">
                          {isProp ? (r.firm_name || '—') : (r.broker_name || r.account_name || '—')}
                        </td>
                        {isProp && (
                          <td className="py-3 px-4 text-[var(--text-secondary)]">{r.stage_type || '—'}</td>
                        )}
                        <td className="py-3 px-4 text-[var(--text-secondary)]">
                          {r.destination_account_name || r.account_name || '—'}
                        </td>
                        <td className="py-3 px-4 text-[var(--text-secondary)] truncate max-w-[200px]">
                          {r.note || r.description || '—'}
                        </td>
                        {isProp && (
                          <td className="py-3 px-4">
                            <div className="flex items-center gap-2">
                              {(r.allowed_transitions || []).map((s: string) => (
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
                              {r.status === 'received' && (
                                <button
                                  onClick={() => openTransfer(r)}
                                  title="ثبت انتقال بین‌حسابی (درآمد نیست)"
                                  className="text-xs font-bold text-[#6366f1] hover:underline"
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
                        )}
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
                style={{ background: 'linear-gradient(135deg, #6366f1, #A78BFA)' }}
              >
                🔄
              </div>
              <div>
                <h3 className="text-lg font-extrabold text-[var(--text-primary)]">ثبت انتقال بین‌حسابی</h3>
                <p className="text-[11px] text-[var(--text-muted)]">
                  این انتقال <b>درآمد نیست</b>؛ فقط بین حساب‌های مالی جابه‌جا می‌شود.
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
                  <option value="USD">USD</option>
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
                style={{ background: 'linear-gradient(135deg, #6366f1, #A78BFA)' }}
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




