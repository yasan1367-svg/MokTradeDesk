import { useMemo, useState, useEffect, lazy, Suspense } from 'react';
import Sidebar from './components/Sidebar';
import ErrorBoundary from './components/ErrorBoundary';
import CommandPalette from './components/CommandPalette';
import type { CommandItem } from './components/CommandPalette';
import { useToast } from './components/ToastProvider';
// فاز ۴۸c — صفحهٔ فعال در URL نگه داشته می‌شود (بدون react-router؛ History API خام)
import { writeSearch } from './utils/urlState';
import { applyFontSize, applyTheme, resolveInitialTheme } from './utils/theme';
import type { Theme } from './utils/theme';
import { getPropAlerts, getSettings } from './api/client';

// ── فاز ۱۵.۴: Code Splitting — هر صفحه یک chunk جداگانه ──
const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const AnalysisPage = lazy(() => import('./pages/AnalysisPage'));
const ComparisonPage = lazy(() => import('./pages/ComparisonPage'));
const StrategyPage = lazy(() => import('./pages/StrategyPage'));
const TradesPage = lazy(() => import('./pages/TradesPage'));
const JournalPage = lazy(() => import('./pages/JournalPage'));
const PropPage = lazy(() => import('./pages/PropPage'));
const CalendarPage = lazy(() => import('./pages/CalendarPage'));
const RiskManagementPage = lazy(() => import('./pages/RiskManagementPage'));
const ImportPage = lazy(() => import('./pages/ImportPage'));
const FinancePage = lazy(() => import('./pages/FinancePage'));
const SettingsPage = lazy(() => import('./pages/SettingsPage'));
const PayoutHistoryPage = lazy(() => import('./pages/PayoutHistoryPage'));

// preload صفحهٔ پیش‌فرض (Dashboard) — فاز ۱۵.۴
const preloadDashboard = () => { void import('./pages/DashboardPage'); };

type Page = 'dashboard' | 'analysis' | 'comparison' | 'strategy' | 'trades' | 'journal' | 'prop' | 'calendar' | 'risk' | 'import' | 'finance' | 'payouts' | 'settings';

const PAGE_TITLES: Record<Page, { title: string; subtitle: string }> = {
  dashboard: { title: '📊 داشبورد', subtitle: 'نمای کلی عملکرد معاملاتی' },
  analysis: { title: '📈 تحلیل', subtitle: 'تحلیل کامل یک نسخه' },
  comparison: { title: '⚖️ مقایسه', subtitle: 'مقایسه‌ی چند نسخه' },
  strategy: { title: '🎯 استراتژی', subtitle: 'مدیریت استراتژی‌ها و نسخه‌ها' },
  trades: { title: '📋 معاملات', subtitle: 'مدیریت معاملات و اسکرین‌شات' },
  journal: { title: '📔 ژورنال', subtitle: 'مرور و درس‌های معاملات' },
  prop: { title: '🏢 پراپ', subtitle: 'مدیریت چالش‌های پراپ' },
  calendar: { title: '📅 تقویم', subtitle: 'تقویم شمسی معاملات' },
  risk: { title: '🛡️ مدیریت ریسک', subtitle: 'تحلیل شاخص‌های ریسک و پیشنهاد Position Sizing' },
  import: { title: '📥 واردات', subtitle: 'واردات معاملات از فایل' },
  finance: { title: '💰 مالی', subtitle: 'مدیریت حساب‌ها و تراکنش‌های مالی' },
  payouts: { title: '💸 برداشت‌ها', subtitle: 'تاریخچهٔ برداشت‌های پراپ و بروکر' },
  settings: { title: '⚙️ تنظیمات', subtitle: 'تنظیمات نرم‌افزار' },
};

const PAGE_KEYS = Object.keys(PAGE_TITLES) as Page[];

/**
 * فاز ۴۸c — صفحهٔ اولیه از URL (`?page=analysis`) خوانده می‌شود تا refresh
 * کاربر را به داشبورد پرت نکند و فیلترهای ذخیره‌شدهٔ صفحه‌ها (مثل مقایسه) معنا داشته باشند.
 */
function readPageFromUrl(): Page {
  if (typeof window === 'undefined') return 'dashboard';
  const raw = new URLSearchParams(window.location.search).get('page');
  return raw && (PAGE_KEYS as string[]).includes(raw) ? (raw as Page) : 'dashboard';
}

// ── فاز ۱۵.۴: fallback آگاه از Dark Mode (با CSS Variables) ──
function PageLoading() {
  return (
    <div className="flex items-center justify-center min-h-[320px] h-full w-full">
      <div className="flex flex-col items-center gap-3 text-[var(--text-secondary)]">
        <div className="w-9 h-9 rounded-full border-2 border-[var(--border-subtle)] border-t-[var(--accent)] animate-spin" />
        <span className="text-xs">در حال بارگذاری…</span>
      </div>
    </div>
  );
}

function useTheme() {
  // فاز ۵۳.۶.۳: منبع یگانه (utils/theme) — هم‌خوان با SettingsPage
  const [theme, setTheme] = useState<Theme>(resolveInitialTheme);

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  return { theme, toggleTheme: () => setTheme(t => t === 'dark' ? 'light' : 'dark') };
}

export default function App() {
  const [page, setPage] = useState<Page>(readPageFromUrl);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const { theme, toggleTheme } = useTheme();
  const toast = useToast();

  useEffect(() => {
    getSettings()
      .then((res) => {
        const fontSize = Number(res.data?.font_size);
        if (Number.isFinite(fontSize) && fontSize > 0) applyFontSize(fontSize);
      })
      .catch(() => { /* Keep the CSS default when settings cannot be loaded. */ });
  }, []);

  // فاز ۵۳.۶.۱ — نشانگر هشدارهای خوانده‌نشدهٔ پراپ روی دکمهٔ 🔔
  const [unreadAlerts, setUnreadAlerts] = useState(0);
  useEffect(() => {
    getPropAlerts({ unread_only: true })
      .then((res) => setUnreadAlerts((res.data || []).length))
      .catch(() => { /* بی‌صدا: نبودِ هشدار مشکل UI نیست */ });
  }, [page]);

  // ── preload صفحهٔ پیش‌فرض (فاز ۱۵.۴) ──
  useEffect(() => { preloadDashboard(); }, []);

  // فاز ۴۸c — همگام‌سازی صفحهٔ فعال با URL (dashboard = پیش‌فرض ⇒ بدون پارامتر)
  useEffect(() => {
    writeSearch({ page: page === 'dashboard' ? null : page });
  }, [page]);

// ── میانبرهای کیبورد ──
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const ctrl = e.ctrlKey || e.metaKey;
      const key = e.key.toLowerCase();

      // Esc: close modals
      if (e.key === 'Escape') {
        // Dispatch a custom event so any modal can listen
        window.dispatchEvent(new CustomEvent('mok-close-modal'));
        return;
      }

      if (!ctrl) return;

      switch (key) {
        case 'd': e.preventDefault(); setPage('dashboard'); break;
        case 't': e.preventDefault(); setPage('trades'); break;
        case 'k':
        case '/':
          e.preventDefault();
          setPaletteOpen((v) => !v);
          break;
        case 'n':
          e.preventDefault();
          setPage('trades');
          window.dispatchEvent(new CustomEvent('mok-new-trade'));
          toast.info('فرم ثبت معامله جدید باز شد');
          break;
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [toast]);

  // ── آیتم‌های جستجوی سریع ──
  const commandItems = useMemo<CommandItem[]>(() => {
    const pageItems = (Object.keys(PAGE_TITLES) as Page[]).map((key) => ({
      id: `page-${key}`,
      label: PAGE_TITLES[key].title,
      icon: PAGE_TITLES[key].title.split(' ')[0],
      hint: 'صفحه',
      run: () => setPage(key),
    }));
    return [
      {
        id: 'action-new-trade',
        label: 'ثبت معامله جدید',
        icon: '🆕',
        hint: 'Ctrl+N',
        run: () => {
          setPage('trades');
          window.dispatchEvent(new CustomEvent('mok-new-trade'));
        },
      },
      ...pageItems,
    ];
  }, []);
  return (
    <div className="flex h-screen overflow-hidden bg-[var(--bg-base)]">
      <Sidebar currentPage={page} onNavigate={(p) => setPage(p as Page)} />

      <main className="flex-1 flex flex-col overflow-hidden">
        <div className="h-[68px] bg-[var(--bg-card)]/85 backdrop-blur-xl border-b border-[var(--border-subtle)] flex items-center justify-between px-7 shrink-0">
          <div>
            <div className="text-base font-bold text-[var(--text-primary)]">{PAGE_TITLES[page].title}</div>
            <div className="text-xs text-[var(--text-secondary)] mt-0.5">{PAGE_TITLES[page].subtitle}</div>
          </div>
          <div className="flex gap-3 items-center">
            <button
              onClick={() => setPaletteOpen(true)}
              className="hidden md:flex items-center gap-2 h-10 px-3 rounded-xl bg-[var(--bg-card)] border border-[var(--border-subtle)] text-[var(--text-secondary)] hover:border-[var(--border-accent)] hover:text-[var(--accent)] transition-all text-sm"
              title="جستجوی سریع (Ctrl+K)"
            >
              🔍 <span className="text-xs">جستجو</span>
              <kbd className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--bg-base)] border border-[var(--border-subtle)] font-mono">Ctrl K</kbd>
            </button>
            <button
              onClick={toggleTheme}
              className="w-10 h-10 rounded-xl bg-[var(--bg-card)] border border-[var(--border-subtle)] flex items-center justify-center cursor-pointer text-base text-[var(--text-secondary)] transition-all hover:bg-[var(--accent-soft)] hover:border-[var(--border-accent)] hover:text-[var(--accent)]"
              title={theme === 'dark' ? 'حالت روشن' : 'حالت تاریک'}
            >
              {theme === 'dark' ? '☀️' : '🌙'}
            </button>
            <button
              onClick={() => setPage('prop')}
              className="relative w-10 h-10 rounded-xl bg-[var(--bg-card)] border border-[var(--border-subtle)] flex items-center justify-center cursor-pointer text-base text-[var(--text-secondary)] transition-all hover:bg-[var(--accent-soft)] hover:border-[var(--border-accent)] hover:text-[var(--accent)]"
              title={unreadAlerts > 0 ? `${unreadAlerts} هشدار خوانده‌نشدهٔ پراپ` : 'هشدارهای پراپ'}
            >
              🔔
              {unreadAlerts > 0 && (
                <span className="absolute -top-1 -left-1 min-w-[16px] h-4 px-1 rounded-full bg-[var(--loss)] text-white text-[9px] font-bold flex items-center justify-center">
                  {unreadAlerts > 9 ? '9+' : unreadAlerts}
                </span>
              )}
            </button>
            <button
              onClick={() => setPage('settings')}
              className="w-10 h-10 rounded-xl bg-[var(--bg-card)] border border-[var(--border-subtle)] flex items-center justify-center cursor-pointer text-base text-[var(--text-secondary)] transition-all hover:bg-[var(--accent-soft)] hover:border-[var(--border-accent)] hover:text-[var(--accent)]"
            >
              ⚙️
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-7">
          <Suspense fallback={<PageLoading />}>
            {page === 'dashboard' && <ErrorBoundary label="داشبورد"><DashboardPage onNavigate={(p) => setPage(p as Page)} /></ErrorBoundary>}
            {page === 'analysis' && <ErrorBoundary label="تحلیل"><AnalysisPage /></ErrorBoundary>}
            {page === 'comparison' && <ErrorBoundary label="مقایسه"><ComparisonPage /></ErrorBoundary>}
            {page === 'strategy' && <ErrorBoundary label="استراتژی"><StrategyPage /></ErrorBoundary>}
            {page === 'trades' && <ErrorBoundary label="معاملات"><TradesPage /></ErrorBoundary>}
            {page === 'journal' && <ErrorBoundary label="ژورنال"><JournalPage /></ErrorBoundary>}
            {page === 'prop' && <ErrorBoundary label="پراپ"><PropPage /></ErrorBoundary>}
            {page === 'calendar' && <ErrorBoundary label="تقویم"><CalendarPage /></ErrorBoundary>}
            {page === 'risk' && <ErrorBoundary label="مدیریت ریسک"><RiskManagementPage /></ErrorBoundary>}
            {page === 'import' && <ErrorBoundary label="واردات"><ImportPage /></ErrorBoundary>}
            {page === 'finance' && <ErrorBoundary label="مالی"><FinancePage /></ErrorBoundary>}
            {page === 'payouts' && <ErrorBoundary label="برداشت‌ها"><PayoutHistoryPage /></ErrorBoundary>}
            {page === 'settings' && <ErrorBoundary label="تنظیمات"><SettingsPage /></ErrorBoundary>}
          </Suspense>
        </div>
      </main>

      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} items={commandItems} />
    </div>
  );
}