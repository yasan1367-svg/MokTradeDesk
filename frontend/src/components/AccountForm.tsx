import { useState, useEffect } from 'react';
import GlassCard from './GlassCard';
import LoadingButton from './ui/LoadingButton';

interface AccountFormProps {
  mode: 'create' | 'edit';
  initialData?: {
    id: number;
    name: string;
    type: string;
    currency: string;
    balance: number;
    card_number?: string;
    broker_name?: string;
    prop_firm_name?: string;
    prop_firm_id?: number | null;
  };
  onSave: (data: Record<string, any>) => Promise<void>;
  onCancel: () => void;
}

const ACCOUNT_TYPES = [
  { value: 'bank', label: '🏦 بانک' },
  { value: 'exchange', label: '🔄 صرافی' },
  { value: 'crypto_wallet', label: '₿ کیف‌پول ارز دیجیتال' },
  { value: 'broker', label: '📊 بروکر' },
  { value: 'prop', label: '🏢 پراپ' },
];

const CURRENCIES = [
  { value: 'USD', label: 'USD 🇺🇸' },
  { value: 'IRR', label: 'IRR 🇮🇷' },
];

export default function AccountForm({ mode, initialData, onSave, onCancel }: AccountFormProps) {
  const [name, setName] = useState('');
  const [type, setType] = useState('bank');
  const [currency, setCurrency] = useState('USD');
  const [balance, setBalance] = useState('0');
  const [cardNumber, setCardNumber] = useState('');
  const [brokerName, setBrokerName] = useState('');
  const [propFirmName, setPropFirmName] = useState('');
  const [propFirmId, setPropFirmId] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (mode === 'edit' && initialData) {
      setName(initialData.name);
      setType(initialData.type);
      setCurrency(initialData.currency);
      setBalance(String(initialData.balance));
      setCardNumber(initialData.card_number || '');
      setBrokerName(initialData.broker_name || '');
      setPropFirmName(initialData.prop_firm_name || '');
      setPropFirmId(initialData.prop_firm_id ? String(initialData.prop_firm_id) : '');
    }
  }, [mode, initialData]);

  const handleSubmit = async () => {
    if (!name.trim()) return;
    setSaving(true);
    try {
      await onSave({
        name: name.trim(),
        type,
        currency,
        balance: parseFloat(balance) || 0,
        card_number: cardNumber || null,
        broker_name: brokerName || null,
        prop_firm_name: propFirmName || null,
        prop_firm_id: propFirmId ? parseInt(propFirmId) : null,
      });
      setName('');
      setType('bank');
      setCurrency('USD');
      setBalance('0');
      setCardNumber('');
      setBrokerName('');
      setPropFirmName('');
      setPropFirmId('');
    } finally {
      setSaving(false);
    }
  };
  return (
    <GlassCard className="mb-6">
      <div className="p-6">
        <div className="flex items-center gap-3 mb-6 pb-4 border-b border-[var(--border-subtle)]">
          <span className="text-2xl">{mode === 'create' ? '🆕' : '✏️'}</span>
          <h3 className="text-base font-extrabold text-[var(--text-primary)]">
            {mode === 'create' ? 'حساب مالی جدید' : 'ویرایش حساب'}
          </h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          {/* نام */}
          <div className="md:col-span-2">
            <label className="text-[var(--text-secondary)] text-xs block mb-1">نام حساب *</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="مثلاً حساب بانکی ملت"
              className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-4 py-3 text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none transition-all"
            />
          </div>

          {/* نوع حساب */}
          <div>
            <label className="text-[var(--text-secondary)] text-xs block mb-1">نوع حساب *</label>
            <select
              value={type}
              onChange={(e) => setType(e.target.value)}
              className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-4 py-3 text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none transition-all"
            >
              {ACCOUNT_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>

          {/* ارز */}
          <div>
            <label className="text-[var(--text-secondary)] text-xs block mb-1">ارز</label>
            <select
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
              className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-4 py-3 text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none transition-all"
            >
              {CURRENCIES.map((c) => (
                <option key={c.value} value={c.value}>{c.label}</option>
              ))}
            </select>
          </div>

          {/* موجودی */}
          <div>
            <label className="text-[var(--text-secondary)] text-xs block mb-1">موجودی</label>
            <input
              type="number"
              value={balance}
              onChange={(e) => setBalance(e.target.value)}
              placeholder="0"
              className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-4 py-3 text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none transition-all"
            />
          </div>

          {/* شماره کارت */}
          <div>
            <label className="text-[var(--text-secondary)] text-xs block mb-1">شماره کارت</label>
            <input
              value={cardNumber}
              onChange={(e) => setCardNumber(e.target.value)}
              placeholder="6219-..."
              className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-4 py-3 text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none transition-all"
            />
          </div>

          {/* نام بروکر */}
          <div>
            <label className="text-[var(--text-secondary)] text-xs block mb-1">نام بروکر/صرافی</label>
            <input
              value={brokerName}
              onChange={(e) => setBrokerName(e.target.value)}
              placeholder="مثلاً Binance"
              className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-4 py-3 text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none transition-all"
            />
          </div>

          {/* نام پراپ */}
          <div>
            <label className="text-[var(--text-secondary)] text-xs block mb-1">نام پراپ فرم</label>
            <input
              value={propFirmName}
              onChange={(e) => setPropFirmName(e.target.value)}
              placeholder="مثلاً FTMO"
              className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-4 py-3 text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none transition-all"
            />
          </div>
        </div>

        {/* دکمه‌ها */}
        <div className="flex gap-3 justify-end">
          <button
            onClick={onCancel}
            className="bg-[var(--bg-card)] border border-[var(--border-subtle)] hover:border-[var(--border-accent)] text-[var(--text-secondary)] px-7 py-3 rounded-[12px] text-sm font-bold transition-all"
          >
            ✕ لغو
          </button>
          <LoadingButton
            onClick={handleSubmit}
            disabled={!name.trim()}
            loading={saving}
            loadingText="در حال ذخیره..."
            className="px-7"
          >
            {mode === 'create' ? '💾 ایجاد حساب' : '💾 ذخیره تغییرات'}
          </LoadingButton>
        </div>
      </div>
    </GlassCard>
  );
}