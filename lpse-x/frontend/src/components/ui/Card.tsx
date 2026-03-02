import React from 'react';

export interface CardProps {
  children?: React.ReactNode;
  className?: string;
  hover?: boolean;
  padding?: 'sm' | 'md' | 'lg' | 'none';
}

export function Card({ children, className = '', hover = false, padding = 'md' }: CardProps) {
  let paddingClass = '';
  if (padding === 'sm') paddingClass = 'p-3';
  else if (padding === 'md') paddingClass = 'p-4';
  else if (padding === 'lg') paddingClass = 'p-6';

  const hoverClass = hover 
    ? 'motion-safe:hover:shadow-card-hover motion-safe:hover:ring-slate-600 motion-safe:transition-all motion-safe:duration-200' 
    : '';

  return (
    <div className={`bg-slate-800 ring-1 ring-slate-700 shadow-card rounded-card ${paddingClass} ${hoverClass} ${className}`.trim()}>
      {children}
    </div>
  );
}
