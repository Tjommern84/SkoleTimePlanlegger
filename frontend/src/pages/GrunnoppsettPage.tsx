import { useQuery } from "@tanstack/react-query";
import { Home, Pencil } from "lucide-react";
import { api } from "../api/client";
import { PageHeader } from "../components/ui/PageHeader";
import { Card } from "../components/ui/Card";
import { StatCard } from "../components/ui/StatCard";
import { EmptyState } from "../components/ui/EmptyState";

export function GrunnoppsettPage({ schoolYearId }: { schoolYearId: number }) {
  const trinn = useQuery({ queryKey: ["trinn", schoolYearId], queryFn: () => api.trinn.list(schoolYearId) });
  const classesQuery = useQuery({
    queryKey: ["allClasses", schoolYearId, trinn.data?.map((t) => t.id).join(",")],
    queryFn: async () => {
      if (!trinn.data) return [];
      const lists = await Promise.all(trinn.data.map((t) => api.classes.list(t.id)));
      return lists.flat();
    },
    enabled: !!trinn.data,
  });

  return (
    <div>
      <PageHeader
        title="Grunnoppsett"
        description="Skoleår, trinn, klasser og periodeoppsett (ringetider, lunsj, halvtimer)."
      />

      <Card>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-ink">Oversikt</h2>
          <button
            type="button"
            title="Redigering av grunnoppsettet kommer i en senere versjon"
            className="flex items-center gap-1.5 rounded-full border border-border bg-surface px-3 py-1.5 text-sm font-medium text-ink-muted opacity-60"
          >
            <Pencil className="h-3.5 w-3.5" />
            Rediger
          </button>
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatCard value={trinn.data?.length ?? "–"} label="Trinn" />
          <StatCard value={classesQuery.data?.length ?? "–"} label="Klasser" />
          <StatCard value="Man–Fre" label="Skoledager" />
          <StatCard value="6 / 4" label="Perioder (normal / tirsdag)" />
        </div>
      </Card>

      <div className="mt-6">
        <EmptyState
          icon={<Home className="h-6 w-6" />}
          title="Full redigering kommer senere"
          description="Skoleår, trinn, klasser og periodeoppsett kan i dag settes opp via API/seed-data. Et eget redigeringsgrensesnitt for grunnoppsettet er ikke bygget ennå."
        />
      </div>
    </div>
  );
}
