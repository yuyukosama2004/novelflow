import { Badge } from "./ui/badge";

interface StatusPillProps {
  children: string;
  tone?: "neutral" | "ok" | "warn";
}

const toneMap = {
  neutral: "neutral",
  ok: "success",
  warn: "warning",
} as const;

export function StatusPill({ children, tone = "neutral" }: StatusPillProps) {
  return <Badge tone={toneMap[tone]}>{children}</Badge>;
}
