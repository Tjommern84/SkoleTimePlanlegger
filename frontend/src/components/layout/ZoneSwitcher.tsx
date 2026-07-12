import { ChevronDown } from "lucide-react";
import type { ZoneSummary } from "../../api/client";

interface ZoneSwitcherProps {
  zones: ZoneSummary[];
  activeZoneId: number;
  onChange: (id: number) => void;
}

/** Only worth showing once a user belongs to more than one zone (their own
 * plus zones they've been invited into) -- most users will only ever have
 * one, so the parent should skip rendering this entirely in that case. */
export function ZoneSwitcher({ zones, activeZoneId, onChange }: ZoneSwitcherProps) {
  return (
    <div className="relative">
      <select
        className="appearance-none rounded-lg border border-border bg-surface py-2 pr-8 pl-3 text-sm font-medium text-ink shadow-sm"
        value={activeZoneId}
        onChange={(e) => onChange(Number(e.target.value))}
        title="Bytt sone"
      >
        {zones.map((z) => (
          <option key={z.id} value={z.id}>
            {z.name}
          </option>
        ))}
      </select>
      <ChevronDown className="pointer-events-none absolute top-1/2 right-2.5 h-3.5 w-3.5 -translate-y-1/2 text-ink-soft" />
    </div>
  );
}
