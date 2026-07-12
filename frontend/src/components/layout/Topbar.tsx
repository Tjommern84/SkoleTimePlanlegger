import { useState } from "react";
import { Bell, ChevronDown, Plus, Sparkles, Users } from "lucide-react";
import { API_BASE_URL, type ZoneSummary } from "../../api/client";
import { Badge } from "../ui/Badge";
import { TeacherAvatar } from "../teachers/TeacherAvatar";
import { ManageCollaboratorsModal } from "../zone/ManageCollaboratorsModal";
import { ZoneSwitcher } from "./ZoneSwitcher";
import type { Tone } from "../ui/tone";

interface TopbarProps {
  schoolYears: { id: number; label: string }[];
  schoolYearId: number | null;
  onSchoolYearChange: (id: number) => void;
  statusLabel: string;
  statusTone: Tone;
  userEmail?: string;
  onGenerate: () => void;
  generating?: boolean;
  zones: ZoneSummary[];
  activeZoneId: number;
  onZoneChange: (id: number) => void;
  onCreateSchoolYear: () => void;
}

export function Topbar({
  schoolYears,
  schoolYearId,
  onSchoolYearChange,
  statusLabel,
  statusTone,
  userEmail,
  onGenerate,
  generating,
  zones,
  activeZoneId,
  onZoneChange,
  onCreateSchoolYear,
}: TopbarProps) {
  const [collaboratorsOpen, setCollaboratorsOpen] = useState(false);
  const isOwner = zones.find((z) => z.id === activeZoneId)?.role === "owner";

  return (
    <header className="flex items-center justify-between gap-4 border-b border-border/70 bg-surface/70 px-6 py-3.5 backdrop-blur-sm">
      <div className="flex items-center gap-3">
        <div className="relative">
          <select
            className="appearance-none rounded-lg border border-border bg-surface py-2 pr-8 pl-3 text-sm font-medium text-ink shadow-sm"
            value={schoolYearId ?? ""}
            onChange={(e) => onSchoolYearChange(Number(e.target.value))}
          >
            {schoolYears.map((y) => (
              <option key={y.id} value={y.id}>
                {y.label}
              </option>
            ))}
          </select>
          <ChevronDown className="pointer-events-none absolute top-1/2 right-2.5 h-3.5 w-3.5 -translate-y-1/2 text-ink-soft" />
        </div>
        <button
          type="button"
          onClick={onCreateSchoolYear}
          className="flex h-8 w-8 items-center justify-center rounded-full border border-border bg-surface text-ink-muted hover:bg-bg-soft"
          aria-label="Nytt skoleår"
          title="Nytt skoleår"
        >
          <Plus className="h-4 w-4" />
        </button>
        {zones.length > 1 && (
          <ZoneSwitcher zones={zones} activeZoneId={activeZoneId} onChange={onZoneChange} />
        )}
        <Badge tone={statusTone}>{statusLabel}</Badge>
      </div>

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onGenerate}
          disabled={generating}
          className="flex items-center gap-2 rounded-full bg-primary px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-primary-dark disabled:opacity-60"
        >
          <Sparkles className="h-4 w-4" />
          {generating ? "Genererer..." : "Generer timeplan"}
        </button>
        <button
          type="button"
          onClick={() => setCollaboratorsOpen(true)}
          className="flex h-9 w-9 items-center justify-center rounded-full border border-border bg-surface text-ink-muted"
          aria-label="Del sonen"
          title="Del sonen"
        >
          <Users className="h-4 w-4" />
        </button>
        <button
          type="button"
          className="flex h-9 w-9 items-center justify-center rounded-full border border-border bg-surface text-ink-muted"
          aria-label="Varsler"
        >
          <Bell className="h-4 w-4" />
        </button>
        {userEmail && (
          <form action={`${API_BASE_URL}/auth/logout`} method="post" title={`Logg ut (${userEmail})`}>
            <button type="submit">
              <TeacherAvatar initials={userEmail.slice(0, 2)} />
            </button>
          </form>
        )}
      </div>

      {collaboratorsOpen && (
        <ManageCollaboratorsModal isOwner={isOwner} onClose={() => setCollaboratorsOpen(false)} />
      )}
    </header>
  );
}
