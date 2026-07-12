import { Pencil, Star, Trash2, Users } from "lucide-react";
import { toneClasses, type Tone } from "../ui/tone";
import { Badge } from "../ui/Badge";

export type ActivityKind = "NORMAL" | "SPLIT_PARALLEL" | "TRINNFAG";

const KIND_META: Record<ActivityKind, { tone: Tone; icon: typeof Users; label: string }> = {
  NORMAL: { tone: "success", icon: Users, label: "NORMAL" },
  SPLIT_PARALLEL: { tone: "warning", icon: Users, label: "SPLIT_PARALLEL" },
  TRINNFAG: { tone: "accent", icon: Star, label: "TRINNFAG" },
};

interface ActivityCardProps {
  title: string;
  lines: string[];
  kind: ActivityKind;
  occurrenceLabel: string;
  onEdit?: () => void;
  onDelete?: () => void;
}

export function ActivityCard({ title, lines, kind, occurrenceLabel, onEdit, onDelete }: ActivityCardProps) {
  const meta = KIND_META[kind];
  const Icon = meta.icon;
  return (
    <div className="flex gap-3 rounded-lg border border-border bg-surface-soft p-3">
      <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full ${toneClasses[meta.tone]}`}>
        <Icon className="h-4 w-4" />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-2">
          <p className="truncate text-sm font-semibold text-ink">{title}</p>
          <div className="flex shrink-0 items-center gap-1">
            <Badge tone={meta.tone}>{meta.label}</Badge>
            {onEdit && (
              <button type="button" onClick={onEdit} className="rounded-full p-1 text-ink-soft hover:bg-bg-soft" title="Rediger">
                <Pencil className="h-3 w-3" />
              </button>
            )}
            {onDelete && (
              <button
                type="button"
                onClick={onDelete}
                className="rounded-full p-1 text-ink-soft hover:bg-danger-soft hover:text-danger"
                title="Slett"
              >
                <Trash2 className="h-3 w-3" />
              </button>
            )}
          </div>
        </div>
        <div className="mt-0.5 space-y-0.5">
          {lines.map((line, i) => (
            <p key={i} className="truncate text-xs text-ink-muted">
              {line}
            </p>
          ))}
        </div>
        <p className="mt-1 text-[11px] font-medium text-ink-soft">{occurrenceLabel}</p>
      </div>
    </div>
  );
}
