import { useState, useEffect, useCallback } from 'react';
import type { ReactElement } from 'react';
import GlassCard from '../components/GlassCard';
import { getCalendarData } from '../api/client';
import { CalendarSkeleton } from '../components/Skeleton';

interface DayTrade { id: number; symbol: string; direction: string; size: number; pnl: number; close_time: string; }
interface CalendarDayData { date: string; trade_count: number; total_pnl: number; win_rate: number; trades: DayTrade[]; }

const JALALI_MONTHS = ['فروردین','اردیبهشت','خرداد','تیر','مرداد','شهریور','مهر','آبان','آذر','دی','بهمن','اسفند'];
const WEEKDAYS = ['ش','ی','د','س','چ','پ','ج'];

function gregorianToJalali(gy: number, gm: number, gd: number): [number, number, number] {
  const g_d_m = [0,31,59,90,120,151,181,212,243,273,304,334];
  let jy = gy <= 1600 ? 0 : 979;
  gy -= gy <= 1600 ? 621 : 1600;
  const gy2 = gm > 2 ? gy + 1 : gy;
  let days = 365*gy + Math.floor((gy2+3)/4) - Math.floor((gy2+99)/100) + Math.floor((gy2+399)/400) - 80 + gd + g_d_m[gm-1];
  jy += 33 * Math.floor(days / 12053);
  days %= 12053;
  jy += 4 * Math.floor(days / 1461);
  days %= 1461;
  if (days > 365) { jy += Math.floor((days-1)/365); days = (days-1) % 365; }
  const jm = days < 186 ? 1 + Math.floor(days/31) : 7 + Math.floor((days-186)/30);
  const jd = 1 + (days < 186 ? days % 31 : (days-186) % 30);
  return [jy, jm, jd];
}

function jalaliToGregorian(jy: number, jm: number, jd: number): [number, number, number] {
  jy += 1595;
  let days = -355668 + 365*jy + Math.floor(jy/33)*8 + Math.floor(((jy%33)+3)/4) + jd;
  if (jm < 7) days += (jm-1)*31; else days += (jm-7)*30 + 186;
  let gy = 400 * Math.floor(days / 146097);
  days %= 146097;
  if (days > 36524) { gy += 100 * Math.floor(--days / 36524); days %= 36524; if (days >= 365) days++; }
  gy += 4 * Math.floor(days / 1461);
  days %= 1461;
  if (days > 365) { gy += Math.floor((days-1)/365); days = (days-1) % 365; }
  const gd = days + 1;
  const sal_a = [0,31,(gy%4===0&&gy%100!==0)||gy%400===0?29:28,31,30,31,30,31,31,30,31,30,31];
  let gm = 0, remaining = gd;
  for (let i=0; i<13; i++) { if (remaining <= sal_a[i]) { gm = i; break; } remaining -= sal_a[i]; }
  return [gy, gm, remaining];
}

function getJalaliMonthDays(jy: number, jm: number): number {
  if (jm <= 6) return 31;
  if (jm <= 11) return 30;
  return ((jy+621)%4===0&&(jy+621)%100!==0)||(jy+621)%400===0 ? 30 : 29;
}

function getStartWeekday(jy: number, jm: number): number {
  const [gy,gm,gd] = jalaliToGregorian(jy, jm, 1);
  return (new Date(gy, gm-1, gd).getDay() + 1) % 7;
}

function isoToJalali(iso: string): [number, number, number] {
  const d = new Date(iso);
  return gregorianToJalali(d.getFullYear(), d.getMonth()+1, d.getDate());
}

export default function CalendarPage() {
  const today = new Date();
  const [jy0,jm0,jd0] = gregorianToJalali(today.getFullYear(), today.getMonth()+1, today.getDate());
  const [jalaliYear, setJalaliYear] = useState(jy0);
  const [jalaliMonth, setJalaliMonth] = useState(jm0);
  const [calendarData, setCalendarData] = useState<CalendarDayData[]>([]);
  const [selectedDay, setSelectedDay] = useState<CalendarDayData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const loadData = useCallback(async () => {
    setLoading(true); setError(null);
    try { const r = await getCalendarData({ year: jalaliYear, month: jalaliMonth }); setCalendarData(r.data); }
    catch (e: any) {
      const detail = e.response?.data?.detail;
      if (typeof detail === 'string') setError(detail);
      else if (Array.isArray(detail)) setError(detail.map((d: any) => d.msg || JSON.stringify(d)).join('; '));
      else if (detail?.msg) setError(detail.msg);
      else setError(e.message || 'خطا در بارگذاری');
    }
    finally { setLoading(false); }
  }, [jalaliYear, jalaliMonth]);

  useEffect(() => { loadData(); }, [loadData]);

  const monthDays = getJalaliMonthDays(jalaliYear, jalaliMonth);
  const startWeekday = getStartWeekday(jalaliYear, jalaliMonth);
  const dataMap = new Map<string, CalendarDayData>();
  calendarData.forEach(d => dataMap.set(d.date, d));

  const nav = (dir: number) => {
    let y = jalaliYear, m = jalaliMonth + dir;
    if (m < 1) { m = 12; y--; } if (m > 12) { m = 1; y++; }
    setJalaliYear(y); setJalaliMonth(m); setSelectedDay(null);
  };
  const goToday = () => { setJalaliYear(jy0); setJalaliMonth(jm0); setSelectedDay(null); };

  const handleDayClick = (day: number) => {
    const [gy,gm,gd] = jalaliToGregorian(jalaliYear, jalaliMonth, day);
    const key = `${gy}-${String(gm).padStart(2,'0')}-${String(gd).padStart(2,'0')}`;
    const d = dataMap.get(key);
    setSelectedDay(d ? { ...d, date: key } : null);
  };

  const emptyCells = Array.from({ length: startWeekday }, (_, i) => <div key={`e${i}`} className='h-14' />);
  const dayCells = Array.from({ length: monthDays }, (_, i) => {
    const day = i + 1;
    const [gy,gm,gd] = jalaliToGregorian(jalaliYear, jalaliMonth, day);
    const key = `${gy}-${String(gm).padStart(2,'0')}-${String(gd).padStart(2,'0')}`;
    const data = dataMap.get(key);
    const isToday = day === jd0 && jalaliMonth === jm0 && jalaliYear === jy0;
    const isSel = selectedDay?.date === key;
    let cls = 'bg-[#1E2F4D]/30 text-[var(--sidebar-text)]';
    let badge: ReactElement | null = null;
    if (data) {
      cls = data.total_pnl > 0 ? 'bg-[#13AE81]/15 hover:bg-[#13AE81]/25 text-[var(--profit)]' : 'bg-[#E45D72]/15 hover:bg-[#E45D72]/25 text-[var(--loss)]';
      badge = <span className={`text-[10px] font-bold ${data.total_pnl>0?'text-[var(--profit)]':'text-[var(--loss)]'}`}>{data.total_pnl>0?'+':''}{data.total_pnl.toFixed(1)}</span>;
    }
    if (isToday) cls += ' ring-2 ring-[var(--accent)]';
    if (isSel) cls += ' ring-2 ring-[var(--accent)]';
    return (
      <div key={day} onClick={() => handleDayClick(day)} className={`h-14 rounded-lg flex flex-col items-center justify-center cursor-pointer transition-all ${cls}`}>
        <span className='text-sm font-bold'>{day}</span>{badge}
        {data && !badge && <span className='text-[10px] text-[var(--text-muted)]'>{data.trade_count} معامله</span>}
      </div>
    );
  });
return (
    <div className='space-y-6'>
      <div className='flex items-center justify-between'>
        <div className='flex items-center gap-4'>
          <h2 className='text-[var(--text-primary)] text-2xl font-extrabold'>📅 تقویم معاملات</h2>
          <span className='text-[var(--text-secondary)] text-sm'>{JALALI_MONTHS[jalaliMonth-1]} {jalaliYear}</span>
        </div>
        <div className='flex gap-2'>
          <button onClick={goToday} className='bg-[var(--accent)] hover:bg-[var(--accent-strong)] text-white px-4 py-2 rounded-xl text-sm transition-all'>امروز</button>
          <button onClick={() => nav(-1)} className='bg-[var(--bg-sidebar-hover)] hover:bg-[#1E2F4D]/80 text-[var(--sidebar-text)] px-3 py-2 rounded-xl text-sm transition-all'>◀</button>
          <button onClick={() => nav(1)} className='bg-[var(--bg-sidebar-hover)] hover:bg-[#1E2F4D]/80 text-[var(--sidebar-text)] px-3 py-2 rounded-xl text-sm transition-all'>▶</button>
        </div>
      </div>

      {loading && <CalendarSkeleton />}
      {error && <div className='flex items-center justify-center py-10'><div className='text-[var(--loss)] text-lg'>❌ {error}</div></div>}

      {!loading && !error && <div className='flex gap-6'>
        <div className='flex-1'>
          <GlassCard>
            <div className='grid grid-cols-7 gap-1 mb-2'>
              {WEEKDAYS.map(w => <div key={w} className='text-center text-[var(--sidebar-text-muted)] text-xs font-bold py-2'>{w}</div>)}
            </div>
            <div className='grid grid-cols-7 gap-1'>{emptyCells}{dayCells}</div>
          </GlassCard>
          <div className='flex gap-6 mt-3 text-xs text-[var(--text-secondary)]'>
            <div className='flex items-center gap-2'><div className='w-3 h-3 rounded bg-[#13AE81]/30' /><span>سود</span></div>
            <div className='flex items-center gap-2'><div className='w-3 h-3 rounded bg-[#E45D72]/30' /><span>زیان</span></div>
            <div className='flex items-center gap-2'><div className='w-3 h-3 rounded bg-[#1E2F4D]/30' /><span>بدون معامله</span></div>
          </div>
        </div>

        <div className='w-[380px] shrink-0'>
          <GlassCard>
            {selectedDay ? (
              <>
                <div className='flex items-center justify-between mb-4'>
                  <h3 className='text-[var(--text-primary)] font-bold text-base'>
                    {(() => { const [y,m,d] = isoToJalali(selectedDay.date); return `${d} ${JALALI_MONTHS[m-1]} ${y}`; })()}
                  </h3>
                  <span className={`text-sm font-bold ${selectedDay.total_pnl>=0?'text-[var(--profit)]':'text-[var(--loss)]'}`}>
                    {selectedDay.total_pnl>=0?'+':''}{selectedDay.total_pnl.toFixed(2)} USDT
                  </span>
                </div>
                <div className='flex gap-4 mb-4 text-xs'>
                  <div className='bg-[#1E2F4D]/30 px-3 py-2 rounded-lg text-center'>
                    <div className='text-[var(--sidebar-text)] font-bold'>{selectedDay.trade_count}</div>
                    <div className='text-[var(--text-secondary)]'>معامله</div>
                  </div>
                  <div className='bg-[#1E2F4D]/30 px-3 py-2 rounded-lg text-center'>
                    <div className='text-[var(--sidebar-text)] font-bold'>{selectedDay.win_rate.toFixed(1)}%</div>
                    <div className='text-[var(--text-secondary)]'>نرخ برد</div>
                  </div>
                </div>
                <div className='space-y-1.5 max-h-[320px] overflow-y-auto'>
                  <div className='text-[var(--sidebar-text-muted)] text-[11px] font-bold mb-2'>معاملات:</div>
                  {selectedDay.trades.map(t => (
                    <div key={t.id} className='bg-[#1E2F4D]/20 rounded-lg px-3 py-2 flex items-center justify-between text-xs'>
                      <div className='flex items-center gap-2'>
                        <span className='text-[var(--sidebar-text)] font-bold'>{t.symbol}</span>
                        <span className={t.direction==='buy'?'text-[var(--profit)]':'text-[var(--loss)]'}>{t.direction==='buy'?'▲':'▼'}</span>
                        <span className='text-[var(--text-secondary)]'>{t.size}</span>
                      </div>
                      <span className={`font-bold ${t.pnl>=0?'text-[var(--profit)]':'text-[var(--loss)]'}`}>{t.pnl>=0?'+':''}{t.pnl.toFixed(2)}</span>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className='text-center py-12 text-[var(--text-secondary)]'>
                <div className='text-3xl mb-3'>📌</div>
                <div className='text-sm'>روزی را برای مشاهده جزئیات انتخاب کنید</div>
              </div>
            )}
          </GlassCard>
        </div>
      </div>}
    </div>
  );
}
