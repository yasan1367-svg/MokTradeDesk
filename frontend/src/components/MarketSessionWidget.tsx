import { useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { api } from '../api/client';

type SessionId = 'sydney' | 'tokyo' | 'london' | 'newYork';

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

const MINUTE_MS = 60_000;
const DAY_SECONDS = 24 * 60 * 60;
const REFETCH_MS = 60_000;
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
  const sessions = SESSION_DEFINITIONS.map((session): SessionStatus => {
    const startSeconds = session.start * 3600;
    const endSeconds = session.end * 3600;
    const isOpen = tehranSeconds >= startSeconds && tehranSeconds < endSeconds;
    const remainingSeconds = isOpen ? endSeconds - tehranSeconds : 0;
    const untilOpenSeconds = isOpen
      ? 0
      : (startSeconds - tehranSeconds + DAY_SECONDS) % DAY_SECONDS || DAY_SECONDS;

    return {
      ...session,
      isOpen,
      remainingMs: remainingSeconds * 1000,
      untilOpenMs: untilOpenSeconds * 1000,
    };
  });

  const overlapActive = tehranSeconds >= 16 * 3600 && tehranSeconds < 19 * 3600;
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
    if (tehranSeconds >= start && tehranSeconds < end) {
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
  return <><div className="block" dir="auto">{lines[0]}</div><div className="block" dir="auto" style={{ fontSize: '11px', opacity: 0.8 }}>{lines[1]}</div></>;
}

function SessionDot({ open }: { open: boolean }) {
  return <span aria-hidden="true" className={`inline-block h-2 w-2 rounded-full ${open ? 'bg-[var(--profit)]' : 'bg-[var(--text-muted)]'}`} />;
}

export default function MarketSessionWidget() {
  const [now, setNow] = useState(() => new Date());
  const [expanded, setExpanded] = useState(false);
  const [intervals, setIntervals] = useState<PoursamadiInterval[]>([]);
  const [selectedSymbol, setSelectedSymbol] = useState<string>(() => {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '"XAUUSD"'); } catch { return 'XAUUSD'; }
  });
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

  useEffect(() => {
    const interval = window.setInterval(() => setNow(new Date()), MINUTE_MS);
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
    <div ref={widgetRef} className="relative inline-flex max-w-full text-sm text-[var(--text-secondary)]">
      <button
        type="button"
        onClick={() => setExpanded((value) => !value)}
        aria-expanded={expanded}
        aria-label="وضعیت سشن‌های بازار فارکس و پنجره‌های پورصمدی"
        className="max-w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-card)] px-2.5 py-1 text-right text-sm transition-colors hover:border-[var(--border-accent)] hover:bg-[var(--accent-soft)]"
      >
        {getCollapsedSummary(state, activeWindow)}
      </button>

      {expanded && (
        <div className="absolute right-0 top-full z-50 mt-2 w-[min(24rem,calc(100vw-2rem))] rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-card)] p-3 text-[var(--text-primary)] shadow-[var(--shadow-md)] max-h-[80vh] overflow-y-auto">
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

          <div className={`mt-3 flex items-center justify-between gap-3 border-t border-[var(--border-subtle)] pt-3 ${state.overlapActive ? 'text-[var(--warning)]' : 'text-[var(--text-secondary)]'}`}>
            <span className="shrink-0 text-sm"><span className="text-xs">🔥</span> همپوشانی لندن + نیویورک</span>
            <span dir="ltr" className="shrink-0 tabular-nums">۱۶:۰۰–۱۹:۰۰</span>
            <span className="flex shrink-0 items-center gap-1 text-sm">
              {state.overlapActive
                ? <>فعال · <span className="text-xs">{formatCountdown(state.overlapRemainingMs)}</span> باقی‌مانده</>
                : 'غیرفعال'}
            </span>
          </div>

          {/* ─── Poursamadi Time Windows ─── */}
          {Object.keys(groupedIntervals).length > 0 && (
            <div className="mt-3 border-t border-[var(--border-subtle)] pt-3">
              <div className="flex items-center justify-between gap-3 mb-2">
                <span className="shrink-0 text-sm font-bold">🕐 پنجره‌های زمانی پورصمدی</span>
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
                      const isActive = nowSec >= startSec && nowSec < endSec;
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
            </div>
          )}
        </div>
      )}
    </div>
  );
}