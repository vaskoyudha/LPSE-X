export interface SkeletonProps {
  className?: string;
  lines?: number;
  variant?: 'text' | 'card' | 'table-row';
}

export function Skeleton({ className = '', lines = 1, variant = 'text' }: SkeletonProps) {
  if (variant === 'card') {
    return (
      <div className={`h-32 w-full bg-slate-800 rounded-card ring-1 ring-slate-700 shimmer ${className}`.trim()} />
    );
  }

  if (variant === 'table-row') {
    return (
      <div className={`flex items-center gap-4 ${className}`.trim()}>
        <div className="h-4 bg-slate-700 rounded w-1/4 shimmer" />
        <div className="h-4 bg-slate-700 rounded w-1/2 shimmer" />
        <div className="h-4 bg-slate-700 rounded w-1/5 shimmer" />
        <div className="h-4 bg-slate-700 rounded w-1/6 shimmer" />
      </div>
    );
  }

  return (
    <div className={`flex flex-col gap-2 ${className}`.trim()}>
      {Array.from({ length: lines }).map((_, i) => (
        <div 
          key={i} 
          className={`h-4 bg-slate-700 rounded shimmer ${i === lines - 1 && lines > 1 ? 'w-3/4' : 'w-full'}`} 
        />
      ))}
    </div>
  );
}
