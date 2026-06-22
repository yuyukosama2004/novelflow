import type { ButtonHTMLAttributes, ReactNode } from 'react';

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  icon: ReactNode;
  label: string;
  tone?: 'primary' | 'subtle' | 'danger';
}

const toneClasses = {
  primary: 'bg-slate-900 text-white hover:bg-slate-700',
  subtle: 'border border-slate-200 bg-white text-slate-700 hover:border-emerald-400',
  danger: 'border border-rose-200 bg-white text-rose-700 hover:border-rose-400',
};

export function IconButton({ icon, label, tone = 'subtle', className = '', ...props }: IconButtonProps) {
  return (
    <button
      {...props}
      title={label}
      aria-label={label}
      className={`inline-flex h-9 items-center justify-center gap-2 rounded-md px-3 text-sm font-medium transition ${toneClasses[tone]} disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
    >
      {icon}
      <span>{label}</span>
    </button>
  );
}
