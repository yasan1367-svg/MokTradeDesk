import { useState, useEffect, useRef } from 'react';
import GlassCard from '../components/GlassCard';
import PersianDateInput from '../components/PersianDateInput';
import ConfirmDialog from '../components/ui/ConfirmDialog';
import {
  getTrades,
  getTrade,
  updateTrade,
  deleteTrade,
  batchDeleteTrades,
  createManualTrade,
  type TradeTestType,
  uploadTradeScreenshot,
  getTradeScreenshots,
  deleteScreenshot,
  getAllVersions,
  getAllPropStages,
  getPersonalTradingAccounts,
  exportTradesCsv,
  exportTradesPdf,
} from '../api/client';

interface Trade {
  id: number;
  symbol: string;
  direction: string;
  open_time: string;
  close_time: string | null;
  open_price: number;
  close_price: number | null;
  size: number;
  pnl: number | null;
  net_pnl?: number | null;
  source: string;
  test_type: string;
  note: string | null;
  version_name: string | null;
  strategy_name: string | null;
  prop_stage_id: number | null;
  screenshots_count: number;
}

export default function TradesPage() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [total, setTotal] = useState(0);
  const [versions, setVersions] = useState<any[]>([]);
  const [propStages, setPropStages] = useState<any[]>([]);
  const [personalAccounts, setPersonalAccounts] = useState<any[]>([]);

  const [filterVersion, setFilterVersion] = useState<number | null>(null);
  const [filterSymbol, setFilterSymbol] = useState('');
  const [filterTestType, setFilterTestType] = useState('');
  const [filterSource, setFilterSource] = useState('');
  const [filterDateFrom, setFilterDateFrom] = useState('');
  const [filterDateTo, setFilterDateTo] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  const [showEditModal, setShowEditModal] = useState(false);
  const [editingTrade, setEditingTrade] = useState<any>(null);
  const [editNote, setEditNote] = useState('');
  const [editScreenshots, setEditScreenshots] = useState<any[]>([]);
  const [uploadingScreenshot, setUploadingScreenshot] = useState(false);
  const screenshotInputRef = useRef<HTMLInputElement>(null);

  const [showManualModal, setShowManualModal] = useState(false);
  const [showGalleryModal, setShowGalleryModal] = useState(false);
const [galleryTrade, setGalleryTrade] = useState<Trade | null>(null);
const [galleryScreenshots, setGalleryScreenshots] = useState<any[]>([]);
  const [manualTrade, setManualTrade] = useState({
    symbol: 'XAUUSD',
    direction: 'buy',
    open_time: '',
    close_time: '',
    open_price: '',
    close_price: '',
    size: '',
    sl: '',
    tp: '',
    pnl: '',
    test_type: 'backtest' as TradeTestType,
    note: '',
    version_id: '',
    prop_stage_id: '',
    personal_trading_account_id: '',
  });

  // فاز ۳۸.۵ — نمایش و اعتبارسنجی شرطی دامنه، طبق قرارداد فاز ۲۷
  const isRealPersonal = manualTrade.test_type === 'real_personal';
  const isRealProp = manualTrade.test_type === 'real_prop';

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [lightboxImage, setLightboxImage] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const pageSize = 50;

  // فاز ۲۵: انتخاب گروهی + تأیید حذف
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [pendingDelete, setPendingDelete] = useState<{ ids: number[]; message: string } | null>(null);
  const handleOpenGallery = async (trade: Trade) => {
  if (trade.screenshots_count === 0) return;
  try {
    const res = await getTradeScreenshots(trade.id);
    setGalleryScreenshots(res.data);
    setGalleryTrade(trade);
    setShowGalleryModal(true);
  } catch (err: any) {
    setError(err.response?.data?.detail || 'خطا در بارگذاری اسکرین‌شات‌ها');
  }
};
  useEffect(() => {
    loadFilters();
  }, []);

  // وقتی فیلترها عوض می‌شوند، به صفحه‌ی ۱ برگرد و انتخاب گروهی را پاک کن
  useEffect(() => {
    setCurrentPage(1);
    setSelectedIds([]);
  }, [filterVersion, filterSymbol, filterTestType, filterSource, filterDateFrom, filterDateTo]);

  useEffect(() => {
    loadTrades();
  }, [filterVersion, filterSymbol, filterTestType, filterSource, filterDateFrom, filterDateTo, currentPage]);

  const loadFilters = async () => {
    try {
      const [versionsRes, stagesRes, ptaRes] = await Promise.all([
        getAllVersions(),
        getAllPropStages(),
        getPersonalTradingAccounts(),
      ]);
      setVersions(versionsRes.data);
      setPropStages(stagesRes.data);
      // فاز ۳۸.۵: دامنهٔ REAL_PERSONAL از «حساب معاملاتی شخصی» پر می‌شود (نه حساب مالی)
      setPersonalAccounts(ptaRes.data || []);
    } catch (err) {
      console.error('خطا:', err);
    }
  };

  const loadTrades = async () => {
    setLoading(true);
    try {
      const res = await getTrades({
        version_id: filterVersion || undefined,
        symbol: filterSymbol || undefined,
        test_type: filterTestType || undefined,
        source: filterSource || undefined,
        date_from: filterDateFrom || undefined,
        date_to: filterDateTo || undefined,
        search: searchQuery || undefined,
        page: currentPage,
        page_size: pageSize,
      });
      setTrades(res.data.trades);
      setTotal(res.data.total);
      setTotalPages(res.data.total_pages || 1);
    } catch (err) {
      console.error('خطا:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => {
    loadTrades();
  };

  // ═════════════════════════════════════════════
  // Edit Trade
  // ═════════════════════════════════════════════
  const handleOpenEdit = async (trade: Trade) => {
    try {
      const [tradeRes, screenshotsRes] = await Promise.all([
        getTrade(trade.id),
        getTradeScreenshots(trade.id),
      ]);
      setEditingTrade(tradeRes.data);
      setEditNote(tradeRes.data.note || '');
      setEditScreenshots(screenshotsRes.data);
      setShowEditModal(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'خطا در بارگذاری معامله');
    }
  };

  const handleSaveNote = async () => {
    if (!editingTrade) return;
    try {
      await updateTrade(editingTrade.id, { note: editNote });
      setSuccessMessage('یادداشت ذخیره شد');
      setShowEditModal(false);
      await loadTrades();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'خطا در ذخیره‌ی یادداشت');
    }
  };

  // ═════════════════════════════════════════════
  // Screenshots
  // ═════════════════════════════════════════════
  const handleUploadScreenshot = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !editingTrade) return;

    setUploadingScreenshot(true);
    try {
      await uploadTradeScreenshot(editingTrade.id, file);
      const res = await getTradeScreenshots(editingTrade.id);
      setEditScreenshots(res.data);
      setSuccessMessage('اسکرین‌شات آپلود شد');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'خطا در آپلود اسکرین‌شات');
    } finally {
      setUploadingScreenshot(false);
      if (screenshotInputRef.current) screenshotInputRef.current.value = '';
    }
  };

  const handleDeleteScreenshot = async (screenshotId: number) => {
    if (!confirm('آیا مطمئنید؟')) return;
    try {
      await deleteScreenshot(screenshotId);
      setEditScreenshots(editScreenshots.filter((s) => s.id !== screenshotId));
      setSuccessMessage('اسکرین‌شات حذف شد');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'خطا در حذف');
    }
  };

  // ═════════════════════════════════════════════
  // Delete Trade (فاز ۲۵: تأیید + حذف گروهی)
  // ═════════════════════════════════════════════
  // باز کردن دیالوگ تأیید برای یک معامله
  const handleDeleteTrade = (trade: Trade) => {
    setPendingDelete({
      ids: [trade.id],
      message: `آیا از حذف دائمی معامله #${trade.id} (${trade.symbol}) مطمئن هستید؟ این عمل قابل بازگشت نیست.`,
    });
  };

  // باز کردن دیالوگ تأیید برای حذف گروهی
  const handleBatchDelete = () => {
    if (selectedIds.length === 0) return;
    setPendingDelete({
      ids: [...selectedIds],
      message: `آیا از حذف دائمی ${selectedIds.length} معامله‌ی انتخاب‌شده مطمئن هستید؟ این عمل قابل بازگشت نیست.`,
    });
  };

  // اجرای حذف پس از تأیید
  const executeDelete = async () => {
    if (!pendingDelete) return;
    const ids = pendingDelete.ids;
    setPendingDelete(null);
    try {
      if (ids.length === 1) {
        await deleteTrade(ids[0]);
        setSuccessMessage('معامله حذف شد');
      } else {
        await batchDeleteTrades(ids);
        setSuccessMessage(`${ids.length} معامله حذف شد`);
      }
      setSelectedIds((prev) => prev.filter((id) => !ids.includes(id)));
      setShowEditModal(false);
      await loadTrades();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'خطا در حذف');
    }
  };

  // انتخاب/لغو انتخاب یک معامله
  const toggleSelect = (id: number) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  // انتخاب/لغو انتخاب همه‌ی معاملات صفحه‌ی جاری
  const toggleSelectAll = () => {
    const pageIds = trades.map((t) => t.id);
    const allSelected = pageIds.length > 0 && pageIds.every((id) => selectedIds.includes(id));
    setSelectedIds((prev) =>
      allSelected
        ? prev.filter((id) => !pageIds.includes(id))
        : Array.from(new Set([...prev, ...pageIds]))
    );
  };

  const allPageSelected =
    trades.length > 0 && trades.every((t) => selectedIds.includes(t.id));

  // ═════════════════════════════════════════════
  // Manual Trade
  // ═════════════════════════════════════════════
  const handleOpenManualModal = () => {
    setManualTrade({
      symbol: 'XAUUSD',
      direction: 'buy',
      open_time: new Date().toISOString().slice(0, 16),
      close_time: '',
      open_price: '',
      close_price: '',
      size: '',
      sl: '',
      tp: '',
      pnl: '',
      test_type: 'backtest',
      note: '',
      version_id: '',
      prop_stage_id: '',
      personal_trading_account_id: '',
    });
    setShowManualModal(true);
  };

  const handleCreateManualTrade = async () => {
    if (!manualTrade.symbol || !manualTrade.open_price || !manualTrade.size) {
      setError('نماد، قیمت باز شدن و حجم الزامی هستند');
      return;
    }

    if (!manualTrade.version_id) {
      setError('برای تمام معاملات، نسخه‌ی استراتژی الزامی است');
      return;
    }

    // فاز ۳۸.۵ — اعتبارسنجی هم‌سو با `TradeValidator` بک‌اند (قرارداد فاز ۲۷)
    // (`isRealPersonal` / `isRealProp` در بالای کامپوننت تعریف شده‌اند)
    if (isRealPersonal && !manualTrade.personal_trading_account_id) {
      setError('برای معامله‌ی رییل شخصی، انتخاب «حساب معاملاتی شخصی» الزامی است');
      return;
    }
    if (isRealPersonal && manualTrade.prop_stage_id) {
      setError('برای معامله‌ی رییل شخصی، نباید «مرحله‌ی پراپ» انتخاب شود');
      return;
    }
    if (isRealProp && !manualTrade.prop_stage_id) {
      setError('برای معامله‌ی رییل پراپ، انتخاب «مرحله‌ی پراپ» الزامی است');
      return;
    }
    if (isRealProp && manualTrade.personal_trading_account_id) {
      setError('برای معامله‌ی رییل پراپ، نباید «حساب معاملاتی شخصی» انتخاب شود');
      return;
    }
    if (!isRealPersonal && !isRealProp) {
      if (manualTrade.prop_stage_id) {
        setError('برای Backtest و Forward، نباید مرحله‌ی پراپ انتخاب شود');
        return;
      }
      if (manualTrade.personal_trading_account_id) {
        setError('برای Backtest و Forward، نباید حساب معاملاتی شخصی انتخاب شود');
        return;
      }
    }

    try {
      await createManualTrade({
        symbol: manualTrade.symbol,
        direction: manualTrade.direction,
        open_time: manualTrade.open_time,
        close_time: manualTrade.close_time || undefined,
        open_price: parseFloat(manualTrade.open_price),
        close_price: manualTrade.close_price ? parseFloat(manualTrade.close_price) : undefined,
        size: parseFloat(manualTrade.size),
        sl: manualTrade.sl ? parseFloat(manualTrade.sl) : undefined,
        tp: manualTrade.tp ? parseFloat(manualTrade.tp) : undefined,
        pnl: manualTrade.pnl ? parseFloat(manualTrade.pnl) : undefined,
        test_type: manualTrade.test_type,
        note: manualTrade.note || undefined,
        version_id: parseInt(manualTrade.version_id),
        personal_trading_account_id: manualTrade.personal_trading_account_id
          ? parseInt(manualTrade.personal_trading_account_id) : undefined,
        prop_stage_id: manualTrade.prop_stage_id ? parseInt(manualTrade.prop_stage_id) : undefined,
      });
      setSuccessMessage('معامله‌ی دستی ثبت شد');
      setShowManualModal(false);
      await loadTrades();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'خطا در ثبت');
    }
  };

  const getSourceLabel = (source: string) => {
    const labels: Record<string, string> = {
      soft4x_import: '📊 Soft4X',
      mt4_import: '📈 متاتریدر',
      manual: '✏️ دستی',
    };
    return labels[source] || source;
  };

  const downloadExport = async (apiFn: any, ext: string) => {
    try {
      const params: Record<string, any> = {};
      if (filterVersion) params.version_id = filterVersion;
      if (filterSymbol) params.symbol = filterSymbol;
      if (filterTestType) params.test_type = filterTestType;
      if (filterSource) params.source = filterSource;
      if (searchQuery) params.search = searchQuery;
      // فاز ۵۳.۵.۳: خروجی باید همان فیلترهای صفحه (شامل بازهٔ تاریخ) را حفظ کند
      if (filterDateFrom) params.date_from = filterDateFrom;
      if (filterDateTo) params.date_to = filterDateTo;

      const res = await apiFn(params);
      const blob = new Blob([res.data], { type: res.headers['content-type'] });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `trades_${new Date().toISOString().slice(0, 19).replace(/[:-]/g, '')}.${ext}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    } catch (err: any) {
      setError(err.response?.data?.detail || `خطا در دانلود فایل ${ext.toUpperCase()}`);
    }
  };

  // فاز ۳۸.۵: مقادیر قرارداد فاز ۲۷ (REAL_PERSONAL/REAL_PROP) + سازگاری با دادهٔ قدیمی ('real')
  const getTestTypeLabel = (testType: string) => {
    const labels: Record<string, string> = {
      backtest: '🧪 بک‌تست',
      forward: '🔭 فوروارد',
      real_personal: '💰 رییل شخصی',
      real_prop: '🏢 رییل پراپ',
      real: '💰 رییل (قدیمی)',
    };
    return labels[testType] || testType;
  };

  return (
    <div>
      {error && (
        <div className="mb-4 bg-loss/10 border border-loss/30 text-[var(--loss)] p-3 rounded-xl">
          ❌ {error}
          <button onClick={() => setError(null)} className="float-left text-xs">✕</button>
        </div>
      )}
      {successMessage && (
        <div className="mb-4 bg-profit/10 border border-profit/30 text-[var(--profit)] p-3 rounded-xl">
          ✅ {successMessage}
        </div>
      )}

      <div className="flex gap-3 mb-6 flex-wrap items-center">
        <button
          onClick={handleOpenManualModal}
          className="bg-[var(--accent)] hover:bg-accent/80 text-white px-5 py-2 rounded-xl transition-all"
        >
          ➕ معامله‌ی دستی
        </button>
        {selectedIds.length > 0 && (
          <button
            onClick={handleBatchDelete}
            className="bg-[var(--loss)] hover:bg-loss/80 text-white px-5 py-2 rounded-xl transition-all"
          >
            🗑️ حذف گروهی ({selectedIds.length})
          </button>
        )}
        {selectedIds.length > 0 && (
          <button
            onClick={() => setSelectedIds([])}
            className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] px-3 py-2 rounded-xl text-sm transition-all"
          >
            لغو انتخاب
          </button>
        )}
      </div>

      <GlassCard className="mb-6">
        <h3 className="text-[var(--text-primary)] font-bold mb-4">🔍 فیلترها</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 mb-3">
          <div>
            <label className="text-[var(--text-secondary)] text-xs block mb-1">نسخه</label>
            <select
              value={filterVersion || ''}
              onChange={(e) => setFilterVersion(e.target.value ? Number(e.target.value) : null)}
              className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-3 py-2 text-[var(--text-primary)] text-sm"
            >
              <option value="">همه</option>
              {versions.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.strategy_name} / {v.version_name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-[var(--text-secondary)] text-xs block mb-1">نماد</label>
            <select
              value={filterSymbol}
              onChange={(e) => setFilterSymbol(e.target.value)}
              className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-3 py-2 text-[var(--text-primary)] text-sm"
            >
              <option value="">همه</option>
              <option value="XAUUSD">🥇 طلا</option>
              <option value="DJIUSD">📊 داوجونز</option>
            </select>
          </div>

          <div>
            <label className="text-[var(--text-secondary)] text-xs block mb-1">نوع تست</label>
            <select
              value={filterTestType}
              onChange={(e) => setFilterTestType(e.target.value)}
              className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-3 py-2 text-[var(--text-primary)] text-sm"
            >
              <option value="">همه</option>
              <option value="backtest">🧪 بک‌تست</option>
              <option value="forward">🔭 فوروارد</option>
              <option value="real_personal">💰 رییل شخصی</option>
              <option value="real_prop">🏢 رییل پراپ</option>
            </select>
          </div>

          <div>
            <label className="text-[var(--text-secondary)] text-xs block mb-1">منبع</label>
            <select
              value={filterSource}
              onChange={(e) => setFilterSource(e.target.value)}
              className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-3 py-2 text-[var(--text-primary)] text-sm"
            >
              <option value="">همه</option>
              <option value="soft4x_import">📊 Soft4X</option>
              <option value="mt4_import">📈 متاتریدر</option>
              <option value="manual">✏️ دستی</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
          <PersianDateInput
            value={filterDateFrom}
            onChange={(v) => setFilterDateFrom(v)}
            label="از تاریخ"
          />
          <PersianDateInput
            value={filterDateTo}
            onChange={(v) => setFilterDateTo(v)}
            label="تا تاریخ"
          />
        </div>

        <div className="flex gap-2">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="🔍 جستجو در یادداشت‌ها..."
            className="flex-1 bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-4 py-2 text-[var(--text-primary)]"
          />
          <button
            onClick={handleSearch}
            className="bg-[var(--accent)] hover:bg-accent/80 text-white px-6 py-2 rounded-xl"
          >
            جستجو
          </button>
          <button
            onClick={() => downloadExport(exportTradesCsv, 'csv')}
            className="bg-[var(--profit)] hover:bg-[var(--profit)]/80 text-white px-4 py-2 rounded-xl text-sm flex items-center gap-1"
            title="دانلود CSV"
          >
            📥 CSV
          </button>
          <button
            onClick={() => downloadExport(exportTradesPdf, 'pdf')}
            className="bg-[var(--loss)] hover:bg-[var(--loss)]/80 text-white px-4 py-2 rounded-xl text-sm flex items-center gap-1"
            title="دانلود PDF"
          >
            📄 PDF
          </button>
        </div>
      </GlassCard>

      <GlassCard>
        <h3 className="text-[var(--text-primary)] font-bold mb-4">📋 معاملات ({total})</h3>

        {loading ? (
          <div className="text-[var(--text-secondary)] text-center py-8">⏳ در حال بارگذاری...</div>
        ) : trades.length === 0 ? (
          <div className="text-[var(--text-secondary)] text-center py-8">معامله‌ای یافت نشد</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-[var(--text-secondary)] border-b border-[var(--border-subtle)]">
                  <th className="text-right py-2 w-8">
                    <input
                      type="checkbox"
                      checked={allPageSelected}
                      onChange={toggleSelectAll}
                      className="accent-[var(--accent)] cursor-pointer"
                      title="انتخاب همه"
                      aria-label="انتخاب همه"
                    />
                  </th>
                  <th className="text-right py-2">#</th>
                  <th className="text-right py-2">نماد</th>
                  <th className="text-right py-2">جهت</th>
                  <th className="text-right py-2">حجم</th>
                  <th className="text-right py-2">سود خالص</th>
                  <th className="text-right py-2">منبع</th>
                  <th className="text-right py-2">نوع تست</th>
                  <th className="text-right py-2">نسخه</th>
                  <th className="text-right py-2">یادداشت</th>
                  <th className="text-right py-2">📷</th>
                  <th className="text-right py-2">عملیات</th>
                </tr>
              </thead>
              <tbody>
                {trades.map((t) => (
                  <tr key={t.id} className="border-b border-card-border/50 hover:bg-card/50">
                    <td className="py-2">
                      <input
                        type="checkbox"
                        checked={selectedIds.includes(t.id)}
                        onChange={() => toggleSelect(t.id)}
                        className="accent-[var(--accent)] cursor-pointer"
                        aria-label={`انتخاب معامله ${t.id}`}
                      />
                    </td>
                    <td className="py-2 text-[var(--text-secondary)] text-xs">{t.id}</td>
                    <td className="py-2 text-[var(--text-primary)] font-bold">{t.symbol}</td>
                    <td className={`py-2 ${t.direction === 'buy' ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
                      {t.direction === 'buy' ? 'خرید' : 'فروش'}
                    </td>
                    <td className="py-2 text-[var(--text-primary)]">{t.size}</td>
                    <td className={`py-2 font-bold ${(t.net_pnl || 0) >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
                      {(t.net_pnl || 0) >= 0 ? '+' : ''}{t.net_pnl?.toFixed(2)} USDT
                    </td>
                    <td className="py-2 text-[var(--text-secondary)] text-xs">{getSourceLabel(t.source)}</td>
                    <td className="py-2 text-[var(--text-secondary)] text-xs">{getTestTypeLabel(t.test_type)}</td>
                    <td className="py-2 text-[var(--text-secondary)] text-xs">{t.version_name || '-'}</td>
                    <td className="py-2 text-[var(--text-secondary)] text-xs max-w-[150px] truncate">
                      {t.note || '-'}
                    </td>
                    <td className="py-2">
  {t.screenshots_count > 0 ? (
    <button
      onClick={() => handleOpenGallery(t)}
      className="text-[var(--accent)] hover:bg-accent/20 px-2 py-1 rounded-lg transition-all"
    >
      📷 {t.screenshots_count}
    </button>
  ) : (
    <span className="text-text-secondary/50">📷 ۰</span>
  )}
</td>
                    <td className="py-2">
                      <button
                        onClick={() => handleOpenEdit(t)}
                        className="text-[var(--accent)] hover:bg-accent/20 px-3 py-1 rounded-lg text-xs"
                      >
                        ✏️ ویرایش
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* صفحه‌بندی */}
        {total > pageSize && (
          <div className="flex items-center justify-between mt-4 px-2 pb-2" dir="ltr">
            <span className="text-[12px] text-[var(--text-secondary)] font-medium">
              {total > 0 ? `نمایش ${(currentPage - 1) * pageSize + 1}–${Math.min(currentPage * pageSize, total)} از ${total} معامله` : ''}
            </span>
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                disabled={currentPage <= 1}
                className="px-3 py-1.5 rounded-lg text-[12px] font-bold transition-all disabled:opacity-30 disabled:cursor-not-allowed border border-[var(--border-subtle)] hover:bg-[var(--accent-soft)] text-[var(--text-secondary)] hover:text-[var(--accent)]"
              >
                ‹ قبلی
              </button>

              {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
                let pageNum: number;
                if (totalPages <= 7) {
                  pageNum = i + 1;
                } else if (currentPage <= 4) {
                  pageNum = i + 1;
                } else if (currentPage >= totalPages - 3) {
                  pageNum = totalPages - 6 + i;
                } else {
                  pageNum = currentPage - 3 + i;
                }
                return (
                  <button
                    key={pageNum}
                    onClick={() => setCurrentPage(pageNum)}
                    className={`min-w-[32px] h-[32px] rounded-lg text-[12px] font-bold transition-all ${
                      currentPage === pageNum
                        ? 'text-white shadow-[0_4px_10px_rgba(63,124,255,0.3)]'
                        : 'text-[var(--text-secondary)] border border-[var(--border-subtle)] hover:bg-[var(--accent-soft)] hover:text-[var(--accent)]'
                    }`}
                    style={currentPage === pageNum ? { background: 'linear-gradient(135deg, var(--accent), var(--accent-strong))' } : {}}
                  >
                    {pageNum}
                  </button>
                );
              })}

              <button
                onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                disabled={currentPage >= totalPages}
                className="px-3 py-1.5 rounded-lg text-[12px] font-bold transition-all disabled:opacity-30 disabled:cursor-not-allowed border border-[var(--border-subtle)] hover:bg-[var(--accent-soft)] text-[var(--text-secondary)] hover:text-[var(--accent)]"
              >
                بعدی ›
              </button>
            </div>
          </div>
        )}
      </GlassCard>

      {/* مودال ویرایش */}
      {showEditModal && editingTrade && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="glass-card max-w-2xl w-full max-h-[90vh] overflow-y-auto p-6">
            <div className="flex justify-between items-center mb-5">
              <h3 className="text-xl font-bold text-[var(--text-primary)]">
                ✏️ ویرایش معامله #{editingTrade.id}
              </h3>
              <button onClick={() => setShowEditModal(false)} className="text-[var(--text-secondary)]">✕</button>
            </div>

            <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl p-4 mb-5">
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
                <div>
                  <div className="text-[var(--text-secondary)] text-xs">نماد</div>
                  <div className="text-[var(--text-primary)] font-bold">{editingTrade.symbol}</div>
                </div>
                <div>
                  <div className="text-[var(--text-secondary)] text-xs">جهت</div>
                  <div className={`font-bold ${editingTrade.direction === 'buy' ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
                    {editingTrade.direction === 'buy' ? 'خرید' : 'فروش'}
                  </div>
                </div>
                <div>
                  <div className="text-[var(--text-secondary)] text-xs">حجم</div>
                  <div className="text-[var(--text-primary)] font-bold">{editingTrade.size}</div>
                </div>
                <div>
                  <div className="text-[var(--text-secondary)] text-xs">قیمت باز</div>
                  <div className="text-[var(--text-primary)]">{editingTrade.open_price}</div>
                </div>
                <div>
                  <div className="text-[var(--text-secondary)] text-xs">قیمت بسته</div>
                  <div className="text-[var(--text-primary)]">{editingTrade.close_price || '-'}</div>
                </div>
                <div>
                  <div className="text-[var(--text-secondary)] text-xs">سود خالص</div>
                  <div className={`font-bold ${(editingTrade.net_pnl || 0) >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
                    {editingTrade.net_pnl?.toFixed(2)} USDT
                  </div>
                </div>
              </div>
              <div className="flex flex-wrap gap-3 mt-2">
                <span className="text-[10px] text-[var(--text-secondary)]">
                  سود ناخالص: {editingTrade.pnl?.toFixed(2) || '0.00'} |
                  کمیسیون: {editingTrade.commission?.toFixed(2) || '0.00'} |
                  سواپ: {editingTrade.swap?.toFixed(2) || '0.00'}
                </span>
              </div>
            </div>

            <div className="mb-5">
              <label className="text-[var(--text-secondary)] text-sm block mb-2">📝 یادداشت</label>
              <textarea
                value={editNote}
                onChange={(e) => setEditNote(e.target.value)}
                rows={4}
                className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-4 py-3 text-[var(--text-primary)] resize-none"
              />
            </div>

            <div className="mb-5">
              <div className="flex justify-between items-center mb-2">
                <label className="text-[var(--text-secondary)] text-sm">📷 اسکرین‌شات‌ها</label>
                <button
                  onClick={() => screenshotInputRef.current?.click()}
                  disabled={uploadingScreenshot}
                  className="bg-[var(--accent)] hover:bg-accent/80 text-white px-3 py-1 rounded-lg text-xs"
                >
                  {uploadingScreenshot ? '⏳...' : '➕ آپلود'}
                </button>
                <input
                  ref={screenshotInputRef}
                  type="file"
                  accept="image/*"
                  onChange={handleUploadScreenshot}
                  className="hidden"
                />
              </div>

              {editScreenshots.length === 0 ? (
                <div className="text-[var(--text-secondary)] text-sm text-center py-4 bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl">
                  اسکرین‌شاتی آپلود نشده
                </div>
              ) : (
                <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                  {editScreenshots.map((s) => (
                    <div key={s.id} className="relative group">
                      <img
  src={`http://localhost:8000/${s.file_path}`}
  alt="اسکرین‌شات"
  className="w-full h-24 object-cover rounded-lg border border-[var(--border-subtle)] cursor-pointer hover:opacity-80 transition-opacity"
  onClick={() => setLightboxImage(`http://localhost:8000/${s.file_path}`)}
/>
                      <button
                        onClick={() => handleDeleteScreenshot(s.id)}
                        className="absolute top-1 left-1 bg-loss/80 text-white w-6 h-6 rounded-full text-xs opacity-0 group-hover:opacity-100 transition-all"
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="flex gap-3">
              <button
                onClick={handleSaveNote}
                className="flex-1 bg-[var(--profit)] hover:bg-profit/80 text-white py-3 rounded-xl font-bold"
              >
                💾 ذخیره
              </button>
              <button
                onClick={() => handleDeleteTrade(editingTrade)}
                className="bg-[var(--loss)] hover:bg-loss/80 text-white px-6 py-3 rounded-xl"
              >
                🗑️ حذف
              </button>
              <button
                onClick={() => setShowEditModal(false)}
                className="bg-[var(--border-subtle)] hover:bg-card-border/80 text-[var(--text-secondary)] px-6 py-3 rounded-xl"
              >
                ✕ لغو
              </button>
            </div>
          </div>
        </div>
      )}

      {/* مودال معامله‌ی دستی */}
      {showManualModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="glass-card max-w-3xl w-full max-h-[90vh] overflow-y-auto p-6">
            <div className="flex justify-between items-center mb-5">
              <h3 className="text-xl font-bold text-[var(--text-primary)]">➕ معامله‌ی دستی جدید</h3>
              <button onClick={() => setShowManualModal(false)} className="text-[var(--text-secondary)]">✕</button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
              <div>
                <label className="text-[var(--text-secondary)] text-xs block mb-1">نماد *</label>
                <select
                  value={manualTrade.symbol}
                  onChange={(e) => setManualTrade({ ...manualTrade, symbol: e.target.value })}
                  className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-3 py-2 text-[var(--text-primary)]"
                >
                  <option value="XAUUSD">🥇 طلا</option>
                  <option value="DJIUSD">📊 داوجونز</option>
                </select>
              </div>

              <div>
                <label className="text-[var(--text-secondary)] text-xs block mb-1">جهت *</label>
                <select
                  value={manualTrade.direction}
                  onChange={(e) => setManualTrade({ ...manualTrade, direction: e.target.value })}
                  className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-3 py-2 text-[var(--text-primary)]"
                >
                  <option value="buy">خرید</option>
                  <option value="sell">فروش</option>
                </select>
              </div>

              <div>
                <label className="text-[var(--text-secondary)] text-xs block mb-1">حجم *</label>
                <input
                  type="number"
                  step="0.01"
                  value={manualTrade.size}
                  onChange={(e) => setManualTrade({ ...manualTrade, size: e.target.value })}
                  className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-3 py-2 text-[var(--text-primary)]"
                />
              </div>

              <div>
                <label className="text-[var(--text-secondary)] text-xs block mb-1">قیمت باز شدن *</label>
                <input
                  type="number"
                  step="0.01"
                  value={manualTrade.open_price}
                  onChange={(e) => setManualTrade({ ...manualTrade, open_price: e.target.value })}
                  className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-3 py-2 text-[var(--text-primary)]"
                />
              </div>

              <div>
                <label className="text-[var(--text-secondary)] text-xs block mb-1">قیمت بسته شدن</label>
                <input
                  type="number"
                  step="0.01"
                  value={manualTrade.close_price}
                  onChange={(e) => setManualTrade({ ...manualTrade, close_price: e.target.value })}
                  className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-3 py-2 text-[var(--text-primary)]"
                />
              </div>

              <div>
                <label className="text-[var(--text-secondary)] text-xs block mb-1">سود/زیان (USDT )</label>
                <input
                  type="number"
                  step="0.01"
                  value={manualTrade.pnl}
                  onChange={(e) => setManualTrade({ ...manualTrade, pnl: e.target.value })}
                  className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-3 py-2 text-[var(--text-primary)]"
                />
              </div>

              <div>
                <label className="text-[var(--text-secondary)] text-xs block mb-1">حد ضرر</label>
                <input
                  type="number"
                  step="0.01"
                  value={manualTrade.sl}
                  onChange={(e) => setManualTrade({ ...manualTrade, sl: e.target.value })}
                  className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-3 py-2 text-[var(--text-primary)]"
                />
              </div>

              <div>
                <label className="text-[var(--text-secondary)] text-xs block mb-1">حد سود</label>
                <input
                  type="number"
                  step="0.01"
                  value={manualTrade.tp}
                  onChange={(e) => setManualTrade({ ...manualTrade, tp: e.target.value })}
                  className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-3 py-2 text-[var(--text-primary)]"
                />
              </div>

              <div>
                <label className="text-[var(--text-secondary)] text-xs block mb-1">نوع تست</label>
                <select
                  value={manualTrade.test_type}
                  onChange={(e) => setManualTrade({ ...manualTrade, test_type: e.target.value as TradeTestType })}
                  className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-3 py-2 text-[var(--text-primary)]"
                >
                  <option value="backtest">🧪 بک‌تست</option>
                  <option value="forward">🔭 فوروارد</option>
                  <option value="real_personal">💰 رییل شخصی</option>
                  <option value="real_prop">🏢 رییل پراپ</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
              <div>
                <label className="text-[var(--text-secondary)] text-xs block mb-1">زمان باز شدن *</label>
                <input
                  type="datetime-local"
                  value={manualTrade.open_time}
                  onChange={(e) => setManualTrade({ ...manualTrade, open_time: e.target.value })}
                  className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-3 py-2 text-[var(--text-primary)]"
                />
              </div>

              <div>
                <label className="text-[var(--text-secondary)] text-xs block mb-1">زمان بسته شدن</label>
                <input
                  type="datetime-local"
                  value={manualTrade.close_time}
                  onChange={(e) => setManualTrade({ ...manualTrade, close_time: e.target.value })}
                  className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-3 py-2 text-[var(--text-primary)]"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
              <div>
                <label className="text-[var(--text-secondary)] text-xs block mb-1">نسخه *</label>
                <select
                  value={manualTrade.version_id}
                  onChange={(e) => setManualTrade({ ...manualTrade, version_id: e.target.value })}
                  className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-3 py-2 text-[var(--text-primary)]"
                >
                  <option value="">انتخاب نسخه</option>
                  {versions.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.strategy_name} / {v.version_name}
                    </option>
                  ))}
                </select>
              </div>

              {isRealPersonal && (
                <div>
                  <label className="text-[var(--text-secondary)] text-xs block mb-1">حساب معاملاتی شخصی *</label>
                  <select
                    value={manualTrade.personal_trading_account_id}
                    onChange={(e) => setManualTrade({ ...manualTrade, personal_trading_account_id: e.target.value })}
                    className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-3 py-2 text-[var(--text-primary)]"
                  >
                    <option value="">انتخاب حساب معاملاتی</option>
                    {personalAccounts.map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.account_label || a.account_number || `#${a.id}`}
                        {a.broker_name ? ` — ${a.broker_name}` : ''}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>

            {isRealProp && (
              <div className="mb-3">
                <label className="text-[var(--text-secondary)] text-xs block mb-1">مرحله‌ی پراپ *</label>
                <select
                  value={manualTrade.prop_stage_id}
                  onChange={(e) => setManualTrade({ ...manualTrade, prop_stage_id: e.target.value })}
                  className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-3 py-2 text-[var(--text-primary)]"
                >
                  <option value="">انتخاب مرحله‌ی پراپ</option>
                  {propStages.map((s) => (
                    <option key={s.id} value={s.id}>{s.display_name || s.stage_type || `Stage ${s.id}`}</option>
                  ))}
                </select>
              </div>
            )}

            <div className="mb-5">
              <label className="text-[var(--text-secondary)] text-xs block mb-1">یادداشت</label>
              <textarea
                value={manualTrade.note}
                onChange={(e) => setManualTrade({ ...manualTrade, note: e.target.value })}
                rows={2}
                className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-3 py-2 text-[var(--text-primary)] resize-none"
              />
            </div>

            <div className="flex gap-3">
              <button
                onClick={handleCreateManualTrade}
                className="flex-1 bg-[var(--profit)] hover:bg-profit/80 text-white py-3 rounded-xl font-bold"
              >
                💾 ثبت معامله
              </button>
              <button
                onClick={() => setShowManualModal(false)}
                className="flex-1 bg-[var(--border-subtle)] hover:bg-card-border/80 text-[var(--text-secondary)] py-3 rounded-xl"
              >
                ✕ لغو
              </button>
            </div>
          </div>
        </div>
      )}
      {/* Lightbox */}
      {lightboxImage && (
        <div
          className="fixed inset-0 bg-black/90 backdrop-blur-sm flex items-center justify-center z-[100] p-4"
          onClick={() => setLightboxImage(null)}
        >
          <button
            onClick={() => setLightboxImage(null)}
            className="absolute top-4 right-4 bg-[var(--bg-card)]/20 hover:bg-[var(--bg-card)]/30 text-white w-10 h-10 rounded-full flex items-center justify-center text-2xl transition-all"
          >
            ✕
          </button>
          <img
            src={lightboxImage}
            alt="اسکرین‌شات بزرگ"
            className="max-w-full max-h-full object-contain rounded-lg"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
      {/* مودال گالری اسکرین‌شات‌ها */}
{showGalleryModal && galleryTrade && (
  <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-[90] p-4">
    <div className="glass-card max-w-4xl w-full max-h-[90vh] overflow-y-auto p-6">
      <div className="flex justify-between items-center mb-5">
        <div>
          <h3 className="text-xl font-bold text-[var(--text-primary)]">
            📷 اسکرین‌شات‌های معامله #{galleryTrade.id}
          </h3>
          <div className="text-[var(--text-secondary)] text-sm mt-1">
            {galleryTrade.symbol} • {galleryTrade.direction === 'buy' ? 'خرید' : 'فروش'} • {galleryTrade.size} لات
          </div>
        </div>
        <button
          onClick={() => setShowGalleryModal(false)}
          className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] text-xl"
        >
          ✕
        </button>
      </div>

      {galleryScreenshots.length === 0 ? (
        <div className="text-[var(--text-secondary)] text-center py-8">
          اسکرین‌شاتی وجود ندارد
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {galleryScreenshots.map((s) => (
            <div key={s.id} className="relative group">
              <img
                src={`http://localhost:8000/${s.file_path.replace(/\\/g, '/')}`}
                alt="اسکرین‌شات"
                className="w-full rounded-lg border border-[var(--border-subtle)] cursor-pointer hover:opacity-90 transition-all"
                onClick={() => setLightboxImage(`http://localhost:8000/${s.file_path.replace(/\\/g, '/')}`)}
              />
              {s.description && (
                <div className="text-[var(--text-secondary)] text-xs mt-1 text-center">
                  {s.description}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  </div>
)}

      {/* فاز ۲۵: دیالوگ تأیید حذف (تکی/گروهی) */}
      <ConfirmDialog
        open={!!pendingDelete}
        title={pendingDelete && pendingDelete.ids.length > 1 ? 'تأیید حذف گروهی' : 'تأیید حذف'}
        message={pendingDelete?.message ?? ''}
        confirmLabel="حذف"
        cancelLabel="انصراف"
        danger
        onConfirm={executeDelete}
        onCancel={() => setPendingDelete(null)}
      />
    </div>
  );
}
