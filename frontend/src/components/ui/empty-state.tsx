import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "../../utils/cn";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center rounded-xl border border-dashed border-stone-300 bg-stone-50/70 px-5 py-9 text-center",
        className,
      )}
    >
      <span className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-50 text-brand-700">
        <Icon size={20} aria-hidden="true" />
      </span>
      <p className="mt-3 text-sm font-semibold text-stone-800">{title}</p>
      {description ? (
        <p className="mt-1 max-w-sm text-sm leading-6 text-stone-500">
          {description}
        </p>
      ) : null}
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}
