import { Badge } from "../ui/Badge";
import type { Tone } from "../ui/tone";

export type RuleKind = "hard" | "soft" | "fixed";

const KIND_LABEL: Record<RuleKind, { label: string; tone: Tone }> = {
  hard: { label: "Hard regel", tone: "danger" },
  soft: { label: "Myk regel", tone: "accent" },
  fixed: { label: "Fast plassering", tone: "primary" },
};

interface RuleCardProps {
  name: string;
  kind: RuleKind;
  active: boolean;
  weight?: "lav" | "middels" | "høy";
}

export function RuleCard({ name, kind, active, weight }: RuleCardProps) {
  const meta = KIND_LABEL[kind];
  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border border-border bg-surface-soft px-4 py-3">
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-ink">{name}</p>
        <div className="mt-1 flex items-center gap-2">
          <Badge tone={meta.tone}>{meta.label}</Badge>
          {weight && <Badge tone="neutral">Vekt: {weight}</Badge>}
        </div>
      </div>
      <Badge tone={active ? "success" : "neutral"}>{active ? "Aktiv" : "Inaktiv"}</Badge>
    </div>
  );
}
