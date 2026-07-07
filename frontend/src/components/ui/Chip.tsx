import type { ReactNode } from "react";
import { toneClasses, type Tone } from "./tone";

interface ChipProps {
  children: ReactNode;
  tone?: Tone;
  icon?: ReactNode;
}

export function Chip({ children, tone = "neutral", icon }: ChipProps) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium whitespace-nowrap ${toneClasses[tone]}`}
    >
      {icon}
      {children}
    </span>
  );
}
