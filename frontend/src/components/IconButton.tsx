import type { ButtonHTMLAttributes, ReactNode } from "react";

import { cn } from "../utils/cn";

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  icon: ReactNode;
  label: string;
  tone?: "primary" | "subtle" | "danger";
}

const toneClasses = {
  primary: "bg-brand-700 text-white shadow-sm hover:bg-brand-800",
  subtle:
    "border border-stone-200 bg-white text-stone-700 shadow-sm hover:border-brand-200 hover:bg-brand-50",
  danger: "border border-rose-200 bg-white text-rose-700 hover:bg-rose-50",
};

export function IconButton({
  icon,
  label,
  tone = "subtle",
  className = "",
  ...props
}: IconButtonProps) {
  return (
    <button
      {...props}
      title={label}
      aria-label={label}
      className={cn(
        "inline-flex h-9 items-center justify-center gap-2 rounded-lg px-3 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
        toneClasses[tone],
        className,
      )}
    >
      {icon}
      <span>{label}</span>
    </button>
  );
}
