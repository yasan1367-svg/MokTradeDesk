import { useMemo, useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import ErrorBoundary from './components/ErrorBoundary';
import CommandPalette from './components/CommandPalette';
import type { CommandItem } from './components/CommandPalette';
import { useToast } from './components/ToastProvider';
import AnalysisPage from './pages/AnalysisPage';
import ComparisonPage from './pages/ComparisonPage';
import StrategyPage from './pages/StrategyPage';
import TradesPage from './pages/TradesPage';
import JournalPage from './pages/JournalPage';
import PropPage from './pages/PropPage';
import RiskManagementPage from './pages/RiskManagementPage';
import ImportPage from './pages/ImportPage';
import DashboardPage from './pages/DashboardPage';
import SettingsPage from './pages/SettingsPage';

import CalendarPage from './pages/CalendarPage';
import FinancePage from './pages/FinancePage';

type Page = 'dashboard' | 'analysis' | 'comparison' | 'strategy' | 'trades' | 'journal' | 'prop' | 'calendar' | 'risk' | 'import' | 'finance' | 'settings';

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
  settings: { title: '⚙️ تنظیمات', subtitle: 'تنظیمات نرم‌افزار' },
};

function useTheme() {
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    // ۱. اولویت با localStorage
    const stored = localStorage.getItem('moktrade-theme');
    if (stored === 'dark' || stored === 'light') return stored;
    // ۲. بعد system preference
    if (window.matchMedia('(prefers-color-scheme: dark)').matches) return 'dark';
    return 'light';
  });

  useEffect(() => {
    const root = document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
    localStorage.setItem('moktrade-theme', theme);
  }, [theme]);

  // گوش دادن به تغییر system preference
  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = (e: MediaQueryListEvent) => {
      const stored = localStorage.getItem('moktrade-theme');
      if (!stored) {
        setTheme(e.matches ? 'dark' : 'light');
      }
    };
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  return { theme, toggleTheme: () => setTheme(t => t === 'dark' ? 'light' : 'dark') };
}

export default function App() {
  const [page, setPage] = useState<Page>('dashboard');
  const [paletteOpen, setPaletteOpen] = useState(false);
  const { theme, toggleTheme } = useTheme();
  const toast = useToast();

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
            <button className="w-10 h-10 rounded-xl bg-[var(--bg-card)] border border-[var(--border-subtle)] flex items-center justify-center cursor-pointer text-base text-[var(--text-secondary)] transition-all hover:bg-[var(--accent-soft)] hover:border-[var(--border-accent)] hover:text-[var(--accent)]">
              🔔
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
          {page === 'dashboard' && <ErrorBoundary label="داشبورد"><DashboardPage /></ErrorBoundary>}
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
          {page === 'settings' && <ErrorBoundary label="تنظیمات"><SettingsPage /></ErrorBoundary>}
        </div>
      </main>

      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} items={commandItems} />
    </div>
  );
}