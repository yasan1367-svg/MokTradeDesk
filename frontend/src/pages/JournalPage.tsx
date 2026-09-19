import { useState, useEffect } from 'react';
import {
  getJournalReviews,
  createJournalReview,
  deleteJournalReview,
  getTrades,
  uploadReviewScreenshot,
  getReviewScreenshots,
  deleteReviewScreenshot,
} from '../api/client';

const StarRating = ({ value, onChange }: { value: number; onChange?: (v: number) => void }) => {
  return (
    <div className="flex gap-1" dir="ltr">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          onClick={() => onChange && onChange(star)}
          className={`text-2xl transition-all ${onChange ? 'hover:scale-110 cursor-pointer' : 'cursor-default'} ${
            star <= value ? 'text-[#F59E0B]' : 'text-[#E5EBF3]'
          }`}
        >
          ★
        </button>
      ))}
    </div>
  );
};

export default function JournalPage() {
  const [reviews, setReviews] = useState<any[]>([]);
  const [trades, setTrades] = useState<any[]>([]);
  const [reviewScreenshots, setReviewScreenshots] = useState<Record<number, any[]>>({});
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // فرم
  const [selectedTradeId, setSelectedTradeId] = useState<number | null>(null);
  const [setupQuality, setSetupQuality] = useState(3);
  const [executionQuality, setExecutionQuality] = useState(3);
  const [rating, setRating] = useState(3);
  const [ruleViolations, setRuleViolations] = useState('');
  const [notes, setNotes] = useState('');
  const [lessons, setLessons] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [reviewsRes, tradesRes] = await Promise.all([
        getJournalReviews().catch(() => ({ data: [] })),
        getTrades({ limit: 200 }).catch(() => ({ data: { trades: [] } })),
      ]);
      const nextReviews = reviewsRes.data || [];
      setReviews(nextReviews);
      setTrades(tradesRes.data.trades || []);
      for (const review of nextReviews) {
        await loadReviewScreenshots(review.id);
      }
    } catch (err) {
      console.error('خطا:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    if (!selectedTradeId) {
      setError('لطفاً یک معامله را انتخاب کنید');
      return;
    }
    try {
      await createJournalReview({
        trade_id: selectedTradeId,
        setup_quality: setupQuality,
        execution_quality: executionQuality,
        rating: rating,
        rule_violations: ruleViolations || undefined,
        notes: notes || undefined,
        lessons: lessons || undefined,
      });
      setSuccessMessage('مرور معامله ثبت شد');
      setShowForm(false);
      setSelectedTradeId(null);
      setSetupQuality(3);
      setExecutionQuality(3);
      setRating(3);
      setRuleViolations('');
      setNotes('');
      setLessons('');
      await loadData();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'خطا در ثبت مرور');
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('حذف این مرور؟')) return;
    try {
      await deleteJournalReview(id);
      setSuccessMessage('مرور حذف شد');
      await loadData();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'خطا');
    }
  };

  const loadReviewScreenshots = async (reviewId: number) => {
    try {
      const res = await getReviewScreenshots(reviewId);
      setReviewScreenshots((prev) => ({ ...prev, [reviewId]: res.data }));
    } catch (err) {
      console.error('خطا در بارگذاری اسکرین‌شات‌های مرور:', err);
      setReviewScreenshots((prev) => ({ ...prev, [reviewId]: [] }));
    }
  };

  const handleUploadReviewScreenshot = async (reviewId: number, file: File) => {
    try {
      await uploadReviewScreenshot(reviewId, file);
      await loadReviewScreenshots(reviewId);
      setSuccessMessage('اسکرین‌شات مرور آپلود شد');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'خطا در آپلود اسکرین‌شات مرور');
    }
  };

  const handleDeleteReviewScreenshot = async (screenshotId: number, reviewId: number) => {
    if (!confirm('حذف این اسکرین‌شات؟')) return;
    try {
      await deleteReviewScreenshot(screenshotId);
      await loadReviewScreenshots(reviewId);
      setSuccessMessage('اسکرین‌شات حذف شد');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'خطا در حذف اسکرین‌شات');
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
      {successMessage && (
        <div className="bg-[#E5F8F1] border border-[#A8E6CF] text-[#13AE81] p-4 rounded-[14px] text-sm font-semibold shadow-sm">
          ✅ {successMessage}
        </div>
      )}

      {/* دکمه */}
      <div className="flex gap-3">
        <button
          onClick={() => setShowForm(!showForm)}
          className="text-white px-6 py-3 rounded-[12px] text-sm font-extrabold transition-all shadow-[0_6px_16px_rgba(63,124,255,0.3)] hover:shadow-[0_10px_24px_rgba(63,124,255,0.4)] hover:-translate-y-0.5"
          style={{ background: 'linear-gradient(135deg, #3F7CFF, #5B8DEF)' }}
        >
          ➕ مرور معامله جدید
        </button>
      </div>

      {/* فرم */}
      {showForm && (
        <div className="bg-white border-2 border-[#3F7CFF] rounded-[22px] p-6 shadow-lg">
          <div className="flex items-center gap-3 mb-6 pb-4 border-b border-[#E5EBF3]">
            <div className="w-11 h-11 rounded-[14px] flex items-center justify-center text-xl text-white"
              style={{ background: 'linear-gradient(135deg, #3F7CFF, #5B8DEF)' }}>✏️</div>
            <div>
              <h3 className="text-lg font-extrabold text-[#1A2B47]">مرور معامله جدید</h3>
              <p className="text-[12px] text-[#6B7A94] mt-0.5">کیفیت ستاپ، اجرا و درس‌های معامله</p>
            </div>
          </div>

          <div className="space-y-5">
            {/* انتخاب معامله */}
            <div>
              <label className="text-[13px] text-[#1A2B47] font-bold block mb-2">
                معامله <span className="text-[#E45D72]">*</span>
              </label>
              <select
                value={selectedTradeId || ''}
                onChange={(e) => setSelectedTradeId(Number(e.target.value))}
                className="w-full bg-[#F8FAFF] border-2 border-[#E5EBF3] rounded-[12px] px-5 py-3.5 text-[#1A2B47] text-sm font-bold focus:border-[#3F7CFF] focus:outline-none cursor-pointer"
              >
                <option value="">— انتخاب معامله —</option>
                {trades.slice(0, 100).map((t) => (
                  <option key={t.id} value={t.id}>
                    #{t.id} - {t.symbol} {t.direction === 'buy' ? 'خرید' : 'فروش'} ({t.pnl >= 0 ? '+' : ''}{t.pnl?.toFixed(2)}$)
                  </option>
                ))}
              </select>
            </div>

            {/* رتبه‌بندی */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              <div>
                <label className="text-[13px] text-[#1A2B47] font-bold block mb-2">🎯 کیفیت ستاپ</label>
                <StarRating value={setupQuality} onChange={setSetupQuality} />
              </div>
              <div>
                <label className="text-[13px] text-[#1A2B47] font-bold block mb-2">⚡ کیفیت اجرا</label>
                <StarRating value={executionQuality} onChange={setExecutionQuality} />
              </div>
              <div>
                <label className="text-[13px] text-[#1A2B47] font-bold block mb-2">⭐ امتیاز کلی</label>
                <StarRating value={rating} onChange={setRating} />
              </div>
            </div>

            {/* نقض قوانین */}
            <div>
              <label className="text-[13px] text-[#1A2B47] font-bold block mb-2">⚠️ نقض قوانین</label>
              <input
                type="text"
                value={ruleViolations}
                onChange={(e) => setRuleViolations(e.target.value)}
                placeholder="مثلاً: حد ضرر جابجا شد"
                className="w-full bg-[#F8FAFF] border-2 border-[#E5EBF3] rounded-[12px] px-5 py-3 text-[#1A2B47] text-sm font-medium focus:border-[#3F7CFF] focus:outline-none"
              />
            </div>

            {/* یادداشت */}
            <div>
              <label className="text-[13px] text-[#1A2B47] font-bold block mb-2">📝 یادداشت</label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="چه اتفاقی افتاد؟"
                rows={3}
                className="w-full bg-[#F8FAFF] border-2 border-[#E5EBF3] rounded-[12px] px-5 py-3 text-[#1A2B47] text-sm font-medium focus:border-[#3F7CFF] focus:outline-none resize-none"
              />
            </div>

            {/* درس‌ها */}
            <div>
              <label className="text-[13px] text-[#1A2B47] font-bold block mb-2">💡 درس‌ها</label>
              <textarea
                value={lessons}
                onChange={(e) => setLessons(e.target.value)}
                placeholder="برای دفعه‌ی بعد چه چیزی یاد گرفتم؟"
                rows={3}
                className="w-full bg-[#F8FAFF] border-2 border-[#E5EBF3] rounded-[12px] px-5 py-3 text-[#1A2B47] text-sm font-medium focus:border-[#3F7CFF] focus:outline-none resize-none"
              />
            </div>
          </div>

          <div className="flex gap-3 pt-5 mt-5 border-t border-[#E5EBF3]">
            <button
              onClick={handleSubmit}
              className="text-white px-7 py-3 rounded-[12px] text-sm font-extrabold"
              style={{ background: 'linear-gradient(135deg, #13AE81, #4DD9A9)' }}
            >
              💾 ذخیره
            </button>
            <button
              onClick={() => setShowForm(false)}
              className="bg-white border-2 border-[#E5EBF3] text-[#6B7A94] px-7 py-3 rounded-[12px] text-sm font-bold hover:border-[#A9C1FA]"
            >
              ✕ لغو
            </button>
          </div>
        </div>
      )}

      {/* لیست مرورها */}
      <div className="bg-white border border-[#E5EBF3] rounded-[22px] p-6 shadow-md">
        <div className="flex items-center gap-3 mb-5 pb-4 border-b border-[#E5EBF3]">
          <div className="w-11 h-11 rounded-[14px] bg-[#F1ECFF] flex items-center justify-center text-xl">📔</div>
          <div>
            <h3 className="text-base font-extrabold text-[#1A2B47]">مرورهای ثبت‌شده</h3>
            <p className="text-[12px] text-[#6B7A94] mt-0.5">{reviews.length} مرور</p>
          </div>
        </div>

        {loading ? (
          <div className="text-center py-12 text-[#9AA8BF]">⏳ در حال بارگذاری...</div>
        ) : reviews.length === 0 ? (
          <div className="text-center py-16">
            <div className="text-6xl mb-4">📔</div>
            <div className="text-[15px] font-bold text-[#1A2B47]">هنوز مروری ثبت نکرده‌اید</div>
            <div className="text-[12px] text-[#9AA8BF] mt-2">روی "➕ مرور معامله جدید" کلیک کنید</div>
          </div>
        ) : (
          <div className="space-y-3">
            {reviews.map((review) => (
              <div
                key={review.id}
                className="bg-[#F8FAFF] border-2 border-[#E5EBF3] rounded-[16px] p-5 hover:border-[#A9C1FA] hover:bg-white transition-all"
              >
                <div className="flex justify-between items-start mb-3">
                  <div className="flex items-center gap-3">
                    <div className={`w-11 h-11 rounded-[12px] flex items-center justify-center text-lg font-extrabold ${
                      (review.trade_pnl || 0) >= 0 ? 'bg-[#E5F8F1] text-[#13AE81]' : 'bg-[#FFEDF0] text-[#E45D72]'
                    }`}>
                      {(review.trade_pnl || 0) >= 0 ? '✅' : '❌'}
                    </div>
                    <div>
                      <div className="text-[15px] font-extrabold text-[#1A2B47]">
                        {review.trade_symbol}
                        <span className="text-[12px] text-[#6B7A94] font-normal mr-2">
                          #{review.trade_id}
                        </span>
                      </div>
                      <div className={`text-[12px] font-bold ${(review.trade_pnl || 0) >= 0 ? 'text-[#13AE81]' : 'text-[#E45D72]'}`}>
                        {(review.trade_pnl || 0) >= 0 ? '+' : ''}{review.trade_pnl?.toFixed(2)} $
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={() => handleDelete(review.id)}
                    className="text-[#E45D72] hover:bg-[#FFEDF0] px-3 py-1.5 rounded-[8px] text-[12px] font-bold"
                  >
                    🗑️
                  </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
                  <div>
                    <div className="text-[11px] text-[#6B7A94] font-bold mb-1">🎯 کیفیت ستاپ</div>
                    <StarRating value={review.setup_quality || 0} />
                  </div>
                  <div>
                    <div className="text-[11px] text-[#6B7A94] font-bold mb-1">⚡ کیفیت اجرا</div>
                    <StarRating value={review.execution_quality || 0} />
                  </div>
                  <div>
                    <div className="text-[11px] text-[#6B7A94] font-bold mb-1">⭐ امتیاز کلی</div>
                    <StarRating value={review.rating || 0} />
                  </div>
                </div>

                {review.rule_violations && (
                  <div className="bg-[#FFEDF0] border border-[#F0A6B2] rounded-[10px] p-3 mb-2 text-[12px] font-semibold text-[#E45D72]">
                    ⚠️ نقض: {review.rule_violations}
                  </div>
                )}

                {review.notes && (
                  <div className="bg-white border border-[#E5EBF3] rounded-[10px] p-3 mb-2 text-[12px] text-[#1A2B47]">
                    <span className="font-bold">📝 یادداشت: </span>
                    {review.notes}
                  </div>
                )}

                {review.lessons && (
                  <div className="bg-[#EDF3FF] border border-[#A9C1FA] rounded-[10px] p-3 text-[12px] text-[#1A2B47]">
                    <span className="font-bold">💡 درس: </span>
                    {review.lessons}
                  </div>
                )}

                <div className="mt-4 border-t border-[#E5EBF3] pt-4">
                  <div className="flex items-center justify-between mb-3">
                    <div className="text-[12px] text-[#6B7A94] font-bold">📷 اسکرین‌شات‌های مرور</div>
                    <label className="cursor-pointer text-[11px] font-bold text-[#3F7CFF] hover:text-[#2C63D6]">
                      + آپلود عکس
                      <input
                        type="file"
                        accept="image/*"
                        className="hidden"
                        onChange={(e) => {
                          const file = e.target.files?.[0];
                          if (file) handleUploadReviewScreenshot(review.id, file);
                          e.target.value = '';
                        }}
                      />
                    </label>
                  </div>

                  {reviewScreenshots[review.id] && reviewScreenshots[review.id].length > 0 ? (
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      {reviewScreenshots[review.id].map((screenshot) => (
                        <div key={screenshot.id} className="relative group">
                          <img
                            src={`http://localhost:8000/${screenshot.file_path}`}
                            alt="review screenshot"
                            className="w-full h-28 object-cover rounded-[10px] border border-[#E5EBF3]"
                          />
                          <button
                            type="button"
                            onClick={() => handleDeleteReviewScreenshot(screenshot.id, review.id)}
                            className="absolute top-2 left-2 bg-[#1A2B47]/75 text-white rounded-full w-7 h-7 text-xs opacity-0 group-hover:opacity-100 transition-opacity"
                            title="حذف"
                          >
                            ×
                          </button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-[12px] text-[#9AA8BF]">هنوز اسکرین‌شاتی برای این مرور آپلود نشده است.</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}