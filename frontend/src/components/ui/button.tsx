import { cva, type VariantProps } from "class-variance-authority";
import type { ButtonHTMLAttributes } from "react";

import { cn } from "../../utils/cn";

const buttonVariants = cva(
  "inline-flex min-h-9 items-center justify-center gap-2 rounded-lg px-3 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        primary:
          "bg-brand-700 text-white shadow-sm hover:bg-brand-800 active:bg-brand-900",
        secondary:
          "border border-stone-200 bg-white text-stone-700 shadow-sm hover:border-brand-200 hover:bg-brand-50 hover:text-brand-800",
        ghost: "text-stone-600 hover:bg-stone-100 hover:text-stone-950",
        danger:
          "border border-rose-200 bg-white text-rose-700 hover:bg-rose-50 hover:text-rose-800",
      },
      size: {
        sm: "min-h-8 px-2.5 text-xs",
        md: "min-h-9 px-3",
        lg: "min-h-10 px-4 text-base",
        icon: "h-9 min-h-9 w-9 px-0",
      },
    },
    defaultVariants: { variant: "secondary", size: "md" },
  },
);

export interface ButtonProps
  extends
    ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export function Button({
  className,
  variant,
  size,
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  );
}
