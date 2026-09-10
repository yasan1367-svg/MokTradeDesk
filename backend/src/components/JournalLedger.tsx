import React, { useEffect, useState } from 'react';
import { useLedgerStore } from '../stores/useLedgerStore';

export const JournalLedger: React.FC = () => {
  const { transactions, cashFlow, fetchTransactions, fetchCashFlow, submitJournalReview, uploadScreenshot } =
    useLedgerStore();

  const [tradeId, setTradeId] = useState('');
  const [emotionalState, setEmotionalState] = useState('Calm');
  const [executionQuality, setExecutionQuality] = useState('A+ (Flawless)');
  const [notes, setNotes] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  useEffect(() => {
    fetchTransactions();
    fetchCashFlow();
  }, [fetchTransactions, fetchCashFlow]);

  const handleJournalSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await submitJournalReview({
      trade_id: tradeId,
      emotional_state: emotionalState,
      execution_quality: executionQuality,
      notes,
    });

    if (selectedFile) {
      await uploadScreenshot(tradeId, selectedFile);
    }
    alert('ژورنال با موفقیت ذخیره شد');
  };

  return (
    <div dir="rtl" className="min-h-screen bg-[#0A0A0F] text-white p-6 font-['Vazirmatn']">
      <h1 className="text-2xl font-bold mb-6 text-[#00D4AA]">دفتر کل مالی و ژورنال روان‌شناسی</h1>

      {/* Cashflow Summary */}
      {cashFlow && (
        <div className="bg-[#14141E]/80 backdrop-blur-xl border border-white/10 p-6 rounded-2xl mb-8">
          <h2 className="text-lg font-bold mb-4">خلاصه جریان نقدی (Cash Flow)</h2>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div className="bg-emerald-500/10 p-4 rounded-xl border border-emerald-500/20">
              <span className="text-xs text-gray-400">ورودی / درآمد</span>
              <p className="text-xl font-bold text-emerald-400">${cashFlow.summary.total_income}</p>
            </div>
            <div className="bg-red-500/10 p-4 rounded-xl border border-red-500/20">
              <span className="text-xs text-gray-400">خروجی / هزینه‌ها</span>
              <p className="text-xl font-bold text-red-400">${cashFlow.summary.total_expense}</p>
            </div>
            <div className="bg-purple-500/10 p-4 rounded-xl border border-purple-500/20">
              <span className="text-xs text-gray-400">خالص جریان نقدی</span>
              <p className="text-xl font-bold text-[#6C63FF]">${cashFlow.summary.net_cash_flow}</p>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Ledger Transactions Table */}
        <div className="bg-[#14141E]/80 backdrop-blur-xl border border-white/10 p-6 rounded-2xl overflow-x-auto shadow-xl">
          <h2 className="text-lg font-bold mb-4">تراکنش‌های دفتر کل</h2>
          <table className="w-full text-right text-xs">
            <thead>
              <tr className="border-b border-white/10 text-gray-400">
                <th className="p-2">دسته‌بندی</th>
                <th className="p-2">نوع</th>
                <th className="p-2">مبلغ</th>
                <th className="p-2">توضیحات</th>
              </tr>
            </thead>
            <tbody>
              {transactions.map((t) => (
                <tr key={t.id} className="border-b border-white/5">
                  <td className="p-2">{t.category}</td>
                  <td
                    className={`p-2 font-bold ${
                      t.type === 'Income' ? 'text-emerald-400' : 'text-red-400'
                    }`}
                  >
                    {t.type}
                  </td>
                  <td className="p-2 font-bold">${t.amount}</td>
                  <td className="p-2 text-gray-400">{t.description || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Psychological Journal Entry */}
        <div className="bg-[#14141E]/80 backdrop-blur-xl border border-white/10 p-6 rounded-2xl shadow-xl">
          <h2 className="text-lg font-bold mb-4">ثبت ژورنال و وضعیت روحی معامله</h2>
          <form onSubmit={handleJournalSubmit} className="space-y-4 text-xs">
            <div>
              <label className="block text-gray-400 mb-1">شناسه معامله (Trade ID):</label>
              <input
                type="text"
                required
                value={tradeId}
                onChange={(e) => setTradeId(e.target.value)}
                className="w-full bg-[#0A0A0F] border border-white/10 rounded-lg p-2.5 text-white"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-gray-400 mb-1">حالت روحی (Emotional State):</label>
                <select
                  value={emotionalState}
                  onChange={(e) => setEmotionalState(e.target.value)}
                  className="w-full bg-[#0A0A0F] border border-white/10 rounded-lg p-2.5 text-white"
                >
                  <option value="Calm">آرام (Calm)</option>
                  <option value="Confident">با اعتماد به نفس (Confident)</option>
                  <option value="Anxious">مضطرب (Anxious)</option>
                  <option value="Revenge Trading">انتقام‌جویانه (Revenge)</option>
                  <option value="FOMO">فومو (FOMO)</option>
                </select>
              </div>

              <div>
                <label className="block text-gray-400 mb-1">کیفیت اجرا (Execution):</label>
                <select
                  value={executionQuality}
                  onChange={(e) => setExecutionQuality(e.target.value)}
                  className="w-full bg-[#0A0A0F] border border-white/10 rounded-lg p-2.5 text-white"
                >
                  <option value="A+ (Flawless)">A+ (بی‌نقص)</option>
                  <option value="A (Good Execution)">A (خوب)</option>
                  <option value="B (Minor Mistakes)">B (اشتباه کوچک)</option>
                  <option value="C (Broke Rules)">C (نقض قوانین)</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-gray-400 mb-1">یادداشت‌ها و نکات معامله:</label>
              <textarea
                rows={3}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                className="w-full bg-[#0A0A0F] border border-white/10 rounded-lg p-2.5 text-white"
              />
            </div>

            <div>
              <label className="block text-gray-400 mb-1">آپلود اسکرین‌شات چارت:</label>
              <input
                type="file"
                accept="image/*"
                onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                className="w-full bg-[#0A0A0F] border border-white/10 rounded-lg p-2 text-gray-400"
              />
            </div>

            <button
              type="submit"
              className="w-full bg-gradient-to-r from-[#00D4AA] to-[#6C63FF] font-bold py-3 rounded-xl transition hover:opacity-90"
            >
              ذخیره ژورنال معامله
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};