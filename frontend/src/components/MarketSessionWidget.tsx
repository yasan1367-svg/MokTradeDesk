import { useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';

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

const MINUTE_MS = 60_000;
const DAY_SECONDS = 24 * 60 * 60;
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

function getCollapsedSummary(state: MarketSessionState): ReactNode {
  if (state.overlapActive) {
    return <><span className="text-xs">🔥</span> همپوشانی لندن + نیویورک · <span className="text-xs">{formatCountdown(state.overlapRemainingMs)}</span> باقی‌مانده</>;
  }

  const openSessions = state.sessions.filter((session) => session.isOpen);
  if (openSessions.length === 1) {
    const [session] = openSessions;
    return <><span className="text-xs">🟢</span> بازار {session.name} باز است · <span className="text-xs">{formatCountdown(session.remainingMs)}</span> باقی‌مانده</>;
  }
  if (openSessions.length > 1) {
    return <><span className="text-xs">🟢</span> بازارها باز است · {openSessions.map((session) => session.name).join(' و ')}</>;
  }
  return <><span className="text-xs">⚪</span> همه بازارها بسته · {state.nextOpening.name} <span className="text-xs">{formatCountdown(state.nextOpening.untilOpenMs)}</span> دیگر باز می‌شود</>;
}

function SessionDot({ open }: { open: boolean }) {
  return <span aria-hidden="true" className={`inline-block h-2 w-2 rounded-full ${open ? 'bg-[var(--profit)]' : 'bg-[var(--text-muted)]'}`} />;
}

export default function MarketSessionWidget() {
  const [now, setNow] = useState(() => new Date());
  const [expanded, setExpanded] = useState(false);
  const widgetRef = useRef<HTMLDivElement>(null);
  const state = getMarketSessionState(now);

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

  return (
    <div ref={widgetRef} className="relative inline-flex max-w-full text-sm text-[var(--text-secondary)]">
      <button
        type="button"
        onClick={() => setExpanded((value) => !value)}
        aria-expanded={expanded}
        aria-label="وضعیت سشن‌های بازار فارکس"
        className="max-w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-card)] px-2.5 py-1 text-right text-sm transition-colors hover:border-[var(--border-accent)] hover:bg-[var(--accent-soft)]"
      >
        {getCollapsedSummary(state)}
      </button>

      {expanded && (
        <div className="absolute right-0 top-full z-50 mt-2 w-[min(22rem,calc(100vw-2rem))] rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-card)] p-3 text-[var(--text-primary)] shadow-[var(--shadow-md)]">
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
        </div>
      )}
    </div>
  );
}