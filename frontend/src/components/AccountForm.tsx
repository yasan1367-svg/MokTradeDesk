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
  };
  allowedTypes?: string[];
  defaultType?: string;
  onSave: (data: Record<string, any>) => Promise<void>;
  onCancel: () => void;
}

const ACCOUNT_TYPES = [
  { value: 'bank', label: '🏦 بانک' },
  { value: 'exchange', label: '🔄 صرافی' },
  { value: 'crypto_wallet', label: '₿ کیف‌پول ارز دیجیتال' },
  { value: 'card', label: '💳 کارت بانکی' },        // فاز ۳۸.۲
  { value: 'cash', label: '💵 پول نقد' },            // فاز ۳۸.۲
  { value: 'trust_wallet', label: '🤝 کیف پول Trust' }, // فاز ۳۸.۲
];

const CURRENCIES = [
  { value: 'USDT', label: 'USDT' },
  { value: 'IRR', label: 'IRR 🇮🇷' },
];

export default function AccountForm({
  mode, initialData, allowedTypes, defaultType, onSave, onCancel,
}: AccountFormProps) {
  const [name, setName] = useState('');
  const [type, setType] = useState(defaultType || 'bank');
  const [currency, setCurrency] = useState('USDT');
  const currencyOptions = ['trust_wallet', 'crypto_wallet'].includes(type)
    ? CURRENCIES.filter((item) => item.value === 'USDT')
    : CURRENCIES;
  const [balance, setBalance] = useState('0');
  const [cardNumber, setCardNumber] = useState('');
  // فاز ۳۸.۳ — فیلدهای بی‌اثر `broker_name` / `prop_firm_name` / `prop_firm_id` حذف شدند
  // (در `AccountCreate` بک‌اند وجود ندارند ⇒ Pydantic بی‌صدا دور می‌ریخت)
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (mode === 'edit' && initialData) {
      setName(initialData.name);
      setType(initialData.type);
      setCurrency(
        ['trust_wallet', 'crypto_wallet'].includes(initialData.type)
          ? 'USDT'
          : initialData.currency,
      );
      setBalance(String(initialData.balance));
      setCardNumber(initialData.card_number || '');
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
      });
      setName('');
      setType(defaultType || 'bank');
      setCurrency('USDT');
      setBalance('0');
      setCardNumber('');
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
            {mode === 'create'
              ? allowedTypes ? 'کیف‌پول یا حساب صرافی جدید' : 'حساب مالی جدید'
              : allowedTypes ? 'ویرایش کیف‌پول یا حساب صرافی' : 'ویرایش حساب'}
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
              onChange={(e) => {
                const nextType = e.target.value;
                setType(nextType);
                if (['trust_wallet', 'crypto_wallet'].includes(nextType)) setCurrency('USDT');
              }}
              className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-4 py-3 text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none transition-all"
            >
              {ACCOUNT_TYPES.filter((t) => !allowedTypes || allowedTypes.includes(t.value)).map((t) => (
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
              {currencyOptions.map((c) => (
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
            {mode === 'create'
              ? allowedTypes ? '💾 ایجاد کیف‌پول/صرافی' : '💾 ایجاد حساب'
              : '💾 ذخیره تغییرات'}
          </LoadingButton>
        </div>
      </div>
    </GlassCard>
  );
}
