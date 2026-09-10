import React, { useEffect, useState } from 'react';
import { usePropStore } from '../stores/usePropStore';

export const PropDesk: React.FC = () => {
  const { accounts, analytics, fetchAccounts, fetchAnalytics, passStage, failStage, withdraw } =
    usePropStore();

  const [withdrawAmount, setWithdrawAmount] = useState<number>(0);
  const [selectedAccId, setSelectedAccId] = useState<number | null>(null);

  useEffect(() => {
    fetchAccounts();
    fetchAnalytics();
  }, [fetchAccounts, fetchAnalytics]);

  return (
    <div dir="rtl" className="min-h-screen bg-[#0A0A0F] text-white p-6 font-['Vazirmatn']">
      <h1 className="text-2xl font-bold mb-6 text-[#6C63FF]">مدیریت حساب‌های پراپ (Prop Desk)</h1>

      {/* Desk Analytics */}
      {analytics && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-[#14141E]/80 backdrop-blur-md border border-white/10 p-4 rounded-xl">
            <span className="text-xs text-gray-400">کل حساب‌ها</span>
            <p className="text-xl font-bold">{analytics.total_accounts}</p>
          </div>
          <div className="bg-[#14141E]/80 backdrop-blur-md border border-white/10 p-4 rounded-xl">
            <span className="text-xs text-gray-400">کل سرمایه Funded</span>
            <p className="text-xl font-bold text-[#00D4AA]">${analytics.total_funded_capital}</p>
          </div>
          <div className="bg-[#14141E]/80 backdrop-blur-md border border-white/10 p-4 rounded-xl">
            <span className="text-xs text-gray-400">مجموع برداشت‌ها</span>
            <p className="text-xl font-bold text-emerald-400">${analytics.total_payouts_claimed}</p>
          </div>
          <div className="bg-[#14141E]/80 backdrop-blur-md border border-white/10 p-4 rounded-xl">
            <span className="text-xs text-gray-400">نرخ قبولی (Pass Rate)</span>
            <p className="text-xl font-bold text-[#6C63FF]">{analytics.pass_rate_pct}%</p>
          </div>
        </div>
      )}

      {/* Accounts List */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {accounts.map((acc) => (
          <div
            key={acc.id}
            className="bg-[#14141E]/80 backdrop-blur-xl border border-white/10 p-6 rounded-2xl relative shadow-xl"
          >
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="font-bold text-lg">اکانت #{acc.account_number}</h3>
                <span className="text-xs text-gray-400">اندازه: ${acc.account_size}</span>
              </div>
              <span
                className={`px-3 py-1 rounded-full text-xs font-semibold ${
                  acc.status === 'Active'
                    ? 'bg-emerald-500/20 text-emerald-400'
                    : 'bg-red-500/20 text-red-400'
                }`}
              >
                {acc.current_stage_type} - {acc.status}
              </span>
            </div>

            <div className="space-y-2 text-sm text-gray-300 mb-6">
              <div className="flex justify-between">
                <span>سود جاری:</span>
                <span className="font-bold text-[#00D4AA]">${acc.current_profit}</span>
              </div>
              <div className="flex justify-between">
                <span>مجموع برداشت:</span>
                <span className="font-bold">${acc.total_withdrawn}</span>
              </div>
            </div>

            {/* Stage Actions */}
            <div className="flex gap-2">
              <button
                onClick={() => passStage(acc.id)}
                className="flex-1 bg-emerald-600 hover:bg-emerald-500 py-2 rounded-lg text-xs font-bold transition"
              >
                پاس کردن Stage
              </button>
              <button
                onClick={() => failStage(acc.id, 'تخطی از حد دراودان')}
                className="flex-1 bg-red-600 hover:bg-red-500 py-2 rounded-lg text-xs font-bold transition"
              >
                رد شدن (Fail)
              </button>
            </div>

            {acc.current_stage_type === 'Funded' && (
              <div className="mt-4 pt-4 border-t border-white/10">
                <input
                  type="number"
                  placeholder="مبلغ برداشت ($)"
                  onChange={(e) => setWithdrawAmount(Number(e.target.value))}
                  className="w-full bg-[#0A0A0F] border border-white/10 rounded-lg p-2 text-xs mb-2"
                />
                <button
                  onClick={() => withdraw(acc.id, withdrawAmount)}
                  className="w-full bg-[#6C63FF] hover:bg-indigo-600 py-2 rounded-lg text-xs font-bold transition"
                >
                  ثبت برداشت و انتقال به دفتر کل
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};