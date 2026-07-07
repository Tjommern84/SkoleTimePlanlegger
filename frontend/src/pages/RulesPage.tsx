import { PageHeader } from "../components/ui/PageHeader";
import { Card } from "../components/ui/Card";
import { RuleCard, type RuleKind } from "../components/rules/RuleCard";

interface RuleDef {
  name: string;
  kind: RuleKind;
  active: boolean;
  weight?: "lav" | "middels" | "høy";
}

// Reflects the constraints actually implemented in the solver
// (backend/app/solver/model_builder.py + soft_constraints.py) -- not a
// configurable rule engine yet, see section note below.
const HARD_RULES: RuleDef[] = [
  { name: "Lærer kan ikke være to steder samtidig", kind: "hard", active: true },
  { name: "Klasse kan ikke ha to fag samtidig", kind: "hard", active: true },
  { name: "Maks 2 samtidige KRØV-økter, ingen samtidig med hallbruk", kind: "hard", active: true },
  { name: "Tirsdag slutter etter periode 4", kind: "hard", active: true },
  { name: "Ingen halvtime kan stå alene i periode 2/3", kind: "hard", active: true },
  { name: "En klasses hel- og halvgruppe kan ikke begge være aktive samtidig", kind: "hard", active: true },
];

const SOFT_RULES: RuleDef[] = [
  { name: "Matematikk bør ligge før lunsj", kind: "soft", active: true, weight: "middels" },
  { name: "Musikk bør ikke ligge på sammenhengende perioder", kind: "soft", active: true, weight: "middels" },
  { name: "KRØV på 10. trinn bør ligge periode 3–4", kind: "soft", active: true, weight: "lav" },
  { name: "Mat og helse bør starte i periode 2", kind: "soft", active: true, weight: "middels" },
  { name: "KRØV bør helst ha maks 1 samtidig økt", kind: "soft", active: true, weight: "lav" },
];

const FIXED_RULES: RuleDef[] = [
  { name: "Fremmedspråk 10. trinn: onsdag periode 5–6", kind: "fixed", active: true },
];

export function RulesPage() {
  return (
    <div>
      <PageHeader
        title="Regler"
        description="Reglene som styrer timeplanmotoren. Vektjustering og egendefinerte regler kommer i en senere versjon."
      />

      <div className="space-y-6">
        <Card>
          <h2 className="mb-3 text-sm font-semibold text-ink">Harde regler</h2>
          <div className="grid gap-2 sm:grid-cols-2">
            {HARD_RULES.map((r) => (
              <RuleCard key={r.name} {...r} />
            ))}
          </div>
        </Card>

        <Card>
          <h2 className="mb-3 text-sm font-semibold text-ink">Myke regler</h2>
          <div className="grid gap-2 sm:grid-cols-2">
            {SOFT_RULES.map((r) => (
              <RuleCard key={r.name} {...r} />
            ))}
          </div>
        </Card>

        <Card>
          <h2 className="mb-3 text-sm font-semibold text-ink">Faste plasseringer</h2>
          <div className="grid gap-2 sm:grid-cols-2">
            {FIXED_RULES.map((r) => (
              <RuleCard key={r.name} {...r} />
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
