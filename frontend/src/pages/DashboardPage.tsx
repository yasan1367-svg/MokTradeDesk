import { useState, useEffect } from 'react';
import StatCard from '../components/ui/StatCard';
import { Card, CardHeader } from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import ProgressBar from '../components/ui/ProgressBar';
import {
  getAllVersions,
  getVersionAnalysis,
  getPropAccounts,
  getActivePropStages,
  checkPassReady,
} from '../api/client';

export default function DashboardPage() {
  const [selectedVersionId, setSelectedVersionId] = useState<number | null>(null);
  const [analysis, setAnalysis] = useState<any>(null);
  const [propAccounts, setPropAccounts] = useState<any[]>([]);
  const [activeStages, setActiveStages] = useState<any[]>([]);
const [currentStageProgress, setCurrentStageProgress] = useState<any>(null);

  useEffect(() => {
  getAllVersions().then((res) => {
    if (res.data.length > 0) setSelectedVersionId(res.data[0].id);
  });

  getPropAccounts().then((res) => setPropAccounts(res.data));

  getActivePropStages().then((res) => {
    const active = res.data.filter((s: any) => s.status === 'active');
    setActiveStages(active);
    if (active.length > 0) {
      checkPassReady(active[0].id)
        .then((progressRes) => setCurrentStageProgress(progressRes.data))
        .catch(() => null);
    }
  });
}, []);

  useEffect(() => {
    if (!selectedVersionId) return;
    getVersionAnalysis(selectedVersionId)
      .then((res) => setAnalysis(res.data))
      .catch(() => setAnalysis(null));
  }, [selectedVersionId]);

  return (
    <div className="space-y-7">
      {/* کارت‌های آماری */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        <StatCard
          icon="💰"
          label="سود خالص"
          value={analysis ? `${analysis.net_pnl >= 0 ? '+' : ''}${analysis.net_pnl} $` : '—'}
          change="۱۲.۴٪"
          changeType="up"
          color="profit"
          sparkData={[30, 55, 40, 70, 60, 85, 75, 95]}
        />
        <StatCard
          icon="📈"
          label="نرخ برد"
          value={analysis ? `${analysis.win_rate}٪` : '—'}
          change="۲.۱٪"
          changeType="up"
          color="accent"
          sparkData={[50, 65, 55, 80, 70, 90, 85, 92]}
        />
        <StatCard
          icon="⚠️"
          label="حداکثر ضرر"
          value={analysis ? `-${analysis.max_dd} $` : '—'}
          change="۰.۵٪"
          changeType="down"
          color="loss"
          sparkData={[20, 35, 25, 45, 30, 50, 40, 55]}
        />
        <StatCard
          icon="🏆"
          label="فاکتور سود"
          value={analysis ? analysis.profit_factor : '—'}
          change="۸.۳٪"
          changeType="up"
          color="purple"
          sparkData={[40, 60, 50, 75, 65, 88, 80, 95]}
        />
      </div>

      {/* Hero Card */}
      <div
        className="relative rounded-[28px] p-8 flex justify-between items-center flex-wrap gap-7 overflow-hidden shadow-lg border border-[#A9C1FA]"
        style={{ background: 'linear-gradient(135deg, #FFFFFF 0%, #F0F6FF 100%)' }}
      >
        <div
          className="absolute top-0 right-0 left-0 h-1"
          style={{ background: 'linear-gradient(90deg, #3F7CFF, #7959D6, #13AE81)' }}
        />
        <div
          className="absolute -top-24 -left-24 w-[300px] h-[300px] rounded-full pointer-events-none"
          style={{ background: 'radial-gradient(circle, rgba(63,124,255,0.08), transparent 70%)' }}
        />

        <div className="relative z-10">
          <div className="text-[13px] text-[#6B7A94] font-medium mb-1.5">سرمایه کل</div>
          <div className="text-[46px] font-extrabold tracking-tighter accent-gradient-text leading-none">
            {analysis ? `${(10000 + (analysis.net_pnl || 0)).toLocaleString()} $` : '—'}
          </div>
        </div>

        <div className="flex gap-11 flex-wrap relative z-10">
          <div>
            <div className="text-[13px] text-[#6B7A94] font-medium mb-1.5">سود این ماه</div>
            <div className="text-[22px] font-extrabold text-[#13AE81]">
              {analysis ? `${analysis.net_pnl >= 0 ? '+' : ''}${analysis.net_pnl} $` : '—'}
            </div>
          </div>
          <div>
            <div className="text-[13px] text-[#6B7A94] font-medium mb-1.5">معاملات</div>
            <div className="text-[22px] font-extrabold">{analysis?.total_trades || 0}</div>
          </div>
          <div>
            <div className="text-[13px] text-[#6B7A94] font-medium mb-1.5">R کل</div>
            <div className="text-[22px] font-extrabold text-[#13AE81]">
              {analysis ? `+${analysis.net_r || 0} R` : '—'}
            </div>
          </div>
        </div>

        <div className="flex items-end gap-1 h-[70px] min-w-[300px] flex-1 relative z-10">
          {[30, 45, 35, 60, 55, 70, 65, 80, 75, 90, 85, 95, 88, 100].map((h, i) => (
            <div
              key={i}
              className="flex-1 rounded-t opacity-75 hover:opacity-100 transition-all hover:scale-y-110"
              style={{ height: `${h}%`, background: 'linear-gradient(180deg, #3F7CFF, #5B8DEF)' }}
            />
          ))}
        </div>
      </div>

      {/* جدول */}
      <Card>
        <CardHeader
          title="📋 آخرین معاملات"
          action={
            <button className="text-xs px-4 py-2 rounded-[10px] bg-[#F8FAFF] text-[#6B7A94] border border-[#E5EBF3] hover:bg-[#EDF3FF] hover:text-[#3F7CFF] hover:border-[#A9C1FA] transition-all font-semibold">
              مشاهده همه ←
            </button>
          }
        />
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-[#F5F7FB] text-[#6B7A94] text-[11px] uppercase tracking-wider">
                <th className="text-right px-4 py-3.5 font-bold rounded-r-xl">#</th>
                <th className="text-right px-4 py-3.5 font-bold">نماد</th>
                <th className="text-right px-4 py-3.5 font-bold">جهت</th>
                <th className="text-right px-4 py-3.5 font-bold">حجم</th>
                <th className="text-right px-4 py-3.5 font-bold">سود/زیان</th>
                <th className="text-right px-4 py-3.5 font-bold">R</th>
                <th className="text-right px-4 py-3.5 font-bold">وضعیت</th>
                <th className="text-right px-4 py-3.5 font-bold rounded-l-xl">تاریخ</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-[#E5EBF3] hover:bg-[#EDF3FF] transition-colors">
                <td className="px-4 py-3.5 text-[#6B7A94]">۱۲۴</td>
                <td className="px-4 py-3.5 font-bold text-[#1A2B47]">XAUUSD</td>
                <td className="px-4 py-3.5 text-[#13AE81] font-bold">خرید</td>
                <td className="px-4 py-3.5 text-[#6B7A94]">0.10</td>
                <td className="px-4 py-3.5 text-[#13AE81] font-bold">+۱۲.۵ $</td>
                <td className="px-4 py-3.5 text-[#13AE81] font-bold">1.24</td>
                <td className="px-4 py-3.5"><Badge variant="success">✅ سود</Badge></td>
                <td className="px-4 py-3.5 text-[#6B7A94]">۱۴۰۵/۰۶/۲۳</td>
              </tr>
              <tr className="border-b border-[#E5EBF3] hover:bg-[#EDF3FF] transition-colors">
                <td className="px-4 py-3.5 text-[#6B7A94]">۱۲۳</td>
                <td className="px-4 py-3.5 font-bold text-[#1A2B47]">DJIUSD</td>
                <td className="px-4 py-3.5 text-[#E45D72] font-bold">فروش</td>
                <td className="px-4 py-3.5 text-[#6B7A94]">0.07</td>
                <td className="px-4 py-3.5 text-[#E45D72] font-bold">-۴.۸ $</td>
                <td className="px-4 py-3.5 text-[#E45D72] font-bold">-0.85</td>
                <td className="px-4 py-3.5"><Badge variant="danger">❌ ضرر</Badge></td>
                <td className="px-4 py-3.5 text-[#6B7A94]">۱۴۰۵/۰۶/۲۳</td>
              </tr>
              <tr className="hover:bg-[#EDF3FF] transition-colors">
                <td className="px-4 py-3.5 text-[#6B7A94]">۱۲۲</td>
                <td className="px-4 py-3.5 font-bold text-[#1A2B47]">XAUUSD</td>
                <td className="px-4 py-3.5 text-[#13AE81] font-bold">خرید</td>
                <td className="px-4 py-3.5 text-[#6B7A94]">0.05</td>
                <td className="px-4 py-3.5 text-[#13AE81] font-bold">+۲۳.۰ $</td>
                <td className="px-4 py-3.5 text-[#13AE81] font-bold">1.96</td>
                <td className="px-4 py-3.5"><Badge variant="success">✅ سود</Badge></td>
                <td className="px-4 py-3.5 text-[#6B7A94]">۱۴۰۵/۰۶/۲۲</td>
              </tr>
            </tbody>
          </table>
        </div>
      </Card>
{/* پراپ فعال */}
{activeStages.length > 0 && currentStageProgress && (
  <div className="bg-white border border-[#E5EBF3] rounded-[22px] p-6 shadow-md">
    <div className="flex items-center justify-between gap-3 mb-5 pb-4 border-b border-[#E5EBF3]">
      <div className="flex items-center gap-3">
        <div
          className="w-11 h-11 rounded-[14px] flex items-center justify-center text-xl text-white"
          style={{ background: 'linear-gradient(135deg, #7959D6, #A78BFA)' }}
        >
          🏢
        </div>
        <div>
          <h3 className="text-base font-extrabold text-[#1A2B47]">پراپ فعال</h3>
          <p className="text-[12px] text-[#6B7A94] mt-0.5">{activeStages.length} مرحله‌ی فعال</p>
        </div>
      </div>
    </div>

    {activeStages.slice(0, 3).map((stage: any) => {
      const isCurrentStage = stage.id === currentStageProgress.stage_id;
      return (
        <div
          key={stage.id}
          className={`mb-4 p-4 rounded-[14px] border-2 ${
            isCurrentStage ? 'bg-[#EDF3FF] border-[#A9C1FA]' : 'bg-[#F8FAFF] border-[#E5EBF3]'
          }`}
        >
          <div className="flex justify-between items-center mb-3 flex-wrap gap-2">
            <div>
              <div className="text-[14px] font-extrabold text-[#1A2B47]">
                {stage.firm_name} / {stage.account_label}
              </div>
              <div className="text-[12px] text-[#6B7A94] mt-0.5 font-semibold">
                {stage.stage_label}
              </div>
            </div>
            {isCurrentStage && currentStageProgress && (
              <span
                className={`text-[11px] font-bold px-3 py-1 rounded-full ${
                  currentStageProgress.suggested_status === 'ready_to_pass'
                    ? 'bg-[#E5F8F1] text-[#13AE81]'
                    : currentStageProgress.suggested_status === 'failed_daily_dd' ||
                      currentStageProgress.suggested_status === 'failed_total_dd'
                    ? 'bg-[#FFEDF0] text-[#E45D72]'
                    : 'bg-[#EDF3FF] text-[#3F7CFF]'
                }`}
              >
                {currentStageProgress.suggested_status === 'ready_to_pass' && '✅ آماده‌ی پاس'}
                {currentStageProgress.suggested_status === 'in_progress' && '⏳ در حال پیشرفت'}
                {currentStageProgress.suggested_status === 'failed_daily_dd' && '❌ DD روزانه'}
                {currentStageProgress.suggested_status === 'failed_total_dd' && '❌ DD کلی'}
              </span>
            )}
          </div>

          {isCurrentStage && currentStageProgress && (
            <div className="space-y-3">
              <div>
                <div className="flex justify-between mb-1.5">
                  <span className="text-[11px] text-[#6B7A94] font-bold">🎯 هدف سود</span>
                  <span
                    className={`text-[11px] font-extrabold ${
                      currentStageProgress.target_reached ? 'text-[#13AE81]' : 'text-[#1A2B47]'
                    }`}
                  >
                    {currentStageProgress.current_profit} $ /{' '}
                    {currentStageProgress.profit_target} $
                  </span>
                </div>
                <div className="h-2 bg-white rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${
                      currentStageProgress.target_reached
                        ? 'bg-gradient-to-r from-[#13AE81] to-[#4DD9A9]'
                        : 'bg-gradient-to-r from-[#3F7CFF] to-[#5B8DEF]'
                    }`}
                    style={{
                      width: `${Math.min(currentStageProgress.profit_progress_percent, 100)}%`,
                    }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between mb-1.5">
                  <span className="text-[11px] text-[#6B7A94] font-bold">⚠️ DD روزانه</span>
                  <span
                    className={`text-[11px] font-extrabold ${
                      currentStageProgress.daily_dd_violated ? 'text-[#E45D72]' : 'text-[#1A2B47]'
                    }`}
                  >
                    {currentStageProgress.max_daily_loss} $ /{' '}
                    {currentStageProgress.max_daily_dd_limit} $
                  </span>
                </div>
                <div className="h-2 bg-white rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${
                      currentStageProgress.daily_dd_violated
                        ? 'bg-gradient-to-r from-[#E45D72] to-[#F0A6B2]'
                        : 'bg-gradient-to-r from-[#3F7CFF] to-[#5B8DEF]'
                    }`}
                    style={{
                      width: `${Math.min(currentStageProgress.daily_dd_progress_percent, 100)}%`,
                    }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between mb-1.5">
                  <span className="text-[11px] text-[#6B7A94] font-bold">📉 DD کلی</span>
                  <span
                    className={`text-[11px] font-extrabold ${
                      currentStageProgress.total_dd_violated ? 'text-[#E45D72]' : 'text-[#1A2B47]'
                    }`}
                  >
                    {currentStageProgress.max_total_dd} $ /{' '}
                    {currentStageProgress.max_total_dd_limit} $
                  </span>
                </div>
                <div className="h-2 bg-white rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${
                      currentStageProgress.total_dd_violated
                        ? 'bg-gradient-to-r from-[#E45D72] to-[#F0A6B2]'
                        : 'bg-gradient-to-r from-[#3F7CFF] to-[#5B8DEF]'
                    }`}
                    style={{
                      width: `${Math.min(currentStageProgress.total_dd_progress_percent, 100)}%`,
                    }}
                  />
                </div>
              </div>

              <div className="flex justify-between items-center bg-white rounded-[10px] p-2.5 border border-[#E5EBF3]">
                <span className="text-[11px] text-[#6B7A94] font-bold">📅 روزهای معاملاتی</span>
                <span
                  className={`text-[12px] font-extrabold ${
                    currentStageProgress.days_met ? 'text-[#13AE81]' : 'text-[#1A2B47]'
                  }`}
                >
                  {currentStageProgress.trading_days} / {currentStageProgress.min_trading_days}
                </span>
              </div>
            </div>
          )}
        </div>
      );
    })}
  </div>
)}
      {/* پراپ + اهداف */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <Card>
          <CardHeader title="🏢 وضعیت پراپ" />
          <div className="space-y-6">
            {propAccounts.length === 0 ? (
              <div className="text-[#9AA8BF] text-center py-4 text-sm">اکانتی وجود ندارد</div>
            ) : (
              propAccounts.slice(0, 3).map((acc: any) => (
                <div key={acc.id}>
                  <div className="flex justify-between mb-2">
                    <span className="text-sm font-bold text-[#1A2B47]">{acc.account_label}</span>
                    <Badge variant="info">{acc.firm_name}</Badge>
                  </div>
                  <ProgressBar value={65} variant="profit" />
                  <div className="flex justify-between mt-1.5">
                    <span className="text-[11px] text-[#9AA8BF]">{acc.stages_count} مرحله</span>
                    <span className="text-[11px] text-[#13AE81] font-bold">۶۵٪ پیشرفت</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </Card>

        <Card>
          <CardHeader title="🎯 پیشرفت اهداف" />
          <div className="space-y-6">
            <div>
              <div className="flex justify-between mb-2">
                <span className="text-xs text-[#6B7A94]">هدف ماهانه</span>
                <span className="text-xs font-bold text-[#13AE81]">۷۸٪</span>
              </div>
              <ProgressBar value={78} variant="profit" />
            </div>
            <div>
              <div className="flex justify-between mb-2">
                <span className="text-xs text-[#6B7A94]">هدف فصلی</span>
                <span className="text-xs font-bold text-[#3F7CFF]">۹۲٪</span>
              </div>
              <ProgressBar value={92} variant="accent" />
            </div>
            <div>
              <div className="flex justify-between mb-2">
                <span className="text-xs text-[#6B7A94]">هدف سالانه</span>
                <span className="text-xs font-bold text-[#D99B25]">۶۵٪</span>
              </div>
              <ProgressBar value={65} variant="warning" />
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}