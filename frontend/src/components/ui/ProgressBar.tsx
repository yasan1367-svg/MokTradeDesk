interface ProgressBarProps {
  value: number;
  variant?: 'profit' | 'loss' | 'accent' | 'warning';
}

const VARIANTS = {
  accent: 'bg-gradient-to-r from-[#3F7CFF] to-[#5B8DEF] shadow-[0_2px_6px_rgba(63,124,255,0.4)]',
  profit: 'bg-gradient-to-r from-[#13AE81] to-[#4DD9A9] shadow-[0_2px_6px_rgba(19,174,129,0.4)]',
  warning: 'bg-gradient-to-r from-[#D99B25] to-[#F0BE5C] shadow-[0_2px_6px_rgba(217,155,37,0.4)]',
  loss: 'bg-gradient-to-r from-[#E45D72] to-[#F0A6B2] shadow-[0_2px_6px_rgba(228,93,114,0.4)]',
};

export default function ProgressBar({ value, variant = 'accent' }: ProgressBarProps) {
  return (
    <div className="h-2 bg-[#F5F7FB] rounded-full overflow-hidden shadow-[inset_0_1px_2px_rgba(0,0,0,0.04)]">
      <div
        className={`h-full rounded-full transition-all duration-500 ${VARIANTS[variant]}`}
        style={{ width: `${Math.min(value, 100)}%` }}
      />
    </div>
  );
}