import type { ReactNode } from "react";
import { toneClasses, type Tone } from "./tone";

interface StatCardProps {
  icon?: ReactNode;
  value: ReactNode;
  label: string;
  tone?: Tone;
}

export function StatCard({ icon, value, label, tone = "neutral" }: StatCardProps) {
  return (
    <div className="flex flex-col items-center gap-1.5 rounded-lg border border-border bg-surface-soft px-3 py-4 text-center">
      {icon && (
        <span className={`flex h-8 w-8 items-center justify-center rounded-full ${toneClasses[tone]}`}>{icon}</span>
      )}
      <span className="text-xl font-semibold text-ink">{value}</span>
      <span className="text-xs text-ink-muted">{label}</span>
    </div>
  );
}
