import { describe, expect, it } from 'vitest';
import { formatCountdown, getMarketSessionState } from '../components/MarketSessionWidget';

describe('market session calculations (Tehran time)', () => {
  it('uses Tehran time for an instant independent of the browser timezone', () => {
    // 09:00 UTC is 12:30 in Tehran; no browser-local timezone assumptions.
    const state = getMarketSessionState(new Date('2026-01-15T09:00:00.000Z'));
    expect(state.sessions.find((session) => session.id === 'london')?.isOpen).toBe(true);
    expect(state.sessions.find((session) => session.id === 'tokyo')?.isOpen).toBe(false);
    expect(state.overlapActive).toBe(false);
  });

  it('activates only the London/New York overlap and counts down to 19:00 Tehran', () => {
    const state = getMarketSessionState(new Date('2026-01-15T13:15:00.000Z'));
    expect(state.overlapActive).toBe(true);
    expect(state.overlapRemainingMs).toBe(135 * 60_000);
    expect(state.sessions.filter((session) => session.isOpen).map((session) => session.id)).toEqual(['london', 'newYork']);
  });

  it('treats New York close as midnight and selects the next opening when all sessions are closed', () => {
    const justBeforeMidnight = getMarketSessionState(new Date('2026-01-15T20:29:00.000Z'));
    expect(justBeforeMidnight.sessions.find((session) => session.id === 'newYork')?.isOpen).toBe(true);

    const afterMidnight = getMarketSessionState(new Date('2026-01-15T20:30:00.000Z'));
    expect(afterMidnight.sessions.every((session) => !session.isOpen)).toBe(true);
    expect(afterMidnight.nextOpening.id).toBe('sydney');
    expect(afterMidnight.nextOpening.untilOpenMs).toBe(60 * 60_000);
  });

  it('formats countdowns in Persian digits as H:MM or minutes under one hour', () => {
    expect(formatCountdown(80 * 60_000)).toBe('۱:۲۰');
    expect(formatCountdown(20 * 60_000)).toBe('۲۰ دقیقه');
  });
});