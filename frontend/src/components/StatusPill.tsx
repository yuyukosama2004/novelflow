interface StatusPillProps {
  children: string;
  tone?: "neutral" | "ok" | "warn";
}

const toneClasses = {
  neutral: "border-slate-200 bg-white text-slate-600",
  ok: "border-emerald-200 bg-emerald-50 text-emerald-700",
  warn: "border-amber-200 bg-amber-50 text-amber-800",
};

export function StatusPill({ children, tone = "neutral" }: StatusPillProps) {
  return (
    <span
      className={`inline-flex rounded-md border px-2 py-1 text-xs font-medium ${toneClasses[tone]}`}
    >
      {children}
    </span>
  );
}
