import React, { useState } from 'react';

interface ImportModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ImportModal: React.FC<ImportModalProps> = ({ isOpen, onClose }) => {
  const [file, setFile] = useState<File | null>(null);
  const [previewData, setPreviewData] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setIsLoading(true);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('/api/import/file', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      setPreviewData(data.trades || []);
    } catch (err) {
      alert('خطا در بارگذاری فایل');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-md flex items-center justify-center p-4 z-50 font-['Vazirmatn']">
      <div dir="rtl" className="bg-[#14141E] border border-white/10 rounded-2xl w-full max-w-2xl p-6 text-white shadow-2xl">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold text-[#00D4AA]">آپلود و واردسازی تاریخچه معاملات</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white">✕</button>
        </div>

        <div className="border-2 border-dashed border-white/20 rounded-xl p-8 text-center mb-6 bg-[#0A0A0F]/50">
          <input
            type="file"
            accept=".csv, .html, .xlsx"
            onChange={handleFileChange}
            className="hidden"
            id="file-upload"
          />
          <label htmlFor="file-upload" className="cursor-pointer">
            <p className="text-sm text-gray-300">
              {file ? file.name : 'فایل گزارش MT4/MT5، Soft4X یا CSV را انتخاب یا اینجا رها کنید'}
            </p>
            <span className="inline-block mt-3 bg-white/10 hover:bg-white/20 px-4 py-2 rounded-lg text-xs font-bold transition">
              انتخاب فایل
            </span>
          </label>
        </div>

        {file && (
          <button
            onClick={handleUpload}
            disabled={isLoading}
            className="w-full bg-[#6C63FF] hover:bg-indigo-600 font-bold py-2.5 rounded-xl text-sm mb-6 transition"
          >
            {isLoading ? 'در حال پردازش...' : 'پردازش و نمایش پیش‌نمایش'}
          </button>
        )}

        {/* Data Preview Table */}
        {previewData.length > 0 && (
          <div>
            <h3 className="text-sm font-bold mb-3 text-gray-300">پیش‌نمایش داده‌های استخراج‌شده ({previewData.length} معامله)</h3>
            <div className="max-h-60 overflow-y-auto border border-white/10 rounded-xl">
              <table className="w-full text-right text-xs">
                <thead className="bg-[#0A0A0F] sticky top-0">
                  <tr className="text-gray-400">
                    <th className="p-2">Ticket</th>
                    <th className="p-2">Symbol</th>
                    <th className="p-2">Type</th>
                    <th className="p-2">Lots</th>
                    <th className="p-2">Profit</th>
                  </tr>
                </thead>
                <tbody>
                  {previewData.map((t, idx) => (
                    <tr key={idx} className="border-b border-white/5">
                      <td className="p-2">{t.ticket}</td>
                      <td className="p-2">{t.symbol}</td>
                      <td className="p-2">{t.order_type}</td>
                      <td className="p-2">{t.lots}</td>
                      <td className={`p-2 font-bold ${t.profit >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        ${t.profit}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};