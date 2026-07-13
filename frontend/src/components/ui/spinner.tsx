import { LoaderCircle } from "lucide-react";

import { cn } from "../../utils/cn";

export function Spinner({ className }: { className?: string }) {
  return (
    <LoaderCircle
      aria-label="加载中"
      className={cn("animate-spin text-brand-700", className)}
      size={18}
    />
  );
}
