import { useState, useEffect, useRef } from 'react';
import {
  getAllVersions,
  previewImport,
  commitImport,
  cancelImportBatch,
  getAllPropStages,
  getSymbolMappings,
  createSymbolMapping,
  deleteSymbolMapping,
  seedSymbolMappings,
} from '../api/client';

interface Version {
  id: number;
  version_name: string;
  strategy_name: string;
}

interface PropStage {
  id: number;
  display_name: string;
}

export default function ImportPage() {
  const [versions, setVersions] = useState<Version[]>([]);
  const [propStages, setPropStages] = useState<PropStage[]>([]);
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null);
  const [selectedPropStage, setSelectedPropStage] = useState<number | null>(null);
  const [importTarget, setImportTarget] = useState<'strategy' | 'prop'>('strategy');
  const [fileType, setFileType] = useState<'soft4x' | 'mt4'>('soft4x');
  const [symbol, setSymbol] = useState<string>('XAUUSD');
  const [testType, setTestType] = useState<'backtest' | 'forward' | 'real'>('backtest');
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  // فاز ۳۰: خروجی Preview (تا تأیید کاربر هیچ معامله‌ای ساخته نمی‌شود)
  const [preview, setPreview] = useState<any>(null);
  const [allowPossible, setAllowPossible] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Symbol Mapping
  const [showMappingModal, setShowMappingModal] = useState(false);
  const [mappings, setMappings] = useState<any[]>([]);
  const [newOriginal, setNewOriginal] = useState('');
  const [newCanonical, setNewCanonical] = useState('');
  const [newDescription, setNewDescription] = useState('');
  const [mappingError, setMappingError] = useState<string | null>(null);

  useEffect(() => {
    getAllVersions()
      .then((res) => setVersions(res.data))
      .catch((err) => console.error('خطا در دریافت نسخه‌ها:', err));

    getAllPropStages()
      .then((res) => setPropStages(res.data))
      .catch((err) => console.error('خطا در دریافت مراحل پراپ:', err));
  }, []);

  // ═════════════════════════════════════════════
  // File Handling
  // ═════════════════════════════════════════════
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => setIsDragging(false);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      setFile(droppedFile);
      setResult(null);
      setPreview(null);
      setError(null);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (selected) {
      setFile(selected);
      setResult(null);
      setPreview(null);
      setError(null);
    }
  };

  // تغییر تنظیمات ⇒ Preview قبلی بی‌اعتبار می‌شود
  useEffect(() => {
    setPreview(null);
    setAllowPossible(false);
  }, [fileType, importTarget, selectedVersion, selectedPropStage, symbol, testType]);

  const handleSubmit = async () => {
    if (!file) {
      setError('لطفاً یک فایل انتخاب کنید');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);
    setPreview(null);
    setAllowPossible(false);

    try {
      const response = await previewImport(
        file,
        fileType === 'soft4x' ? 'soft4x_xlsx' : 'mt4_html',
        {
          versionId: selectedVersion || undefined,
          propStageId: importTarget === 'prop' ? selectedPropStage || undefined : undefined,
          symbol: fileType === 'soft4x' ? symbol : undefined,
          testType,
        },
      );
      setPreview(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'خطا در پیش‌نمایش فایل');
    } finally {
      setLoading(false);
    }
  };

  // تأیید کاربر ⇒ Commit اتمیک روی همان batch (بدون آپلود دوباره)
  const handleConfirm = async () => {
    if (!preview?.batch_id) return;

    setLoading(true);
    setError(null);

    try {
      const response = await commitImport(preview.batch_id, allowPossible);
      const data = response.data;
      setResult({
        total_trades: data.total,
        saved_trades: data.imported,
        duplicates_count: data.duplicate,
        message: data.message,
      });
      setPreview(null);
      setAllowPossible(false);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'خطا در ذخیره‌ی ایمپورت');
    } finally {
      setLoading(false);
    }
  };

  const handleCancelPreview = async () => {
    if (preview?.batch_id) {
      try {
        await cancelImportBatch(preview.batch_id);
      } catch (err) {
        console.error('لغو ایمپورت:', err);
      }
    }
    setPreview(null);
    setAllowPossible(false);
  };

  // ═════════════════════════════════════════════
  // Symbol Mapping Handlers
  // ═════════════════════════════════════════════
  const loadMappings = async () => {
    try {
      const res = await getSymbolMappings();
      setMappings(res.data);
    } catch (err) {
      console.error('خطا:', err);
    }
  };

  const handleOpenMappingModal = async () => {
    await loadMappings();
    setShowMappingModal(true);
  };

  const handleCreateMapping = async () => {
    if (!newOriginal.trim() || !newCanonical.trim()) {
      setMappingError('نماد اصلی و استاندارد الزامی هستند');
      return;
    }
    try {
      await createSymbolMapping({
        original_symbol: newOriginal,
        canonical_symbol: newCanonical,
        description: newDescription,
      });
      setNewOriginal('');
      setNewCanonical('');
      setNewDescription('');
      setMappingError(null);
      await loadMappings();
    } catch (err: any) {
      setMappingError(err.response?.data?.detail || 'خطا');
    }
  };

  const handleDeleteMapping = async (id: number) => {
    if (!confirm('حذف این Mapping؟')) return;
    try {
      await deleteSymbolMapping(id);
      await loadMappings();
    } catch (err: any) {
      setMappingError(err.response?.data?.detail || 'خطا');
    }
  };

  const handleSeedMappings = async () => {
    try {
      await seedSymbolMappings();
      await loadMappings();
    } catch (err: any) {
      setMappingError(err.response?.data?.detail || 'خطا');
    }
  };

  return (
    <div className="space-y-6">
      {error && (
        <div className="bg-[var(--loss-soft)] border border-[var(--loss-border)] text-[var(--loss)] p-4 rounded-[14px] text-sm font-semibold shadow-sm">
          ❌ {error}
          <button onClick={() => setError(null)} className="float-left text-xs font-bold">✕</button>
        </div>
      )}

      {/* دکمه‌ی مدیریت Symbol Mapping */}
      <div className="flex gap-3 flex-wrap">
        <button
          onClick={handleOpenMappingModal}
          className="bg-[var(--bg-card)] border-2 border-[var(--border-subtle)] text-[var(--text-secondary)] hover:border-[var(--border-accent)] hover:text-[var(--accent)] px-6 py-3 rounded-[12px] text-sm font-extrabold transition-all shadow-sm"
        >
          🔗 مدیریت Symbol Mapping
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* ستون چپ: تنظیمات */}
        <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-6 shadow-md">
          <div className="flex items-center gap-3 mb-6 pb-4 border-b border-[var(--border-subtle)]">
            <div className="w-11 h-11 rounded-[14px] flex items-center justify-center text-xl text-white"
              style={{ background: 'linear-gradient(135deg, var(--accent), #5B8DEF)' }}>
              ⚙️
            </div>
            <div>
              <h3 className="text-lg font-extrabold text-[var(--text-primary)]">تنظیمات</h3>
              <p className="text-[12px] text-[var(--text-secondary)] mt-0.5">مشخصات واردات را تعیین کنید</p>
            </div>
          </div>

          {/* نوع فایل */}
          <div className="mb-5">
            <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">📁 نوع فایل</label>
            <div className="flex gap-2">
              <button
                onClick={() => setFileType('soft4x')}
                className={`flex-1 py-3 rounded-[12px] text-[13px] font-extrabold transition-all ${
                  fileType === 'soft4x'
                    ? 'text-white shadow-[0_6px_16px_rgba(63,124,255,0.3)]'
                    : 'bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] text-[var(--text-secondary)] hover:border-[var(--border-accent)]'
                }`}
                style={fileType === 'soft4x' ? { background: 'linear-gradient(135deg, var(--accent), #5B8DEF)' } : {}}
              >
                📊 Soft4X (اکسل)
              </button>
              <button
                onClick={() => setFileType('mt4')}
                className={`flex-1 py-3 rounded-[12px] text-[13px] font-extrabold transition-all ${
                  fileType === 'mt4'
                    ? 'text-white shadow-[0_6px_16px_rgba(63,124,255,0.3)]'
                    : 'bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] text-[var(--text-secondary)] hover:border-[var(--border-accent)]'
                }`}
                style={fileType === 'mt4' ? { background: 'linear-gradient(135deg, var(--accent), #5B8DEF)' } : {}}
              >
                📈 متاتریدر (HTML)
              </button>
            </div>
          </div>

          {/* مقصد */}
          <div className="mb-5">
            <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">🎯 مقصد واردات</label>
            <div className="flex gap-2 flex-wrap">
                            <button
                onClick={() => {
                  setImportTarget('strategy');
                  setTestType('backtest');
                }}
                className={`flex-1 min-w-[100px] py-3 rounded-[12px] text-[13px] font-extrabold transition-all ${
                  importTarget === 'strategy'
                    ? 'text-white shadow-[0_6px_16px_rgba(19,174,129,0.3)]'
                    : 'bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] text-[var(--text-secondary)] hover:border-[var(--border-accent)]'
                }`}
                style={importTarget === 'strategy' ? { background: 'linear-gradient(135deg, var(--profit), #4DD9A9)' } : {}}
              >
                🎯 استراتژی
              </button>
              <button
                onClick={() => {
                  setImportTarget('prop');
                  setTestType('real');
                }}
                className={`flex-1 min-w-[100px] py-3 rounded-[12px] text-[13px] font-extrabold transition-all ${
                  importTarget === 'prop'
                    ? 'text-white shadow-[0_6px_16px_rgba(121,89,214,0.3)]'
                    : 'bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] text-[var(--text-secondary)] hover:border-[var(--border-accent)]'
                }`}
                style={importTarget === 'prop' ? { background: 'linear-gradient(135deg, var(--purple), #A78BFA)' } : {}}
              >
                🏢 پراپ
              </button>
            </div>
          </div>

          {/* نماد (فقط Soft4X) */}
          {fileType === 'soft4x' && (
            <div className="mb-5">
              <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">🥇 نماد</label>
              <select
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
                className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[12px] px-5 py-3.5 text-[var(--text-primary)] text-sm font-bold focus:border-[var(--accent)] focus:bg-[var(--bg-card)] focus:outline-none focus:ring-4 focus:ring-[var(--accent-soft)] transition-all cursor-pointer"
              >
                <option value="XAUUSD">🥇 طلا (XAUUSD)</option>
                <option value="DJIUSD">📊 داوجونز (DJIUSD)</option>
              </select>
            </div>
          )}

                    {/* نوع تست — فقط برای استراتژی */}
          {importTarget === 'strategy' && (
            <div className="mb-5">
              <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">🧪 نوع تست</label>
              <div className="flex gap-2">
                {[
                  { value: 'backtest', label: '🧪 بک‌تست' },
                  { value: 'forward', label: '🔭 فوروارد' },
                  { value: 'real', label: '💰 رییل' },
                ].map((t) => {
                  const isActive = testType === t.value;
                  return (
                    <button
                      key={t.value}
                      onClick={() => setTestType(t.value as any)}
                      className={`flex-1 py-3 rounded-[12px] text-[12px] font-extrabold transition-all ${
                        isActive
                          ? 'text-white shadow-[0_6px_16px_rgba(63,124,255,0.3)]'
                          : 'bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] text-[var(--text-secondary)] hover:border-[var(--border-accent)]'
                      }`}
                      style={isActive ? { background: 'linear-gradient(135deg, var(--accent), #5B8DEF)' } : {}}
                    >
                      {t.label}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* مقصد انتخابی */}
          {importTarget === 'strategy' && (
            <div className="mb-2">
              <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">
                📌 نسخه‌ی استراتژی <span className="text-[var(--loss)]">*</span>
              </label>
              <select
                value={selectedVersion || ''}
                onChange={(e) => setSelectedVersion(e.target.value ? Number(e.target.value) : null)}
                className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[12px] px-5 py-3.5 text-[var(--text-primary)] text-sm font-bold focus:border-[var(--accent)] focus:bg-[var(--bg-card)] focus:outline-none focus:ring-4 focus:ring-[var(--accent-soft)] transition-all cursor-pointer"
              >
                <option value="">— انتخاب نسخه —</option>
                {versions.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.strategy_name} / {v.version_name}
                  </option>
                ))}
              </select>
            </div>
          )}

                    {importTarget === 'prop' && (
            <>
              <div className="mb-2">
                <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">
                  🎯 نسخه‌ی استراتژی <span className="text-[var(--loss)]">*</span>
                </label>
                <select
                  value={selectedVersion || ''}
                  onChange={(e) => setSelectedVersion(e.target.value ? Number(e.target.value) : null)}
                  className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[12px] px-5 py-3.5 text-[var(--text-primary)] text-sm font-bold focus:border-[var(--purple)] focus:bg-[var(--bg-card)] focus:outline-none focus:ring-4 focus:ring-[var(--purple-soft)] transition-all cursor-pointer"
                >
                  <option value="">— انتخاب نسخه —</option>
                  {versions.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.strategy_name} / {v.version_name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="mb-2">
                <label className="text-[13px] text-[var(--text-primary)] font-bold block mb-2">
                  📌 مرحله‌ی پراپ <span className="text-[var(--loss)]">*</span>
                </label>
                <select
                  value={selectedPropStage || ''}
                  onChange={(e) => setSelectedPropStage(e.target.value ? Number(e.target.value) : null)}
                  className="w-full bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[12px] px-5 py-3.5 text-[var(--text-primary)] text-sm font-bold focus:border-[var(--purple)] focus:bg-[var(--bg-card)] focus:outline-none focus:ring-4 focus:ring-[var(--purple-soft)] transition-all cursor-pointer"
                >
                  <option value="">— انتخاب مرحله —</option>
                  {propStages.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.display_name}
                    </option>
                  ))}
                </select>
              </div>
            </>
          )}
        </div>

        {/* ستون راست: آپلود */}
        <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-6 shadow-md">
          <div className="flex items-center gap-3 mb-6 pb-4 border-b border-[var(--border-subtle)]">
            <div className="w-11 h-11 rounded-[14px] flex items-center justify-center text-xl text-white"
              style={{ background: 'linear-gradient(135deg, var(--profit), #4DD9A9)' }}>
              📤
            </div>
            <div>
              <h3 className="text-lg font-extrabold text-[var(--text-primary)]">آپلود فایل</h3>
              <p className="text-[12px] text-[var(--text-secondary)] mt-0.5">فایل مورد نظر را انتخاب کنید</p>
            </div>
          </div>

          {/* Drag & Drop */}
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-[18px] p-10 text-center cursor-pointer transition-all ${
              isDragging
                ? 'border-[var(--accent)] bg-[var(--accent-soft)] shadow-[0_0_0_4px_rgba(63,124,255,0.1)]'
                : file
                ? 'border-[var(--profit)] bg-[var(--profit-soft)]'
                : 'border-[var(--border-subtle)] hover:border-[var(--border-accent)] hover:bg-[var(--bg-input)]'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept={fileType === 'soft4x' ? '.xlsx' : '.html'}
              onChange={handleFileSelect}
              className="hidden"
            />

            {file ? (
              <div>
                <div className="text-5xl mb-3">✅</div>
                <div className="text-[15px] font-extrabold text-[var(--text-primary)] break-all">{file.name}</div>
                <div className="text-[12px] text-[var(--text-secondary)] mt-2 font-semibold">
                  {(file.size / 1024).toFixed(2)} KB
                </div>
                <div className="text-[11px] text-[var(--profit)] mt-2 font-bold">
                  ✓ فایل آماده‌ی آپلود است
                </div>
              </div>
            ) : (
              <div>
                <div className="text-6xl mb-4">📁</div>
                <div className="text-[15px] font-extrabold text-[var(--text-primary)] mb-2">
                  فایل را اینجا رها کنید
                </div>
                <div className="text-[12px] text-[var(--text-secondary)] font-semibold">
                  یا کلیک کنید تا انتخاب کنید
                </div>
                <div className="text-[11px] text-[var(--text-muted)] mt-3">
                  {fileType === 'soft4x' ? 'فرمت پشتیبانی: xlsx' : 'فرمت پشتیبانی: html'}
                </div>
              </div>
            )}
          </div>

          {/* دکمه‌ی پیش‌نمایش (فاز ۳۰: Preview قبل از Commit) */}
          <button
            onClick={handleSubmit}
            disabled={loading || !file}
            className={`w-full mt-5 py-4 rounded-[14px] text-[15px] font-extrabold transition-all ${
              loading || !file
                ? 'bg-[var(--bg-elevated)] text-[var(--text-muted)] cursor-not-allowed'
                : 'text-white shadow-[0_6px_20px_rgba(63,124,255,0.4)] hover:shadow-[0_10px_28px_rgba(63,124,255,0.5)] hover:-translate-y-0.5'
            }`}
            style={!loading && file ? { background: 'linear-gradient(135deg, var(--accent), #5B8DEF)' } : {}}
          >
            {loading ? '⏳ در حال پردازش...' : '🔍 پیش‌نمایش ایمپورت'}
          </button>

          {/* پنل پیش‌نمایش + تأیید کاربر */}
          {preview && (
            <div className="mt-5 bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[18px] p-5 space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="text-[14px] font-extrabold text-[var(--text-primary)]">
                  👁️ پیش‌نمایش (بدون تغییر در معاملات)
                </h4>
                <span className="text-[11px] font-bold text-[var(--text-muted)]" dir="ltr">
                  Import #{preview.batch_id}
                </span>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="bg-[var(--bg-input)] border border-[var(--border-subtle)] rounded-[12px] p-3">
                  <div className="text-[11px] font-bold text-[var(--text-secondary)]">کل ردیف‌ها</div>
                  <div className="text-[20px] font-extrabold text-[var(--accent)]">{preview.total}</div>
                </div>
                <div className="bg-[var(--profit-soft)] border border-[var(--profit-border)] rounded-[12px] p-3">
                  <div className="text-[11px] font-bold text-[var(--text-secondary)]">جدید</div>
                  <div className="text-[20px] font-extrabold text-[var(--profit)]">
                    {preview.counts?.new ?? 0}
                  </div>
                </div>
                <div className="bg-[var(--warning-soft)] border border-[var(--warning-border)] rounded-[12px] p-3">
                  <div className="text-[11px] font-bold text-[var(--text-secondary)]">تکراری</div>
                  <div className="text-[20px] font-extrabold text-[var(--warning)]">{preview.duplicate}</div>
                </div>
                <div className="bg-[var(--loss-soft)] border border-[var(--loss-border)] rounded-[12px] p-3">
                  <div className="text-[11px] font-bold text-[var(--text-secondary)]">نامعتبر</div>
                  <div className="text-[20px] font-extrabold text-[var(--loss)]">{preview.failed}</div>
                </div>
              </div>

              {(preview.counts?.possible_duplicate ?? 0) > 0 && (
                <label className="flex items-center gap-3 bg-[var(--warning-soft)] border border-[var(--warning-border)] rounded-[12px] p-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={allowPossible}
                    onChange={(e) => setAllowPossible(e.target.checked)}
                    className="w-4 h-4 accent-[var(--warning)]"
                  />
                  <span className="text-[12px] font-bold text-[var(--text-primary)]">
                    {preview.counts.possible_duplicate} ردیف مشکوک به تکرار هم وارد شود
                  </span>
                </label>
              )}

              {preview.failed > 0 && (
                <div className="bg-[var(--loss-soft)] border border-[var(--loss-border)] rounded-[12px] p-3 text-[12px] font-bold text-[var(--loss)]">
                  ⛔ {preview.failed} ردیف نامعتبر است؛ Import اتمیک است و تا اصلاح فایل ذخیره
                  انجام نمی‌شود.
                </div>
              )}

              <div className="max-h-56 overflow-auto rounded-[12px] border border-[var(--border-subtle)]">
                <table className="w-full text-[11px]">
                  <thead className="bg-[var(--bg-elevated)] sticky top-0">
                    <tr className="text-[var(--text-secondary)]">
                      <th className="p-2 text-right">#</th>
                      <th className="p-2 text-right">نماد</th>
                      <th className="p-2 text-right">جهت</th>
                      <th className="p-2 text-right">زمان ورود</th>
                      <th className="p-2 text-right">وضعیت</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(preview.rows || []).map((row: any) => (
                      <tr key={row.row_number} className="border-t border-[var(--border-subtle)]">
                        <td className="p-2 text-[var(--text-muted)]">{row.row_number}</td>
                        <td className="p-2 font-bold text-[var(--text-primary)]" dir="ltr">
                          {row.symbol}
                        </td>
                        <td className="p-2 text-[var(--text-secondary)]" dir="ltr">
                          {row.direction}
                        </td>
                        <td className="p-2 text-[var(--text-secondary)]" dir="ltr">
                          {row.open_time ? String(row.open_time).slice(0, 16).replace('T', ' ') : '-'}
                        </td>
                        <td className="p-2 font-bold">
                          {row.status === 'new' && <span className="text-[var(--profit)]">جدید</span>}
                          {row.status === 'duplicate' && (
                            <span className="text-[var(--warning)]">تکراری</span>
                          )}
                          {row.status === 'possible_duplicate' && (
                            <span className="text-[var(--warning)]">مشکوک</span>
                          )}
                          {row.status === 'invalid' && <span className="text-[var(--loss)]">نامعتبر</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={handleConfirm}
                  disabled={loading || preview.failed > 0}
                  className={`flex-1 py-3 rounded-[12px] text-[13px] font-extrabold transition-all ${
                    loading || preview.failed > 0
                      ? 'bg-[var(--bg-elevated)] text-[var(--text-muted)] cursor-not-allowed'
                      : 'text-white shadow-[0_6px_16px_rgba(19,174,129,0.35)]'
                  }`}
                  style={
                    !loading && preview.failed === 0
                      ? { background: 'linear-gradient(135deg, var(--profit), #4DD9A9)' }
                      : {}
                  }
                >
                  {loading ? '⏳ در حال ذخیره...' : '✅ تأیید و ذخیره'}
                </button>
                <button
                  onClick={handleCancelPreview}
                  disabled={loading}
                  className="px-5 py-3 rounded-[12px] text-[13px] font-extrabold bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] text-[var(--text-secondary)] hover:border-[var(--loss-border)] hover:text-[var(--loss)] transition-all"
                >
                  ✕ لغو
                </button>
              </div>
            </div>
          )}

          {/* راهنما */}
          <div className="mt-5 bg-[var(--accent-soft)] border border-[var(--border-accent)] rounded-[14px] p-4">
            <div className="flex items-start gap-3">
              <div className="text-2xl shrink-0">💡</div>
              <div className="text-[12px] text-[var(--text-primary)] leading-relaxed">
                {fileType === 'soft4x' ? (
                  <>
                    <span className="font-extrabold">راهنما:</span> فایل اکسل خروجی Soft4X را آپلود کنید.
                    ستون‌های مورد نیاز: Order, Type, Size, Open Time, Open Price, ...
                  </>
                ) : (
                  <>
                    <span className="font-extrabold">راهنما:</span> فایل HTML خروجی متاتریدر را آپلود کنید.
                    فقط معاملات بخش <span className="font-extrabold">Positions</span> استخراج می‌شوند.
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* نتیجه‌ی واردات */}
      {result && (
        <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-6 shadow-md">
          <div className="flex items-center gap-3 mb-5 pb-4 border-b border-[var(--border-subtle)]">
            <div className="w-11 h-11 rounded-[14px] flex items-center justify-center text-xl text-white"
              style={{ background: 'linear-gradient(135deg, var(--profit), #4DD9A9)' }}>
              ✅
            </div>
            <div>
              <h3 className="text-lg font-extrabold text-[var(--text-primary)]">نتیجه‌ی واردات</h3>
              <p className="text-[12px] text-[var(--text-secondary)] mt-0.5">{result.message}</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            <div className="bg-[var(--accent-soft)] border border-[var(--border-accent)] rounded-[16px] p-5">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 rounded-[12px] bg-[var(--bg-card)] flex items-center justify-center text-xl shadow-sm">
                  📊
                </div>
                <div className="text-[12px] text-[var(--text-secondary)] font-bold">شناسایی‌شده</div>
              </div>
              <div className="text-[28px] font-extrabold text-[var(--accent)]">{result.total_trades}</div>
            </div>

            <div className={`border rounded-[16px] p-5 ${result.saved_trades > 0 ? 'bg-[var(--profit-soft)] border-[var(--profit-border)]' : 'bg-[var(--bg-elevated)] border-[var(--border-subtle)]'}`}>
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 rounded-[12px] bg-[var(--bg-card)] flex items-center justify-center text-xl shadow-sm">
                  💾
                </div>
                <div className="text-[12px] text-[var(--text-secondary)] font-bold">ذخیره‌شده</div>
              </div>
              <div className={`text-[28px] font-extrabold ${result.saved_trades > 0 ? 'text-[var(--profit)]' : 'text-[var(--text-secondary)]'}`}>
                {result.saved_trades}
              </div>
            </div>

            <div className="bg-[var(--warning-soft)] border border-[var(--warning-border)] rounded-[16px] p-5">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 rounded-[12px] bg-[var(--bg-card)] flex items-center justify-center text-xl shadow-sm">
                  📝
                </div>
                <div className="text-[12px] text-[var(--text-secondary)] font-bold">وضعیت</div>
              </div>
              <div className="text-[13px] font-extrabold text-[var(--warning)] leading-relaxed">
                {result.message}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ═════════════════════════════════════════════
          مودال Symbol Mapping
      ═════════════════════════════════════════════ */}
      {showMappingModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-[var(--bg-card)] rounded-[22px] max-w-3xl w-full max-h-[90vh] overflow-hidden shadow-2xl">
            <div className="flex justify-between items-center p-6 border-b border-[var(--border-subtle)]">
              <div className="flex items-center gap-3">
                <div className="w-11 h-11 rounded-[14px] flex items-center justify-center text-xl text-white"
                  style={{ background: 'linear-gradient(135deg, var(--purple), #A78BFA)' }}>
                  🔗
                </div>
                <div>
                  <h3 className="text-lg font-extrabold text-[var(--text-primary)]">مدیریت Symbol Mapping</h3>
                  <p className="text-[12px] text-[var(--text-secondary)] mt-0.5">تبدیل نمادهای مختلف به نماد استاندارد</p>
                </div>
              </div>
              <button
                onClick={() => setShowMappingModal(false)}
                className="text-[var(--text-secondary)] text-xl w-9 h-9 rounded-lg hover:bg-[var(--bg-elevated)] transition-all"
              >
                ✕
              </button>
            </div>

            <div className="p-6 max-h-[calc(90vh-120px)] overflow-y-auto space-y-5">
              {mappingError && (
                <div className="bg-[var(--loss-soft)] border border-[var(--loss-border)] text-[var(--loss)] p-3 rounded-[12px] text-[13px] font-semibold">
                  ❌ {mappingError}
                </div>
              )}

              {/* فرم افزودن */}
              <div className="bg-[var(--bg-input)] border-2 border-[var(--border-subtle)] rounded-[14px] p-5">
                <h4 className="text-[14px] font-extrabold text-[var(--text-primary)] mb-4">➕ افزودن Mapping جدید</h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
                  <div>
                    <label className="text-[12px] text-[var(--text-secondary)] font-bold block mb-1.5">نماد اصلی *</label>
                    <input
                      type="text"
                      value={newOriginal}
                      onChange={(e) => setNewOriginal(e.target.value)}
                      placeholder="DJIUSD.x"
                      dir="ltr"
                      className="w-full bg-[var(--bg-card)] border-2 border-[var(--border-subtle)] rounded-[10px] px-3 py-2.5 text-[var(--text-primary)] text-sm font-bold focus:border-[var(--purple)] focus:outline-none text-center font-mono"
                    />
                  </div>
                  <div>
                    <label className="text-[12px] text-[var(--text-secondary)] font-bold block mb-1.5">نماد استاندارد *</label>
                    <input
                      type="text"
                      value={newCanonical}
                      onChange={(e) => setNewCanonical(e.target.value)}
                      placeholder="DJIUSD"
                      dir="ltr"
                      className="w-full bg-[var(--bg-card)] border-2 border-[var(--border-subtle)] rounded-[10px] px-3 py-2.5 text-[var(--text-primary)] text-sm font-bold focus:border-[var(--purple)] focus:outline-none text-center font-mono"
                    />
                  </div>
                  <div>
                    <label className="text-[12px] text-[var(--text-secondary)] font-bold block mb-1.5">توضیحات</label>
                    <input
                      type="text"
                      value={newDescription}
                      onChange={(e) => setNewDescription(e.target.value)}
                      placeholder="اختیاری"
                      className="w-full bg-[var(--bg-card)] border-2 border-[var(--border-subtle)] rounded-[10px] px-3 py-2.5 text-[var(--text-primary)] text-sm font-medium focus:border-[var(--purple)] focus:outline-none"
                    />
                  </div>
                </div>
                <button
                  onClick={handleCreateMapping}
                  className="text-white px-5 py-2.5 rounded-[10px] text-[12px] font-extrabold"
                  style={{ background: 'linear-gradient(135deg, var(--purple), #A78BFA)' }}
                >
                  ➕ افزودن
                </button>
              </div>

              {/* لیست Mappingها */}
              <div>
                <div className="flex justify-between items-center mb-3">
                  <h4 className="text-[14px] font-extrabold text-[var(--text-primary)]">
                    📋 لیست Mappingها ({mappings.length})
                  </h4>
                  {mappings.length === 0 && (
                    <button
                      onClick={handleSeedMappings}
                      className="bg-[var(--accent-soft)] border border-[var(--border-accent)] text-[var(--accent)] px-4 py-2 rounded-[10px] text-[12px] font-bold hover:bg-[var(--accent-light)] transition-all"
                    >
                      📦 وارد کردن پیش‌فرض‌ها
                    </button>
                  )}
                </div>

                {mappings.length === 0 ? (
                  <div className="text-[var(--text-muted)] text-sm text-center py-8 bg-[var(--bg-input)] rounded-[12px]">
                    هنوز Mappingی تعریف نکرده‌اید
                  </div>
                ) : (
                  <div className="space-y-2">
                    {mappings.map((m) => (
                      <div
                        key={m.id}
                        className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[12px] p-4 flex justify-between items-center hover:border-[var(--border-accent)] transition-all"
                      >
                        <div className="flex items-center gap-3 flex-wrap">
                          <span className="bg-[var(--bg-elevated)] border border-[var(--border-subtle)] px-3 py-1.5 rounded-[8px] text-[13px] font-mono font-bold text-[var(--text-secondary)]" dir="ltr">
                            {m.original_symbol}
                          </span>
                          <span className="text-[var(--text-muted)] text-lg">→</span>
                          <span className="bg-[var(--profit-soft)] border border-[var(--profit-border)] px-3 py-1.5 rounded-[8px] text-[13px] font-mono font-bold text-[var(--profit)]" dir="ltr">
                            {m.canonical_symbol}
                          </span>
                          {m.description && (
                            <span className="text-[11px] text-[var(--text-muted)] font-medium">
                              ({m.description})
                            </span>
                          )}
                        </div>
                        <button
                          onClick={() => handleDeleteMapping(m.id)}
                          className="text-[var(--loss)] hover:bg-[var(--loss-soft)] px-3 py-1.5 rounded-[8px] text-[12px] font-bold transition-all"
                        >
                          🗑️
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}