import { useState, useEffect } from 'react';
import { getSettings, updateSettings } from '../api/client';
import BackupManager from '../components/BackupManager';

export default function SettingsPage() {
  const [tab, setTab] = useState<'general' | 'backup'>('general');
  const [settings, setSettings] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getSettings()
      .then((res) => setSettings(res.data))
      .catch(() => setError('خطا در بارگذاری تنظیمات'))
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      await updateSettings(settings);
      setSuccessMessage('تنظیمات با موفقیت ذخیره شد');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'خطا');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="text-center py-12 text-[var(--text-muted)]">⏳ در حال بارگذاری...</div>;
  if (!settings) return <div className="text-center py-12 text-[var(--loss)]">خطا در بارگذاری</div>;

  return (
    <div className="space-y-6 max-w-4xl">
      {error && (
        <div className="bg-[var(--loss-soft)] border border-[var(--loss-border)] text-[var(--loss)] p-4 rounded-[14px] text-sm font-semibold">
          ❌ {error}
        </div>
      )}
      {successMessage && (
        <div className="bg-[var(--profit-soft)] border border-[var(--profit-border)] text-[var(--profit)] p-4 rounded-[14px] text-sm font-semibold">
          ✅ {successMessage}
        </div>
      )}

      {/* تب‌ها (فاز ۱۷) */}
      <div className="flex gap-2 bg-[var(--bg-elevated)] p-1.5 rounded-[14px] w-fit">
        {([['general', '⚙️ تنظیمات عمومی'], ['backup', '💾 Backup']] as const).map(([k, label]) => (
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

      {tab === 'backup' ? (
        <BackupManager />
      ) : (
        <>
      {/* ظاهر */}
      <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-6 shadow-md">
        <div className="flex items-center gap-3 mb-6 pb-4 border-b border-[var(--border-subtle)]">
          <div className="w-11 h-11 rounded-[14px] flex items-center justify-center text-xl text-white"
            style={{ background: 'linear-gradient(135deg, #3F7CFF, #5B8DEF)' }}>🎨</div>
          <div>
            <h3 className="text-lg font-extrabold text-[var(--text-primary)]">ظاهر و نمایش</h3>
            <p className="text-[12px] text-[var(--text-secondary)] mt-0.5">تم، فونت و اندازه</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div>
            <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">🎨 تم</label>
            <select
              value={settings.theme}
              onChange={(e) => setSettings({ ...settings, theme: e.target.value })}
              className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[12px] px-5 py-3 text-[var(--text-primary)] text-sm font-bold focus:border-[var(--accent)] focus:outline-none cursor-pointer"
            >
              <option value="dark">🌙 تیره (Dark)</option>
              <option value="light">☀️ روشن (Light)</option>
              <option value="system">💻 سیستم</option>
            </select>
          </div>

          <div>
            <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">📏 اندازه‌ی فونت</label>
            <select
              value={settings.font_size}
              onChange={(e) => setSettings({ ...settings, font_size: Number(e.target.value) })}
              className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[12px] px-5 py-3 text-[var(--text-primary)] text-sm font-bold focus:border-[var(--accent)] focus:outline-none cursor-pointer"
            >
              <option value={12}>کوچک (۱۲px)</option>
              <option value={14}>متوسط (۱۴px)</option>
              <option value={16}>بزرگ (۱۶px)</option>
              <option value={18}>خیلی بزرگ (۱۸px)</option>
            </select>
          </div>
        </div>
      </div>

      {/* منطقه‌ی زمانی و ارز */}
      <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-6 shadow-md">
        <div className="flex items-center gap-3 mb-6 pb-4 border-b border-[var(--border-subtle)]">
          <div className="w-11 h-11 rounded-[14px] flex items-center justify-center text-xl text-white"
            style={{ background: 'linear-gradient(135deg, #7959D6, #A78BFA)' }}>🌍</div>
          <div>
            <h3 className="text-lg font-extrabold text-[var(--text-primary)]">منطقه و ارز</h3>
            <p className="text-[12px] text-[var(--text-secondary)] mt-0.5">منطقه‌ی زمانی، ارز و تقویم</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          <div>
            <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">🕐 منطقه‌ی زمانی</label>
            <select
              value={settings.timezone}
              onChange={(e) => setSettings({ ...settings, timezone: e.target.value })}
              className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[12px] px-5 py-3 text-[var(--text-primary)] text-sm font-bold focus:border-[var(--purple)] focus:outline-none cursor-pointer"
            >
              <option value="Asia/Tehran">🇮🇷 Tehran</option>
              <option value="UTC">🌍 UTC</option>
              <option value="America/New_York">🇺🇸 New York</option>
              <option value="Europe/London">🇬🇧 London</option>
              <option value="Asia/Tokyo">🇯🇵 Tokyo</option>
            </select>
          </div>

          <div>
            <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">💵 ارز</label>
            <select
              value={settings.currency}
              onChange={(e) => setSettings({ ...settings, currency: e.target.value })}
              className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[12px] px-5 py-3 text-[var(--text-primary)] text-sm font-bold focus:border-[var(--purple)] focus:outline-none cursor-pointer"
            >
              <option value="USDT">USDT</option>
              <option value="IRR">IRR - ریال</option>
            </select>
          </div>

          <div>
            <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">📅 تقویم</label>
            <select
              value={settings.calendar}
              onChange={(e) => setSettings({ ...settings, calendar: e.target.value })}
              className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[12px] px-5 py-3 text-[var(--text-primary)] text-sm font-bold focus:border-[var(--purple)] focus:outline-none cursor-pointer"
            >
              <option value="persian">🌙 شمسی</option>
              <option value="gregorian">🌍 میلادی</option>
            </select>
          </div>
        </div>
      </div>

      {/* پیش‌فرض‌های ریسک */}
      <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-6 shadow-md">
        <div className="flex items-center gap-3 mb-6 pb-4 border-b border-[var(--border-subtle)]">
          <div className="w-11 h-11 rounded-[14px] flex items-center justify-center text-xl text-white"
            style={{ background: 'linear-gradient(135deg, #13AE81, #4DD9A9)' }}>⚙️</div>
          <div>
            <h3 className="text-lg font-extrabold text-[var(--text-primary)]">پیش‌فرض‌های ریسک و پراپ</h3>
            <p className="text-[12px] text-[var(--text-secondary)] mt-0.5">مقادیر پیش‌فرض برای ساخت جدید</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div>
            <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">⚠️ ریسک پیش‌فرض (%)</label>
            <input
              type="number"
              value={settings.default_risk_percent}
              onChange={(e) => setSettings({ ...settings, default_risk_percent: Number(e.target.value) })}
              className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[12px] px-5 py-3 text-[var(--text-primary)] text-sm font-bold focus:border-[var(--profit)] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">🏢 سهم کاربر در پراپ (%)</label>
            <input
              type="number"
              value={settings.default_profit_share}
              onChange={(e) => setSettings({ ...settings, default_profit_share: Number(e.target.value) })}
              className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[12px] px-5 py-3 text-[var(--text-primary)] text-sm font-bold focus:border-[var(--profit)] focus:outline-none"
            />
          </div>
        </div>
      </div>

      {/* دکمه‌ی ذخیره */}
      <div className="flex justify-end">
        <button
          onClick={handleSave}
          disabled={saving}
          className="text-white px-8 py-4 rounded-[12px] text-sm font-extrabold shadow-[0_6px_20px_rgba(63,124,255,0.4)] hover:shadow-[0_10px_28px_rgba(63,124,255,0.5)] hover:-translate-y-0.5 transition-all disabled:opacity-50"
          style={{ background: 'linear-gradient(135deg, #3F7CFF, #5B8DEF)' }}
        >
          {saving ? '⏳ در حال ذخیره...' : '💾 ذخیره‌ی تنظیمات'}
        </button>
      </div>
        </>
      )}
    </div>
  );
}
