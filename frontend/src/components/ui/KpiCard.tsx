import { useRef, useState } from 'react';
import type { MouseEvent } from 'react';

interface KpiCardProps {
  icon: string;
  label: string;
  value: string | number;
  valueColor?: 'profit' | 'loss' | 'neutral' | 'accent';
  subtitle?: string;
  hint?: string;
  index?: number;
}

export default function KpiCard({
  icon,
  label,
  value,
  valueColor = 'neutral',
  subtitle,
  hint,
  index = 0,
}: KpiCardProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [mousePos, setMousePos] = useState({ x: 50, y: 50 });
  const [isHover, setIsHover] = useState(false);

  const colorMap = {
    profit: 'var(--profit)',
    loss: 'var(--loss)',
    accent: 'var(--accent)',
    neutral: 'var(--text-primary)',
  };

  const gradientMap = {
    profit: 'linear-gradient(135deg, var(--profit) 0%, var(--accent) 100%)',
    loss: 'linear-gradient(135deg, var(--loss) 0%, var(--warning) 100%)',
    accent: 'linear-gradient(135deg, var(--accent) 0%, var(--accent-strong) 100%)',
    neutral: 'linear-gradient(135deg, var(--text-primary) 0%, var(--text-secondary) 100%)',
  };

  const glowMap = {
    profit: 'rgba(34,197,94,0.25)',
    loss: 'rgba(239,68,68,0.25)',
    accent: 'rgba(0,229,160,0.25)',
    neutral: 'rgba(63,124,255,0.15)',
  };

  const handleMouseMove = (e: MouseEvent<HTMLDivElement>) => {
    if (!ref.current) return;
    const rect = ref.current.getBoundingClientRect();
    setMousePos({
      x: ((e.clientX - rect.left) / rect.width) * 100,
      y: ((e.clientY - rect.top) / rect.height) * 100,
    });
  };

  return (
    <div
      ref={ref}
      className="kpi-card relative p-5 transition-all duration-300 hover:-translate-y-1 cursor-default"
      style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border-subtle)',
        boxShadow: isHover
          ? `0 16px 40px ${glowMap[valueColor]}, 0 4px 12px rgba(0,0,0,0.08)`
          : '0 2px 8px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.03)',
        animationDelay: `${index * 0.05}s`,
        clipPath: 'polygon(0 0, calc(100% - 16px) 0, 100% 16px, 100% 100%, 0 100%)',
      }}
      onMouseMove={handleMouseMove}
      onMouseEnter={() => setIsHover(true)}
      onMouseLeave={() => setIsHover(false)}
    >
      <div
        className="kpi-top-bar absolute top-0 left-0 right-0 h-1 transition-all duration-500"
        style={{
          background: isHover
            ? `linear-gradient(90deg, ${colorMap[valueColor]} 0%, ${colorMap[valueColor]} 40%, transparent 100%)`
            : `linear-gradient(90deg, ${colorMap[valueColor]} 0%, transparent 60%)`,
        }}
      />

      <div
        className="absolute inset-0 pointer-events-none transition-opacity duration-300"
        style={{
          background: `radial-gradient(circle at ${mousePos.x}% ${mousePos.y}%, ${glowMap[valueColor]}, transparent 50%)`,
          opacity: isHover ? 0.5 : 0,
        }}
      />

      <span
        className="absolute top-4 left-4 text-3xl transition-all duration-300"
        style={{
          opacity: isHover ? 0.35 : 0.12,
          transform: isHover ? 'scale(1.15) rotate(-5deg)' : 'scale(1)',
          filter: isHover ? `drop-shadow(0 0 8px ${glowMap[valueColor]})` : 'none',
        }}
      >
        {icon}
      </span>

      <div className="relative">
        <div
          className="text-[11px] font-bold uppercase tracking-widest mb-4"
          style={{ color: 'var(--text-secondary)' }}
        >
          {label}
        </div>

        <div
          className="text-[28px] font-black tabular-nums leading-none mb-2"
          style={{
            background: gradientMap[valueColor],
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
          }}
          title={hint}
        >
          {value}
        </div>

        {subtitle && (
          <div
            className="text-[12px] font-medium"
            style={{ color: 'var(--text-muted)' }}
          >
            {subtitle}
          </div>
        )}
      </div>
    </div>
  );
}