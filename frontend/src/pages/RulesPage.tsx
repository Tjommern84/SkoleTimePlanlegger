import { useState } from "react";
import { PageHeader } from "../components/ui/PageHeader";
import { Card } from "../components/ui/Card";
import { HintToggle } from "../components/ui/HintToggle";
import { RuleCard, type RuleKind } from "../components/rules/RuleCard";

interface RuleDef {
  name: string;
  kind: RuleKind;
  active: boolean;
  weight?: "lav" | "middels" | "høy";
  description: string;
}

// Reflects the constraints actually implemented in the solver
// (backend/app/solver/model_builder.py + soft_constraints.py) -- not a
// configurable rule engine yet, see section note below.
const HARD_RULES: RuleDef[] = [
  {
    name: "Lærer kan ikke være to steder samtidig",
    kind: "hard",
    active: true,
    description:
      "Hvis en lærer er satt opp på to aktiviteter i samme periode, avviser solveren den plasseringen helt. Denne regelen kan aldri brytes, uansett hvor mye annet må vike.",
  },
  {
    name: "Klasse kan ikke ha to fag samtidig",
    kind: "hard",
    active: true,
    description:
      "En klasse (eller klassegruppe) kan bare ha ett fag om gangen. Delte grupper (f.eks. \"9A halvparten\") regnes som egne enheter, så to halvgrupper i samme klasse KAN ha ulike fag samtidig — det er nettopp poenget med en delt aktivitet.",
  },
  {
    name: "Maks 2 samtidige KRØV-økter, ingen samtidig med hallbruk",
    kind: "hard",
    active: true,
    description:
      "Styres av \"KRØV\"-flagget og \"bruker hall\"-flagget på fag (se Fag og timetall). Et fag som bruker hallen (f.eks. valgfag) blokkerer all kroppsøving for HELE skolen mens det pågår — fordi hallen bare finnes én gang.",
  },
  {
    name: "Tirsdag slutter etter periode 4",
    kind: "hard",
    active: true,
    description:
      "Hardkodet til akkurat tirsdag i dagens versjon — hvis skolen din har en annen kort dag, må periodene for den dagen rett og slett ikke opprettes i Grunnoppsett (se periodetabellen der).",
  },
  {
    name: "Ingen halvtime kan stå alene i periode 2/3",
    kind: "hard",
    active: true,
    description:
      "En 30-minutters økt må alltid pares med en annen 30-minutters økt i samme periode (2 eller 3) samme dag, ellers er den umulig å plassere. Aktivitets-skjemaet varsler deg om dette når du velger en varighet som ikke er delelig på 60 minutter.",
  },
  {
    name: "En klasses hel- og halvgruppe kan ikke begge være aktive samtidig",
    kind: "hard",
    active: true,
    description:
      "Hvis en klasse er delt i to halvgrupper for en økt, kan ikke hele klassen samtidig ha en annen, felles aktivitet — de representerer de samme elevene.",
  },
  {
    name: "Aldri flere enn én økt per dag for et fag (per fag, valgfritt)",
    kind: "hard",
    active: true,
    description:
      "Styres av \"Aldri flere enn én økt per dag\"-flagget på faget (se Fag og timetall) — av og på per fag, ikke en generell regel for alle fag. Motsatt av \"Unngå sammenhengende økter\" (Musikk), som bevisst tillater to økter samme dag så lenge de ikke ligger rett etter hverandre.",
  },
  {
    name: "Maks samtidige økter for et fag med begrenset ressurs (per fag, valgfritt)",
    kind: "hard",
    active: true,
    description:
      "Styres av \"Maks samtidige økter for hele skolen\"-feltet på faget (se Fag og timetall) — for fag som deler en knapp ressurs skolen bare har noen få av, f.eks. naturfagrom/labber. Uavhengig av KRØV/hall-mekanismen over.",
  },
];

const SOFT_RULES: RuleDef[] = [
  {
    name: "Matematikk bør ligge før lunsj",
    kind: "soft",
    active: true,
    weight: "middels",
    description:
      "Styres av \"Bør ligge før lunsj\"-flagget på faget. Solveren prøver å oppfylle dette, men vil bryte det hvis det er nødvendig for i det hele tatt å finne en gyldig plan.",
  },
  {
    name: "Musikk bør ikke ligge på sammenhengende perioder",
    kind: "soft",
    active: true,
    weight: "middels",
    description:
      "Styres av \"Unngå sammenhengende økter\"-flagget på faget. En myk preferanse — brytes hvis timeplanen ellers ikke går opp.",
  },
  {
    name: "KRØV på 10. trinn bør ligge periode 3–4",
    kind: "soft",
    active: true,
    weight: "lav",
    description:
      "En preferanse spesifikt for 10. trinns kroppsøving, lav vekt — den vike lett for andre hensyn.",
  },
  {
    name: "Mat og helse bør starte i periode 2",
    kind: "soft",
    active: true,
    weight: "middels",
    description:
      "Styres av \"Trenger sammenhengende perioder\"-flagget kombinert med fagets kode — praktiske fag som trenger en lengre sammenhengende økt plasseres helst tidlig på dagen.",
  },
  {
    name: "KRØV bør helst ha maks 1 samtidig økt",
    kind: "soft",
    active: true,
    weight: "lav",
    description:
      "Selv om reglene tillater opptil 2 samtidige KRØV-økter (se den harde regelen over), foretrekker solveren å holde seg til 1 om gangen når det er mulig, av hensyn til hallplass.",
  },
  {
    name: "Bør ligge i periode 1-2",
    kind: "soft",
    active: true,
    weight: "middels",
    description:
      "Styres av \"Bør ligge i periode 1-2\"-flagget på faget (f.eks. valgfag). Strengere enn \"bør ligge før lunsj\" — solveren prøver spesifikt å legge faget i de to første periodene.",
  },
  {
    name: "Bør ikke ligge fredag etter lunsj",
    kind: "soft",
    active: true,
    weight: "middels",
    description:
      "Styres av \"Unngå fredag etter lunsj\"-flagget på faget (f.eks. fremmedspråk). En myk preferanse — brytes hvis timeplanen ellers ikke går opp.",
  },
];

const FIXED_RULES: RuleDef[] = [
  {
    name: "Fremmedspråk 10. trinn: onsdag periode 5–6",
    kind: "fixed",
    active: true,
    description:
      "En fast, ikke-forhandlingsbar plassering spesifikt for denne skolens 10.-trinns fremmedspråk-fag. Dette er ikke en generell regel for alle fag — det er hardkodet til akkurat dette faget og trinnet.",
  },
];

export function RulesPage() {
  const [showIntroHint, setShowIntroHint] = useState(false);
  const [showHardHints, setShowHardHints] = useState(false);
  const [showSoftHints, setShowSoftHints] = useState(false);
  const [showFixedHints, setShowFixedHints] = useState(false);

  return (
    <div>
      <PageHeader
        title="Regler"
        description="Reglene som styrer timeplanmotoren. Vektjustering og egendefinerte regler kommer i en senere versjon."
      />

      <Card className="mb-6">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-ink">Hvordan lese denne siden</h2>
          <HintToggle checked={showIntroHint} onChange={setShowIntroHint} />
        </div>
        {showIntroHint && (
          <ul className="list-disc space-y-1.5 pl-5 text-sm text-ink-muted">
            <li>
              <span className="font-medium text-ink">Harde regler</span> kan aldri brytes — solveren finner rett og
              slett ingen løsning hvis den ikke klarer å oppfylle alle sammen.
            </li>
            <li>
              <span className="font-medium text-ink">Myke regler</span> er ønsker med en vekt (lav/middels/høy) —
              høyere vekt betyr at solveren strekker seg lenger for å oppfylle den, men den kan brytes hvis
              timeplanen ellers ikke går opp.
            </li>
            <li>
              <span className="font-medium text-ink">Faste plasseringer</span> er unntak som er hardkodet til et
              helt spesifikt fag/trinn/tidspunkt — de gjelder ikke generelt for alle skoler eller alle fag.
            </li>
            <li>
              Mange av reglene under styres av flaggene du setter per fag på{" "}
              <span className="font-medium text-ink">Fag og timetall</span>-siden (KRØV, bruker hall, unngå
              sammenhengende, osv.) — se forklaringen der når du oppretter eller redigerer et fag.
            </li>
          </ul>
        )}
      </Card>

      <div className="space-y-6">
        <Card>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-ink">Harde regler</h2>
            <HintToggle checked={showHardHints} onChange={setShowHardHints} />
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            {HARD_RULES.map((r) => (
              <RuleCard key={r.name} {...r} description={showHardHints ? r.description : undefined} />
            ))}
          </div>
        </Card>

        <Card>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-ink">Myke regler</h2>
            <HintToggle checked={showSoftHints} onChange={setShowSoftHints} />
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            {SOFT_RULES.map((r) => (
              <RuleCard key={r.name} {...r} description={showSoftHints ? r.description : undefined} />
            ))}
          </div>
        </Card>

        <Card>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-ink">Faste plasseringer</h2>
            <HintToggle checked={showFixedHints} onChange={setShowFixedHints} />
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            {FIXED_RULES.map((r) => (
              <RuleCard key={r.name} {...r} description={showFixedHints ? r.description : undefined} />
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
