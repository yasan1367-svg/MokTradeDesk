import { useState, useEffect } from 'react';
import {
  getBrokers, createBroker, updateBroker, deleteBroker,
  getPersonalTradingAccounts, createPersonalTradingAccount,
  updatePersonalTradingAccount, deletePersonalTradingAccount,
} from '../api/client';
import { useToast } from '../components/ToastProvider';
import EmptyState from '../components/ui/EmptyState';

type Broker = {
  id: number;
  name: string;
  website?: string | null;
  notes?: string | null;
  is_active: boolean;
  created_at?: string;
};

type PTA = {
  id: number;
  broker_id: number;
  broker_name?: string;
  account_number: string;
  account_label?: string | null;
  currency: string;
  initial_balance: number;
  current_balance: number;
  is_active: boolean;
};

const inputCls = 'w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[12px] px-4 py-2.5 text-[var(--text-primary)] text-sm focus:border-[var(--accent)] focus:outline-none';

export default function BrokersPage() {
  const toast = useToast();
  const [brokers, setBrokers] = useState<Broker[]>([]);
  const [accounts, setAccounts] = useState<PTA[]>([]);
  const [loading, setLoading] = useState(true);

  const [showBrokerForm, setShowBrokerForm] = useState(false);
  const [editBroker, setEditBroker] = useState<Broker | null>(null);
  const [showAccountForm, setShowAccountForm] = useState(false);
  const [editAccount, setEditAccount] = useState<PTA | null>(null);
  const [selectedBrokerId, setSelectedBrokerId] = useState<number | null>(null);

  const loadAll = async () => {
    setLoading(true);
    try {
      const [b, a] = await Promise.all([getBrokers(), getPersonalTradingAccounts()]);
      setBrokers(b.data || []);
      setAccounts(a.data || []);
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'خطا در بارگذاری بروکرها');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadAll(); }, []);

  if (loading) return <div className="text-center py-16 text-[var(--text-secondary)]">⏳ در حال بارگذاری...</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-[14px] flex items-center justify-center text-2xl text-white"
               style={{ background: 'linear-gradient(135deg, var(--accent), var(--accent-strong))' }}>🏢</div>
          <div>
            <h2 className="text-2xl font-extrabold text-[var(--text-primary)]">بروکرها و حساب‌های معاملاتی</h2>
            <p className="text-xs text-[var(--text-secondary)] mt-0.5">
              بروکر و حساب شخصی بساز تا در واردات معاملات و گردش مالی بروکر استفاده کنی.
            </p>
          </div>
        </div>
        <button
          onClick={() => { setEditBroker(null); setShowBrokerForm(true); }}
          className="text-white px-5 py-3 rounded-[12px] text-sm font-extrabold shadow-[0_6px_16px_rgba(63,124,255,0.3)] hover:-translate-y-0.5 transition-all"
          style={{ background: 'linear-gradient(135deg, var(--accent), var(--accent-strong))' }}
        >
          🆕 بروکر جدید
        </button>
      </div>

      {showBrokerForm && (
        <BrokerForm
          key={editBroker ? `edit-${editBroker.id}` : 'create'}
          initialData={editBroker}
          onSave={async (data) => {
            if (editBroker) {
              await updateBroker(editBroker.id, data);
              toast.success('بروکر به‌روزرسانی شد');
            } else {
              await createBroker(data);
              toast.success('بروکر ساخته شد');
            }
            setShowBrokerForm(false); setEditBroker(null); await loadAll();
          }}
          onCancel={() => { setShowBrokerForm(false); setEditBroker(null); }}
        />
      )}

      {showAccountForm && selectedBrokerId !== null && (
        <AccountForm
          key={editAccount ? `edit-${editAccount.id}` : `create-${selectedBrokerId}`}
          initialData={editAccount}
          onSave={async (data) => {
            if (editAccount) {
              await updatePersonalTradingAccount(editAccount.id, data);
              toast.success('حساب معاملاتی به‌روزرسانی شد');
            } else {
              await createPersonalTradingAccount({ ...data, broker_id: selectedBrokerId });
              toast.success('حساب معاملاتی ساخته شد');
            }
            setShowAccountForm(false); setEditAccount(null); setSelectedBrokerId(null); await loadAll();
          }}
          onCancel={() => { setShowAccountForm(false); setEditAccount(null); setSelectedBrokerId(null); }}
        />
      )}

      {brokers.length === 0 ? (
        <EmptyState
          icon="🏢"
          title="هیچ بروکری ثبت نشده"
          description="برای شروع، یک بروکر جدید بساز (مثلاً SGB Broker)"
          actionLabel="بروکر جدید"
          onAction={() => { setEditBroker(null); setShowBrokerForm(true); }}
        />
      ) : (
        <div className="space-y-4">
          {brokers.map((broker) => {
            const brokerAccounts = accounts.filter((a) => a.broker_id === broker.id);
            return (
              <div key={broker.id} className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-5">
                <div className="flex items-start justify-between flex-wrap gap-3 mb-4">
                  <div>
                    <div className="text-lg font-extrabold text-[var(--text-primary)]">
                      {broker.name}
                      {!broker.is_active && <span className="text-xs text-[var(--text-secondary)] mr-2">(غیرفعال)</span>}
                    </div>
                    {broker.website && <div className="text-xs text-[var(--text-secondary)] mt-1">🌐 {broker.website}</div>}
                    {broker.notes && <div className="text-xs text-[var(--text-secondary)] mt-1">📝 {broker.notes}</div>}
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => { setSelectedBrokerId(broker.id); setEditAccount(null); setShowAccountForm(true); }}
                      className="text-xs px-3 py-2 rounded-lg bg-[var(--accent-soft)] text-[var(--accent)] font-bold hover:bg-[var(--accent)] hover:text-white transition-all"
                    >
                      ➕ حساب معاملاتی
                    </button>
                    <button
                      onClick={() => { setEditBroker(broker); setShowBrokerForm(true); }}
                      className="text-xs px-3 py-2 rounded-lg bg-[var(--bg-base)] text-[var(--text-secondary)] hover:text-[var(--accent)] transition-all"
                    >✏️</button>
                    <button
                      onClick={async () => {
                        if (!confirm(`بروکر «${broker.name}» حذف شود؟`)) return;
                        try {
                          await deleteBroker(broker.id);
                          toast.success('بروکر حذف شد');
                          await loadAll();
                        } catch (err: any) {
                          toast.error(err?.response?.data?.detail || 'حذف ممکن نشد');
                        }
                      }}
                      className="text-xs px-3 py-2 rounded-lg bg-[var(--bg-base)] text-[var(--text-secondary)] hover:text-red-500 transition-all"
                    >🗑️</button>
                  </div>
                </div>

                {brokerAccounts.length === 0 ? (
                  <div className="text-xs text-[var(--text-secondary)] text-center py-4 bg-[var(--bg-input)] rounded-[14px]">
                    هیچ حساب معاملاتی برای این بروکر ساخته نشده
                  </div>
                ) : (
                  <div className="space-y-2">
                    {brokerAccounts.map((acc) => (
                      <div key={acc.id} className="flex items-center justify-between bg-[var(--bg-input)] border border-[var(--border-subtle)] rounded-[14px] px-4 py-3">
                        <div>
                          <div className="text-sm font-bold text-[var(--text-primary)]">{acc.account_label || acc.account_number}</div>
                          <div className="text-xs text-[var(--text-secondary)] mt-0.5">
                            شماره: {acc.account_number} • ارز: {acc.currency} {!acc.is_active && '• (غیرفعال)'}
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          <div className="text-left">
                            <div className="text-sm font-extrabold text-[var(--text-primary)]">
                              {acc.current_balance?.toLocaleString() ?? 0}
                            </div>
                            <div className="text-[10px] text-[var(--text-secondary)]">{acc.currency}</div>
                          </div>
                          <button
                            onClick={() => { setSelectedBrokerId(broker.id); setEditAccount(acc); setShowAccountForm(true); }}
                            className="w-8 h-8 rounded-lg bg-[var(--bg-base)] text-[var(--text-secondary)] hover:text-[var(--accent)] flex items-center justify-center text-xs"
                          >✏️</button>
                          <button
                            onClick={async () => {
                              if (!confirm(`حساب «${acc.account_label || acc.account_number}» حذف شود؟`)) return;
                              try {
                                await deletePersonalTradingAccount(acc.id);
                                toast.success('حساب حذف شد');
                                await loadAll();
                              } catch (err: any) {
                                toast.error(err?.response?.data?.detail || 'حذف ممکن نشد');
                              }
                            }}
                            className="w-8 h-8 rounded-lg bg-[var(--bg-base)] text-[var(--text-secondary)] hover:text-red-500 flex items-center justify-center text-xs"
                          >🗑️</button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function BrokerForm({ initialData, onSave, onCancel }: {
  initialData: Broker | null;
  onSave: (data: any) => Promise<void>;
  onCancel: () => void;
}) {
  const [name, setName] = useState(initialData?.name || '');
  const [website, setWebsite] = useState(initialData?.website || '');
  const [notes, setNotes] = useState(initialData?.notes || '');
  const [isActive, setIsActive] = useState(initialData?.is_active ?? true);
  const [saving, setSaving] = useState(false);

  const submit = async () => {
    if (!name.trim()) return;
    setSaving(true);
    try {
      await onSave({
        name: name.trim(),
        website: website.trim() || undefined,
        notes: notes.trim() || undefined,
        is_active: isActive,
      });
    } finally { setSaving(false); }
  };

  return (
    <div className="bg-[var(--bg-card)] border-2 border-[var(--border-accent)] rounded-[22px] p-6">
      <h3 className="text-lg font-extrabold text-[var(--text-primary)] mb-5">
        {initialData ? '✏️ ویرایش بروکر' : '🆕 بروکر جدید'}
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5">
        <div className="md:col-span-2">
          <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">نام بروکر *</label>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="مثلاً SGB Broker" className={inputCls} />
        </div>
        <div>
          <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">وب‌سایت</label>
          <input value={website} onChange={(e) => setWebsite(e.target.value)} placeholder="https://..." className={inputCls} />
        </div>
        <div className="flex items-end">
          <label className="flex items-center gap-2 text-sm text-[var(--text-primary)] cursor-pointer">
            <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
            فعال
          </label>
        </div>
        <div className="md:col-span-2">
          <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">یادداشت</label>
          <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} className={inputCls + ' resize-none'} />
        </div>
      </div>
      <div className="flex justify-end gap-3">
        <button onClick={onCancel} className="px-5 py-3 rounded-[12px] text-sm font-extrabold bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] text-[var(--text-secondary)]">انصراف</button>
        <button onClick={submit} disabled={!name.trim() || saving}
                className="text-white px-7 py-3 rounded-[12px] text-sm font-extrabold disabled:opacity-50"
                style={{ background: 'linear-gradient(135deg, var(--accent), var(--accent-strong))' }}>
          {saving ? '⏳...' : initialData ? '💾 ذخیره' : '💾 ایجاد'}
        </button>
      </div>
    </div>
  );
}

function AccountForm({ initialData, onSave, onCancel }: {
  initialData: PTA | null;
  onSave: (data: any) => Promise<void>;
  onCancel: () => void;
}) {
  const [accountNumber, setAccountNumber] = useState(initialData?.account_number || '');
  const [accountLabel, setAccountLabel] = useState(initialData?.account_label || '');
  const [currency, setCurrency] = useState(initialData?.currency || 'USDT');
  const [initialBalance, setInitialBalance] = useState(String(initialData?.initial_balance ?? 0));
  const [isActive, setIsActive] = useState(initialData?.is_active ?? true);
  const [saving, setSaving] = useState(false);

  const submit = async () => {
    if (!accountNumber.trim()) return;
    setSaving(true);
    try {
      await onSave({
        account_number: accountNumber.trim(),
        account_label: accountLabel.trim() || undefined,
        currency,
        initial_balance: parseFloat(initialBalance) || 0,
        is_active: isActive,
      });
    } finally { setSaving(false); }
  };

  return (
    <div className="bg-[var(--bg-card)] border-2 border-[var(--border-accent)] rounded-[22px] p-6">
      <h3 className="text-lg font-extrabold text-[var(--text-primary)] mb-5">
        {initialData ? '✏️ ویرایش حساب معاملاتی' : '🆕 حساب معاملاتی جدید'}
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5">
        <div>
          <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">شماره حساب *</label>
          <input value={accountNumber} onChange={(e) => setAccountNumber(e.target.value)} placeholder="مثلاً SGB-001" className={inputCls} />
        </div>
        <div>
          <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">برچسب حساب</label>
          <input value={accountLabel} onChange={(e) => setAccountLabel(e.target.value)} placeholder="مثلاً SGB Personal USDT" className={inputCls} />
        </div>
        <div>
          <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">ارز</label>
          <select value={currency} onChange={(e) => setCurrency(e.target.value)} className={inputCls}>
            <option value="USDT">USDT</option>
            <option value="IRR">IRR</option>
          </select>
        </div>
        <div>
          <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">موجودی اولیه</label>
          <input type="number" value={initialBalance} onChange={(e) => setInitialBalance(e.target.value)} className={inputCls} />
        </div>
        <div className="md:col-span-2">
          <label className="flex items-center gap-2 text-sm text-[var(--text-primary)] cursor-pointer">
            <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
            فعال
          </label>
        </div>
      </div>
      <div className="flex justify-end gap-3">
        <button onClick={onCancel} className="px-5 py-3 rounded-[12px] text-sm font-extrabold bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] text-[var(--text-secondary)]">انصراف</button>
        <button onClick={submit} disabled={!accountNumber.trim() || saving}
                className="text-white px-7 py-3 rounded-[12px] text-sm font-extrabold disabled:opacity-50"
                style={{ background: 'linear-gradient(135deg, var(--accent), var(--accent-strong))' }}>
          {saving ? '⏳...' : initialData ? '💾 ذخیره' : '💾 ایجاد'}
        </button>
      </div>
    </div>
  );
}