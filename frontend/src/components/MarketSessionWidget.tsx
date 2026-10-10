import { useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { api } from '../api/client';

type SessionId = 'sydney' | 'tokyo' | 'london' | 'newYork';
const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'] as const;
type TehranWeekday = typeof WEEKDAYS[number];

function getTehranWeekday(now: Date): TehranWeekday {
  return new Intl.DateTimeFormat('en-US', {
    timeZone: 'Asia/Tehran',
    weekday: 'short',
  }).format(now) as TehranWeekday;
}

function isSessionDay(weekday: TehranWeekday): boolean {
  return weekday !== 'Sat' && weekday !== 'Sun';
}

type SessionDefinition = {
  id: SessionId;
  name: string;
  flag: string;
  start: number;
  end: number;
  startLabel: string;
  endLabel: string;
};

type SessionStatus = SessionDefinition & {
  isOpen: boolean;
  remainingMs: number;
  untilOpenMs: number;
};

export type MarketSessionState = {
  sessions: SessionStatus[];
  overlapActive: boolean;
  overlapRemainingMs: number;
  nextOpening: SessionStatus;
};

interface PoursamadiInterval {
  id: number;
  symbol: string;
  name: string;
  start_hour: number;
  start_minute: number;
  end_hour: number;
  end_minute: number;
  label: string;
  priority: number;
}

export interface NewsEvent {
  id: number;
  title: string;
  currency: string;
  impact: string;
  event_time: string; // ISO
  forecast: string | null;
  previous: string | null;
  minutes_until: number;
}

const MINUTE_MS = 60_000;
const DAY_SECONDS = 24 * 60 * 60;
const REFETCH_MS = 60_000;
const NEWS_CACHE_MS = 300_000; // 5 min
const NEWS_ALERT_THRESHOLD_MIN = 15;
const NEWS_ALERT_DURATION_MS = 30_000;
const NEWS_ALERTED_KEY = 'mok_news_alerted';
const STORAGE_KEY = 'mok_widget_symbol';

const SESSION_DEFINITIONS: SessionDefinition[] = [
  { id: 'sydney', name: 'سیدنی', flag: '🇦🇺', start: 1, end: 10, startLabel: '۰۱:۰۰', endLabel: '۱۰:۰۰' },
  { id: 'tokyo', name: 'توکیو', flag: '🇯🇵', start: 3, end: 12, startLabel: '۰۳:۰۰', endLabel: '۱۲:۰۰' },
  { id: 'london', name: 'لندن', flag: '🇬🇧', start: 10, end: 19, startLabel: '۱۰:۰۰', endLabel: '۱۹:۰۰' },
  { id: 'newYork', name: 'نیویورک', flag: '🇺🇸', start: 16, end: 24, startLabel: '۱۶:۰۰', endLabel: '۲۴:۰۰' },
];

function getTehranSeconds(now: Date): number {
  const parts = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Asia/Tehran',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(now);
  const value = (type: string) => Number(parts.find((part) => part.type === type)?.value ?? 0);
  return value('hour') * 3600 + value('minute') * 60 + value('second');
}

/** Pure session calculation: the input is an instant and is always interpreted in Tehran time. */
export function getMarketSessionState(now: Date): MarketSessionState {
  const tehranSeconds = getTehranSeconds(now);
  const weekday = getTehranWeekday(now);
  const weekdayIndex = WEEKDAYS.indexOf(weekday);
  const sessions = SESSION_DEFINITIONS.map((session): SessionStatus => {
    const startSeconds = session.start * 3600;
    const endSeconds = session.end * 3600;
    const isOpen = isSessionDay(weekday) && tehranSeconds >= startSeconds && tehranSeconds < endSeconds;
    const remainingSeconds = isOpen ? endSeconds - tehranSeconds : 0;
    let daysUntilOpen = tehranSeconds < startSeconds ? 0 : 1;
    // Keep the widget's fixed Tehran schedule, skipping non-session days.
    while (!isSessionDay(WEEKDAYS[(weekdayIndex + daysUntilOpen) % WEEKDAYS.length])) {
      daysUntilOpen += 1;
    }
    const untilOpenSeconds = isOpen ? 0 : daysUntilOpen * DAY_SECONDS + startSeconds - tehranSeconds;

    return {
      ...session,
      isOpen,
      remainingMs: remainingSeconds * 1000,
      untilOpenMs: untilOpenSeconds * 1000,
    };
  });

  const overlapActive = sessions.some(session => session.id === 'london' && session.isOpen)
    && sessions.some(session => session.id === 'newYork' && session.isOpen);
  const overlapRemainingMs = overlapActive ? (19 * 3600 - tehranSeconds) * 1000 : 0;
  const nextOpening = sessions
    .filter((session) => !session.isOpen)
    .reduce((soonest, session) => session.untilOpenMs < soonest.untilOpenMs ? session : soonest);

  return { sessions, overlapActive, overlapRemainingMs, nextOpening };
}

/** Formats a non-negative duration as Persian H:MM, or MM دقیقه when under an hour. */
export function formatCountdown(milliseconds: number): string {
  const totalMinutes = Math.max(0, Math.ceil(milliseconds / MINUTE_MS));
  const persianDigits = (value: number) => String(value).replace(/\d/g, (digit) => '۰۱۲۳۴۵۶۷۸۹'[Number(digit)]);

  if (totalMinutes < 60) return `${persianDigits(totalMinutes)} دقیقه`;
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return `${persianDigits(hours)}:${persianDigits(minutes).padStart(2, '۰')}`;
}

/** Convert an integer to Persian digit string. */
function persian(n: number): string {
  return String(n).replace(/\d/g, (d) => '۰۱۲۳۴۵۶۷۸۹'[Number(d)]);
}

/** Truncate without splitting UTF-16 surrogate pairs such as emoji. */
export function truncateTitle(title: string, max = 18): string {
  const characters = Array.from(title);
  if (characters.length <= max) return title;
  return `${characters.slice(0, Math.max(0, max - 1)).join('').trimEnd()}…`;
}

/** Return the semantic urgency token at the exact minute boundaries. */
export function urgencyColor(minutesUntil: number): string {
  if (minutesUntil < 60) return 'var(--loss)';
  if (minutesUntil < 180) return 'var(--warning)';
  return 'var(--border-subtle)';
}

function tehranDateKey(value: Date): string {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Tehran', year: 'numeric', month: '2-digit', day: '2-digit',
  }).format(value);
}

function isTehranToday(event: NewsEvent, now: Date): boolean {
  return tehranDateKey(parseEventTime(event.event_time)) === tehranDateKey(now);
}

function minutesFromNow(event: NewsEvent, now: Date): number {
  return Math.ceil((parseEventTime(event.event_time).getTime() - now.getTime()) / MINUTE_MS);
}

function formatTehranTime(eventTime: string): string {
  const parts = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Asia/Tehran', hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).formatToParts(parseEventTime(eventTime));
  const value = (type: string) => parts.find((part) => part.type === type)?.value ?? '00';
  return `${persian(Number(value('hour'))).padStart(2, '۰')}:${persian(Number(value('minute'))).padStart(2, '۰')}`;
}

/** Parse API timestamps as UTC only when serialization omits the offset. */
export function parseEventTime(eventTime: string): Date {
  const timePart = eventTime.includes('T') ? eventTime.slice(eventTime.indexOf('T') + 1) : eventTime;
  const hasTimezone = /Z$/i.test(timePart) || /[+-]\d{2}:?\d{2}$/.test(timePart);
  return new Date(hasTimezone ? eventTime : `${eventTime}Z`);
}

/** Format an event's relative time against an injectable instant. */
export function formatNewsCountdown(eventTime: string, now: Date = new Date()): string {
  const differenceMinutes = Math.ceil((parseEventTime(eventTime).getTime() - now.getTime()) / MINUTE_MS);
  if (differenceMinutes <= 0) return `${persian(Math.abs(differenceMinutes))} دقیقه پیش`;
  const hours = Math.floor(differenceMinutes / 60);
  const minutes = differenceMinutes % 60;
  return `${persian(hours)}:${persian(minutes).padStart(2, '۰')} دیگر`;
}

/** Compute the currently active Poursamadi window for a symbol, given a Tehran-time instant. */
function getActivePoursamadiWindow(
  intervals: PoursamadiInterval[],
  symbol: string,
  now: Date,
): { interval: PoursamadiInterval; remainingMs: number } | null {
  const tehranSeconds = getTehranSeconds(now);
  const sym = intervals.filter((i) => i.symbol === symbol);
  for (const interval of sym) {
    const start = interval.start_hour * 3600 + interval.start_minute * 60;
    const end = interval.end_hour * 3600 + interval.end_minute * 60;
    if (tehranSeconds >= start && tehranSeconds <= end) {
      return { interval, remainingMs: (end - tehranSeconds) * 1000 };
    }
  }
  return null;
}

function getCollapsedSummary(state: MarketSessionState, activeWindow: { interval: PoursamadiInterval; remainingMs: number } | null): ReactNode {
  const lines: ReactNode[] = [];
  if (state.overlapActive) {
    lines.push(<><span className="text-xs">🔥</span> همپوشانی لندن + نیویورک · <span className="text-xs">{formatCountdown(state.overlapRemainingMs)}</span> باقی‌مانده</>);
  } else {
    const openSessions = state.sessions.filter((session) => session.isOpen);
    if (openSessions.length === 1) {
      const [session] = openSessions;
      lines.push(<><span className="text-xs">🟢</span> بازار {session.name} باز است · <span className="text-xs">{formatCountdown(session.remainingMs)}</span> باقی‌مانده</>);
    } else if (openSessions.length > 1) {
      lines.push(<><span className="text-xs">🟢</span> بازارها باز است · {openSessions.map((session) => session.name).join(' و ')}</>);
    } else {
      lines.push(<><span className="text-xs">⚪</span> همه بازارها بسته · {state.nextOpening.name} <span className="text-xs">{formatCountdown(state.nextOpening.untilOpenMs)}</span> دیگر باز می‌شود</>);
    }
  }

  if (activeWindow) {
    const { interval, remainingMs } = activeWindow;
    const labelColor = interval.label === 'A' ? 'var(--profit)' : interval.label === 'B' ? 'var(--accent)' : 'var(--text-muted)';
    lines.push(
      <><span className="text-xs">🅰</span> <span style={{ color: `var(${labelColor})` }}>{interval.symbol === 'XAUUSD' ? 'طلا' : interval.symbol === 'EURUSD' ? 'یورو' : 'داو'}</span> — پنجره‌ی {interval.label} · <span className="text-xs">{formatCountdown(remainingMs)}</span> باقی‌مانده</>
    );
  }

  if (lines.length === 0) return <><span>&nbsp;</span></>;
  if (lines.length === 1) return lines[0];
  return <>{lines.map((line, index) => (
    <div key={index} className="block" dir="auto" style={index > 0 ? { fontSize: '11px', opacity: 0.8 } : {}}>{line}</div>
  ))}</>;
}

export function NewsCollapsed({ events, now }: { events: NewsEvent[]; now: Date }) {
  const highEvents = events
    .filter((event) => event.impact === 'High' && isTehranToday(event, now))
    .sort((left, right) => parseEventTime(left.event_time).getTime() - parseEventTime(right.event_time).getTime());
  const displayed = highEvents.slice(0, 3);
  const nextEvent = highEvents.find((event) => minutesFromNow(event, now) > 0);
  const borderColor = nextEvent ? urgencyColor(minutesFromNow(nextEvent, now)) : 'transparent';
  const titleMax = displayed.length === 1 ? 40 : displayed.length === 2 ? 26 : 18;

  if (displayed.length === 0) {
    return (
      <div
        data-testid="collapsed-news"
        dir="rtl"
        className="min-w-0 flex-1 overflow-hidden text-ellipsis line-clamp-2 border-l-[3px] pl-1.5 font-medium text-sm text-[var(--text-muted)]"
        style={{ borderLeftColor: 'transparent' }}
      >
        📰 خبر مهمی امروز نیست
      </div>
    );
  }

  return (
    <div
      data-testid="collapsed-news"
      dir="rtl"
      className="min-w-0 flex-1 overflow-hidden text-ellipsis line-clamp-2 border-l-[3px] pl-1.5 font-semibold text-sm text-[var(--text-primary)]"
      style={{ borderLeftColor: borderColor }}
    >
      {displayed.length === 1 ? '📰 خبر مهم امروز: ' : '📰 خبرهای مهم امروز: '}
      {displayed.map((event, index) => (
        <span
          key={event.id}
          className={`font-semibold text-sm text-[var(--text-primary)] ${minutesFromNow(event, now) <= 0 ? 'opacity-60' : ''}`}
        >
          {index > 0 ? '، ' : null}🔴<bdi title={event.title}>{truncateTitle(event.title, titleMax)}</bdi>
        </span>
      ))}
    </div>
  );
}

export function NewsExpanded({ events, now, stale = false }: { events: NewsEvent[]; now: Date; stale?: boolean }) {
  const todayEvents = events
    .filter((event) => isTehranToday(event, now))
    .sort((left, right) => parseEventTime(left.event_time).getTime() - parseEventTime(right.event_time).getTime());

  return (
    <section>
      <div className="mb-2 flex items-center gap-2 border-t border-[var(--border-subtle)] pt-2 text-xs font-bold text-[var(--text-secondary)]">
        <span aria-hidden="true">📰</span><span>اخبار مهم USD امروز</span>
      </div>
      {stale && <div className="mb-2 text-[10px] text-[var(--warning)]">ممکن است قدیمی باشد</div>}
      <div data-testid="expanded-news-list" className="max-h-[320px] overflow-y-auto">
        {todayEvents.map((event) => {
          const minutesUntil = minutesFromNow(event, now);
          const isPast = minutesUntil <= 0;
          const forecast = event.forecast?.trim();
          const previous = event.previous?.trim();
          return (
            <div
              key={event.id}
              className={`mb-2 flex flex-col gap-1 rounded-lg border border-[var(--border-subtle)] border-l-[3px] bg-[var(--bg-elevated)] px-[10px] py-2 text-[var(--text-primary)] ${isPast ? 'opacity-60' : ''}`}
              style={{ borderLeftColor: isPast ? 'var(--border-subtle)' : urgencyColor(minutesUntil) }}
            >
              <div className="flex items-center justify-between gap-2">
                <span aria-label={event.impact} className="shrink-0 text-xs">{event.impact === 'High' ? '🔴' : '🟡'}</span>
                <bdi className="min-w-0 flex-1 text-right font-semibold">{event.title}</bdi>
                <span className="shrink-0 rounded-[4px] bg-[var(--bg-card)] px-1.5 py-0.5 text-[10px] font-semibold text-[var(--text-secondary)]">
                  {formatTehranTime(event.event_time)}
                </span>
              </div>
              {(forecast || previous) && (
                <div className="text-xs text-[var(--text-muted)]">
                  {forecast ? `پیش‌بینی: ${forecast}` : null}
                  {forecast && previous ? ' · ' : null}
                  {previous ? `قبلی: ${previous}` : null}
                </div>
              )}
              <div className="text-xs font-medium text-[var(--text-muted)]">⏱ {formatNewsCountdown(event.event_time, now)}</div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function SessionDot({ open }: { open: boolean }) {
  return <span aria-hidden="true" className={`inline-block h-2 w-2 rounded-full ${open ? 'bg-[var(--profit)]' : 'bg-[var(--text-muted)]'}`} />;
}

export default function MarketSessionWidget({ nowProvider = () => new Date() }: { nowProvider?: () => Date }) {
  const nowProviderRef = useRef(nowProvider);
  const [now, setNow] = useState(() => nowProviderRef.current());
  const [expanded, setExpanded] = useState(false);
  const [intervals, setIntervals] = useState<PoursamadiInterval[]>([]);
  const [selectedSymbol, setSelectedSymbol] = useState<string>(() => {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '"XAUUSD"'); } catch { return 'XAUUSD'; }
  });
  const [newsEvents, setNewsEvents] = useState<NewsEvent[]>([]);
  const [newsStale, setNewsStale] = useState(false);
  const [toastMessage, setToastMessage] = useState<string>('');
  const [toastTimer, setToastTimer] = useState<ReturnType<typeof setTimeout> | null>(null);
  const widgetRef = useRef<HTMLDivElement>(null);
  const state = getMarketSessionState(now);
  const activeWindow = getActivePoursamadiWindow(intervals, selectedSymbol, now);

  // Fetch intervals on mount and every REFETCH_MS
  useEffect(() => {
    const fetchIntervals = async () => {
      try {
        const res = await api.get('/api/analytics/intervals/');
        setIntervals(res.data || []);
      } catch { /* silent */ }
    };
    fetchIntervals();
    const interval = window.setInterval(fetchIntervals, REFETCH_MS);
    return () => window.clearInterval(interval);
  }, []);

  // Fetch news events on mount and every NEWS_CACHE_MS
  useEffect(() => {
    const fetchNews = async () => {
      try {
        const res = await api.get('/api/news/upcoming?scope=today&limit=20');
        const data: { events: NewsEvent[]; stale: boolean } = res.data;
        setNewsEvents(data.events || []);
        setNewsStale(Boolean(data.stale));
      } catch { /* silent */ }
    };
    fetchNews();
    const interval = window.setInterval(fetchNews, NEWS_CACHE_MS);
    return () => window.clearInterval(interval);
  }, []);

  // Alert toast for events < 15 min away; the shared minute tick updates `now`.
  useEffect(() => {
    const checkAlerts = () => {
      const nowLocal = now;
      const alertedIds: number[] = [];
      try {
        const stored = localStorage.getItem(NEWS_ALERTED_KEY);
        if (stored) alertedIds.push(...(JSON.parse(stored) as number[]));
      } catch { /* ignore */ }

      // Clear old entries (older than today)
      const todayStr = nowLocal.toDateString();
      const storedDay = localStorage.getItem(NEWS_ALERTED_KEY + '_day');
      if (storedDay !== todayStr) {
        localStorage.setItem(NEWS_ALERTED_KEY + '_day', todayStr);
        localStorage.setItem(NEWS_ALERTED_KEY, JSON.stringify([]));
        alertedIds.length = 0;
      }

      for (const ev of newsEvents) {
        const eventMinutesUntil = minutesFromNow(ev, nowLocal);
        if (eventMinutesUntil < NEWS_ALERT_THRESHOLD_MIN && eventMinutesUntil > 0 && !alertedIds.includes(ev.id)) {
          const msg = `⚠️ ${ev.title} — ${persian(NEWS_ALERT_THRESHOLD_MIN)} دقیقه دیگر`;
          setToastMessage(msg);
          if (toastTimer) clearTimeout(toastTimer);
          const timer = setTimeout(() => setToastMessage(''), NEWS_ALERT_DURATION_MS);
          setToastTimer(timer);

          alertedIds.push(ev.id);
          localStorage.setItem(NEWS_ALERTED_KEY, JSON.stringify(alertedIds));
          break; // one toast at a time
        }
      }
    };

    checkAlerts();
    return () => { if (toastTimer) clearTimeout(toastTimer); };
  }, [newsEvents, now]);

  useEffect(() => {
    const interval = window.setInterval(() => setNow(nowProviderRef.current()), MINUTE_MS);
    return () => window.clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!expanded) return undefined;

    const collapseOutside = (event: PointerEvent) => {
      if (event.target instanceof Node && !widgetRef.current?.contains(event.target)) {
        setExpanded(false);
      }
    };
    document.addEventListener('pointerdown', collapseOutside);
    return () => document.removeEventListener('pointerdown', collapseOutside);
  }, [expanded]);

  const handleSymbolChange = (sym: string) => {
    setSelectedSymbol(sym);
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(sym)); } catch { /* silent */ }
  };

  // Group intervals by symbol for expanded view
  const groupedIntervals: Record<string, PoursamadiInterval[]> = {};
  for (const iv of intervals) {
    if (!groupedIntervals[iv.symbol]) groupedIntervals[iv.symbol] = [];
    groupedIntervals[iv.symbol].push(iv);
  }
  // Sort each group by start time
  for (const sym in groupedIntervals) {
    groupedIntervals[sym].sort((a, b) => (a.start_hour * 60 + a.start_minute) - (b.start_hour * 60 + b.start_minute));
  }

  return (
    <div ref={widgetRef} className="relative flex min-w-0 flex-1 text-sm text-[var(--text-secondary)]">
      <button
        type="button"
        onClick={() => setExpanded((value) => !value)}
        aria-expanded={expanded}
        aria-label="وضعیت سشن‌های بازار فارکس و پنجره‌های پورصمدی"
        className="w-full min-w-0 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-card)] px-2.5 py-1 text-right text-sm transition-colors hover:border-[var(--border-accent)] hover:bg-[var(--accent-soft)]"
      >
        <div>{getCollapsedSummary(state, activeWindow)}</div>
        <NewsCollapsed events={newsEvents} now={now} />
      </button>

      {expanded && (
        <div className="absolute right-0 top-full z-50 mt-2 w-[min(24rem,calc(100vw-2rem))] rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-card)] p-3 text-[var(--text-primary)] shadow-[var(--shadow-md)] max-h-[80vh] overflow-y-auto">
          <div className="space-y-3">
            <section>
              <div className="mb-2 flex items-center gap-2 border-t border-[var(--border-subtle)] pt-2 text-xs font-bold text-[var(--text-secondary)]">
                <span aria-hidden="true">🌍</span><span>سشن‌ها</span>
              </div>
              <div className="space-y-2">
                {state.sessions.map((session) => (
                  <div key={session.id} className="flex items-center justify-between gap-3">
                    <span className="shrink-0 text-sm"><span className="text-xs">{session.flag}</span> {session.name}</span>
                    <span dir="ltr" className="shrink-0 tabular-nums text-sm text-[var(--text-secondary)]">{session.startLabel}–{session.endLabel}</span>
                    <span className={`flex shrink-0 items-center gap-1 text-sm ${session.isOpen ? 'text-[var(--profit)]' : 'text-[var(--text-secondary)]'}`}>
                      <SessionDot open={session.isOpen} />
                      {session.isOpen
                        ? <>باز · <span className="text-xs">{formatCountdown(session.remainingMs)}</span> باقی‌مانده</>
                        : <>بسته · <span className="text-xs">{formatCountdown(session.untilOpenMs)}</span> دیگر باز می‌شود</>}
                    </span>
                  </div>
                ))}
              </div>

              <div className={`mt-2 flex items-center justify-between gap-3 ${state.overlapActive ? 'text-[var(--warning)]' : 'text-[var(--text-secondary)]'}`}>
                <span className="shrink-0 text-sm"><span className="text-xs">🔥</span> همپوشانی لندن + نیویورک</span>
                <span dir="ltr" className="shrink-0 tabular-nums">۱۶:۰۰–۱۹:۰۰</span>
                <span className="flex shrink-0 items-center gap-1 text-sm">
                  {state.overlapActive
                    ? <>فعال · <span className="text-xs">{formatCountdown(state.overlapRemainingMs)}</span> باقی‌مانده</>
                    : 'غیرفعال'}
                </span>
              </div>
            </section>

          {/* ─── Poursamadi Time Windows ─── */}
          {Object.keys(groupedIntervals).length > 0 && (
            <section>
              <div className="mb-2 flex items-center gap-2 border-t border-[var(--border-subtle)] pt-2 text-xs font-bold text-[var(--text-secondary)]">
                <span aria-hidden="true">🕐</span><span>پنجره‌های پورصمدی</span>
              </div>
              <div className="flex items-center justify-between gap-3 mb-2">
                <select
                  onChange={(e) => handleSymbolChange(e.target.value)}
                  value={selectedSymbol}
                  className="bg-[var(--bg-input)] border border-[var(--border-subtle)] rounded-[6px] px-2 py-0.5 text-[11px] text-[var(--text-primary)] outline-none"
                >
                  {Object.keys(groupedIntervals).sort().map((sym) => (
                    <option key={sym} value={sym}>
                      {sym === 'XAUUSD' ? 'طلا' : sym === 'EURUSD' ? 'یورو' : sym === 'DJIUSD' ? 'داو' : sym}
                    </option>
                  ))}
                </select>
              </div>
              {(['XAUUSD', 'DJIUSD', 'EURUSD'] as const).map((sym) => {
                const group = groupedIntervals[sym];
                if (!group || group.length === 0) return null;
                const symLabel = { XAUUSD: 'طلا', DJIUSD: 'داو', EURUSD: 'یورو' } as Record<string, string>;
                const nowSec = getTehranSeconds(now);
                return (
                  <div key={sym} className="mb-1">
                    <div className="text-[11px] text-[var(--text-primary)] font-bold">{symLabel[sym] || sym}</div>
                    {group.map((iv) => {
                      const startSec = iv.start_hour * 3600 + iv.start_minute * 60;
                      const endSec = iv.end_hour * 3600 + iv.end_minute * 60;
                      const isActive = nowSec >= startSec && nowSec <= endSec;
                      const remainingMs = isActive ? (endSec - nowSec) * 1000 : 0;
                      const labelColor = iv.label === 'A' ? 'var(--profit)' : iv.label === 'B' ? 'var(--accent)' : 'var(--text-muted)';
                      const _h = (v: number) => String(v).replace(/\d/g, (d: string) => '۰۱۲۳۴۵۶۷۸۹'[Number(d)]);
                      const t = (h: number, m: number) => `${_h(h).padStart(2, '۰')}:${_h(m).padStart(2, '۰')}`;
                      return (
                        <div key={iv.id} className="flex items-center justify-between gap-2 text-[11px] py-0.5">
                          <span className="shrink-0">
                            <span style={{ color: `var(${labelColor})`, fontWeight: 700 }}>
                              {iv.label === 'A' ? '🅰' : iv.label === 'B' ? '🅱' : '🅲'}
                            </span>
                            {' '}{iv.name}
                          </span>
                          <span dir="ltr" className="tabular-nums text-[var(--text-secondary)]">{t(iv.start_hour, iv.start_minute)}–{t(iv.end_hour, iv.end_minute)}</span>
                          <span className={`shrink-0 ${isActive ? 'text-[var(--profit)]' : 'text-[var(--text-secondary)]'}`}>
                            {isActive ? <>● فعال · <span className="text-xs">{formatCountdown(remainingMs)}</span> باقی‌مانده</> : <>○ بسته</>}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                );
              })}
            </section>
          )}

          {/* ─── News (Forex Factory Calendar) ─── */}
          <NewsExpanded events={newsEvents} now={now} stale={newsStale} />

          </div>
        </div>
      )}
      {toastMessage && (
        <div
          role="status"
          aria-live="polite"
          dir="rtl"
          className="fixed top-4 right-4 z-[9999] flex items-center gap-3 px-4 py-3 rounded-[12px] border border-[var(--warning)]/40 shadow-lg bg-[var(--bg-card)]/95 backdrop-blur-xl"
        >
          <span className="text-sm font-bold text-[var(--warning)]">{toastMessage}</span>
          <button
            onClick={() => { setToastMessage(''); if (toastTimer) clearTimeout(toastTimer); }}
            aria-label="بستن"
            className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] text-sm transition-colors cursor-pointer"
          >
            ✕
          </button>
        </div>
      )}
    </div>
  );
}
