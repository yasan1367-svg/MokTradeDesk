import React from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';

const mockEquityData = [
  { date: '01 Jan', equity: 10000, propPayouts: 0 },
  { date: '05 Jan', equity: 10450, propPayouts: 0 },
  { date: '10 Jan', equity: 10300, propPayouts: 500 },
  { date: '15 Jan', equity: 11200, propPayouts: 500 },
  { date: '20 Jan', equity: 11800, propPayouts: 1500 },
  { date: '25 Jan', equity: 12400, propPayouts: 1500 },
  { date: '30 Jan', equity: 13100, propPayouts: 2800 },
];

export const Dashboard: React.FC = () => {
  return (
    <div dir="rtl" className="min-h-screen bg-[#0A0A0F] text-white p-6 font-['Vazirmatn']">
      <div className="mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-[#00D4AA] to-[#6C63FF] bg-clip-text text-transparent">
            داشبورد مدیریت MokTradeDesk
          </h1>
          <p className="text-gray-400 text-sm mt-1">نمای کلی از وضعیت سرمایه، عملکرد معاملات و پراپ دسک</p>
        </div>
      </div>

      {/* Glassmorphism Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-[#14141E]/80 backdrop-blur-xl border border-white/10 p-5 rounded-2xl shadow-xl">
          <p className="text-gray-400 text-xs font-medium">موجودی کل حساب‌ها</p>
          <h3 className="text-2xl font-bold mt-2 text-[#00D4AA]">$13,100.00</h3>
          <span className="text-xs text-emerald-400 mt-2 inline-block">+31.0% رشد این ماه</span>
        </div>

        <div className="bg-[#14141E]/80 backdrop-blur-xl border border-white/10 p-5 rounded-2xl shadow-xl">
          <p className="text-gray-400 text-xs font-medium">سرمایه فعال پراپ (Funded)</p>
          <h3 className="text-2xl font-bold mt-2 text-[#6C63FF]">$150,000.00</h3>
          <span className="text-xs text-purple-400 mt-2 inline-block">۲ اکانت فعال</span>
        </div>

        <div className="bg-[#14141E]/80 backdrop-blur-xl border border-white/10 p-5 rounded-2xl shadow-xl">
          <p className="text-gray-400 text-xs font-medium">وین‌ریت کلی (Win Rate)</p>
          <h3 className="text-2xl font-bold mt-2 text-white">64.5%</h3>
          <span className="text-xs text-gray-400 mt-2 inline-block">Profit Factor: 1.85</span>
        </div>

        <div className="bg-[#14141E]/80 backdrop-blur-xl border border-white/10 p-5 rounded-2xl shadow-xl">
          <p className="text-gray-400 text-xs font-medium">مجموع برداشت‌های پراپ</p>
          <h3 className="text-2xl font-bold mt-2 text-[#00D4AA]">$2,800.00</h3>
          <span className="text-xs text-emerald-400 mt-2 inline-block">واریز شده به دفتر کل</span>
        </div>
      </div>

      {/* Equity Curve Chart */}
      <div className="bg-[#14141E]/80 backdrop-blur-xl border border-white/10 p-6 rounded-2xl shadow-2xl">
        <h2 className="text-lg font-bold mb-4 text-gray-200">منحنی رشد اکوئیتی (Equity Curve)</h2>
        <div className="h-80 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={mockEquityData}>
              <defs>
                <linearGradient id="colorEquity" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#00D4AA" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#00D4AA" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="colorPayouts" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6C63FF" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#6C63FF" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#222" />
              <XAxis dataKey="date" stroke="#666" />
              <YAxis stroke="#666" />
              <Tooltip
                contentStyle={{ backgroundColor: '#14141E', borderColor: '#333', borderRadius: '8px' }}
              />
              <Area
                type="monotone"
                dataKey="equity"
                name="اکوئیتی ($)"
                stroke="#00D4AA"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#colorEquity)"
              />
              <Area
                type="monotone"
                dataKey="propPayouts"
                name="برداشت پراپ ($)"
                stroke="#6C63FF"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#colorPayouts)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};