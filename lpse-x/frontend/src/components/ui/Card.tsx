import React from 'react';

export interface CardProps {
  children?: React.ReactNode;
  className?: string;
  hover?: boolean;
  padding?: 'sm' | 'md' | 'lg' | 'none';
  variant?: 'default' | 'elevated' | 'glass' | 'glow';
}

export function Card({ children, className = '', hover = false, padding = 'md', variant = 'default' }: CardProps) {
  let paddingClass = '';
  if (padding === 'sm') paddingClass = 'p-3';
  else if (padding === 'md') paddingClass = 'p-4';
  else if (padding === 'lg') paddingClass = 'p-6';

  const hoverClass = hover 
    ? 'motion-safe:hover:shadow-card-hover motion-safe:hover:ring-slate-600 motion-safe:transition-all motion-safe:duration-200' 
    : '';

  let variantClass = 'bg-slate-800 ring-1 ring-slate-700 shadow-card rounded-card';
  if (variant === 'elevated') variantClass = 'bg-slate-700 ring-1 ring-slate-600 shadow-card-hover rounded-card';
  if (variant === 'glass') variantClass = 'glass-card rounded-2xl';
  if (variant === 'glow') variantClass = 'bg-white/5 border border-cyan-500/30 rounded-2xl shadow-[0_0_20px_rgba(6,182,212,0.2)] motion-safe:hover:shadow-[0_0_30px_rgba(6,182,212,0.35)] motion-safe:transition-shadow duration-300';

  const animationClass = 'motion-safe:animate-[fade-in-up_0.5s_ease-out_both]';

  return (
    <div className={`${variantClass} ${paddingClass} ${hoverClass} ${animationClass} ${className}`.trim()}>
      {children}
    </div>
  );
}
