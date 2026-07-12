---
name: school-import
description: Turn a free-form description of a school's timetable setup (a subject-hour table, a teacher-assignment matrix, a class list, period/bell-schedule notes -- e.g. a forwarded email or a transcribed screenshot) into a JSON file matching backend/app/schemas/import_.py's SchoolImport schema, ready to upload via the app's "Importer fra fil" button. Use when a developer or technical colleague needs to bulk-onboard a new school's data into a fresh zone. Ask clarifying questions wherever the source material is ambiguous or incomplete rather than guessing silently.
---

# School Import

## Who this is for

This skill produces a JSON **file**. It does not call the API itself and
does not edit any existing zone's data. It is meant to be invoked by a
developer or technical colleague relaying a school's description on their
behalf — **never by the non-technical school staff themselves** (they
describe their school by email/conversation; they don't touch this skill
or the JSON directly). Write all output messages (summaries, clarifying
questions) for that technical operator, not for the end user.

## Step 0 — always re-read the schema first

Before writing any JSON, read `backend/app/schemas/import_.py` in full. It
is the single source of truth for field names/types/defaults; the shape
described below may have drifted since this skill file was last updated.
If anything here disagrees with that file, the file wins.

## Step 1 — gather the source material

Ask the operator for the raw description if it hasn't been pasted yet
(an email, a transcribed spreadsheet/screenshot, a written summary). Read
it carefully before extracting anything. If it's incomplete in an
important way, say so immediately rather than partway through.

## Step 2 — extract, in this order

1. **Bell schedule / periods.** Days the school has lessons, period
   numbers, start/end times, which periods are splittable into two 30-min
   sessions, which are before lunch. **If this is entirely unstated, stop
   and ask** — never invent bell times, they're foundational and this
   school's own schedule may look nothing like any other school's.

2. **Trinn (grade levels) and classes.** Which levels exist, which named
   classes each has (e.g. "8A", "9A"), and whether any class is ever split
   into simultaneous halves for a subject (e.g. half the class does one
   subject while the other half does another, at the same time) — those
   need an `extra_groups` entry (e.g. `["half1", "half2"]`); a class that's
   never split needs no `extra_groups` at all (the `"whole"` group is
   automatic).

3. **Teacher roster.** Initials + full name for every teacher who appears
   anywhere in the assignment matrix. If only initials are given, ask for
   full names; if genuinely unavailable, use the initials as a placeholder
   `full_name` and add a note in your final summary like
   `USIKKER: fullt navn ukjent for XY, bruker forbokstaver` — the same
   uncertainty-flagging convention already used in this project's example
   fixture (`backend/tests/fixtures/school_example_data.py`, search for
   `"USIKKER"`).

4. **Subjects + weekly-hour table per trinn.** The UDIR-style table:
   subject name, short code, and weekly hours per trinn level. Also decide
   the boolean flags per subject:
   - `is_krov`: true for kroppsøving/gym.
   - `uses_hall`: true only for subjects that physically occupy the
     school's hall/gym space (this is usually **not** the same set as
     `is_trinnfag` — e.g. a whole-grade valgfag block typically uses the
     hall, a whole-grade fremmedspråk block typically does not, even
     though both are trinnfag). If the source doesn't say, **ask** — this
     genuinely isn't guessable from the subject name alone.
   - `is_trinnfag`: true for subjects taught as a whole-grade block across
     parallel groups (valgfag, fremmedspråk) rather than per-class.
   - `avoid_consecutive` / `prefer_before_lunch` / `needs_consecutive_periods`:
     only set these if the source actually states a preference (e.g.
     "musikk skal ikke ligge to timer på rad", "mat og helse trenger
     sammenhengende dobbelttime") — don't invent them for subjects the
     source doesn't mention a preference for.

5. **Activities, from the teacher-assignment matrix.** This is the trickiest
   part. Apply these patterns exactly:

   - **Co-teaching** (a class's subject has a primary teacher, with a
     second teacher present for some but not all sessions): create **two**
     `NORMAL` activities for that class+subject — one with both teachers'
     initials in `teacher_initials` and the co-taught occurrence count in
     `occurrences_per_week`, one with just the primary teacher and the
     remaining solo occurrence count. This is the preferred, clean form
     when every occurrence has the same duration (matches how the app's
     own manual "Ny aktivitet" form works, and how this project's
     hand-authored example activities are written — see the `"8A Norsk
     co-taught"` / `"8A Norsk solo"` pair in `school_example_data.py`).
     **Do not** put multiple sessions of the same class+subject as
     multiple legs on one activity — a `NORMAL` activity always has
     exactly one leg; different occurrence-counts/teacher-lists become
     separate activities, never separate legs.
     - *Alternative, also valid*: if a subject's weekly hours don't split
       evenly into same-shape chunks (e.g. a genuine odd 30-minute
       remainder that doesn't repeat every week the same way), it's fine
       to instead emit one `NORMAL` activity per individual session, each
       with `occurrences_per_week: 1` — `school_example_data.py`'s own
       generic decomposition path does exactly this for ordinary subjects.
       Prefer the merged form (fewer, clearer activities) whenever the
       sessions are genuinely identical in shape.
     - **Never invent a 30-minute remainder if the source doesn't
       genuinely have one.** If total weekly hours are a whole number,
       every session should already be 60 minutes.

   - **Split-parallel** (two different subjects taught to two halves of
     one class at the same time, explicitly stated as simultaneous in the
     source): one `SPLIT_PARALLEL` activity, exactly two legs, one
     `class_ref` per half (e.g. `"9A:half1"` and `"9A:half2"`). If the
     halves swap subjects on a different day of the week, that's a
     **second**, separate `SPLIT_PARALLEL` activity with the legs'
     subjects/teachers reversed — not one activity trying to express both.
     **Only use this pattern when the source explicitly says the class is
     split into simultaneous halves.** Two teachers merely appearing near
     each other in a table is co-teaching (see above), not this.

   - **Trinnfag** (a whole-grade block — valgfag, fremmedspråk — running as
     N parallel groups across the trinn's classes): one `TRINNFAG`
     activity, one leg per parallel group, `class_ref` set to whichever
     home class that group corresponds to. If the number of parallel
     groups is **greater** than the number of classes in that trinn, the
     extra group(s) get `class_ref: null` (they occupy only their
     teacher(s), not a home class — those students are already accounted
     for by their home-class leg elsewhere in the same activity... no —
     more precisely: every student in the trinn is covered by exactly one
     leg's `class_ref`, and any leg beyond the number of home classes is
     an overflow *teacher* group with no class attached).

   - `duration_minutes` must be a multiple of 30. Prefer 60/90/120-minute
     round sessions; a lone 30- or 90-minute session is technically
     allowed (the import endpoint accepts it with a warning) but genuinely
     may not be placeable by the solver unless another subject
     independently has a matching half-hour session on the same day — flag
     this to the operator rather than silently emitting one.

## Step 3 — when to stop and ask vs. proceed with a noted assumption

**Always stop and ask:**
- Bell schedule / periods entirely unstated.
- A cell's teacher or hours is illegible or internally contradictory
  (e.g. per-session hours don't sum to the subject's stated weekly total).
- Whether a subject is trinnfag and/or uses the hall isn't statable from
  the source context — this is a real fact about the school, not something
  to guess from the subject name.
- Whether two teachers near each other in the matrix means co-teaching or
  a simultaneous split — if genuinely unclear, ask rather than picking one.

**Proceed, but add a `USIKKER: ...` line in your final summary:**
- Minor, clearly-flagged gaps with a defensible default — e.g. guessing
  `is_before_lunch` from the period number when the source doesn't say
  explicitly, or a single hard-to-read cell where the overall shape of the
  data is clear but one digit is ambiguous.

This mirrors the exact convention already used in
`backend/tests/fixtures/school_example_data.py` (search for `"USIKKER"`)
— small, flagged uncertainty is fine; silent, unflagged guessing is not.

## Step 4 — self-check before finishing

Before writing the file, verify:
- Every `subject_code` used anywhere in `activities` appears in `subjects`.
- Every `class_ref` (both the class-name part and, if present, the group
  label after `:`) resolves to a class/group actually declared in `trinn`.
- Every `teacher_initials` entry used in `activities` appears in `teachers`.
- Every `hour_allocations[*].trinn_level` matches a level declared in `trinn`.
- No duplicate class `name` values across the *entire* payload (class
  names must be globally unique, not just unique within their trinn —
  this is a real v1 limitation of the import format, not a schema bug).
- No `leg_count` mismatches: `NORMAL` = exactly 1 leg, `SPLIT_PARALLEL` =
  exactly 2 legs, `TRINNFAG` = at least 1 leg.
- No `duration_minutes` that isn't a positive multiple of 30.

The import endpoint re-validates all of this and returns every problem it
finds at once (not just the first), so a mistake here isn't catastrophic —
but catching it up front saves an upload/fix round-trip.

## Step 5 — output

Write the JSON to an `imports/` directory at the repository root (create
it if it doesn't exist). Name the file `<school-year-label-slugified>-import.json`
(e.g. `2026-2027-import.json`). Check whether `.gitignore` already excludes
`imports/`; if not, add an `imports/` entry — these files contain real
people's names and initials and should not be committed.

Finish with a message to the operator containing, in this order:
1. The file's path.
2. A one-line count summary per section (trinn/classes/teachers/subjects/activities).
3. Every open clarifying question you had to raise (if any) — these mean
   the file is incomplete and shouldn't be uploaded yet until answered.
4. Every `USIKKER: ...` note you inserted, so they're easy to find and
   correct against the source before uploading.
5. The exact next step: upload the file via the "Importer fra fil" button
   (the upload icon next to "+" in the top bar, or the button shown on an
   empty zone's "Ingen skoleår funnet ennå" screen).
