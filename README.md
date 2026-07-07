# Timeplanlegger

Web app for automatisk generering av ukentlig timeplan for ungdomsskolen (trinn 8-10), basert på fag/timetall, lærer-fag-tildeling og skolens skjema-regler. Se planen i `docs/domain-notes.md` for domenekrav.

## Backend (Python / FastAPI)

```
cd backend
.venv\Scripts\activate  # eller: source .venv/Scripts/activate
uvicorn app.main:app --reload --port 8123
```

Kjør migrasjoner:

```
alembic upgrade head
```

Kjør tester:

```
pytest
```

## Frontend (React / TypeScript / Vite)

```
cd frontend
npm install
npm run dev
```

Dev-serveren proxier `/api/*` til backend på port 8123 (se `vite.config.ts`).
