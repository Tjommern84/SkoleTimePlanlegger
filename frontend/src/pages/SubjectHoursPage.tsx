import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { PageHeader } from "../components/ui/PageHeader";
import { Card } from "../components/ui/Card";
import { StatCard } from "../components/ui/StatCard";
import { Chip } from "../components/ui/Chip";

export function SubjectHoursPage({ schoolYearId }: { schoolYearId: number }) {
  const trinn = useQuery({
    queryKey: ["trinn", schoolYearId],
    queryFn: () => api.trinn.list(schoolYearId),
  });
  const subjects = useQuery({
    queryKey: ["subjects", schoolYearId],
    queryFn: () => api.subjects.list(schoolYearId),
  });

  const table = useQuery({
    queryKey: ["subjectHourTable", schoolYearId, subjects.data?.map((s) => s.id).join(",")],
    queryFn: async () => {
      if (!subjects.data) return {};
      const entries = await Promise.all(
        subjects.data.map(async (s) => [s.id, await api.subjects.hourAllocations(s.id)] as const),
      );
      return Object.fromEntries(entries);
    },
    enabled: !!subjects.data,
  });

  const levels = [...(trinn.data ?? [])].sort((a, b) => a.level - b.level);

  const totalByTrinn: Record<number, number> = {};
  for (const allocations of Object.values(table.data ?? {})) {
    for (const a of allocations as { trinn_id: number; weekly_hours: number }[]) {
      totalByTrinn[a.trinn_id] = (totalByTrinn[a.trinn_id] ?? 0) + Number(a.weekly_hours);
    }
  }

  return (
    <div>
      <PageHeader title="Fag og timetall" description="Definer uketimer og egenskaper for hvert fag på hvert trinn." />

      {levels.length > 0 && (
        <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {levels.map((t) => (
            <StatCard key={t.id} value={`${totalByTrinn[t.id] ?? "–"} t`} label={`${t.level}. trinn`} tone="primary" />
          ))}
        </div>
      )}

      <Card padding="none" className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="bg-surface-soft text-xs font-semibold text-ink-muted uppercase">
                <th className="px-4 py-3">Fag</th>
                {levels.map((t) => (
                  <th key={t.id} className="px-4 py-3 text-right">
                    {t.level}. trinn
                  </th>
                ))}
                <th className="px-4 py-3">Egenskaper</th>
              </tr>
            </thead>
            <tbody>
              {(subjects.isLoading || trinn.isLoading) && (
                <tr>
                  <td colSpan={levels.length + 2} className="px-4 py-6 text-center text-ink-muted">
                    Laster...
                  </td>
                </tr>
              )}
              {subjects.data?.map((s) => {
                const allocations = table.data?.[s.id] ?? [];
                return (
                  <tr key={s.id} className="border-t border-border">
                    <td className="px-4 py-3 font-medium text-ink">
                      {s.name} <span className="text-ink-soft">({s.short_code})</span>
                    </td>
                    {levels.map((t) => {
                      const alloc = allocations.find((a: { trinn_id: number }) => a.trinn_id === t.id);
                      return (
                        <td key={t.id} className="px-4 py-3 text-right tabular-nums text-ink">
                          {alloc ? alloc.weekly_hours : "–"}
                        </td>
                      );
                    })}
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1.5">
                        {s.prefer_before_lunch && <Chip tone="success">før lunsj</Chip>}
                        {s.uses_hall && <Chip tone="primary">bruker hall</Chip>}
                        {s.is_trinnfag && <Chip tone="accent">trinnfag</Chip>}
                        {s.avoid_consecutive && <Chip tone="warning">unngå sammenhengende</Chip>}
                        {s.needs_consecutive_periods && <Chip tone="secondary">praktisk fag</Chip>}
                        {s.is_krov && <Chip tone="secondary">KRØV</Chip>}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
