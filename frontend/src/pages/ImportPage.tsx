import { useState, useEffect, useRef } from 'react';
import {
  getAllVersions,
  importSoft4X,
  importMT4,
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
  const [personalAccounts, setPersonalAccounts] = useState<any[]>([]);
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null);
  const [selectedPropStage, setSelectedPropStage] = useState<number | null>(null);
  const [selectedPersonalAccount, setSelectedPersonalAccount] = useState<number | null>(null);
  const [importTarget, setImportTarget] = useState<'strategy' | 'prop' | 'personal'>('strategy');
  const [fileType, setFileType] = useState<'soft4x' | 'mt4'>('soft4x');
  const [symbol, setSymbol] = useState<string>('XAUUSD');
  const [testType, setTestType] = useState<'backtest' | 'forward' | 'real'>('backtest');
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
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

    import('../api/client')
      .then(({ getPersonalAccounts }) => getPersonalAccounts())
      .then((res) => setPersonalAccounts(res.data))
      .catch((err) => console.error('خطا در دریافت حساب‌های شخصی:', err));
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
      setError(null);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (selected) {
      setFile(selected);
      setResult(null);
      setError(null);
    }
  };

  const handleSubmit = async () => {
    if (!file) {
      setError('لطفاً یک فایل انتخاب کنید');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      let response;
      if (fileType === 'soft4x') {
        if (importTarget === 'strategy') {
          response = await importSoft4X(file, selectedVersion || undefined, symbol, testType, undefined, selectedPersonalAccount || undefined);
        } else if (importTarget === 'prop') {
          response = await importSoft4X(file, undefined, symbol, testType, selectedPropStage || undefined, undefined);
        } else {
          response = await importSoft4X(file, selectedVersion || undefined, symbol, testType, undefined, selectedPersonalAccount || undefined);
        }
      } else {
        if (importTarget === 'strategy') {
          response = await importMT4(file, selectedVersion || undefined, testType, undefined, selectedPersonalAccount || undefined);
        } else if (importTarget === 'prop') {
          response = await importMT4(file, undefined, testType, selectedPropStage || undefined, undefined);
        } else {
          response = await importMT4(file, selectedVersion || undefined, testType, undefined, selectedPersonalAccount || undefined);
        }
      }
      setResult(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'خطا در آپلود فایل');
    } finally {
      setLoading(false);
    }
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
        <div className="bg-[#FFEDF0] border border-[#F0A6B2] text-[#E45D72] p-4 rounded-[14px] text-sm font-semibold shadow-sm">
          ❌ {error}
          <button onClick={() => setError(null)} className="float-left text-xs font-bold">✕</button>
        </div>
      )}

      {/* دکمه‌ی مدیریت Symbol Mapping */}
      <div className="flex gap-3 flex-wrap">
        <button
          onClick={handleOpenMappingModal}
          className="bg-white border-2 border-[#E5EBF3] text-[#6B7A94] hover:border-[#A9C1FA] hover:text-[#3F7CFF] px-6 py-3 rounded-[12px] text-sm font-extrabold transition-all shadow-sm"
        >
          🔗 مدیریت Symbol Mapping
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* ستون چپ: تنظیمات */}
        <div className="bg-white border border-[#E5EBF3] rounded-[22px] p-6 shadow-md">
          <div className="flex items-center gap-3 mb-6 pb-4 border-b border-[#E5EBF3]">
            <div className="w-11 h-11 rounded-[14px] flex items-center justify-center text-xl text-white"
              style={{ background: 'linear-gradient(135deg, #3F7CFF, #5B8DEF)' }}>
              ⚙️
            </div>
            <div>
              <h3 className="text-lg font-extrabold text-[#1A2B47]">تنظیمات</h3>
              <p className="text-[12px] text-[#6B7A94] mt-0.5">مشخصات واردات را تعیین کنید</p>
            </div>
          </div>

          {/* نوع فایل */}
          <div className="mb-5">
            <label className="text-[13px] text-[#1A2B47] font-bold block mb-2">📁 نوع فایل</label>
            <div className="flex gap-2">
              <button
                onClick={() => setFileType('soft4x')}
                className={`flex-1 py-3 rounded-[12px] text-[13px] font-extrabold transition-all ${
                  fileType === 'soft4x'
                    ? 'text-white shadow-[0_6px_16px_rgba(63,124,255,0.3)]'
                    : 'bg-[#F8FAFF] border-2 border-[#E5EBF3] text-[#6B7A94] hover:border-[#A9C1FA]'
                }`}
                style={fileType === 'soft4x' ? { background: 'linear-gradient(135deg, #3F7CFF, #5B8DEF)' } : {}}
              >
                📊 Soft4X (اکسل)
              </button>
              <button
                onClick={() => setFileType('mt4')}
                className={`flex-1 py-3 rounded-[12px] text-[13px] font-extrabold transition-all ${
                  fileType === 'mt4'
                    ? 'text-white shadow-[0_6px_16px_rgba(63,124,255,0.3)]'
                    : 'bg-[#F8FAFF] border-2 border-[#E5EBF3] text-[#6B7A94] hover:border-[#A9C1FA]'
                }`}
                style={fileType === 'mt4' ? { background: 'linear-gradient(135deg, #3F7CFF, #5B8DEF)' } : {}}
              >
                📈 متاتریدر (HTML)
              </button>
            </div>
          </div>

          {/* مقصد */}
          <div className="mb-5">
            <label className="text-[13px] text-[#1A2B47] font-bold block mb-2">🎯 مقصد واردات</label>
            <div className="flex gap-2 flex-wrap">
              <button
                onClick={() => setImportTarget('strategy')}
                className={`flex-1 min-w-[100px] py-3 rounded-[12px] text-[13px] font-extrabold transition-all ${
                  importTarget === 'strategy'
                    ? 'text-white shadow-[0_6px_16px_rgba(19,174,129,0.3)]'
                    : 'bg-[#F8FAFF] border-2 border-[#E5EBF3] text-[#6B7A94] hover:border-[#A9C1FA]'
                }`}
                style={importTarget === 'strategy' ? { background: 'linear-gradient(135deg, #13AE81, #4DD9A9)' } : {}}
              >
                🎯 استراتژی
              </button>
              <button
                onClick={() => setImportTarget('personal')}
                className={`flex-1 min-w-[100px] py-3 rounded-[12px] text-[13px] font-extrabold transition-all ${
                  importTarget === 'personal'
                    ? 'text-white shadow-[0_6px_16px_rgba(19,174,129,0.3)]'
                    : 'bg-[#F8FAFF] border-2 border-[#E5EBF3] text-[#6B7A94] hover:border-[#A9C1FA]'
                }`}
                style={importTarget === 'personal' ? { background: 'linear-gradient(135deg, #13AE81, #4DD9A9)' } : {}}
              >
                💼 شخصی
              </button>
              <button
                onClick={() => setImportTarget('prop')}
                className={`flex-1 min-w-[100px] py-3 rounded-[12px] text-[13px] font-extrabold transition-all ${
                  importTarget === 'prop'
                    ? 'text-white shadow-[0_6px_16px_rgba(121,89,214,0.3)]'
                    : 'bg-[#F8FAFF] border-2 border-[#E5EBF3] text-[#6B7A94] hover:border-[#A9C1FA]'
                }`}
                style={importTarget === 'prop' ? { background: 'linear-gradient(135deg, #7959D6, #A78BFA)' } : {}}
              >
                🏢 پراپ
              </button>
            </div>
          </div>

          {/* نماد (فقط Soft4X) */}
          {fileType === 'soft4x' && (
            <div className="mb-5">
              <label className="text-[13px] text-[#1A2B47] font-bold block mb-2">🥇 نماد</label>
              <select
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
                className="w-full bg-[#F8FAFF] border-2 border-[#E5EBF3] rounded-[12px] px-5 py-3.5 text-[#1A2B47] text-sm font-bold focus:border-[#3F7CFF] focus:bg-white focus:outline-none focus:ring-4 focus:ring-[#EDF3FF] transition-all cursor-pointer"
              >
                <option value="XAUUSD">🥇 طلا (XAUUSD)</option>
                <option value="DJIUSD">📊 داوجونز (DJIUSD)</option>
              </select>
            </div>
          )}

          {/* نوع تست */}
          <div className="mb-5">
            <label className="text-[13px] text-[#1A2B47] font-bold block mb-2">🧪 نوع تست</label>
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
                        : 'bg-[#F8FAFF] border-2 border-[#E5EBF3] text-[#6B7A94] hover:border-[#A9C1FA]'
                    }`}
                    style={isActive ? { background: 'linear-gradient(135deg, #3F7CFF, #5B8DEF)' } : {}}
                  >
                    {t.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* مقصد انتخابی */}
          {importTarget === 'strategy' && (
            <div className="mb-2">
              <label className="text-[13px] text-[#1A2B47] font-bold block mb-2">
                📌 نسخه‌ی استراتژی <span className="text-[#E45D72]">*</span>
              </label>
              <select
                value={selectedVersion || ''}
                onChange={(e) => setSelectedVersion(e.target.value ? Number(e.target.value) : null)}
                className="w-full bg-[#F8FAFF] border-2 border-[#E5EBF3] rounded-[12px] px-5 py-3.5 text-[#1A2B47] text-sm font-bold focus:border-[#3F7CFF] focus:bg-white focus:outline-none focus:ring-4 focus:ring-[#EDF3FF] transition-all cursor-pointer"
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

          {importTarget === 'personal' && (
            <div className="mb-2">
              <label className="text-[13px] text-[#1A2B47] font-bold block mb-2">
                💼 حساب شخصی <span className="text-[#E45D72]">*</span>
              </label>
              <select
                value={selectedPersonalAccount || ''}
                onChange={(e) => setSelectedPersonalAccount(e.target.value ? Number(e.target.value) : null)}
                className="w-full bg-[#F8FAFF] border-2 border-[#E5EBF3] rounded-[12px] px-5 py-3.5 text-[#1A2B47] text-sm font-bold focus:border-[#3F7CFF] focus:bg-white focus:outline-none focus:ring-4 focus:ring-[#EDF3FF] transition-all cursor-pointer"
              >
                <option value="">— انتخاب حساب —</option>
                {personalAccounts.map((acc) => (
                  <option key={acc.id} value={acc.id}>
                    {acc.name} ({acc.broker_name})
                  </option>
                ))}
              </select>
            </div>
          )}

          {importTarget === 'prop' && (
            <div className="mb-2">
              <label className="text-[13px] text-[#1A2B47] font-bold block mb-2">
                📌 مرحله‌ی پراپ <span className="text-[#E45D72]">*</span>
              </label>
              <select
                value={selectedPropStage || ''}
                onChange={(e) => setSelectedPropStage(e.target.value ? Number(e.target.value) : null)}
                className="w-full bg-[#F8FAFF] border-2 border-[#E5EBF3] rounded-[12px] px-5 py-3.5 text-[#1A2B47] text-sm font-bold focus:border-[#7959D6] focus:bg-white focus:outline-none focus:ring-4 focus:ring-[#F1ECFF] transition-all cursor-pointer"
              >
                <option value="">— انتخاب مرحله —</option>
                {propStages.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.display_name}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {/* ستون راست: آپلود */}
        <div className="bg-white border border-[#E5EBF3] rounded-[22px] p-6 shadow-md">
          <div className="flex items-center gap-3 mb-6 pb-4 border-b border-[#E5EBF3]">
            <div className="w-11 h-11 rounded-[14px] flex items-center justify-center text-xl text-white"
              style={{ background: 'linear-gradient(135deg, #13AE81, #4DD9A9)' }}>
              📤
            </div>
            <div>
              <h3 className="text-lg font-extrabold text-[#1A2B47]">آپلود فایل</h3>
              <p className="text-[12px] text-[#6B7A94] mt-0.5">فایل مورد نظر را انتخاب کنید</p>
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
                ? 'border-[#3F7CFF] bg-[#EDF3FF] shadow-[0_0_0_4px_rgba(63,124,255,0.1)]'
                : file
                ? 'border-[#13AE81] bg-[#E5F8F1]'
                : 'border-[#E5EBF3] hover:border-[#A9C1FA] hover:bg-[#F8FAFF]'
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
                <div className="text-[15px] font-extrabold text-[#1A2B47] break-all">{file.name}</div>
                <div className="text-[12px] text-[#6B7A94] mt-2 font-semibold">
                  {(file.size / 1024).toFixed(2)} KB
                </div>
                <div className="text-[11px] text-[#13AE81] mt-2 font-bold">
                  ✓ فایل آماده‌ی آپلود است
                </div>
              </div>
            ) : (
              <div>
                <div className="text-6xl mb-4">📁</div>
                <div className="text-[15px] font-extrabold text-[#1A2B47] mb-2">
                  فایل را اینجا رها کنید
                </div>
                <div className="text-[12px] text-[#6B7A94] font-semibold">
                  یا کلیک کنید تا انتخاب کنید
                </div>
                <div className="text-[11px] text-[#9AA8BF] mt-3">
                  {fileType === 'soft4x' ? 'فرمت پشتیبانی: xlsx' : 'فرمت پشتیبانی: html'}
                </div>
              </div>
            )}
          </div>

          {/* دکمه‌ی ذخیره */}
          <button
            onClick={handleSubmit}
            disabled={loading || !file}
            className={`w-full mt-5 py-4 rounded-[14px] text-[15px] font-extrabold transition-all ${
              loading || !file
                ? 'bg-[#F5F7FB] text-[#9AA8BF] cursor-not-allowed'
                : 'text-white shadow-[0_6px_20px_rgba(63,124,255,0.4)] hover:shadow-[0_10px_28px_rgba(63,124,255,0.5)] hover:-translate-y-0.5'
            }`}
            style={!loading && file ? { background: 'linear-gradient(135deg, #3F7CFF, #5B8DEF)' } : {}}
          >
            {loading ? '⏳ در حال پردازش...' : '🚀 وارد کن'}
          </button>

          {/* راهنما */}
          <div className="mt-5 bg-[#EDF3FF] border border-[#A9C1FA] rounded-[14px] p-4">
            <div className="flex items-start gap-3">
              <div className="text-2xl shrink-0">💡</div>
              <div className="text-[12px] text-[#1A2B47] leading-relaxed">
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
        <div className="bg-white border border-[#E5EBF3] rounded-[22px] p-6 shadow-md">
          <div className="flex items-center gap-3 mb-5 pb-4 border-b border-[#E5EBF3]">
            <div className="w-11 h-11 rounded-[14px] flex items-center justify-center text-xl text-white"
              style={{ background: 'linear-gradient(135deg, #13AE81, #4DD9A9)' }}>
              ✅
            </div>
            <div>
              <h3 className="text-lg font-extrabold text-[#1A2B47]">نتیجه‌ی واردات</h3>
              <p className="text-[12px] text-[#6B7A94] mt-0.5">{result.message}</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            <div className="bg-[#EDF3FF] border border-[#A9C1FA] rounded-[16px] p-5">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 rounded-[12px] bg-white flex items-center justify-center text-xl shadow-sm">
                  📊
                </div>
                <div className="text-[12px] text-[#6B7A94] font-bold">شناسایی‌شده</div>
              </div>
              <div className="text-[28px] font-extrabold text-[#3F7CFF]">{result.total_trades}</div>
            </div>

            <div className={`border rounded-[16px] p-5 ${result.saved_trades > 0 ? 'bg-[#E5F8F1] border-[#A8E6CF]' : 'bg-[#F5F7FB] border-[#E5EBF3]'}`}>
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 rounded-[12px] bg-white flex items-center justify-center text-xl shadow-sm">
                  💾
                </div>
                <div className="text-[12px] text-[#6B7A94] font-bold">ذخیره‌شده</div>
              </div>
              <div className={`text-[28px] font-extrabold ${result.saved_trades > 0 ? 'text-[#13AE81]' : 'text-[#6B7A94]'}`}>
                {result.saved_trades}
              </div>
            </div>

            <div className="bg-[#FFF5DB] border border-[#F0BE5C] rounded-[16px] p-5">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 rounded-[12px] bg-white flex items-center justify-center text-xl shadow-sm">
                  📝
                </div>
                <div className="text-[12px] text-[#6B7A94] font-bold">وضعیت</div>
              </div>
              <div className="text-[13px] font-extrabold text-[#D99B25] leading-relaxed">
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
          <div className="bg-white rounded-[22px] max-w-3xl w-full max-h-[90vh] overflow-hidden shadow-2xl">
            <div className="flex justify-between items-center p-6 border-b border-[#E5EBF3]">
              <div className="flex items-center gap-3">
                <div className="w-11 h-11 rounded-[14px] flex items-center justify-center text-xl text-white"
                  style={{ background: 'linear-gradient(135deg, #7959D6, #A78BFA)' }}>
                  🔗
                </div>
                <div>
                  <h3 className="text-lg font-extrabold text-[#1A2B47]">مدیریت Symbol Mapping</h3>
                  <p className="text-[12px] text-[#6B7A94] mt-0.5">تبدیل نمادهای مختلف به نماد استاندارد</p>
                </div>
              </div>
              <button
                onClick={() => setShowMappingModal(false)}
                className="text-[#6B7A94] text-xl w-9 h-9 rounded-lg hover:bg-[#F5F7FB] transition-all"
              >
                ✕
              </button>
            </div>

            <div className="p-6 max-h-[calc(90vh-120px)] overflow-y-auto space-y-5">
              {mappingError && (
                <div className="bg-[#FFEDF0] border border-[#F0A6B2] text-[#E45D72] p-3 rounded-[12px] text-[13px] font-semibold">
                  ❌ {mappingError}
                </div>
              )}

              {/* فرم افزودن */}
              <div className="bg-[#F8FAFF] border-2 border-[#E5EBF3] rounded-[14px] p-5">
                <h4 className="text-[14px] font-extrabold text-[#1A2B47] mb-4">➕ افزودن Mapping جدید</h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
                  <div>
                    <label className="text-[12px] text-[#6B7A94] font-bold block mb-1.5">نماد اصلی *</label>
                    <input
                      type="text"
                      value={newOriginal}
                      onChange={(e) => setNewOriginal(e.target.value)}
                      placeholder="DJIUSD.x"
                      dir="ltr"
                      className="w-full bg-white border-2 border-[#E5EBF3] rounded-[10px] px-3 py-2.5 text-[#1A2B47] text-sm font-bold focus:border-[#7959D6] focus:outline-none text-center font-mono"
                    />
                  </div>
                  <div>
                    <label className="text-[12px] text-[#6B7A94] font-bold block mb-1.5">نماد استاندارد *</label>
                    <input
                      type="text"
                      value={newCanonical}
                      onChange={(e) => setNewCanonical(e.target.value)}
                      placeholder="DJIUSD"
                      dir="ltr"
                      className="w-full bg-white border-2 border-[#E5EBF3] rounded-[10px] px-3 py-2.5 text-[#1A2B47] text-sm font-bold focus:border-[#7959D6] focus:outline-none text-center font-mono"
                    />
                  </div>
                  <div>
                    <label className="text-[12px] text-[#6B7A94] font-bold block mb-1.5">توضیحات</label>
                    <input
                      type="text"
                      value={newDescription}
                      onChange={(e) => setNewDescription(e.target.value)}
                      placeholder="اختیاری"
                      className="w-full bg-white border-2 border-[#E5EBF3] rounded-[10px] px-3 py-2.5 text-[#1A2B47] text-sm font-medium focus:border-[#7959D6] focus:outline-none"
                    />
                  </div>
                </div>
                <button
                  onClick={handleCreateMapping}
                  className="text-white px-5 py-2.5 rounded-[10px] text-[12px] font-extrabold"
                  style={{ background: 'linear-gradient(135deg, #7959D6, #A78BFA)' }}
                >
                  ➕ افزودن
                </button>
              </div>

              {/* لیست Mappingها */}
              <div>
                <div className="flex justify-between items-center mb-3">
                  <h4 className="text-[14px] font-extrabold text-[#1A2B47]">
                    📋 لیست Mappingها ({mappings.length})
                  </h4>
                  {mappings.length === 0 && (
                    <button
                      onClick={handleSeedMappings}
                      className="bg-[#EDF3FF] border border-[#A9C1FA] text-[#3F7CFF] px-4 py-2 rounded-[10px] text-[12px] font-bold hover:bg-[#DCE8FF] transition-all"
                    >
                      📦 وارد کردن پیش‌فرض‌ها
                    </button>
                  )}
                </div>

                {mappings.length === 0 ? (
                  <div className="text-[#9AA8BF] text-sm text-center py-8 bg-[#F8FAFF] rounded-[12px]">
                    هنوز Mappingی تعریف نکرده‌اید
                  </div>
                ) : (
                  <div className="space-y-2">
                    {mappings.map((m) => (
                      <div
                        key={m.id}
                        className="bg-white border border-[#E5EBF3] rounded-[12px] p-4 flex justify-between items-center hover:border-[#A9C1FA] transition-all"
                      >
                        <div className="flex items-center gap-3 flex-wrap">
                          <span className="bg-[#F5F7FB] border border-[#E5EBF3] px-3 py-1.5 rounded-[8px] text-[13px] font-mono font-bold text-[#6B7A94]" dir="ltr">
                            {m.original_symbol}
                          </span>
                          <span className="text-[#9AA8BF] text-lg">→</span>
                          <span className="bg-[#E5F8F1] border border-[#A8E6CF] px-3 py-1.5 rounded-[8px] text-[13px] font-mono font-bold text-[#13AE81]" dir="ltr">
                            {m.canonical_symbol}
                          </span>
                          {m.description && (
                            <span className="text-[11px] text-[#9AA8BF] font-medium">
                              ({m.description})
                            </span>
                          )}
                        </div>
                        <button
                          onClick={() => handleDeleteMapping(m.id)}
                          className="text-[#E45D72] hover:bg-[#FFEDF0] px-3 py-1.5 rounded-[8px] text-[12px] font-bold transition-all"
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