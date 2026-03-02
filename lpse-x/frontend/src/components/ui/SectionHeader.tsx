import React from 'react';

export interface SectionHeaderProps {
  title: string;
  description?: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
}

export function SectionHeader({ title, description, icon, action }: SectionHeaderProps) {
  return (
    <div className="flex justify-between items-start mb-6">
      <div className="flex items-center gap-3">
        {icon && (
          <div className="text-indigo-400 w-5 h-5 flex-shrink-0">
            {icon}
          </div>
        )}
        <div>
          <h2 className="text-lg font-semibold text-white">{title}</h2>
          {description && (
            <p className="text-sm text-slate-400 mt-0.5">{description}</p>
          )}
        </div>
      </div>
      {action && (
        <div>
          {action}
        </div>
      )}
    </div>
  );
}
