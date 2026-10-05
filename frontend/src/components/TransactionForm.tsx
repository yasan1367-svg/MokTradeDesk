import { useState, useEffect } from 'react';
import GlassCard from './GlassCard';
import PersianDateInput from './PersianDateInput';

interface TransactionFormProps {
  mode: 'create' | 'edit';
  accounts: { id: number; name: string; type: string; currency: string }[];
  categories: { id: number; name: string; type: string; color?: string; icon?: string }[];
  initialData?: {
    id: number;
    account_id: number;
    category_id?: number | null;
    amount: number;
    currency: string;
    date: string;
    description?: string;
    type: string;
    from_account_id?: number | null;
    to_account_id?: number | null;
    related_trade_id?: number | null;
    related_prop_account_id?: number | null;
  };
  onSave: (data: Record<string, any>) => Promise<void>;
  onCancel: () => void;
}

const CURRENCIES = [
  { value: 'USDT', label: 'USDT' },
  { value: 'IRR', label: 'IRR 🇮🇷' },
];

const TRANSACTION_TYPES = [
  { value: 'deposit', label: '💵 واریز', color: '#22c55e' },
  { value: 'withdrawal', label: '🏧 برداشت', color: '#ef4444' },
  { value: 'transfer', label: '🔄 انتقال', color: '#8b5cf6' },
  { value: 'profit', label: '📈 سود', color: '#10b981' },
  { value: 'loss', label: '📉 ضرر', color: '#f97316' },
  { value: 'fee', label: '💸 کارمزد', color: '#eab308' },
  { value: 'purchase', label: '🛒 خرید', color: '#ec4899' },
];

export default function TransactionForm({
  mode, accounts, categories, initialData, onSave, onCancel
}: TransactionFormProps) {
  const [accountId, setAccountId] = useState<number | ''>('');
  const [categoryId, setCategoryId] = useState<number | ''>('');
  const [amount, setAmount] = useState('');
  const [currency, setCurrency] = useState('USDT');
  const [date, setDate] = useState('');
  const [description, setDescription] = useState('');
  const [type, setType] = useState('deposit');
  const [fromAccountId, setFromAccountId] = useState<number | ''>('');
  const [toAccountId, setToAccountId] = useState<number | ''>('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (mode === 'edit' && initialData) {
      setAccountId(initialData.account_id);
      setCategoryId(initialData.category_id ?? '');
      setAmount(String(initialData.amount));
      setCurrency(initialData.currency);
      setDate(initialData.date);
      setDescription(initialData.description || '');
      setType(initialData.type);
      setFromAccountId(initialData.from_account_id ?? '');
      setToAccountId(initialData.to_account_id ?? '');
    }
  }, [mode, initialData]);

  const needsTransferFields = type === 'transfer';
  const sourceAccount = accounts.find((account) => account.id === fromAccountId);
  const destinationAccount = accounts.find((account) => account.id === toAccountId);
  const selectedAccount = accounts.find((account) =>
    account.id === (needsTransferFields && destinationAccount ? toAccountId : accountId),
  );
  const transactionCurrency = selectedAccount?.currency || currency;
  const transferCurrencyMismatch = Boolean(
    needsTransferFields && sourceAccount && destinationAccount
      && (sourceAccount.currency !== destinationAccount.currency || sourceAccount.id === destinationAccount.id),
  );
  const currencyOptions = selectedAccount
    ? CURRENCIES.filter((item) => item.value === transactionCurrency)
    : CURRENCIES;

  useEffect(() => {
    if (transactionCurrency && transactionCurrency !== currency) setCurrency(transactionCurrency);
  }, [transactionCurrency, currency]);

  const isTransferValid = fromAccountId !== '' && toAccountId !== '' && !transferCurrencyMismatch;
  const isFormValid = (needsTransferFields ? isTransferValid : accountId !== '')
    && amount !== '' && Number.isFinite(Number(amount)) && Number(amount) > 0 && date !== '';

  const handleSubmit = async () => {
    if (!isFormValid) return;
    setSaving(true);
    try {
      await onSave({
        account_id: (needsTransferFields ? toAccountId : accountId) as number,
        category_id: categoryId !== '' ? (categoryId as number) : null,
        amount: parseFloat(amount) || 0,
        currency: transactionCurrency,
        date: date || undefined,
        description: description || null,
        type,
        from_account_id: needsTransferFields && fromAccountId !== '' ? (fromAccountId as number) : null,
        to_account_id: needsTransferFields && toAccountId !== '' ? (toAccountId as number) : null,
        related_trade_id: null,
        related_prop_account_id: null,
      });
      setAccountId('');
      setCategoryId('');
      setAmount('');
      setCurrency('USDT');
      setDate('');
      setDescription('');
      setType('deposit');
      setFromAccountId('');
      setToAccountId('');
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
            {mode === 'create' ? 'تراکنش جدید' : 'ویرایش تراکنش'}
          </h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          {/* نوع تراکنش */}
          <div>
            <label className="text-[var(--text-secondary)] text-xs block mb-1">نوع تراکنش *</label>
            <select
              value={type}
              onChange={(e) => setType(e.target.value)}
              className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-4 py-3 text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none transition-all"
            >
              {TRANSACTION_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
            {(type === 'deposit' || type === 'profit') && (
              <p className="text-xs text-[var(--text-secondary)] mt-1">
                {selectedAccount?.type === 'bank'
                  ? 'این مبلغ در گزارش درآمد حساب می‌شود.'
                  : selectedAccount
                    ? 'موجودی را افزایش می‌دهد؛ فقط مبالغ ثبت‌شده در حساب بانکی درآمد شمرده می‌شوند.'
                    : 'فقط مبالغ ثبت‌شده در حساب بانکی در گزارش درآمد محاسبه می‌شوند.'}
              </p>
            )}
            {needsTransferFields && destinationAccount && sourceAccount && (
              <p className="text-xs text-[var(--text-secondary)] mt-1">
                {destinationAccount.type === 'bank' && sourceAccount.type !== 'bank'
                  ? 'این انتقال در لحظهٔ رسیدن به بانک در گزارش درآمد می‌آید.'
                  : 'این انتقال درآمد بانکی تازه ثبت نمی‌کند.'}
              </p>
            )}
          </div>

          {/* حساب برای تراکنش عادی؛ انتقال حساب مبدأ و مقصد مستقل دارد */}
          {!needsTransferFields && (
            <div>
              <label className="text-[var(--text-secondary)] text-xs block mb-1">حساب *</label>
              <select
                value={accountId}
                onChange={(e) => setAccountId(e.target.value ? parseInt(e.target.value) : '')}
                className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-4 py-3 text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none transition-all"
              >
                <option value="">انتخاب حساب...</option>
                {accounts.map((a) => (
                  <option key={a.id} value={a.id}>{a.name} ({a.type})</option>
                ))}
              </select>
            </div>
          )}

          {/* مبلغ */}
          <div>
            <label className="text-[var(--text-secondary)] text-xs block mb-1">مبلغ *</label>
            <input
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="0"
              className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-4 py-3 text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none transition-all"
            />
          </div>

          {/* ارز */}
          <div>
            <label className="text-[var(--text-secondary)] text-xs block mb-1">ارز *</label>
            <select
              value={transactionCurrency}
              disabled={Boolean(selectedAccount)}
              onChange={(e) => setCurrency(e.target.value)}
              className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-4 py-3 text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none transition-all"
            >
              {currencyOptions.map((c) => (
                <option key={c.value} value={c.value}>{c.label}</option>
              ))}
            </select>
            {needsTransferFields && sourceAccount && destinationAccount && transferCurrencyMismatch && (
              <p className="text-xs text-[var(--loss)] mt-1">
                {sourceAccount.id === destinationAccount.id
                  ? 'حساب مبدأ و مقصد باید متفاوت باشند.'
                  : 'ارز حساب مبدأ و مقصد باید یکسان باشد.'}
              </p>
            )}
          </div>

          {/* تاریخ شمسی */}
          <div>
            <PersianDateInput
              label="تاریخ *"
              value={date}
              onChange={(v) => setDate(v)}
            />
          </div>

          {/* دسته‌بندی */}
          <div>
            <label className="text-[var(--text-secondary)] text-xs block mb-1">دسته‌بندی</label>
            <select
              value={categoryId}
              onChange={(e) => setCategoryId(e.target.value ? parseInt(e.target.value) : '')}
              className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-4 py-3 text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none transition-all"
            >
              <option value="">بدون دسته‌بندی</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.icon ? c.icon + ' ' : ''}{c.name} ({c.type})
                </option>
              ))}
            </select>
          </div>

          {/* فیلدهای انتقال - فقط برای transfer (فاز ۳۸.۴: exchange حذف شد) */}
          {needsTransferFields && (
            <>
              <div>
                <label className="text-[var(--text-secondary)] text-xs block mb-1">حساب مبدأ</label>
                <select
                  value={fromAccountId}
                  onChange={(e) => setFromAccountId(e.target.value ? parseInt(e.target.value) : '')}
                  className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-4 py-3 text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none transition-all"
                >
                  <option value="">انتخاب حساب مبدأ...</option>
                  {accounts.map((a) => (
                    <option key={a.id} value={a.id}>{a.name} ({a.type})</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-[var(--text-secondary)] text-xs block mb-1">حساب مقصد</label>
                <select
                  value={toAccountId}
                  onChange={(e) => setToAccountId(e.target.value ? parseInt(e.target.value) : '')}
                  className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-4 py-3 text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none transition-all"
                >
                  <option value="">انتخاب حساب مقصد...</option>
                  {accounts.map((a) => (
                    <option key={a.id} value={a.id}>{a.name} ({a.type})</option>
                  ))}
                </select>
              </div>
            </>
          )}

          {/* توضیحات */}
          <div className="md:col-span-2">
            <label className="text-[var(--text-secondary)] text-xs block mb-1">توضیحات</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="توضیحات تراکنش..."
              rows={3}
              className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-4 py-3 text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none transition-all resize-none"
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
          <button
            onClick={handleSubmit}
            disabled={!isFormValid || saving}
            className="text-white px-7 py-3 rounded-[12px] text-sm font-extrabold shadow-[0_6px_16px_rgba(63,124,255,0.3)] hover:shadow-[0_10px_24px_rgba(63,124,255,0.4)] hover:-translate-y-0.5 transition-all disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:translate-y-0"
            style={{ background: 'linear-gradient(135deg, var(--accent), var(--accent-strong))' }}
          >
            {saving ? '⌛ در حال ذخیره...' : mode === 'create' ? '💾 ثبت تراکنش' : '💾 ذخیره تغییرات'}
          </button>
        </div>
      </div>
    </GlassCard>
  );
}
