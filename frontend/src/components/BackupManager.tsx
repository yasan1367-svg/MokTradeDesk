import { useCallback, useEffect, useState } from 'react';
import ConfirmDialog from './ui/ConfirmDialog';
import Skeleton from './Skeleton';
import EmptyState from './ui/EmptyState';
import { useToast } from './ToastProvider';
import {
  listBackups,
  createBackup,
  downloadBackup,
  restoreBackup,
  deleteBackup,
  getBackupSettings,
  updateBackupSettings,
  type BackupItem,
} from '../api/client';
import { gregorianToJalali } from '../utils/jalali';

function faDateTime(iso?: string): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return '—';
  const [jy, jm, jd] = gregorianToJalali(d.getFullYear(), d.getMonth() + 1, d.getDate());
  const hh = String(d.getHours()).padStart(2, '0');
  const mm = String(d.getMinutes()).padStart(2, '0');
  return `${jy}/${String(jm).padStart(2, '0')}/${String(jd).padStart(2, '0')} - ${hh}:${mm}`;
}

function faSize(bytes?: number): string {
  const b = Number(bytes || 0);
  if (b < 1024) return `${b} B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / (1024 * 1024)).toFixed(2)} MB`;
}

/**
 * BackupManager — بخش Backup دیتابیس (فاز ۱۷)
 * ساخت/لیست/دانلود/بازیابی/حذف + تنظیمات Backup خودکار
 */
export default function BackupManager() {
  const toast = useToast();

  const [items, setItems] = useState<BackupItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [settings, setSettings] = useState<{ auto_enabled: boolean; interval_hours: number; keep: number } | null>(null);

  const [confirmRestore, setConfirmRestore] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [list, cfg] = await Promise.all([listBackups(), getBackupSettings()]);
      setItems(list.data || []);
      setSettings(cfg.data || null);
    } catch {
      toast.error('خطا در بارگذاری Backupها');
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async () => {
    setBusy(true);
    try {
      const r = await createBackup();
      toast.success(`Backup ساخته شد: ${r.data?.filename || ''}`);
      load();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'خطا در ساخت Backup');
    } finally {
      setBusy(false);
    }
  };

  const handleDownload = async (filename: string) => {
    try {
      const r = await downloadBackup(filename);
      const url = URL.createObjectURL(new Blob([r.data]));
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      toast.success('دانلود آغاز شد');
    } catch {
      toast.error('خطا در دانلود Backup');
    }
  };

  const handleRestore = async (filename: string) => {
    setConfirmRestore(null);
    setBusy(true);
    try {
      const r = await restoreBackup(filename);
      toast.success(`بازیابی انجام شد (Backup ایمنی: ${r.data?.safety_backup || '—'})`);
      load();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'خطا در بازیابی');
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async (filename: string) => {
    setConfirmDelete(null);
    try {
      await deleteBackup(filename);
      toast.success('Backup حذف شد');
      load();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'خطا در حذف Backup');
    }
  };

  const saveSettings = async (patch: Partial<{ auto_enabled: boolean; interval_hours: number; keep: number }>) => {
    try {
      const r = await updateBackupSettings(patch);
      setSettings(r.data);
      toast.success('تنظیمات Backup ذخیره شد');
    } catch {
      toast.error('خطا در ذخیرهٔ تنظیمات');
    }
  };

  const inputCls =
    'w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[12px] px-4 py-2.5 text-[var(--text-primary)] text-sm focus:border-[var(--accent)] focus:outline-none';

  return (
    <div className="space-y-6">
      <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-6 shadow-md">
        <div className="flex items-center justify-between flex-wrap gap-4 mb-6 pb-4 border-b border-[var(--border-subtle)]">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-[14px] flex items-center justify-center text-xl text-white"
                 style={{ background: 'linear-gradient(135deg, var(--accent), var(--accent-strong))' }}>💾</div>
            <div>
              <h3 className="text-lg font-extrabold text-[var(--text-primary)]">Backup دیتابیس</h3>
              <p className="text-[12px] text-[var(--text-secondary)] mt-0.5">ساخت، دانلود، بازیابی و حذف نسخهٔ پشتیبان</p>
            </div>
          </div>
          <button
            onClick={handleCreate}
            disabled={busy}
            className="text-white px-5 py-3 rounded-[12px] text-sm font-extrabold shadow-[0_6px_16px_rgba(63,124,255,0.3)] hover:-translate-y-0.5 transition-all disabled:opacity-50"
            style={{ background: 'linear-gradient(135deg, var(--accent), var(--accent-strong))' }}
          >
            {busy ? '⏳ در حال انجام…' : '➕ ساخت Backup جدید'}
          </button>
        </div>

        {/* تنظیمات Backup خودکار */}
        {settings && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-6">
            <label className="flex items-center gap-3 bg-[var(--bg-elevated)] rounded-[14px] px-4 py-3 cursor-pointer">
              <input
                type="checkbox"
                checked={!!settings.auto_enabled}
                onChange={(e) => saveSettings({ auto_enabled: e.target.checked })}
                className="w-5 h-5 accent-[var(--accent)]"
              />
              <span className="text-[13px] font-bold text-[var(--text-primary)]">Backup خودکار فعال</span>
            </label>
            <div>
              <label className="text-[12px] text-[var(--text-secondary)] font-bold block mb-2">⏱ بازهٔ زمانی (ساعت)</label>
              <input
                type="number"
                min={1}
                value={settings.interval_hours}
                onChange={(e) => setSettings({ ...settings, interval_hours: Number(e.target.value) })}
                onBlur={(e) => saveSettings({ interval_hours: Number(e.target.value) })}
                className={inputCls}
              />
            </div>
            <div>
              <label className="text-[12px] text-[var(--text-secondary)] font-bold block mb-2">📦 تعداد نگهداری</label>
              <input
                type="number"
                min={1}
                value={settings.keep}
                onChange={(e) => setSettings({ ...settings, keep: Number(e.target.value) })}
                onBlur={(e) => saveSettings({ keep: Number(e.target.value) })}
                className={inputCls}
              />
            </div>
          </div>
        )}

        {/* جدول Backupها */}
        {loading ? (
          <div className="space-y-2">
            <Skeleton variant="rect" count={4} className="h-12" />
          </div>
        ) : items.length === 0 ? (
          <EmptyState icon="💾" title="Backupای وجود ندارد" description="با دکمهٔ بالا اولین نسخهٔ پشتیبان را بسازید" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border-subtle)] text-[var(--text-secondary)]">
                  <th className="text-right py-3 px-3">نام فایل</th>
                  <th className="text-right py-3 px-3">تاریخ</th>
                  <th className="text-right py-3 px-3">حجم</th>
                  <th className="text-right py-3 px-3">عملیات</th>
                </tr>
              </thead>
              <tbody>
                {items.map((b) => (
                  <tr
                    key={b.filename}
                    className="border-b border-[var(--border-subtle)]/50 hover:bg-[var(--accent-soft)]/30 transition-colors"
                  >
                    <td className="py-3 px-3 font-mono text-[12px] text-[var(--text-primary)]">{b.filename}</td>
                    <td className="py-3 px-3 text-[var(--text-secondary)] text-[12px]">{faDateTime(b.created_at)}</td>
                    <td className="py-3 px-3 text-[var(--text-secondary)] text-[12px]">{faSize(b.size)}</td>
                    <td className="py-3 px-3">
                      <div className="flex gap-3">
                        <button onClick={() => handleDownload(b.filename)} title="دانلود"
                                className="text-xs font-bold text-[var(--accent)] hover:underline">
                          ⬇️ دانلود
                        </button>
                        <button onClick={() => setConfirmRestore(b.filename)} title="بازیابی"
                                className="text-xs font-bold text-[var(--warning)] hover:underline">
                          ♻️ بازیابی
                        </button>
                        <button onClick={() => setConfirmDelete(b.filename)} title="حذف"
                                className="text-xs font-bold text-[var(--loss)] hover:underline">
                          🗑️ حذف
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

      <ConfirmDialog
        open={!!confirmRestore}
        title="بازیابی از Backup"
        message={`آیا از بازیابی «${confirmRestore}» مطمئن هستید؟ دیتابیس فعلی جایگزین خواهد شد (یک Backup ایمنی خودکار گرفته میشود).`}
        confirmLabel="بازیابی"
        onConfirm={() => confirmRestore && handleRestore(confirmRestore)}
        onCancel={() => setConfirmRestore(null)}
      />
      <ConfirmDialog
        open={!!confirmDelete}
        title="حذف Backup"
        message={`آیا از حذف «${confirmDelete}» مطمئن هستید؟ این عمل بازگشتپذیر نیست.`}
        confirmLabel="حذف"
        onConfirm={() => confirmDelete && handleDelete(confirmDelete)}
        onCancel={() => setConfirmDelete(null)}
      />
    </div>
  );
}

