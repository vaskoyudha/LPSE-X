

export interface BadgeProps {
  level: string;
  size?: 'sm' | 'md';
  className?: string;
}

export function Badge({ level, size = 'md', className = '' }: BadgeProps) {
  let colorClass = 'bg-slate-700 text-slate-300 ring-1 ring-slate-600';
  
  if (level === 'Aman') {
    colorClass = 'bg-green-900/40 text-green-300 ring-1 ring-green-700/50';
  } else if (level === 'Perlu Pantauan') {
    colorClass = 'bg-amber-900/40 text-amber-300 ring-1 ring-amber-700/50';
  } else if (level === 'Risiko Tinggi') {
    colorClass = 'bg-red-900/40 text-red-300 ring-1 ring-red-700/50';
  } else if (level === 'Risiko Kritis') {
    colorClass = 'bg-red-950 text-red-200 ring-1 ring-red-800';
  }

  const sizeClass = size === 'sm' ? 'text-xs px-2 py-0.5' : 'text-sm px-2.5 py-1';

  return (
    <span className={`inline-flex items-center font-medium rounded-full ${colorClass} ${sizeClass} ${className}`.trim()}>
      {level}
    </span>
  );
}
