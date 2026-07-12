# Statusrapport — Timeplanlegger

Sist oppdatert: 2026-07-12 (økt 6 — onboarding-UI for en ny skole)

## Onboarding-UI: en ny skole kan nå settes opp fra bunnen kun via grensesnittet (denne økten)

Forrige økt (soner) løste isolasjon mellom skoler, men en fersk sone var
fortsatt en blindvei — ingen UI for å opprette skoleår/trinn/klasser/
perioder/fag/aktiviteter, kun visning. Denne økten bygget full CRUD:

- **Backend**: nye PATCH/DELETE-ruter for skoleår, perioder, trinn, klasser,
  klassegrupper, fag og fag-timetall (alle sonescopet på samme måte som
  resten av API-et). Sletting er bevisst "restrict" (blokkeres med 409 hvis
  noe fortsatt refererer raden), ikke kaskade — eneste unntak er
  fag-timetall som slettes automatisk sammen med faget sitt. Ny
  `_validate_leg_count`-sjekk i `POST /activities` håndhever nå
  NORMAL=1/SPLIT_PARALLEL=2/TRINNFAG≥1-ben-regelen som før kun var
  dokumentert, ikke håndhevet. Ny global `IntegrityError`→409-handler i
  `main.py`.
- **Reell bug funnet og rettet**: SQLite håndhever ikke fremmednøkler som
  standard (i motsetning til Postgres i produksjon) — uten
  `PRAGMA foreign_keys=ON` (nå satt i `db/base.py` ved engine-oppstart)
  ville "restrict delete" stille og rolig IKKE blokkert noe i lokal
  utvikling/tester, og latt foreldreløse rader ligge igjen.
- **Frontend**: `GrunnoppsettPage.tsx`, `SubjectHoursPage.tsx` og
  `ActivitiesPage.tsx` gikk fra rene visningssider til full
  opprett/rediger/slett. Ny "opprett skoleår"-inngang (kritisk, siden en
  fersk sone har null skoleår) i både `App.tsx`s tomme-tilstand og en
  "+"-knapp i `Topbar.tsx`. Ny `SubjectEditModal` og `ActivityEditModal`
  (aktivitetsredigering er bevisst "slett og gjenopprett" under panseret,
  ikke en ekte in-place-oppdatering — enklere gitt at brukeren valgte en
  enkel skjema-modal, ikke en full matrise-editor).
- **Alt verifisert**: 69 backend-tester grønne (opp fra 60, inkl. nye
  restrict-delete- og IDOR-tester), frontend `tsc -b`/`lint`/`build` rene,
  og en full live nettleserøkt der en **helt fersk bruker med tom sone**
  bygget en fiktiv "ny skole" utelukkende gjennom grensesnittet — skoleår →
  trinn → klasse → perioder → fag med timetall → lærer → aktivitet — og
  "Generer timeplan" fant en gyldig løsning (status gikk fra "Utkast
  lagret" til "Gyldig plan"), bekreftet i både Aktiviteter- og
  Timeplan-rutenett-visningen. To reelle frontend-bugs ble funnet og
  rettet under selve denne verifiseringen (ikke i produksjonskode, men i
  test-selektorene) — ingen nye appfeil utover FK-pragma-funnet over.
- **Ikke bygget i denne omgang** (bevisst utelatt): sletting/redigering av
  klassegrupper er der, men ingen full matrise-/regnearkeditor for
  aktiviteter (kun én-om-gangen-skjema, som brukeren valgte); ingen
  "kopier periodeoppsett fra mal"-snarvei.

## Multi-tenant "soner" med deling/invitasjon (denne økten)

Appen var bevisst enkelt-tenant (kun Lise + kollega, hardkodet
`ALLOWED_EMAILS`-allowlist, ingen tabell hadde noen eier-/tenant-kolonne).
Nytt mål: alle med en Google-konto kan logge inn, hver med sin egen
isolerte "sone" (arbeidsområde), som kan deles med andre Google-kontoer
via invitasjon (full lese/skrive-tilgang for inviterte medlemmer). Full
plan ligger i den godkjente plan-filen fra denne økten; kort oppsummert
hva som er bygget:

- **Ny datamodell**: `Zone`, `ZoneMembership` (rolle eier/medlem),
  `ZoneInvitation` (status pending/accepted/revoked) —
  `backend/app/db/models/zone.py`. `SchoolYear` og `Teacher` fikk en ny
  `zone_id`-kolonne (de gamle globale unik-constraintene på
  `label`/`initials` ble erstattet med sonescopede sammensatte
  constraints). Alt annet (Subject, Activity, GeneratedTimetable osv.)
  arver sone-tilhørighet transitivt via eksisterende FK-kjede.
- **Migrasjon** `a3f9c1d02b4e_add_zones_multi_tenancy.py` bakfyller
  eksisterende data til én sone eid av (første e-post i)
  `ALLOWED_EMAILS`, med øvrige e-poster lagt til som medlem (hvis
  brukeren finnes) eller ventende invitasjon (hvis ikke). Kjørt og
  verifisert mot ekte dev-DB.
- **Innlogging er nå åpen for alle Google-kontoer** — allowlist-sjekken i
  `auth.py` er fjernet. `sync_zone_state_on_login()`
  (`backend/app/services/zones.py`) kjører på hver innlogging: godkjenner
  automatisk ventende invitasjoner for brukerens e-post, og oppretter en
  ny personlig eid sone KUN hvis brukeren ikke endte opp med noe
  medlemskap i det hele tatt (så en invitert bruker aldri får en ekstra
  tom sone). Ingen e-postutsending bygget — invitasjon er ren
  "auto-godkjenn ved neste innlogging".
- **Sone-tilgang utledes fra ressursen, ikke fra en global header**: de
  fleste ruter mottar allerede en `school_year_id`/`teacher_id` osv. og
  sjekker medlemskap via sonen den tilhører
  (`zone_membership_for_school_year`/`_for_teacher` i `deps.py`). Kun de
  fire rot-endepunktene uten noen eksisterende id å utlede fra
  (`GET/POST /school-years`, `GET/POST /teachers`) krever en eksplisitt
  `X-Zone-Id`-header. Dette var bevisst valgt bl.a. fordi
  Excel-eksport-lenken er en vanlig `<a href>`-nedlasting som ikke kan
  sende egendefinerte headere.
- **Alle eksisterende ruter er sonescopet** (teachers, school_years,
  subjects, activities, solver_settings, solve, export) — ingen av dem
  filtrerte på bruker/sone i det hele tatt før denne økten. To reelle
  krysslekkasje-bugs ble også fikset som en direkte konsekvens (ville
  vært harmløse i en enkelt-tenant-verden, men lekker data på tvers av
  soner nå): en ubetinget `select(Subject)` i `solve_service.py` og en
  ubetinget `select(Teacher)` i `excel_export.py`.
- **Ny `zones.py`-rute** (`/api/zones/current/...`): omdøp sone, liste
  medlemmer, invitere/liste/tilbakekalle invitasjoner, fjerne medlem (kun
  eier for de administrative handlingene; kan ikke fjerne sonens siste
  eier).
- **Frontend**: `client.ts` sender `X-Zone-Id` automatisk (modul-nivå
  state, ikke tredd gjennom hver hook); `App.tsx` fikk en ny `ZoneGate`
  mellom innloggingssjekken og Dashboard som velger aktiv sone (fra
  localStorage) FØR noen sonescopet data hentes; `Topbar.tsx` fikk en
  `ZoneSwitcher` (kun synlig ved >1 sone) og en "Del sonen"-knapp som
  åpner `ManageCollaboratorsModal` (inviter/fjern medlemmer for eier,
  read-only medlemsliste for medlemmer).
- **To reelle frontend-bugs funnet og rettet under live nettleserverifisering**:
  (a) `ZoneGate` satte opprinnelig aktiv sone i en `useEffect`, som kjører
  ETTER at `Dashboard`s egne datahook-er (barn) allerede hadde skutt av
  sine første kall uten `X-Zone-Id`-header (React kjører barn-effekter før
  foreldre-effekter) — flyttet til å settes synkront i
  `useState`-initialiseringen i stedet; (b) `ManageCollaboratorsModal` ble
  rendret som barn av `<header className="...backdrop-blur-sm">` i
  `Topbar.tsx` — `backdrop-filter` oppretter et nytt "containing block" for
  `position: fixed`-etterkommere i Chromium, så modalen ble posisjonert
  relativt til den ~68px høye headeren i stedet for viewporten. Fikset med
  `createPortal(..., document.body)`.
- **Alt verifisert**: 60 backend-tester grønne (inkl. nye
  `test_zone_isolation.py` — den kritiske IDOR-testen som bekrefter at et
  medlem av sone A ikke kan poste data som peker til sone B sin
  `school_year_id`, samt `test_zones_routes.py` og `test_zone_services.py`
  for invitasjons-/rolle-logikk), frontend `tsc -b`/`lint`/`build` rene,
  og en full interaksjonstest i ekte nettleser (Playwright) mot den
  virkelige (migrerte) dev-databasen: innlogget som eier (manuell
  sesjonscookie) → "Del sonen"-modal viser riktig medlem/rolle → inviter
  en test-e-post → vises som "Venter" → tilbakekall → forsvinner; separat
  logget inn som et ekte, ekstra medlem lagt til i samme sone → ser samme
  delte data (lærere/fag) → "Del sonen" viser begge medlemmer men uten
  inviter-/fjern-kontroller (riktig, siden de ikke er eier) → ingen
  konsollfeil i noen av øktene.
- **Ikke bygget i denne omgang** (bevisst utelatt, ikke bugs): faktisk
  e-postutsending av invitasjoner (krever SMTP/tjeneste-oppsett), en
  tredje skrivebeskyttet rolle, og overføring av eierskap/sletting av en
  sone.

## "Generer flere alternativer" er nå en ekte funksjon

Brukeren spurte om solveren alltid gir samme resultat. Empirisk testet:
- Samme data + samme OR-Tools-versjon + samme parametere ⇒ **alltid identisk
  resultat** (CP-SAT er bevisst deterministisk, dokumentert av Google).
- Å bare endre `random_seed` eller sette `randomize_search=True` ga **ingen
  forskjell** for vår fixture — solveren finner en 0-avviks-løsning så raskt
  at den aldri trenger å utforske videre.
- Den eneste teknikken som faktisk ga andre løsninger: løs én gang, forby
  eksplisitt akkurat den løsningen ("no-good cut": minst én av de sanne
  boolske variablene må bli usann), løs på nytt. Testet 6 runder — alle 6
  ga andre, men like gyldige (0 avvik), planer.

Denne teknikken er nå bygget inn for ekte:
- **`solve_school_year_variants()`** i `solve_service.py` — bygger modellen
  én gang, løser opptil `variant_count` ganger med denne ekskluder-og-løs-
  på-nytt-teknikken. `solve_school_year()` er nå bare et tynt lag over
  denne med `variant_count=1` (ingen atferdsendring for eksisterende kode).
- **`POST /api/solve`** tar nå `variant_count` (maks 5, validert
  server-side), returnerer `variants: [{generated_timetable_id, status,
  placement_count, is_active}]`. Alle varianter lagres som egne
  `GeneratedTimetable`-rader; kun den første er aktiv til brukeren velger.
- **Ny rute `POST /api/generated-timetables/{id}/activate`** for å bytte
  hvilken variant som er aktiv.
- **Generer-siden**: avkrysningsboksen "Generer 3 alternative varianter"
  er nå ekte (ikke lenger grået ut). Etter generering vises 3 valgbare
  kort ("Variant 1/2/3", alle med samme antall plasserte økter siden alle
  er like gode), med en forklarende tekst om at de er likeverdige, ikke
  rangert.
- **Reell arkitekturbug funnet og rettet underveis**: Topbar-knappen
  "Generer timeplan" og Generer-sidens egen knapp brukte hver sin
  uavhengige `useSolve()`-instans (TanStack Query lager separat tilstand
  per kall, deler den ikke automatisk på tvers av komponenter) — å trykke
  den ene oppdaterte ikke resultatet vist av den andre. Løst ved å løfte
  solve-tilstanden (`solve`, `variants`, `activeVariantId`, `lastRunAt`)
  opp til `App.tsx` og sende den ned som props til `SolvePage`, slik at
  begge knappene nå deler samme resultat.
- Alt verifisert: 45 backend-tester grønne (inkl. ny test for variant-
  generering + aktivering), frontend build/lint/typecheck rene, og en full
  interaksjonstest i nettleser (genererte 3 varianter, byttet til variant
  2, bekreftet at topbar-knappen deretter oppdaterer samme panel).

## Lærer-redigering (etter redesignet, samme økt)

- Fikset en visuell bug: StatCard med ikon på Grunnoppsett-siden dyttet
  tallet ned av linje med de andre boksene — ikonet er fjernet fra den
  boksen (se `StatCard`-bruk i `GrunnoppsettPage.tsx`).
- **Ny backend-tabell `teacher_subject_qualifications`** (migrasjon
  `1e68749da17e`): enkel liste over hvilke fag en lærer kan undervise +
  omtrentlig timetall, IKKE bundet til klasse. Fullt CRUD
  (`GET/POST/PATCH/DELETE /api/teacher-subject-qualifications`). **Viktig:
  dette driver ikke solveren** — solveren bruker fortsatt kun
  Activity/ActivityLeg. Dette er ren oversikt/metadata, forklart tydelig
  i UI-et (se under).
- **Ny backend-rute `PATCH /api/teachers/{id}`** for å redigere navn/initialer.
- **Nytt `TeacherEditModal`-komponent**
  (`frontend/src/components/teachers/TeacherEditModal.tsx`) åpnet via
  "Rediger"-knapp på hver lærerrad. Inneholder:
  - Navn/initialer (redigerbart, lagrer på blur)
  - Fag-avhukingsbokser + timetall-felt, med en blå info-boks (ikke-teknisk
    forklaring: "dette er IKKE det som setter opp timeplanen") og en gul
    "Huskelapp (utvikler)"-boks som forklarer at dette bør vurderes koblet
    til aktivitetsmatrisen når den bygges.
  - Utilgjengelighet som en klikkbar ukentlig kalenderrute (dag × periode),
    med tilsvarende info-boks (forklarer at dette er et **ukentlig
    gjentakende mønster**, ikke spesifikke kalenderdatoer som ferie-booking
    — backend støtter ikke dato-spesifikk fravær ennå) og en huskelapp om
    at ekte dato-basert fravær er en separat, ikke-bygget fremtidig modell.
- Alt verifisert: 44 backend-tester grønne, frontend `tsc -b`/`lint`/`build`
  rene, og en full interaksjonstest i ekte nettleser (avhuking av fag,
  klikk på utilgjengelighet-rute) — begge lagret korrekt til backend og
  vises igjen i tabellen. Testdata ryddet bort etterpå.

## Visuell redesign (denne økten)

Hele frontend er redesignet fra en enkel tabellbasert prototype til et
"premium SaaS"-uttrykk, basert på en referansemockup brukeren la i
`UI/411b8f5b-...png` (dyp blågrønn venstremeny, varm bakgrunn, hvite kort,
fargekodet timeplan). Ingen backend-logikk, datamodell eller API-kontrakt
er endret — kun frontend.

- **Design tokens** i `frontend/src/index.css` (CSS custom properties +
  Tailwind v4 `@theme`-mapping, så `bg-primary`, `text-ink-muted`,
  `rounded-lg`, `shadow-md` osv. automatisk bruker de nye verdiene).
- **Bakgrunnsbilde**: `UI/pexels-roman-odintsov-8180652.jpg` (en
  zen-hage/sand-foto) beskåret til 16:9 med `sharp`
  (`frontend/scripts/prepare-background.js`, kjør med `npm run prepare:bg`)
  → `frontend/public/backgrounds/app-bg{,-1280}.webp`, brukt subtilt med
  en varm gradient-overlay bak hele appen.
- **Nytt komponentbibliotek** i `frontend/src/components/`: `layout/`
  (AppShell, Sidebar, Topbar), `ui/` (Card, Badge, Chip, StatCard,
  SegmentedControl, PageHeader, EmptyState), `activities/ActivityCard`,
  `rules/RuleCard`, `teachers/TeacherAvatar`, `grid/LessonCard`. Ikoner via
  `lucide-react` (nytt npm-avhengighet).
- **Alle 5 eksisterende sider er redesignet** (Fag og timetall, Lærere,
  Aktiviteter, Generer, Timeplan) — all eksisterende funksjonalitet er
  beholdt, bare den visuelle presentasjonen og noen ekte, ikke-fabrikkerte
  databaserte tillegg (se under).
- **To nye sider lagt til**: `RulesPage` (Regler — viser de faktiske
  harde/myke/faste reglene som allerede er implementert i solveren, ren
  visning, ingen redigering ennå) og `GrunnoppsettPage` (placeholder som
  viser reelle tall — antall trinn/klasser — med en tydelig
  "kommer senere"-melding, ikke fabrikkert funksjonalitet).
- **Ekte nye datavisninger** lagt til underveis (ikke fabrikkert):
  Lærere-siden viser nå fag og reelle ukentlige timer beregnet fra
  aktivitetene (`api.activities` × `duration_ticks`), samt ekte hentet
  lærerutilgjengelighet (`GET /api/teacher-unavailabilities`, som ikke
  hadde en frontend-klient fra før — lagt til i `api/client.ts` +
  `useTeacherUnavailabilities`). Timeplan-siden fikk en fungerende
  **Lærer-visning** (segmentert kontroll Klasse/Lærer/Rom — Rom er et
  ærlig "ikke i bruk ennå siden vi ikke sporer rom"-tomt-state, ikke
  fabrikkerte romnavn).
- **Én reell bug funnet og rettet i backend under dette arbeidet**: ingen
  — kun frontend berørt denne økten.
- Verifisert: `npx tsc -b` (ren), `npm run lint` (oxlint, ren), `npm run
  build` (passerer), og en full visuell gjennomgang av alle 7 faner i en
  ekte headless nettleser (Playwright) på både 1600px og 1440px bredde —
  ingen konsollfeil, matcher referansebildet godt.

## Tidligere økt (økt 3 — full lærermatrise + Google-innlogging)

## Nyeste endringer (denne økten)

1. **Google OAuth er satt opp og fungerer** — ekte credentials i `backend/.env` (ikke i git). Fant og rettet to reelle bugs underveis: (a) `vite.config.ts` proxierte ikke `/auth`, kun `/api`, så innlogging hang for alltid; (b) backend brukte `request.url_for()` for redirect_uri, som ga `127.0.0.1` i stedet for `localhost` og feilet mot Google sin registrerte URI — byttet til en fast konfigurert `oauth_redirect_base_url`; (c) Starlettes `SessionMiddleware` (brukt til OAuth-state) kolliderte med appens egen cookie siden begge het "session" som standard — ga `SessionMiddleware` et eget cookienavn (`oauth_state`); (d) la til `frontend_url`-setting siden backend redirigerte til seg selv (`localhost:8123/`, 404) i stedet for til frontend (`localhost:5173`) etter innlogging i lokal utvikling.
2. **Fixture-dataene er utvidet fra et lite representativt utvalg til en FULL, realistisk timeplan** — alle 9 klasser har nå alle sine fag med lærertildeling (transkribert fra skolens lærermatrise-bilde), ikke bare de tre "vanskelige mønstrene" fra før. Solveren finner `OPTIMAL` for alle 176 økter på under ett sekund, verifisert med 0 brudd i den uavhengige validatoren.
3. **To ekte modelleringsbugs ble oppdaget og rettet** under dette arbeidet (verdt å huske, se `_decompose_hours()` i `tests/fixtures/school_example_data.py` for full forklaring):
   - En **enslig halvtimesøkt** (f.eks. Naturfag 2,5t dekomponert til 2×60min+1×30min) er strukturelt umulig å plassere, siden ingenting annet fyller den andre halvtimen i periode 2/3 samme dag.
   - Mindre åpenbart: en **90-minutters økt** (3 ticks) har samme problem — den kan bare berøre periode 2 ELLER periode 3, aldri begge, siden de to periodene bare er 30 min hver og ligger midt i formiddagsblokka. Generell regel som ble innført: **ingen økt skal noensinne ha et oddetall antall ticks**. Fikset ved å runde brøktimer opp til nærmeste hele time PER FAG, men — siden det blåser opp timetallet forbi kapasitetsgrensen (46 ticks/uke) hvis flere fag gjør dette samtidig for samme klasse — heller la ekte halvtimer stå urundet og pare seg med HVERANDRE (ikke nødvendigvis samme fag) når en klasse har et **partall** antall brøkfag; kun når antallet er oddetall rundes ett fag opp for å fikse paritet.
4. **9A Mat&Helse/Naturfag-delingen er utvidet med en "swap"-aktivitet** slik at hver halvklasse nå faktisk får sine fulle 2t Mat&Helse OG 2t Naturfag i uka (før fikk hver halvklasse bare ett av fagene — en regnefeil i det opprinnelige eksempelet, oppdaget og rettet nå).
5. Noen celler i lærermatrisen var vanskelige å lese sikkert fra skjermbildet — disse er markert med `"USIKKER: ..."` i `notes`-feltet i `NORMAL_SUBJECT_MATRIX` (søk etter "USIKKER" i `school_example_data.py`). Gjelder: 8B/8C Matte (rekkefølge lærer/timetall usikker), 8B/8C UV (utydelig celle), 10B Norsk og 10C Matte (forenklet en delt/todelt samundervisning til én co-lærer).

Fixture-fila har en oppdatert docstring som forklarer hele konvensjonen (samundervisning: rad2-timetall = hvor mange av rad1-lærerens timer som har ekstra lærer inne, IKKE et eget fag) — les den om du skal justere data videre.

## Hvor vi er

**Alle 8 faser fra planen (`domain-notes.md`) er nå bygget: v1 fungerer
end-to-end**, verifisert både med 42 automatiske tester og en faktisk
headless-nettleserøkt (Playwright) som klikket seg gjennom hele appen:
logget inn (via manuelt satt sesjonscookie, se begrensning under), listet
fag/timetall/lærere/aktiviteter, trykket "Generer timeplan", fikk
`OPTIMAL` med 16 plasserte økter, og så resultatet gjengitt korrekt i
rutenett-visningen for både en vanlig klasse (8A) og delt-klasse-mønsteret
(9A Mat&Helse/Naturfag, stablet riktig i periode 2-3 mandag+tirsdag).

Ikke et git-repo ennå — vurder `git init` + første commit nå som v1 er på
plass, før videre iterasjon. Kjør `cd backend && .venv\Scripts\python.exe -m pytest`
for å bekrefte alt er grønt (`42 passed`).

## Hva som faktisk er verifisert live (ikke bare enhetstester)

1. Backend booter, migrerer, serverer OpenAPI-schema.
2. Frontend booter, proxier `/api` OG `/auth` til backend (se
   "feil funnet og rettet" under).
3. LoginPage rendres korrekt uinnlogget, `/auth/me` gir riktig 401.
4. Med en gyldig sesjonscookie (manuelt generert, se begrensning):
   hele app-skallet med faner rendres, alle 5 sider laster uten
   konsoll-feil, "Generer timeplan"-knappen kjører en ekte solve mot
   backend og viser `OPTIMAL`/16 plassert, og timeplan-rutenettet viser
   korrekt data for flere klasser via nedtrekksmenyen.

## Feil funnet og rettet under denne verifiseringen

- **`vite.config.ts` proxierte kun `/api`, ikke `/auth`** — `/auth/me`-kallet
  fra frontend traff aldri backend, så appen sto fast på "Laster..." for
  alltid. Lagt til `/auth` i proxy-oppsettet. Dette er nøyaktig den typen
  feil som bare dukker opp når man faktisk kjører appen i en nettleser,
  ikke i enhetstester — verdt å huske for videre frontend-arbeid.

## Kjente begrensninger / bevisste forenklinger i v1

1. **Ingen ekte Google OAuth-credentials.** `/auth/login` →
   `/auth/callback`-flyten er bygget (Authlib, `.well-known`-discovery,
   e-post-sjekk mot `ALLOWED_EMAILS`, bruker-opprettelse) men ikke
   testet mot ekte Google, siden `GOOGLE_CLIENT_ID`/`SECRET` ikke er satt
   opp. **For å ta appen i bruk**: opprett et OAuth Client ID i Google
   Cloud Console (redirect URI `http://localhost:8123/auth/callback` for
   lokal bruk), legg client_id/secret + de to e-postadressene som skal ha
   tilgang inn i en `backend/.env`-fil (kopier `.env.example`).
2. **Ingen redigerings-UI for aktivitetsmatrisen ennå.** `ActivitiesPage`
   viser eksisterende aktiviteter (lest fra API), men å opprette nye
   aktiviteter (fag × klasse × lærer-mønstre, inkl. delt-klasse og
   trinnfag-mønstre) må gjøres via API/seed-script i denne versjonen — et
   ordentlig matrise-byggeverktøy i UI-et er ikke bygget.
3. **Ingen UI for lærerutilgjengelighet eller solver-innstillinger
   (vekter/preferanser)** — finnes i backend (`SolverSettings`,
   `TeacherUnavailability` + CRUD-endepunkter), men ingen side redigerer
   dem ennå.
4. **Ingen manuell justering av genererte slots** ("dra og slipp" /
   inline-redigering med revalidering) — planen nevner dette som ønsket,
   ikke bygget i v1.
5. **`SchoolYearsPage` for å opprette et nytt skoleår fra bunnen av (med
   perioder, trinn, klasser) finnes ikke** — appen forutsetter i dag at
   dataene er seedet (enten via fixture-scriptet eller manuelt via API).
   For å faktisk bruke dette for et NYTT skoleår trengs enten en slik
   side, eller et sett med seed/importer-script.

Ingen av disse er bugs — de er bevisst utelatt gitt tid/omfang, og bør
prioriteres basert på hva Lise faktisk trenger først.

## Kort oppsummering av alt som er bygget (for full detalj, se git-historikk/kode)

- **Backend** (`backend/app/`): full datamodell (16 tabeller), CRUD for
  alt, en CP-SAT-basert solver (`app/solver/`) med både harde
  constraints (lærer/klasse-no-overlap, KRØV-cap, hall-eksklusivitet
  kun for `uses_hall`, lærerutilgjengelighet, halvtimeregel,
  whole/half-gruppe-eksklusivitet) og myke preferanser (KRØV foretrekker
  1, 10.trinn KRØV foretrekker periode 3-4, Musikk unngår konsekutive
  perioder, Matte før lunsj, Mat&Helse periode 2), en uavhengig
  validator, solve-API med persistering, Excel-eksport (én fane per
  klasse), og Google OAuth-beskyttelse på alle ruter unntatt
  helsesjekk/auth-endepunktene selv.
- **Frontend** (`frontend/src/`): React+TS+Vite+Tailwind, TanStack Query,
  typer generert fra backendens OpenAPI-schema (`npx openapi-typescript`),
  auth-guard i `App.tsx`, 5 sider (fag/timetall, lærere, aktiviteter,
  generer, timeplan-rutenett).
- **42 automatiske tester**, alle grønne.

## Hvordan kjøre alt lokalt

```
cd backend
.venv\Scripts\python.exe -m pytest                  # 42 tester
.venv\Scripts\python.exe -m alembic upgrade head     # oppretter timetable.db
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8123
```

Seed med ekte eksempeldata (kjør etter migrering, mot en tom db):
```python
from app.db.base import SessionLocal
from tests.fixtures.school_example_data import seed_school_example_data
db = SessionLocal(); seed_school_example_data(db); db.close()
```

```
cd frontend
npm run dev   # http://localhost:5173
```

Uten ekte Google-credentials kan du teste det innloggede grensesnittet
ved å opprette en `User`-rad manuelt og generere en sesjonscookie med
`app.auth.session.create_session_token(email)`, sette den som cookie
`session` i nettleseren for `localhost` — se fremgangsmåten i denne
øktens Playwright-script hvis det trengs igjen.

## Naturlige neste steg (i prioritert rekkefølge, ikke i planen som "faser" lenger — dette er finpuss)

1. Sett opp ekte Google OAuth-credentials og test hele innloggingsflyten.
2. Bygg redigerings-UI for aktivitetsmatrisen (den mest komplekse, men
   også mest verdifulle gjenstående UI-biten).
3. Bygg en enkel "nytt skoleår"-oppsettside (perioder/trinn/klasser),
   eller et importerbart seed-script fra deres eksisterende Excel-ark.
4. UI for lærerutilgjengelighet og solver-vekter.
5. Manuell slot-redigering med revalidering mot `validator.py`.
6. `git init` + commit, vurder deploy (Fly.io/Render + Neon/Supabase
   Postgres per planens anbefaling).
