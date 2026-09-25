interface SkeletonProps {
  className?: string;
  variant?: 'text' | 'card' | 'circle' | 'rect';
  width?: string;
  height?: string;
  count?: number;
}

export default function Skeleton({ className = '', variant = 'text', width, height, count = 1 }: SkeletonProps) {
  const baseClass = 'bg-[#1E2F4D]/20 dark:bg-[#2A3F5E]/30 rounded animate-pulse';
  const variants: Record<string, string> = {
    text: 'h-4 w-full rounded',
    card: 'h-32 w-full rounded-[22px]',
    circle: 'h-10 w-10 rounded-full',
    rect: 'h-20 w-full rounded-[12px]',
  };

  const items = Array.from({ length: count }, (_, i) => (
    <div
      key={i}
      className={`${baseClass} ${variants[variant]} ${className}`}
      style={{ width, height }}
    />
  ));

  return <>{items}</>;
}

// ── Skeleton presets for pages ──

export function DashboardSkeleton() {
  return (
    <div className="space-y-7 p-7">
      <Skeleton variant="text" className="w-48 h-6" />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        {Array.from({ length: 4 }, (_, i) => (
          <div key={i} className="bg-white dark:bg-[#152238] border border-[#E5EBF3] dark:border-[#2A3F5E] rounded-[22px] p-5">
            <Skeleton variant="text" className="w-24 h-4 mb-3" />
            <Skeleton variant="text" className="w-32 h-8 mb-2" />
            <Skeleton variant="text" className="w-16 h-3" />
          </div>
        ))}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <Skeleton variant="card" className="h-64" />
        <Skeleton variant="card" className="h-64" />
      </div>
    </div>
  );
}

export function RiskSkeleton() {
  return (
    <div className="space-y-6 p-7">
      <Skeleton variant="card" className="h-24" />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        {Array.from({ length: 4 }, (_, i) => (
          <Skeleton key={i} variant="card" className="h-28" />
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Skeleton variant="card" className="h-72" />
        <Skeleton variant="card" className="h-72" />
      </div>
      <Skeleton variant="card" className="h-48" />
    </div>
  );
}

export function CalendarSkeleton() {
  return (
    <div className="space-y-6 p-7">
      <Skeleton variant="text" className="w-48 h-6" />
      <div className="flex gap-6">
        <div className="flex-1">
          <div className="bg-[#1E2F4D]/10 dark:bg-[#2A3F5E]/20 rounded-[22px] p-6">
            <div className="grid grid-cols-7 gap-2 mb-2">
              {Array.from({ length: 7 }, (_, i) => <Skeleton key={i} variant="text" className="h-4" />)}
            </div>
            {Array.from({ length: 5 }, (_, i) => (
              <div key={i} className="grid grid-cols-7 gap-2 mb-2">
                {Array.from({ length: 7 }, (_, j) => (
                  <Skeleton key={j} variant="rect" className="h-14 rounded-lg" />
                ))}
              </div>
            ))}
          </div>
        </div>
        <Skeleton variant="card" className="w-[380px] h-72 shrink-0" />
      </div>
    </div>
  );
}