import { useState } from 'react';
import { LayoutDashboard, ChartLine, Scale, Target, ClipboardList, BookOpen, Wallet, Building2, ArrowDownToLine, CalendarDays, Shield, Upload, Menu, X, Zap, ChevronDown } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

interface SidebarProps {
  currentPage: string;
  onNavigate: (page: string) => void;
}

const PRIMARY_ITEMS: { key: string; icon: LucideIcon; label: string }[] = [
  { key: 'dashboard', icon: LayoutDashboard, label: 'داشبورد' },
  { key: 'trades', icon: ClipboardList, label: 'معاملات' },
  { key: 'analysis', icon: ChartLine, label: 'تحلیل' },
  { key: 'finance', icon: Wallet, label: 'مالی' },
  { key: 'prop', icon: Building2, label: 'پراپ' },
];

const OTHER_GROUPS = [
  { label: 'تحقیق و توسعه', items: [
    { key: 'comparison', icon: Scale, label: 'مقایسه' },
    { key: 'strategy', icon: Target, label: 'استراتژی' },
    { key: 'journal', icon: BookOpen, label: 'ژورنال' },
  ] },
  { label: 'حساب‌ها', items: [
    { key: 'payouts', icon: ArrowDownToLine, label: 'برداشت‌ها' },
    { key: 'brokers', icon: Building2, label: 'بروکرها' },
  ] },
  { label: 'سیستم', items: [
    { key: 'calendar', icon: CalendarDays, label: 'تقویم' },
    { key: 'risk', icon: Shield, label: 'مدیریت ریسک' },
    { key: 'import', icon: Upload, label: 'واردات' },
  ] },
];

export default function Sidebar({ currentPage, onNavigate }: SidebarProps) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const secondaryActive = OTHER_GROUPS.some(group => group.items.some(item => item.key === currentPage));

  const handleNavigate = (key: string) => {
    onNavigate(key);
    setMobileOpen(false);
  };

  const renderItem = ({ key, icon: Icon, label }: typeof PRIMARY_ITEMS[number]) => (
    <button
      type="button"
      key={key}
      onClick={() => handleNavigate(key)}
      className={`sidebar-item ${currentPage === key ? 'is-active' : ''}`}
      aria-current={currentPage === key ? 'page' : undefined}
    >
      <Icon size={18} strokeWidth={1.7} aria-hidden="true" />
      <span>{label}</span>
    </button>
  );

  const navContent = (
    <>
      <div className="sidebar-brand">
        <div className="sidebar-brand-mark"><Zap size={21} aria-hidden="true" /></div>
        <div className="min-w-0">
          <div className="text-[1.3077rem] font-extrabold text-white tracking-tight">MokTradeDesk</div>
          <div className="text-[.7692rem] text-[var(--sidebar-text-muted)] mt-1" dir="ltr">Analyze · Improve · Grow</div>
        </div>
      </div>
      <nav aria-label="ناوبری اصلی" className="flex-1">
        {PRIMARY_ITEMS.map(renderItem)}
        <details key={secondaryActive ? 'secondary-active' : 'secondary-idle'} open={secondaryActive || undefined} className="sidebar-more">
          <summary>سایر بخش‌ها <ChevronDown size={15} aria-hidden="true" /></summary>
          {OTHER_GROUPS.map(group => (
            <div key={group.label}>
              <div className="sidebar-group-label">{group.label}</div>
              {group.items.map(renderItem)}
            </div>
          ))}
        </details>
      </nav>
      <div className="sidebar-profile">
        <div className="sidebar-avatar">ی‌م</div>
        <div><div className="font-semibold text-white">یوسف مکاری</div><div className="text-[.8462rem] text-[var(--sidebar-text-muted)]">Pro Trader</div></div>
      </div>
    </>
  );

  return (
    <>
      <button type="button" onClick={() => setMobileOpen(!mobileOpen)} className="fixed top-4 right-4 z-50 md:hidden w-10 h-10 rounded-xl bg-[var(--bg-sidebar)] border border-[var(--sidebar-active-border)] flex items-center justify-center text-white shadow-lg" aria-label={mobileOpen ? 'بستن منو' : 'منو'} aria-expanded={mobileOpen} aria-controls={mobileOpen ? 'mobile-sidebar' : undefined}>
        {mobileOpen ? <X size={20} /> : <Menu size={20} />}
      </button>
      <aside className="app-sidebar hidden md:flex w-[208px] xl:w-[238px] flex-col overflow-y-auto shrink-0">
        {navContent}
      </aside>
      {mobileOpen && (
        <div className="fixed inset-0 bg-black/50 z-40 md:hidden" onClick={() => setMobileOpen(false)}>
          <aside id="mobile-sidebar" aria-label="منوی ناوبری" className="app-sidebar flex flex-col w-[280px] max-w-[calc(100vw-32px)] h-full overflow-y-auto" onClick={event => event.stopPropagation()}>
            {navContent}
          </aside>
        </div>
      )}
    </>
  );
}
