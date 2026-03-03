import React from 'react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
}

export function Button({ 
  variant = 'primary', 
  size = 'md', 
  loading = false, 
  disabled, 
  children, 
  className = '', 
  ...props 
}: ButtonProps) {
  let variantClasses = 'bg-indigo-600 hover:bg-indigo-500 text-white motion-safe:hover:scale-105 motion-safe:transition-transform duration-150 hover:shadow-[0_0_20px_rgba(6,182,212,0.35)]';
  if (variant === 'secondary') variantClasses = 'bg-slate-700 hover:bg-slate-600 text-slate-200 ring-1 ring-slate-600';
  else if (variant === 'danger') variantClasses = 'bg-red-700 hover:bg-red-600 text-white';
  else if (variant === 'ghost') variantClasses = 'text-slate-400 hover:text-white hover:bg-slate-800';

  let sizeClasses = 'text-sm px-4 py-2';
  if (size === 'sm') sizeClasses = 'text-xs px-3 py-1.5';
  else if (size === 'lg') sizeClasses = 'text-base px-5 py-2.5';

  const baseClasses = 'inline-flex items-center gap-2 font-medium rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 motion-safe:transition-all motion-safe:duration-150 motion-safe:active:scale-95';
  const isDisabled = disabled || loading;

  return (
    <button 
      className={`${baseClasses} ${variantClasses} ${sizeClasses} ${isDisabled ? 'opacity-50 cursor-not-allowed' : ''} ${className}`.trim()}
      disabled={isDisabled}
      {...props}
    >
      {loading && (
        <div className="animate-spin w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full" />
      )}
      {children}
    </button>
  );
}
