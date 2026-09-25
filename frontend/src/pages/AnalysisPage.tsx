import { useState, useEffect } from 'react';
import GlassCard from '../components/GlassCard';
import MetricCard from '../components/MetricCard';
import AnalysisTable from '../components/AnalysisTable';
import {
  getAllVersions,
  getVersionAnalysis,
  getVersionTrades,
  analyzeVersion,
  exportAnalysisPdf,
} from '../api/client';

import EquityCurveChart from '../components/charts/EquityCurveChart';
import SessionBarChart from '../components/charts/SessionBarChart';
import WinLossPieChart from '../components/charts/WinLossPieChart';
import WeekdayBarChart from '../components/charts/WeekdayBarChart';
import PnLDistributionChart from '../components/charts/PnLDistributionChart';

interface Version {
  id: number;
  version_name: string;
  strategy_name: string;
}

export default function AnalysisPage() {
  const [versions, setVersions] = useState<Version[]>([]);
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null);
  const [analysis, setAnalysis] = useState<any>(null);
  const [trades, setTrades] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ═════════════════════════════════════════════
  // ۱. بارگذاری لیست نسخه‌ها (بدون شرط)
  // ═════════════════════════════════════════════
  useEffect(() => {
    getAllVersions()
      .then((res) => {
        setVersions(res.data);
        if (res.data.length > 0) {
          setSelectedVersion(res.data[0].id);
        }
      })
      .catch((err) => console.error('خطا در دریافت نسخه‌ها:', err));
  }, []);

  // ═════════════════════════════════════════════
  // ۲. بارگذاری تحلیل و معاملات (با شرط selectedVersion)
  // ═════════════════════════════════════════════
  useEffect(() => {
    if (!selectedVersion) return;

    setLoading(true);
    setError(null);

    const loadData = async () => {
      try {
        let analysisData: any = null;
        let tradesData: any[] = [];

        try {
          const analysisRes = await getVersionAnalysis(selectedVersion);
          analysisData = analysisRes.data;
        } catch (e) {
          console.log('تحلیلی یافت نشد');
        }

        try {
          const tradesRes = await getVersionTrades(selectedVersion);
          tradesData = tradesRes.data;
        } catch (e) {
          console.log('معامله‌ای یافت نشد');
        }

        setAnalysis(analysisData);
        setTrades(tradesData);
      } catch (err) {
        setError('خطا در بارگذاری داده‌ها');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [selectedVersion]);

  // ═════════════════════════════════════════════
  // اجرای مجدد تحلیل
  // ═════════════════════════════════════════════
  const handleReanalyze = async () => {
    if (!selectedVersion) return;

    setLoading(true);
    setError(null);
    try {
      await analyzeVersion(selectedVersion);
      const res = await getVersionAnalysis(selectedVersion);
      setAnalysis(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'خطا در تحلیل');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      {/* انتخاب نسخه */}
      <GlassCard className="mb-6">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex-1 min-w-[250px]">
            <label className="text-[var(--text-secondary)] text-sm block mb-2">انتخاب نسخه</label>
            <select
              value={selectedVersion || ''}
              onChange={(e) => setSelectedVersion(Number(e.target.value))}
              className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-4 py-3 text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none"
            >
              {versions.length === 0 ? (
                <option value="">— نسخه‌ای وجود ندارد —</option>
              ) : (
                versions.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.strategy_name} / {v.version_name}
                  </option>
                ))
              )}
            </select>
          </div>

          <button
            onClick={handleReanalyze}
            disabled={loading || !selectedVersion}
            className="bg-[var(--accent)] hover:bg-accent/80 text-white px-6 py-3 rounded-xl transition-all disabled:opacity-50 mt-6"
          >
            {loading ? '⏳ در حال تحلیل...' : '🔄 تحلیل مجدد'}
          </button>
          {analysis && selectedVersion && (
            <button
              onClick={async () => {
                try {
                  const res = await exportAnalysisPdf(selectedVersion!);
                  const blob = new Blob([res.data], { type: 'application/pdf' });
                  const url = window.URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = `analysis_${selectedVersion}_${new Date().toISOString().slice(0, 10)}.pdf`;
                  document.body.appendChild(a); a.click();
                  window.URL.revokeObjectURL(url); a.remove();
                } catch { setError('خطا در دانلود PDF'); }
              }}
              className="bg-[#E45D72] hover:bg-[#E45D72]/80 text-white px-5 py-3 rounded-xl transition-all mt-6 flex items-center gap-1"
            >
              📄 دانلود PDF
            </button>
          )}
        </div>

        {error && (
          <div className="mt-4 bg-loss/10 border border-loss/30 text-[var(--loss)] p-3 rounded-xl text-sm">
            ❌ {error}
          </div>
        )}
      </GlassCard>

      {analysis ? (
        <>
          {/* متریک‌های پایه */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 mb-6">
            <MetricCard
              label="💰 سود خالص"
              value={`${analysis.net_pnl >= 0 ? '+' : ''}${analysis.net_pnl} $`}
              sub={`از ${analysis.total_trades} معامله`}
              color={analysis.net_pnl >= 0 ? 'profit' : 'loss'}
              icon="💰"
            />
            <MetricCard
              label="📈 نرخ برد"
              value={`${analysis.win_rate}٪`}
              sub={`${Math.round((analysis.win_rate / 100) * analysis.total_trades)} برد`}
              icon="📈"
            />
            <MetricCard
              label="🏆 فاکتور سود"
              value={analysis.profit_factor}
              sub="سود کل / ضرر کل"
              color="accent"
              icon="🏆"
            />
            <MetricCard
              label="⚠️ حداکثر ضرر"
              value={`-${analysis.max_dd} $`}
              sub="کمترین نقطه‌ی منحنی"
              color="loss"
              icon="⚠️"
            />
          </div>

          {/* متریک‌های تکمیلی */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 mb-6">
            <MetricCard
              label="🎯 Net R"
              value={`${analysis.net_r} R`}
              sub="مجموع R-Multiple معاملات"
              color={analysis.net_r >= 0 ? 'profit' : 'loss'}
              icon="🎯"
            />
            <MetricCard
              label="📐 اکسپکتنسی"
              value={`${analysis.expectancy} $`}
              sub={analysis.expectancy_r !== null && analysis.expectancy_r !== undefined ? `${analysis.expectancy_r} R به‌ازای هر معامله` : 'به‌ازای هر معامله'}
              color={analysis.expectancy >= 0 ? 'profit' : 'loss'}
              icon="📐"
            />
            <MetricCard
              label="📊 میانگین برد / باخت"
              value={`+${analysis.avg_win} / -${analysis.avg_loss}`}
              sub={`بزرگ‌ترین: +${analysis.largest_win} / -${analysis.largest_loss}`}
              icon="📊"
            />
            <MetricCard
              label="🔻 بیشترین باخت متوالی"
              value={analysis.max_consecutive_losses}
              sub={
                analysis.consistency_analysis
                  ? `نسبت برد/باخت: ${analysis.consistency_analysis.avg_win_avg_loss_ratio}`
                  : undefined
              }
              color="loss"
              icon="🔻"
            />
          </div>

          {analysis.consistency_analysis && (
            <div className="glass-card p-5 mb-6">
              <div className="text-[var(--text-secondary)] text-sm mb-3">📉 تحلیل پایداری (Consistency)</div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                <div>
                  <div className="text-[var(--text-secondary)] text-xs mb-1">انحراف معیار سود معاملات</div>
                  <div className="font-bold text-[var(--text-primary)]">{analysis.consistency_analysis.pnl_std_dev} $</div>
                </div>
                <div>
                  <div className="text-[var(--text-secondary)] text-xs mb-1">وابستگی به معاملات بزرگ</div>
                  <div className="font-bold text-[var(--text-primary)]">
                    {analysis.consistency_analysis.top_trades_contribution_percent}٪ از سود از ۳ معامله‌ی برتر
                  </div>
                </div>
                <div>
                  <div className="text-[var(--text-secondary)] text-xs mb-1">نسبت میانگین برد به باخت</div>
                  <div className="font-bold text-[var(--text-primary)]">{analysis.consistency_analysis.avg_win_avg_loss_ratio}</div>
                </div>
              </div>
            </div>
          )}

{/* نمودارها */}
<div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
  <GlassCard className="lg:col-span-2">
    <h3 className="text-[var(--text-primary)] font-bold mb-4">📈 منحنی سرمایه</h3>
    <EquityCurveChart trades={trades} initialBalance={10000} />
  </GlassCard>

  <GlassCard>
    <h3 className="text-[var(--text-primary)] font-bold mb-4">🥇 برد / باخت</h3>
    <WinLossPieChart
      wins={Math.round((analysis.win_rate / 100) * analysis.total_trades)}
      losses={analysis.total_trades - Math.round((analysis.win_rate / 100) * analysis.total_trades)}
    />
  </GlassCard>
</div>

<div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
  <GlassCard>
    <h3 className="text-[var(--text-primary)] font-bold mb-4">🌍 نرخ برد بر اساس سشن</h3>
    <SessionBarChart data={analysis.session_analysis || {}} metric="win_rate" />
  </GlassCard>

  <GlassCard>
    <h3 className="text-[var(--text-primary)] font-bold mb-4">📅 نرخ برد بر اساس روز هفته</h3>
    <WeekdayBarChart data={analysis.weekday_analysis || {}} metric="win_rate" />
  </GlassCard>
</div>

<div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
  <GlassCard>
    <h3 className="text-[var(--text-primary)] font-bold mb-4">💰 توزیع سود بر اساس نماد</h3>
    <PnLDistributionChart trades={trades} />
  </GlassCard>

  <GlassCard>
    <h3 className="text-[var(--text-primary)] font-bold mb-4">💵 سود خالص بر اساس سشن</h3>
    <SessionBarChart data={analysis.session_analysis || {}} metric="net_pnl" />
  </GlassCard>
</div>

          {/* تحلیل‌های تفکیکی */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            <AnalysisTable
              title="تحلیل سشن‌ها"
              icon="🌍"
              data={analysis.session_analysis || {}}
              firstColumnLabel="سشن"
            />
            <AnalysisTable
              title="تحلیل روزهای هفته"
              icon="📅"
              data={analysis.weekday_analysis || {}}
              firstColumnLabel="روز"
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            <AnalysisTable
              title="تحلیل ساعت‌ها"
              icon="🕐"
              data={analysis.hour_analysis || {}}
              firstColumnLabel="ساعت"
            />
            <AnalysisTable
              title="تحلیل بازه‌های سفارشی"
              icon="⏰"
              data={analysis.custom_time_analysis || {}}
              firstColumnLabel="بازه"
            />
          </div>

          {/* جدول معاملات */}
          <GlassCard>
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-[var(--text-primary)] font-bold">
                📋 لیست معاملات ({trades.length})
              </h3>
            </div>

            {trades.length === 0 ? (
              <div className="text-[var(--text-secondary)] text-sm text-center py-8">
                معامله‌ای برای این نسخه ثبت نشده است
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-[var(--text-secondary)] border-b border-[var(--border-subtle)]">
                      <th className="text-right py-2">#</th>
                      <th className="text-right py-2">نماد</th>
                      <th className="text-right py-2">نوع تست</th>
                      <th className="text-right py-2">جهت</th>
                      <th className="text-right py-2">حجم</th>
                      <th className="text-right py-2">قیمت باز</th>
                      <th className="text-right py-2">قیمت بسته</th>
                      <th className="text-right py-2">سود/زیان</th>
                      <th className="text-right py-2">تاریخ بسته</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trades.map((t, idx) => (
                      <tr key={t.id} className="border-b border-card-border/50 hover:bg-card/50">
                        <td className="py-2 text-[var(--text-secondary)]">{idx + 1}</td>
                        <td className="py-2 text-[var(--text-primary)] font-bold">{t.symbol}</td>
                        <td className="py-2">
                          <span className="text-xs bg-accent/20 text-[var(--accent)] px-2 py-1 rounded">
                            {t.test_type === 'backtest' ? 'بک‌تست' :
                             t.test_type === 'forward' ? 'فوروارد' : 'رییل'}
                          </span>
                        </td>
                        <td className={`py-2 ${t.direction === 'buy' ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
                          {t.direction === 'buy' ? 'خرید' : 'فروش'}
                        </td>
                        <td className="py-2 text-[var(--text-primary)]">{t.size}</td>
                        <td className="py-2 text-[var(--text-primary)]">{t.open_price?.toFixed(2)}</td>
                        <td className="py-2 text-[var(--text-primary)]">{t.close_price?.toFixed(2)}</td>
                        <td className={`py-2 font-bold ${t.pnl >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
                          {t.pnl >= 0 ? '+' : ''}{t.pnl?.toFixed(2)} $
                        </td>
                        <td className="py-2 text-[var(--text-secondary)] text-xs">
                          {t.close_time ? new Date(t.close_time).toLocaleString('fa-IR') : '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </GlassCard>
        </>
      ) : (
        !loading && (
          <GlassCard>
            <div className="text-center py-12 text-[var(--text-secondary)]">
              <div className="text-4xl mb-4">📊</div>
              <div>برای مشاهده‌ی تحلیل، یک نسخه انتخاب کنید و روی "تحلیل مجدد" کلیک کنید</div>
            </div>
          </GlassCard>
        )
      )}
    </div>
  );
}