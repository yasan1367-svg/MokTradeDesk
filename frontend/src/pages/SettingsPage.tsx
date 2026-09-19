import { useState, useEffect } from 'react';
import { getSettings, updateSettings } from '../api/client';

export default function SettingsPage() {
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

  if (loading) return <div className="text-center py-12 text-[#9AA8BF]">⏳ در حال بارگذاری...</div>;
  if (!settings) return <div className="text-center py-12 text-[#E45D72]">خطا در بارگذاری</div>;

  return (
    <div className="space-y-6 max-w-4xl">
      {error && (
        <div className="bg-[#FFEDF0] border border-[#F0A6B2] text-[#E45D72] p-4 rounded-[14px] text-sm font-semibold">
          ❌ {error}
        </div>
      )}
      {successMessage && (
        <div className="bg-[#E5F8F1] border border-[#A8E6CF] text-[#13AE81] p-4 rounded-[14px] text-sm font-semibold">
          ✅ {successMessage}
        </div>
      )}

      {/* ظاهر */}
      <div className="bg-white border border-[#E5EBF3] rounded-[22px] p-6 shadow-md">
        <div className="flex items-center gap-3 mb-6 pb-4 border-b border-[#E5EBF3]">
          <div className="w-11 h-11 rounded-[14px] flex items-center justify-center text-xl text-white"
            style={{ background: 'linear-gradient(135deg, #3F7CFF, #5B8DEF)' }}>🎨</div>
          <div>
            <h3 className="text-lg font-extrabold text-[#1A2B47]">ظاهر و نمایش</h3>
            <p className="text-[12px] text-[#6B7A94] mt-0.5">تم، فونت و اندازه</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div>
            <label className="text-[13px] text-[#1A2B47] font-bold block mb-2">🎨 تم</label>
            <select
              value={settings.theme}
              onChange={(e) => setSettings({ ...settings, theme: e.target.value })}
              className="w-full bg-[#F8FAFF] border-2 border-[#E5EBF3] rounded-[12px] px-5 py-3 text-[#1A2B47] text-sm font-bold focus:border-[#3F7CFF] focus:outline-none cursor-pointer"
            >
              <option value="dark">🌙 تیره (Dark)</option>
              <option value="light">☀️ روشن (Light)</option>
              <option value="system">💻 سیستم</option>
            </select>
          </div>

          <div>
            <label className="text-[13px] text-[#1A2B47] font-bold block mb-2">📏 اندازه‌ی فونت</label>
            <select
              value={settings.font_size}
              onChange={(e) => setSettings({ ...settings, font_size: Number(e.target.value) })}
              className="w-full bg-[#F8FAFF] border-2 border-[#E5EBF3] rounded-[12px] px-5 py-3 text-[#1A2B47] text-sm font-bold focus:border-[#3F7CFF] focus:outline-none cursor-pointer"
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
      <div className="bg-white border border-[#E5EBF3] rounded-[22px] p-6 shadow-md">
        <div className="flex items-center gap-3 mb-6 pb-4 border-b border-[#E5EBF3]">
          <div className="w-11 h-11 rounded-[14px] flex items-center justify-center text-xl text-white"
            style={{ background: 'linear-gradient(135deg, #7959D6, #A78BFA)' }}>🌍</div>
          <div>
            <h3 className="text-lg font-extrabold text-[#1A2B47]">منطقه و ارز</h3>
            <p className="text-[12px] text-[#6B7A94] mt-0.5">منطقه‌ی زمانی، ارز و تقویم</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          <div>
            <label className="text-[13px] text-[#1A2B47] font-bold block mb-2">🕐 منطقه‌ی زمانی</label>
            <select
              value={settings.timezone}
              onChange={(e) => setSettings({ ...settings, timezone: e.target.value })}
              className="w-full bg-[#F8FAFF] border-2 border-[#E5EBF3] rounded-[12px] px-5 py-3 text-[#1A2B47] text-sm font-bold focus:border-[#7959D6] focus:outline-none cursor-pointer"
            >
              <option value="Asia/Tehran">🇮🇷 Tehran</option>
              <option value="UTC">🌍 UTC</option>
              <option value="America/New_York">🇺🇸 New York</option>
              <option value="Europe/London">🇬🇧 London</option>
              <option value="Asia/Tokyo">🇯🇵 Tokyo</option>
            </select>
          </div>

          <div>
            <label className="text-[13px] text-[#1A2B47] font-bold block mb-2">💵 ارز</label>
            <select
              value={settings.currency}
              onChange={(e) => setSettings({ ...settings, currency: e.target.value })}
              className="w-full bg-[#F8FAFF] border-2 border-[#E5EBF3] rounded-[12px] px-5 py-3 text-[#1A2B47] text-sm font-bold focus:border-[#7959D6] focus:outline-none cursor-pointer"
            >
              <option value="USD">USD - دلار</option>
              <option value="EUR">EUR - یورو</option>
              <option value="GBP">GBP - پوند</option>
            </select>
          </div>

          <div>
            <label className="text-[13px] text-[#1A2B47] font-bold block mb-2">📅 تقویم</label>
            <select
              value={settings.calendar}
              onChange={(e) => setSettings({ ...settings, calendar: e.target.value })}
              className="w-full bg-[#F8FAFF] border-2 border-[#E5EBF3] rounded-[12px] px-5 py-3 text-[#1A2B47] text-sm font-bold focus:border-[#7959D6] focus:outline-none cursor-pointer"
            >
              <option value="persian">🌙 شمسی</option>
              <option value="gregorian">🌍 میلادی</option>
            </select>
          </div>
        </div>
      </div>

      {/* پیش‌فرض‌های ریسک */}
      <div className="bg-white border border-[#E5EBF3] rounded-[22px] p-6 shadow-md">
        <div className="flex items-center gap-3 mb-6 pb-4 border-b border-[#E5EBF3]">
          <div className="w-11 h-11 rounded-[14px] flex items-center justify-center text-xl text-white"
            style={{ background: 'linear-gradient(135deg, #13AE81, #4DD9A9)' }}>⚙️</div>
          <div>
            <h3 className="text-lg font-extrabold text-[#1A2B47]">پیش‌فرض‌های ریسک و پراپ</h3>
            <p className="text-[12px] text-[#6B7A94] mt-0.5">مقادیر پیش‌فرض برای ساخت جدید</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div>
            <label className="text-[13px] text-[#1A2B47] font-bold block mb-2">⚠️ ریسک پیش‌فرض (%)</label>
            <input
              type="number"
              value={settings.default_risk_percent}
              onChange={(e) => setSettings({ ...settings, default_risk_percent: Number(e.target.value) })}
              className="w-full bg-[#F8FAFF] border-2 border-[#E5EBF3] rounded-[12px] px-5 py-3 text-[#1A2B47] text-sm font-bold focus:border-[#13AE81] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-[13px] text-[#1A2B47] font-bold block mb-2">🏢 سهم کاربر در پراپ (%)</label>
            <input
              type="number"
              value={settings.default_profit_share}
              onChange={(e) => setSettings({ ...settings, default_profit_share: Number(e.target.value) })}
              className="w-full bg-[#F8FAFF] border-2 border-[#E5EBF3] rounded-[12px] px-5 py-3 text-[#1A2B47] text-sm font-bold focus:border-[#13AE81] focus:outline-none"
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
    </div>
  );
}