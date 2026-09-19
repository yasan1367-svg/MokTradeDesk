import { useState, useEffect, useRef } from 'react';
import GlassCard from '../components/GlassCard';
import {
  getTrades,
  getTrade,
  updateTrade,
  deleteTrade,
  createManualTrade,
  uploadTradeScreenshot,
  getTradeScreenshots,
  deleteScreenshot,
  getAllVersions,
  getAllPropStages,
  getPersonalAccounts,
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
    test_type: 'backtest',
    account_type: 'personal',
    note: '',
    version_id: '',
    personal_account_id: '',
    prop_stage_id: '',
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [lightboxImage, setLightboxImage] = useState<string | null>(null);
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

  useEffect(() => {
    loadTrades();
  }, [filterVersion, filterSymbol, filterTestType, filterSource]);

  const loadFilters = async () => {
    try {
      const [versionsRes, stagesRes, personalRes] = await Promise.all([
        getAllVersions(),
        getAllPropStages(),
        getPersonalAccounts(),
      ]);
      setVersions(versionsRes.data);
      setPropStages(stagesRes.data);
      setPersonalAccounts(personalRes.data);
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
        search: searchQuery || undefined,
        limit: 200,
      });
      setTrades(res.data.trades);
      setTotal(res.data.total);
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
  // Delete Trade
  // ═════════════════════════════════════════════
  const handleDeleteTrade = async (trade: Trade) => {
    if (!confirm('آیا مطمئنید که می‌خواهید این معامله را حذف کنید؟')) return;
    try {
      await deleteTrade(trade.id);
      setSuccessMessage('معامله حذف شد');
      await loadTrades();
      setShowEditModal(false);
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'خطا در حذف');
    }
  };

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
      account_type: 'personal',
      note: '',
      version_id: '',
      personal_account_id: '',
      prop_stage_id: '',
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

    if (manualTrade.test_type === 'real') {
      const hasPersonal = !!manualTrade.personal_account_id;
      const hasProp = !!manualTrade.prop_stage_id;
      if (hasPersonal === hasProp) {
        setError('برای معامله‌ی REAL باید دقیقاً یکی از حساب شخصی یا مرحله‌ی پراپ انتخاب شود');
        return;
      }
    } else if (manualTrade.personal_account_id || manualTrade.prop_stage_id) {
      setError('برای Backtest و Forward، نباید حساب شخصی یا پراپ انتخاب شود');
      return;
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
        personal_account_id: manualTrade.personal_account_id ? parseInt(manualTrade.personal_account_id) : undefined,
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

  const getTestTypeLabel = (testType: string) => {
    const labels: Record<string, string> = {
      backtest: '🧪 بک‌تست',
      forward: '🔭 فوروارد',
      real: '💰 رییل',
    };
    return labels[testType] || testType;
  };

  return (
    <div>
      {error && (
        <div className="mb-4 bg-loss/10 border border-loss/30 text-loss p-3 rounded-xl">
          ❌ {error}
          <button onClick={() => setError(null)} className="float-left text-xs">✕</button>
        </div>
      )}
      {successMessage && (
        <div className="mb-4 bg-profit/10 border border-profit/30 text-profit p-3 rounded-xl">
          ✅ {successMessage}
        </div>
      )}

      <div className="flex gap-3 mb-6">
        <button
          onClick={handleOpenManualModal}
          className="bg-accent hover:bg-accent/80 text-white px-5 py-2 rounded-xl transition-all"
        >
          ➕ معامله‌ی دستی
        </button>
      </div>

      <GlassCard className="mb-6">
        <h3 className="text-text-primary font-bold mb-4">🔍 فیلترها</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 mb-3">
          <div>
            <label className="text-text-secondary text-xs block mb-1">نسخه</label>
            <select
              value={filterVersion || ''}
              onChange={(e) => setFilterVersion(e.target.value ? Number(e.target.value) : null)}
              className="w-full bg-card border border-card-border rounded-xl px-3 py-2 text-text-primary text-sm"
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
            <label className="text-text-secondary text-xs block mb-1">نماد</label>
            <select
              value={filterSymbol}
              onChange={(e) => setFilterSymbol(e.target.value)}
              className="w-full bg-card border border-card-border rounded-xl px-3 py-2 text-text-primary text-sm"
            >
              <option value="">همه</option>
              <option value="XAUUSD">🥇 طلا</option>
              <option value="DJIUSD">📊 داوجونز</option>
            </select>
          </div>

          <div>
            <label className="text-text-secondary text-xs block mb-1">نوع تست</label>
            <select
              value={filterTestType}
              onChange={(e) => setFilterTestType(e.target.value)}
              className="w-full bg-card border border-card-border rounded-xl px-3 py-2 text-text-primary text-sm"
            >
              <option value="">همه</option>
              <option value="backtest">🧪 بک‌تست</option>
              <option value="forward">🔭 فوروارد</option>
              <option value="real">💰 رییل</option>
            </select>
          </div>

          <div>
            <label className="text-text-secondary text-xs block mb-1">منبع</label>
            <select
              value={filterSource}
              onChange={(e) => setFilterSource(e.target.value)}
              className="w-full bg-card border border-card-border rounded-xl px-3 py-2 text-text-primary text-sm"
            >
              <option value="">همه</option>
              <option value="soft4x_import">📊 Soft4X</option>
              <option value="mt4_import">📈 متاتریدر</option>
              <option value="manual">✏️ دستی</option>
            </select>
          </div>
        </div>

        <div className="flex gap-2">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="🔍 جستجو در یادداشت‌ها..."
            className="flex-1 bg-card border border-card-border rounded-xl px-4 py-2 text-text-primary"
          />
          <button
            onClick={handleSearch}
            className="bg-accent hover:bg-accent/80 text-white px-6 py-2 rounded-xl"
          >
            جستجو
          </button>
        </div>
      </GlassCard>

      <GlassCard>
        <h3 className="text-text-primary font-bold mb-4">📋 معاملات ({total})</h3>

        {loading ? (
          <div className="text-text-secondary text-center py-8">⏳ در حال بارگذاری...</div>
        ) : trades.length === 0 ? (
          <div className="text-text-secondary text-center py-8">معامله‌ای یافت نشد</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-text-secondary border-b border-card-border">
                  <th className="text-right py-2">#</th>
                  <th className="text-right py-2">نماد</th>
                  <th className="text-right py-2">جهت</th>
                  <th className="text-right py-2">حجم</th>
                  <th className="text-right py-2">سود/زیان</th>
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
                    <td className="py-2 text-text-secondary text-xs">{t.id}</td>
                    <td className="py-2 text-text-primary font-bold">{t.symbol}</td>
                    <td className={`py-2 ${t.direction === 'buy' ? 'text-profit' : 'text-loss'}`}>
                      {t.direction === 'buy' ? 'خرید' : 'فروش'}
                    </td>
                    <td className="py-2 text-text-primary">{t.size}</td>
                    <td className={`py-2 font-bold ${(t.pnl || 0) >= 0 ? 'text-profit' : 'text-loss'}`}>
                      {(t.pnl || 0) >= 0 ? '+' : ''}{t.pnl?.toFixed(2)} $
                    </td>
                    <td className="py-2 text-text-secondary text-xs">{getSourceLabel(t.source)}</td>
                    <td className="py-2 text-text-secondary text-xs">{getTestTypeLabel(t.test_type)}</td>
                    <td className="py-2 text-text-secondary text-xs">{t.version_name || '-'}</td>
                    <td className="py-2 text-text-secondary text-xs max-w-[150px] truncate">
                      {t.note || '-'}
                    </td>
                    <td className="py-2">
  {t.screenshots_count > 0 ? (
    <button
      onClick={() => handleOpenGallery(t)}
      className="text-accent hover:bg-accent/20 px-2 py-1 rounded-lg transition-all"
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
                        className="text-accent hover:bg-accent/20 px-3 py-1 rounded-lg text-xs"
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
      </GlassCard>

      {/* مودال ویرایش */}
      {showEditModal && editingTrade && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="glass-card max-w-2xl w-full max-h-[90vh] overflow-y-auto p-6">
            <div className="flex justify-between items-center mb-5">
              <h3 className="text-xl font-bold text-text-primary">
                ✏️ ویرایش معامله #{editingTrade.id}
              </h3>
              <button onClick={() => setShowEditModal(false)} className="text-text-secondary">✕</button>
            </div>

            <div className="bg-card border border-card-border rounded-xl p-4 mb-5">
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
                <div>
                  <div className="text-text-secondary text-xs">نماد</div>
                  <div className="text-text-primary font-bold">{editingTrade.symbol}</div>
                </div>
                <div>
                  <div className="text-text-secondary text-xs">جهت</div>
                  <div className={`font-bold ${editingTrade.direction === 'buy' ? 'text-profit' : 'text-loss'}`}>
                    {editingTrade.direction === 'buy' ? 'خرید' : 'فروش'}
                  </div>
                </div>
                <div>
                  <div className="text-text-secondary text-xs">حجم</div>
                  <div className="text-text-primary font-bold">{editingTrade.size}</div>
                </div>
                <div>
                  <div className="text-text-secondary text-xs">قیمت باز</div>
                  <div className="text-text-primary">{editingTrade.open_price}</div>
                </div>
                <div>
                  <div className="text-text-secondary text-xs">قیمت بسته</div>
                  <div className="text-text-primary">{editingTrade.close_price || '-'}</div>
                </div>
                <div>
                  <div className="text-text-secondary text-xs">سود/زیان</div>
                  <div className={`font-bold ${(editingTrade.pnl || 0) >= 0 ? 'text-profit' : 'text-loss'}`}>
                    {editingTrade.pnl?.toFixed(2)} $
                  </div>
                </div>
              </div>
            </div>

            <div className="mb-5">
              <label className="text-text-secondary text-sm block mb-2">📝 یادداشت</label>
              <textarea
                value={editNote}
                onChange={(e) => setEditNote(e.target.value)}
                rows={4}
                className="w-full bg-card border border-card-border rounded-xl px-4 py-3 text-text-primary resize-none"
              />
            </div>

            <div className="mb-5">
              <div className="flex justify-between items-center mb-2">
                <label className="text-text-secondary text-sm">📷 اسکرین‌شات‌ها</label>
                <button
                  onClick={() => screenshotInputRef.current?.click()}
                  disabled={uploadingScreenshot}
                  className="bg-accent hover:bg-accent/80 text-white px-3 py-1 rounded-lg text-xs"
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
                <div className="text-text-secondary text-sm text-center py-4 bg-card border border-card-border rounded-xl">
                  اسکرین‌شاتی آپلود نشده
                </div>
              ) : (
                <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                  {editScreenshots.map((s) => (
                    <div key={s.id} className="relative group">
                      <img
  src={`http://localhost:8000/${s.file_path}`}
  alt="اسکرین‌شات"
  className="w-full h-24 object-cover rounded-lg border border-card-border cursor-pointer hover:opacity-80 transition-opacity"
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
                className="flex-1 bg-profit hover:bg-profit/80 text-white py-3 rounded-xl font-bold"
              >
                💾 ذخیره
              </button>
              {editingTrade.source === 'manual' && (
                <button
                  onClick={() => handleDeleteTrade(editingTrade)}
                  className="bg-loss hover:bg-loss/80 text-white px-6 py-3 rounded-xl"
                >
                  🗑️ حذف
                </button>
              )}
              <button
                onClick={() => setShowEditModal(false)}
                className="bg-card-border hover:bg-card-border/80 text-text-secondary px-6 py-3 rounded-xl"
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
              <h3 className="text-xl font-bold text-text-primary">➕ معامله‌ی دستی جدید</h3>
              <button onClick={() => setShowManualModal(false)} className="text-text-secondary">✕</button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
              <div>
                <label className="text-text-secondary text-xs block mb-1">نماد *</label>
                <select
                  value={manualTrade.symbol}
                  onChange={(e) => setManualTrade({ ...manualTrade, symbol: e.target.value })}
                  className="w-full bg-card border border-card-border rounded-xl px-3 py-2 text-text-primary"
                >
                  <option value="XAUUSD">🥇 طلا</option>
                  <option value="DJIUSD">📊 داوجونز</option>
                </select>
              </div>

              <div>
                <label className="text-text-secondary text-xs block mb-1">جهت *</label>
                <select
                  value={manualTrade.direction}
                  onChange={(e) => setManualTrade({ ...manualTrade, direction: e.target.value })}
                  className="w-full bg-card border border-card-border rounded-xl px-3 py-2 text-text-primary"
                >
                  <option value="buy">خرید</option>
                  <option value="sell">فروش</option>
                </select>
              </div>

              <div>
                <label className="text-text-secondary text-xs block mb-1">حجم *</label>
                <input
                  type="number"
                  step="0.01"
                  value={manualTrade.size}
                  onChange={(e) => setManualTrade({ ...manualTrade, size: e.target.value })}
                  className="w-full bg-card border border-card-border rounded-xl px-3 py-2 text-text-primary"
                />
              </div>

              <div>
                <label className="text-text-secondary text-xs block mb-1">قیمت باز شدن *</label>
                <input
                  type="number"
                  step="0.01"
                  value={manualTrade.open_price}
                  onChange={(e) => setManualTrade({ ...manualTrade, open_price: e.target.value })}
                  className="w-full bg-card border border-card-border rounded-xl px-3 py-2 text-text-primary"
                />
              </div>

              <div>
                <label className="text-text-secondary text-xs block mb-1">قیمت بسته شدن</label>
                <input
                  type="number"
                  step="0.01"
                  value={manualTrade.close_price}
                  onChange={(e) => setManualTrade({ ...manualTrade, close_price: e.target.value })}
                  className="w-full bg-card border border-card-border rounded-xl px-3 py-2 text-text-primary"
                />
              </div>

              <div>
                <label className="text-text-secondary text-xs block mb-1">سود/زیان ($)</label>
                <input
                  type="number"
                  step="0.01"
                  value={manualTrade.pnl}
                  onChange={(e) => setManualTrade({ ...manualTrade, pnl: e.target.value })}
                  className="w-full bg-card border border-card-border rounded-xl px-3 py-2 text-text-primary"
                />
              </div>

              <div>
                <label className="text-text-secondary text-xs block mb-1">حد ضرر</label>
                <input
                  type="number"
                  step="0.01"
                  value={manualTrade.sl}
                  onChange={(e) => setManualTrade({ ...manualTrade, sl: e.target.value })}
                  className="w-full bg-card border border-card-border rounded-xl px-3 py-2 text-text-primary"
                />
              </div>

              <div>
                <label className="text-text-secondary text-xs block mb-1">حد سود</label>
                <input
                  type="number"
                  step="0.01"
                  value={manualTrade.tp}
                  onChange={(e) => setManualTrade({ ...manualTrade, tp: e.target.value })}
                  className="w-full bg-card border border-card-border rounded-xl px-3 py-2 text-text-primary"
                />
              </div>

              <div>
                <label className="text-text-secondary text-xs block mb-1">نوع تست</label>
                <select
                  value={manualTrade.test_type}
                  onChange={(e) => setManualTrade({ ...manualTrade, test_type: e.target.value })}
                  className="w-full bg-card border border-card-border rounded-xl px-3 py-2 text-text-primary"
                >
                  <option value="backtest">🧪 بک‌تست</option>
                  <option value="forward">🔭 فوروارد</option>
                  <option value="real">💰 رییل</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
              <div>
                <label className="text-text-secondary text-xs block mb-1">زمان باز شدن *</label>
                <input
                  type="datetime-local"
                  value={manualTrade.open_time}
                  onChange={(e) => setManualTrade({ ...manualTrade, open_time: e.target.value })}
                  className="w-full bg-card border border-card-border rounded-xl px-3 py-2 text-text-primary"
                />
              </div>

              <div>
                <label className="text-text-secondary text-xs block mb-1">زمان بسته شدن</label>
                <input
                  type="datetime-local"
                  value={manualTrade.close_time}
                  onChange={(e) => setManualTrade({ ...manualTrade, close_time: e.target.value })}
                  className="w-full bg-card border border-card-border rounded-xl px-3 py-2 text-text-primary"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
              <div>
                <label className="text-text-secondary text-xs block mb-1">نسخه *</label>
                <select
                  value={manualTrade.version_id}
                  onChange={(e) => setManualTrade({ ...manualTrade, version_id: e.target.value })}
                  className="w-full bg-card border border-card-border rounded-xl px-3 py-2 text-text-primary"
                >
                  <option value="">انتخاب نسخه</option>
                  {versions.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.strategy_name} / {v.version_name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-text-secondary text-xs block mb-1">نوع حساب</label>
                <select
                  value={manualTrade.account_type}
                  onChange={(e) => {
                    const nextAccountType = e.target.value;
                    setManualTrade({
                      ...manualTrade,
                      account_type: nextAccountType,
                      personal_account_id: nextAccountType === 'personal' ? manualTrade.personal_account_id : '',
                      prop_stage_id: nextAccountType === 'prop' ? manualTrade.prop_stage_id : '',
                    });
                  }}
                  className="w-full bg-card border border-card-border rounded-xl px-3 py-2 text-text-primary"
                  disabled={manualTrade.test_type !== 'real'}
                >
                  <option value="personal">حساب شخصی</option>
                  <option value="prop">پراپ</option>
                </select>
              </div>
            </div>

            {manualTrade.test_type === 'real' && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
                <div>
                  <label className="text-text-secondary text-xs block mb-1">حساب شخصی</label>
                  <select
                    value={manualTrade.personal_account_id}
                    onChange={(e) => setManualTrade({ ...manualTrade, personal_account_id: e.target.value, prop_stage_id: '' })}
                    className="w-full bg-card border border-card-border rounded-xl px-3 py-2 text-text-primary"
                    disabled={manualTrade.account_type !== 'personal'}
                  >
                    <option value="">انتخاب حساب شخصی</option>
                    {personalAccounts.map((acc) => (
                      <option key={acc.id} value={acc.id}>{acc.name} ({acc.broker_name})</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="text-text-secondary text-xs block mb-1">مرحله‌ی پراپ</label>
                  <select
                    value={manualTrade.prop_stage_id}
                    onChange={(e) => setManualTrade({ ...manualTrade, prop_stage_id: e.target.value, personal_account_id: '' })}
                    className="w-full bg-card border border-card-border rounded-xl px-3 py-2 text-text-primary"
                    disabled={manualTrade.account_type !== 'prop'}
                  >
                    <option value="">انتخاب مرحله‌ی پراپ</option>
                    {propStages.map((s) => (
                      <option key={s.id} value={s.id}>{s.display_name || s.stage_type || `Stage ${s.id}`}</option>
                    ))}
                  </select>
                </div>
              </div>
            )}

            {manualTrade.test_type !== 'real' && (
              <div className="mb-3">
                <label className="text-text-secondary text-xs block mb-1">مرحله‌ی پراپ</label>
                <select
                  value={manualTrade.prop_stage_id}
                  onChange={(e) => setManualTrade({ ...manualTrade, prop_stage_id: e.target.value })}
                  className="w-full bg-card border border-card-border rounded-xl px-3 py-2 text-text-primary"
                >
                  <option value="">— بدون پراپ —</option>
                  {propStages.map((s) => (
                    <option key={s.id} value={s.id}>{s.display_name || s.stage_type || `Stage ${s.id}`}</option>
                  ))}
                </select>
              </div>
            )}

            <div className="mb-5">
              <label className="text-text-secondary text-xs block mb-1">یادداشت</label>
              <textarea
                value={manualTrade.note}
                onChange={(e) => setManualTrade({ ...manualTrade, note: e.target.value })}
                rows={2}
                className="w-full bg-card border border-card-border rounded-xl px-3 py-2 text-text-primary resize-none"
              />
            </div>

            <div className="flex gap-3">
              <button
                onClick={handleCreateManualTrade}
                className="flex-1 bg-profit hover:bg-profit/80 text-white py-3 rounded-xl font-bold"
              >
                💾 ثبت معامله
              </button>
              <button
                onClick={() => setShowManualModal(false)}
                className="flex-1 bg-card-border hover:bg-card-border/80 text-text-secondary py-3 rounded-xl"
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
            className="absolute top-4 right-4 bg-white/20 hover:bg-white/30 text-white w-10 h-10 rounded-full flex items-center justify-center text-2xl transition-all"
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
          <h3 className="text-xl font-bold text-text-primary">
            📷 اسکرین‌شات‌های معامله #{galleryTrade.id}
          </h3>
          <div className="text-text-secondary text-sm mt-1">
            {galleryTrade.symbol} • {galleryTrade.direction === 'buy' ? 'خرید' : 'فروش'} • {galleryTrade.size} لات
          </div>
        </div>
        <button
          onClick={() => setShowGalleryModal(false)}
          className="text-text-secondary hover:text-text-primary text-xl"
        >
          ✕
        </button>
      </div>

      {galleryScreenshots.length === 0 ? (
        <div className="text-text-secondary text-center py-8">
          اسکرین‌شاتی وجود ندارد
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {galleryScreenshots.map((s) => (
            <div key={s.id} className="relative group">
              <img
                src={`http://localhost:8000/${s.file_path.replace(/\\/g, '/')}`}
                alt="اسکرین‌شات"
                className="w-full rounded-lg border border-card-border cursor-pointer hover:opacity-90 transition-all"
                onClick={() => setLightboxImage(`http://localhost:8000/${s.file_path.replace(/\\/g, '/')}`)}
              />
              {s.description && (
                <div className="text-text-secondary text-xs mt-1 text-center">
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
    </div>
  );
}