import React, { useEffect } from 'react';
import { useStrategyStore } from '../stores/useStrategyStore';

export const StrategyLab: React.FC = () => {
  const { versions, selectedVersion, monteCarloResult, fetchVersions, selectVersion, runMonteCarlo, isLoading } =
    useStrategyStore();

  useEffect(() => {
    fetchVersions();
  }, [fetchVersions]);

  return (
    <div dir="rtl" className="min-h-screen bg-[#0A0A0F] text-white p-6 font-['Vazirmatn']">
      <h1 className="text-2xl font-bold mb-6 text-[#00D4AA]">آزمایشگاه استراتژی (Strategy Lab)</h1>

      {/* Comparison Table */}
      <div className="bg-[#14141E]/80 backdrop-blur-xl border border-white/10 rounded-2xl p-6 mb-8 overflow-x-auto shadow-2xl">
        <h2 className="text-lg font-bold mb-4">جدول مقایسه نسخه‌های استراتژی</h2>
        <table className="w-full text-right text-sm">
          <thead>
            <tr className="border-b border-white/10 text-gray-400">
              <th className="p-3">نام نسخه</th>
              <th className="p-3">Win Rate</th>
              <th className="p-3">Profit Factor</th>
              <th className="p-3">Max DD</th>
              <th className="p-3">Sharpe Ratio</th>
              <th className="p-3">سود خالص</th>
              <th className="p-3">عملیات</th>
            </tr>
          </thead>
          <tbody>
            {versions.map((v) => (
              <tr
                key={v.id}
                className={`border-b border-white/5 hover:bg-white/5 transition ${
                  selectedVersion?.id === v.id ? 'bg-[#6C63FF]/20' : ''
                }`}
              >
                <td className="p-3 font-semibold text-[#00D4AA]">{v.version_name}</td>
                <td className="p-3">{v.win_rate}%</td>
                <td className="p-3">{v.profit_factor}</td>
                <td className="p-3 text-red-400">{v.max_drawdown}%</td>
                <td className="p-3">{v.sharpe_ratio}</td>
                <td className="p-3 text-emerald-400">${v.net_profit}</td>
                <td className="p-3">
                  <button
                    onClick={() => selectVersion(v)}
                    className="bg-[#6C63FF] hover:bg-indigo-600 px-3 py-1 rounded-lg text-xs transition"
                  >
                    انتخاب
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Monte Carlo Section */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-[#14141E]/80 backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-2xl">
          <h2 className="text-lg font-bold mb-4">شبیه‌سازی مونت‌کارلو (Monte Carlo)</h2>
          <p className="text-xs text-gray-400 mb-6">
            ارزیابی ریسک و احتمال ورشکستگی با انجام ۱,۰۰۰ شبیه‌سازی تصادفی
          </p>
          <button
            onClick={() => selectedVersion && runMonteCarlo(selectedVersion.id)}
            disabled={!selectedVersion || isLoading}
            className="w-full bg-gradient-to-r from-[#00D4AA] to-[#6C63FF] font-bold py-3 rounded-xl hover:opacity-90 transition disabled:opacity-50"
          >
            {isLoading ? 'در حال شبیه‌سازی...' : 'اجرای شبیه‌سازی برای نسخه فعال'}
          </button>

          {monteCarloResult && (
            <div className="mt-6 space-y-3 text-sm border-t border-white/10 pt-4">
              <div className="flex justify-between">
                <span className="text-gray-400">احتمال کال مارجین/ورشکستگی:</span>
                <span className="font-bold text-red-400">{monteCarloResult.ruin_probability}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">دراودان در سطح اطمینان ۹۵٪:</span>
                <span className="font-bold text-orange-400">
                  {monteCarloResult.confidence_95_drawdown}%
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">میانه سرمایه نهایی:</span>
                <span className="font-bold text-emerald-400">
                  ${monteCarloResult.median_final_equity}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Heatmap / Temporal placeholder */}
        <div className="bg-[#14141E]/80 backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-2xl">
          <h2 className="text-lg font-bold mb-4">تحلیل‌های زمانی و هیت‌مپ</h2>
          <div className="flex items-center justify-center h-48 border border-dashed border-white/20 rounded-xl text-gray-500">
            هیت‌مپ سودآوری بر اساس ساعت و روزهای هفته
          </div>
        </div>
      </div>
    </div>
  );
};