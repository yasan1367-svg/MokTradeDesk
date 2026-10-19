import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  formatCountdown,
  formatNewsCountdown,
  getMarketSessionState,
  NewsCollapsed,
  NewsExpanded,
  parseEventTime,
  truncateTitle,
  urgencyColor,
} from '../components/MarketSessionWidget';
import MarketSessionWidget from '../components/MarketSessionWidget';
import type { NewsEvent } from '../components/MarketSessionWidget';

const { apiGet } = vi.hoisted(() => ({ apiGet: vi.fn() }));
vi.mock('../api/client', () => ({ api: { get: apiGet } }));

const NOW = new Date('2026-10-07T12:00:00Z');

beforeEach(() => {
  apiGet.mockReset();
  apiGet.mockImplementation((url: string) => Promise.resolve({
    data: url.includes('/api/news/') ? { events: [], stale: true } : [],
  }));
});

function event(
  id: number,
  title: string,
  minutes: number,
  impact = 'High',
  forecast: string | null = null,
  previous: string | null = null,
): NewsEvent {
  return {
    id, title, impact, forecast, previous, currency: 'USD', minutes_until: minutes,
    event_time: new Date(NOW.getTime() + minutes * 60_000).toISOString(),
  };
}

describe('market session calculations (Tehran time)', () => {
  it('closes all sessions on Saturday October 10 at 23:24 Tehran', () => {
    const state = getMarketSessionState(new Date('2026-10-10T23:24:00+03:30'));
    expect(state.sessions.every(session => !session.isOpen && session.remainingMs === 0)).toBe(true);
    expect(state.nextOpening.id).toBe('sydney');
    expect(state.nextOpening.untilOpenMs).toBe((25 * 60 + 36) * 60_000);
  });

  it.each(['2026-10-10T17:00:00+03:30', '2026-10-11T17:00:00+03:30'])(
    'disables sessions and overlap on a weekend at %s', instant => {
      const state = getMarketSessionState(new Date(instant));
      expect(state.sessions.every(session => !session.isOpen)).toBe(true);
      expect(state.overlapActive).toBe(false);
      expect(state.overlapRemainingMs).toBe(0);
    },
  );

  it('uses the Tehran weekday at the UTC Friday/Saturday boundary', () => {
    const friday = getMarketSessionState(new Date('2026-10-09T20:29:59Z'));
    expect(friday.sessions.find(session => session.id === 'newYork')?.isOpen).toBe(true);
    const saturday = getMarketSessionState(new Date('2026-10-09T20:30:00Z'));
    expect(saturday.sessions.every(session => !session.isOpen)).toBe(true);
    expect(saturday.nextOpening.untilOpenMs).toBe(49 * 60 * 60_000);
    expect(friday.nextOpening.untilOpenMs).toBe(49 * 60 * 60_000 + 1000);
  });

  it('counts down across Sunday midnight to the Monday Sydney opening', () => {
    const sunday = getMarketSessionState(new Date('2026-10-11T23:59:59+03:30'));
    expect(sunday.sessions.every(session => !session.isOpen)).toBe(true);
    expect(sunday.nextOpening.untilOpenMs).toBe(60 * 60_000 + 1000);
    const monday = getMarketSessionState(new Date('2026-10-12T01:00:00+03:30'));
    expect(monday.sessions.find(session => session.id === 'sydney')?.isOpen).toBe(true);
  });

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

describe('news event time handling', () => {
  it('preserves explicit offsets and Z while treating naive timestamps as UTC', () => {
    expect(parseEventTime('2026-10-07T18:00:00+00:00').toISOString()).toBe('2026-10-07T18:00:00.000Z');
    expect(parseEventTime('2026-10-07T18:00:00Z').toISOString()).toBe('2026-10-07T18:00:00.000Z');
    expect(parseEventTime('2026-10-07T18:00:00').toISOString()).toBe('2026-10-07T18:00:00.000Z');
  });

  it('formats future hours and past events against a fixed now', () => {
    expect(formatNewsCountdown('2026-10-07T17:30:00+00:00', NOW)).toBe('۵:۳۰ دیگر');
    expect(formatNewsCountdown('2026-10-07T11:40:00Z', NOW)).toBe('۲۰ دقیقه پیش');
  });
});

describe('news helpers', () => {
  it('truncates by Unicode code points and trims before the ellipsis', () => {
    expect(truncateTitle('short')).toBe('short');
    expect(truncateTitle('123456789012345678')).toBe('123456789012345678');
    expect(truncateTitle('1234567890123456789')).toBe('12345678901234567…');
    expect(truncateTitle('1234567890123456 89')).toBe('1234567890123456…');
    expect(truncateTitle('1234567890123456😀xy')).toBe('1234567890123456😀…');
  });

  it('supports the adaptive collapsed-title limits of 40, 26, and 18', () => {
    const twentyOneCharacters = '123456789012345678901';
    expect(truncateTitle(twentyOneCharacters, 40)).toBe(twentyOneCharacters);
    expect(truncateTitle('123456789012345678901234567', 26)).toBe('1234567890123456789012345…');
    expect(truncateTitle(twentyOneCharacters, 18)).toBe('12345678901234567…');
  });

  it.each([
    [59, 'var(--loss)'], [60, 'var(--warning)'],
    [179, 'var(--warning)'], [180, 'var(--border-subtle)'],
  ])('maps %i minutes to %s', (minutes, color) => {
    expect(urgencyColor(minutes)).toBe(color);
  });
});

describe('collapsed news', () => {
  it('renders three High events with the plural prefix and Persian-comma separators', () => {
    render(<NewsCollapsed events={[event(1, 'One', 30), event(2, 'Two', 60), event(3, 'Three', 90)]} now={NOW} />);
    const line = screen.getByTestId('collapsed-news');
    expect(line).toHaveTextContent('📰 خبرهای مهم امروز: 🔴One، 🔴Two، 🔴Three');
    expect(line.className).toContain('font-semibold');
    expect(line.className).toContain('text-sm');
    expect(line.className).toContain('flex-1');
    expect(line.className).toContain('min-w-0');
    expect(line.querySelectorAll('bdi')).toHaveLength(3);
  });

  it('adapts title truncation to the number of displayed items', () => {
    const title = '123456789012345678901';
    const { rerender } = render(<NewsCollapsed events={[event(1, title, 30)]} now={NOW} />);
    expect(screen.getByTitle(title)).toHaveTextContent(title);

    rerender(<NewsCollapsed events={[event(1, title, 30), event(2, 'Two', 60), event(3, 'Three', 90)]} now={NOW} />);
    expect(screen.getByTitle(title)).toHaveTextContent('12345678901234567…');
  });

  it('uses the singular prefix for one High event', () => {
    render(<NewsCollapsed events={[event(1, 'Only', 30)]} now={NOW} />);
    expect(screen.getByTestId('collapsed-news')).toHaveTextContent('📰 خبر مهم امروز: 🔴Only');
  });

  it('uses the muted medium-weight empty state when only Medium exists', () => {
    render(<NewsCollapsed events={[event(1, 'Medium', 30, 'Medium')]} now={NOW} />);
    const line = screen.getByTestId('collapsed-news');
    expect(line).toHaveTextContent('📰 خبر مهمی امروز نیست');
    expect(line.className).toContain('font-medium');
    expect(line.className).toContain('text-sm');
    expect(line.className).toContain('text-[var(--text-muted)]');
  });

  it('shows at most three of four High events', () => {
    render(<NewsCollapsed events={[event(1, 'One', 10), event(2, 'Two', 20), event(3, 'Three', 30), event(4, 'Four', 40)]} now={NOW} />);
    expect(screen.queryByText('Four')).not.toBeInTheDocument();
    expect(screen.getByTestId('collapsed-news').querySelectorAll('bdi')).toHaveLength(3);
  });

  it.each([
    [[], 'transparent'],
    [[event(1, 'Next', 30)], 'var(--loss)'],
    [[event(1, 'Next', 120)], 'var(--warning)'],
    [[event(1, 'Next', 300)], 'var(--border-subtle)'],
    [[event(1, 'Past', -20)], 'transparent'],
    [[event(1, 'Past', -20), event(2, 'Next', 120)], 'var(--warning)'],
  ] as Array<[NewsEvent[], string]>)('colors the physical left border from the next High event', (events, color) => {
    render(<NewsCollapsed events={events} now={NOW} />);
    expect(screen.getByTestId('collapsed-news').style.borderLeftColor).toBe(color);
  });

  it('excludes an event whose Tehran date is yesterday just after midnight', () => {
    const justAfterMidnight = new Date('2026-10-07T20:31:00Z');
    const yesterday = { ...event(1, 'Yesterday', 0), event_time: '2026-10-07T20:20:00Z' };
    render(<NewsCollapsed events={[yesterday]} now={justAfterMidnight} />);
    expect(screen.getByTestId('collapsed-news')).toHaveTextContent('خبر مهمی امروز نیست');
  });
});

describe('expanded news', () => {
  it('shows High and Medium, a permanent scroll container, and hides empty forecast data', () => {
    render(<NewsExpanded events={[event(1, 'High event', 30), event(2, 'Medium event', 60, 'Medium')]} now={NOW} />);
    const list = screen.getByTestId('expanded-news-list');
    expect(list.className).toContain('max-h-[320px]');
    expect(list.className).toContain('overflow-y-auto');
    expect(screen.getByLabelText('High')).toHaveTextContent('🔴');
    expect(screen.getByLabelText('Medium')).toHaveTextContent('🟡');
    expect(screen.queryByText(/پیش‌بینی:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/قبلی:/)).not.toBeInTheDocument();
  });

  it('shows present forecast parts and formats future and past countdowns', () => {
    render(<NewsExpanded events={[event(1, 'Future', 330, 'High', '1.0%', '0.5%'), event(2, 'Past', -20)]} now={NOW} />);
    expect(screen.getByText('پیش‌بینی: 1.0% · قبلی: 0.5%')).toBeInTheDocument();
    expect(screen.getByText('⏱ ۵:۳۰ دیگر')).toBeInTheDocument();
    const pastCountdown = screen.getByText('⏱ ۲۰ دقیقه پیش');
    expect(pastCountdown.parentElement?.className).toContain('opacity-60');
  });

  it('shows the stale label with an empty list', () => {
    render(<NewsExpanded events={[]} now={NOW} stale />);
    expect(screen.getByText('ممکن است قدیمی باشد')).toBeInTheDocument();
  });
});

describe('news widget integration', () => {
  it('renders all markets closed instead of New York open on Saturday night', async () => {
    render(<MarketSessionWidget nowProvider={() => new Date('2026-10-10T23:24:00+03:30')} />);
    const toggle = screen.getByRole('button', { name: /وضعیت سشن‌های بازار فارکس/ });
    expect(toggle).toHaveTextContent('همه بازارها بسته');
    expect(toggle).toHaveTextContent('۲۵:۳۶');
    expect(toggle).not.toHaveTextContent('بازار نیویورک باز است');
    await waitFor(() => expect(apiGet).toHaveBeenCalled());
  });

  it('requests today with limit 20 and keeps the stale label for an empty response', async () => {
    render(<MarketSessionWidget nowProvider={() => NOW} />);

    await waitFor(() => {
      expect(apiGet).toHaveBeenCalledWith('/api/news/upcoming?scope=today&limit=20');
    });
    expect(screen.getByTestId('collapsed-news')).toHaveTextContent('خبر مهمی امروز نیست');

    fireEvent.click(screen.getByRole('button', { name: /وضعیت سشن‌های بازار فارکس/ }));
    expect(screen.getByText('ممکن است قدیمی باشد')).toBeInTheDocument();
  });
});
