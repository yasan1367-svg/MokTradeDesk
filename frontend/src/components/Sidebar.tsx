import { useState } from 'react';

interface SidebarProps {
  currentPage: string;
  onNavigate: (page: string) => void;
}

const NAV_GROUPS = [
  {
    label: 'عملیات',
    items: [
      { key: 'dashboard', icon: '📊', label: 'داشبورد' },
      { key: 'analysis', icon: '📈', label: 'تحلیل' },
      { key: 'comparison', icon: '⚖️', label: 'مقایسه' },
    ],
  },
  {
  label: 'تحقیق و توسعه',
  items: [
    { key: 'strategy', icon: '🎯', label: 'استراتژی' },
    { key: 'trades', icon: '📋', label: 'معاملات' },
    { key: 'journal', icon: '📔', label: 'ژورنال' },
  ],
},
  {
    label: 'مالی',
    items: [
      { key: 'finance', icon: '💰', label: 'مالی' },
    ],
  },
  {
    label: 'حساب‌ها',
    items: [
      { key: 'prop', icon: '🏢', label: 'پراپ' },
      { key: 'payouts', icon: '💸', label: 'برداشت‌ها' },
    ],
  },
  {
    label: 'سیستم',
    items: [
      { key: 'calendar', icon: '📅', label: 'تقویم' },
      { key: 'risk', icon: '🛡️', label: 'مدیریت ریسک' },
      { key: 'import', icon: '📥', label: 'واردات' },
    ],
  },
];

export default function Sidebar({ currentPage, onNavigate }: SidebarProps) {
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleNavigate = (key: string) => {
    onNavigate(key);
    setMobileOpen(false);
  };

  const navContent = ({ isMobile }: { isMobile?: boolean }) => (
    <>
      {!isMobile && (
        <div className="px-5 pb-7 flex items-center gap-3">
          <div
            className="w-12 h-12 rounded-[14px] flex items-center justify-center text-2xl text-white shadow-[0_8px_20px_rgba(63,124,255,0.4)] shrink-0"
            style={{ background: 'linear-gradient(135deg, var(--accent), var(--accent-strong))' }}
          >
            ⚡
          </div>
          <div>
            <div className="text-2xl font-extrabold text-white leading-tight">MokTradeDesk</div>
            <div className="text-[12px] text-[#5A6B80] tracking-wider mt-0.5">Analyze • Improve • Grow</div>
          </div>
        </div>
      )}

      {NAV_GROUPS.map((group) => (
        <div key={group.label} className="mb-2">
          <div className="px-5 py-3 pb-1 text-[11px] text-[#5A6B80] uppercase tracking-wider font-medium">
            {group.label}
          </div>
          {group.items.map((item) => {
            const isActive = currentPage === item.key;
            return (
              <div
                key={item.key}
                onClick={() => handleNavigate(item.key)}
                className={`group flex items-center gap-3 mx-3 px-5 py-3.5 rounded-[10px] cursor-pointer text-[17px] transition-all relative ${
                  isActive
                    ? 'font-semibold'
                    : 'text-[#A8B8CC] font-normal hover:text-[#E8EDEE] hover:bg-[#1A2733]'
                }`}
                style={isActive ? {
                  color: '#FFFFFF',
                  background: 'linear-gradient(90deg, rgba(63,124,255,0.20), transparent)',
                } : undefined}
              >
                {isActive && (
                  <div className="absolute right-[-12px] top-2.5 bottom-2.5 w-[3px] bg-[#3F7CFF] rounded-r-sm" />
                )}
                <span className={`text-xl w-6 text-center ${isActive ? 'text-white' : 'text-[#7A8FA8] group-hover:text-[var(--accent)]'}`}>{item.icon}</span>
                <span>{item.label}</span>
              </div>
            );
          })}
        </div>
      ))}

      <div className="mt-auto px-5 py-4 border-t border-white/[0.08] flex items-center gap-3">
        <div
          className="w-12 h-12 rounded-full flex items-center justify-center text-sm font-bold text-[var(--accent-strong)] shadow-[0_4px_10px_rgba(0,0,0,0.15)] shrink-0"
          style={{ background: 'linear-gradient(135deg, var(--accent-light), var(--accent-light))' }}
        >
          ی‌م
        </div>
        <div>
          <div className="text-[16px] font-bold text-white">یوسف مکاری</div>
          <div className="text-[12px] text-[var(--sidebar-text-muted)]">Pro Trader</div>
        </div>
      </div>
    </>
  );

  return (
    <>
      {/* همبرگر موبایل */}
      <button
        onClick={() => setMobileOpen(!mobileOpen)}
        className="fixed top-4 right-4 z-50 lg:hidden w-10 h-10 rounded-xl bg-[var(--bg-sidebar)] border border-[var(--border-medium)] flex items-center justify-center text-white text-lg shadow-lg"
        aria-label="منو"
      >
        {mobileOpen ? '✕' : '☰'}
      </button>

      {/* سایدبرگ دسکتاپ */}
      <aside className="hidden lg:flex w-[260px] bg-[#0F1720] text-[#A8B8CC] flex-col py-5 overflow-y-auto shadow-[4px_0_24px_rgba(21,34,56,0.15)] z-10 shrink-0">
        {navContent({})}
      </aside>

      {/* اوورلی موبایل */}
      {mobileOpen && (
        <div className="fixed inset-0 bg-black/50 z-40 lg:hidden" onClick={() => setMobileOpen(false)}>
          <aside
            className="w-[280px] h-full bg-[#0F1720] text-[#A8B8CC] flex flex-col py-5 overflow-y-auto shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex justify-between items-center px-5 pb-3">
              <span className="text-[var(--sidebar-text-muted)] text-xs font-bold">📋 منوی ناوبری</span>
              <button onClick={() => setMobileOpen(false)} className="text-[var(--sidebar-text)] hover:text-white text-xl">✕</button>
            </div>
            {navContent({ isMobile: true })}
          </aside>
        </div>
      )}
    </>
  );
}