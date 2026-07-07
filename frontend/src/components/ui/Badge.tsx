import type { ReactNode } from "react";
import { toneClasses, type Tone } from "./tone";

interface BadgeProps {
  children: ReactNode;
  tone?: Tone;
  icon?: ReactNode;
  outline?: boolean;
}

export function Badge({ children, tone = "neutral", icon, outline = false }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${
        outline ? `border border-current ${toneClasses[tone]}` : toneClasses[tone]
      }`}
    >
      {icon}
      {children}
    </span>
  );
}
