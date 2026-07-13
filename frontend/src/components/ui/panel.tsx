import type { HTMLAttributes } from "react";

import { cn } from "../../utils/cn";

export function Panel({ className, ...props }: HTMLAttributes<HTMLElement>) {
  return (
    <section
      className={cn(
        "rounded-xl border border-stone-200/90 bg-white shadow-panel",
        className,
      )}
      {...props}
    />
  );
}
