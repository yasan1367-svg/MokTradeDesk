import { useState, useEffect } from 'react';
import GlassCard from './GlassCard';

interface CategoryFormProps {
  mode: 'create' | 'edit';
  initialData?: {
    id: number;
    name: string;
    type: string;
    color?: string;
    icon?: string;
  };
  onSave: (data: Record<string, any>) => Promise<void>;
  onCancel: () => void;
}

const CATEGORY_TYPES = [
  { value: 'income', label: '💰 درآمد' },
  { value: 'expense', label: '💸 هزینه' },
  { value: 'transfer', label: '🔄 انتقال' },
  { value: 'exchange', label: '💱 تبدیل' },
];

const PRESET_COLORS = [
  '#22c55e', '#10b981', '#34d399', '#f97316', '#f59e0b',
  '#eab308', '#ef4444', '#ec4899', '#f43f5e', '#6366f1',
  '#8b5cf6', '#a855f7', '#3F7CFF', '#5B8DEF', '#6B7A94',
];

const PRESET_ICONS = [
  '💰', '🎯', '🏦', '💵', '🛒', '🔄', '🏛️', '💸', '📋', '↔️', '💱',
  '🍔', '🚗', '📄', '🎮', '🏥', '🎁', '📈', '📉', '🛡️', '📊', '⚡',
];

export default function CategoryForm({ mode, initialData, onSave, onCancel }: CategoryFormProps) {
  const [name, setName] = useState('');
  const [type, setType] = useState('expense');
  const [color, setColor] = useState('#3F7CFF');
  const [icon, setIcon] = useState('💰');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (mode === 'edit' && initialData) {
      setName(initialData.name);
      setType(initialData.type);
      setColor(initialData.color || '#3F7CFF');
      setIcon(initialData.icon || '💰');
    }
  }, [mode, initialData]);

  const handleSubmit = async () => {
    if (!name.trim()) return;
    setSaving(true);
    try {
      await onSave({
        name: name.trim(),
        type,
        color,
        icon,
      });
      setName('');
      setType('expense');
      setColor('#3F7CFF');
      setIcon('💰');
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
            {mode === 'create' ? 'دسته‌بندی جدید' : 'ویرایش دسته‌بندی'}
          </h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          {/* نام */}
          <div className="md:col-span-2">
            <label className="text-[var(--text-secondary)] text-xs block mb-1">نام دسته‌بندی *</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="مثلاً حقوق، خوراک، اینترنت..."
              className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-4 py-3 text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none transition-all"
            />
          </div>

          {/* نوع */}
          <div>
            <label className="text-[var(--text-secondary)] text-xs block mb-1">نوع *</label>
            <select
              value={type}
              onChange={(e) => setType(e.target.value)}
              className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-4 py-3 text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none transition-all"
            >
              {CATEGORY_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>

          {/* آیکون */}
          <div>
            <label className="text-[var(--text-secondary)] text-xs block mb-1">آیکون</label>
            <select
              value={icon}
              onChange={(e) => setIcon(e.target.value)}
              className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-4 py-3 text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none transition-all"
            >
              {PRESET_ICONS.map((ic) => (
                <option key={ic} value={ic}>{ic}</option>
              ))}
            </select>
          </div>

          {/* رنگ */}
          <div>
            <label className="text-[var(--text-secondary)] text-xs block mb-1">رنگ</label>
            <div className="flex items-center gap-3">
              <input
                type="color"
                value={color}
                onChange={(e) => setColor(e.target.value)}
                className="w-12 h-[42px] bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-0.5 py-0.5 cursor-pointer"
              />
              <div className="flex flex-wrap gap-1.5">
                {PRESET_COLORS.map((pc) => (
                  <button
                    key={pc}
                    onClick={() => setColor(pc)}
                    className={`w-7 h-7 rounded-lg border-2 transition-all ${
                      color === pc ? 'border-white scale-110 shadow-md' : 'border-transparent'
                    }`}
                    style={{ backgroundColor: pc }}
                  />
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* پیش‌نمایش */}
        <div className="mb-6 p-4 bg-[var(--bg-base)] rounded-[16px] flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl flex items-center justify-center text-2xl"
            style={{ backgroundColor: color + '20' }}>
            {icon}
          </div>
          <div>
            <div className="text-base font-extrabold text-[var(--text-primary)]">{name || 'نام دسته‌بندی'}</div>
            <div className="text-xs text-[var(--text-secondary)]">{CATEGORY_TYPES.find(t => t.value === type)?.label || type}</div>
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
            disabled={!name.trim() || saving}
            className="text-white px-7 py-3 rounded-[12px] text-sm font-extrabold shadow-[0_6px_16px_rgba(63,124,255,0.3)] hover:shadow-[0_10px_24px_rgba(63,124,255,0.4)] hover:-translate-y-0.5 transition-all disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:translate-y-0"
            style={{ background: 'linear-gradient(135deg, #3F7CFF, #5B8DEF)' }}
          >
            {saving ? '⌛ در حال ذخیره...' : mode === 'create' ? '💾 ایجاد دسته‌بندی' : '💾 ذخیره تغییرات'}
          </button>
        </div>
      </div>
    </GlassCard>
  );
}