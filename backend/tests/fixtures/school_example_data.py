"""Real (anonymized-teacher-initials) example data from the school's own
2025/2026 timetable, used as the primary dev/test fixture. Covers:

- The full UDIR-derived weekly-hours table per subject x trinn (high
  confidence -- taken verbatim from the school's own spreadsheet).
- All 9 classes (8A-C, 9A-C, 10A-C) and the full teacher-assignment matrix
  (fag x klasse x lærer), transcribed from the school's own screenshot.
- Every subject for every class is covered (a FULL weekly timetable, not
  just a representative subset), using this modeling convention agreed
  with the user: where a subject has two teacher-rows (e.g. "Matte" +
  "Matte 2"), row 1's hours are the subject's total weekly hours for that
  class, and row 2's hours are how many of those are CO-TAUGHT (a second
  teacher present) -- same mechanism as Norsk. Two teachers are only
  modeled as a SPLIT_PARALLEL (half-class) group where the source
  explicitly said so (Mat&Helse/Naturfag for 9A).

TRANSCRIPTION CONFIDENCE: most cells are high-confidence (row 1's hours
match the official subject-hour table exactly). A handful of cells were
genuinely hard to read in the source screenshot or had numbers that don't
cleanly fit the row1=total/row2=co-taught pattern; those are marked with
notes containing "USIKKER" (uncertain) so they're easy to find and correct
against the school's real spreadsheet later. Some fractional co-teaching
splits (e.g. a subject co-taught by two DIFFERENT partial-hour teachers)
were simplified to a single co-teacher for the clearer portion.
"""

from datetime import time

from sqlalchemy.orm import Session

from app.db.models.activity import Activity, ActivityLeg, ActivityLegTeacher, ActivityType
from app.db.models.period import DayOfWeek, PeriodDefinition
from app.db.models.school_year import SchoolYear
from app.db.models.solver_settings import SolverSettings
from app.db.models.subject import Subject, SubjectHourAllocation
from app.db.models.teacher import Teacher
from app.db.models.trinn_class import ClassGroup, SchoolClass, Trinn

# (name, short_code, weekly_hours for trinn 8, 9, 10 -- None if not taught that year)
SUBJECT_HOUR_TABLE: list[tuple[str, str, float | None, float | None, float | None]] = [
    ("Norsk", "NO", 4.0, 3.5, 3.0),
    ("Matematikk", "MA", 3.0, 3.0, 3.0),
    ("Engelsk", "EN", 2.0, 2.0, 2.0),
    ("Utdanningsvalg", "UV", 1.0, 1.0, 0.5),
    ("Naturfag", "NAT", 2.5, 2.0, 2.0),
    ("Samfunnsfag", "SAM", 2.0, 2.5, 2.0),
    ("KRLE", "KRLE", 1.0, 1.5, 1.5),
    ("Kroppsoving", "KROV", 2.0, 2.0, 1.5),
    ("Fremmedspraak", "SPRAK", 2.0, 2.0, 2.0),
    ("Valgfag", "VALG", 1.5, 1.5, 1.5),
    ("Musikk", "MUS", None, None, 2.0),
    ("Kunst og handverk", "KH", 2.0, None, 2.0),
    ("Mat og helse", "MH", None, 2.0, None),
]

TEACHER_INITIALS = [
    "GB", "EB", "LEN", "KE", "MWJ", "ANW", "NO", "TSS", "LH", "AS", "BTS",
    "EHK", "AB", "AT", "TL", "MC", "TS", "ER", "KA", "ADI", "TC", "EG",
]

# Mon/Wed/Thu/Fri: 6 periods, periods 2+3 are 30-min and independently
# splittable (or combinable into one 60-min session). Tuesday is a short
# day: only periods 1-4, same period-2/3 halving.
_FULL_DAY_PERIODS = [
    (1, time(8, 30), time(9, 30), False),
    (2, time(9, 30), time(10, 0), True),
    (3, time(10, 10), time(10, 40), True),
    (4, time(10, 40), time(11, 40), False),
    (5, time(12, 20), time(13, 20), False),
    (6, time(13, 30), time(14, 30), False),
]
_SHORT_DAY_PERIODS = _FULL_DAY_PERIODS[:4]

# --- Full teacher-assignment matrix (row1 = total hours, row2 = co-taught
# subset of those hours, per the agreed convention). Format per entry:
# class_name: {subject_code: (primary_teacher, total_hours, co_teacher_or_None, co_hours, notes_or_None)}
NORMAL_SUBJECT_MATRIX: dict[str, dict[str, tuple[str, float, str | None, float, str | None]]] = {
    "8A": {
        "MA": ("NO", 3.0, "ANW", 2.0, None),
        "EN": ("MWJ", 2.0, "LEN", 2.0, None),
        "UV": ("GB", 1.0, None, 0, None),
        "NAT": ("NO", 2.5, None, 0, None),
        "SAM": ("MWJ", 2.0, None, 0, None),
        "KRLE": ("GB", 1.0, None, 0, None),
        "KROV": ("EG", 2.0, None, 0, None),
        "KH": ("KE", 2.0, None, 0, None),
    },
    "8B": {
        "MA": ("NO", 3.0, "ANW", 2.0, "USIKKER: rekkefølge lærer/timetall i kilden ga ikke opplagt totalsum, byttet om"),
        "EN": ("LEN", 2.0, "MWJ", 2.0, None),
        "UV": ("ANW", 1.0, None, 0, "USIKKER: celle vanskelig å lese i kilden (ANW/LEN(0,...)"),
        "NAT": ("ANW", 2.5, None, 0, None),
        "SAM": ("LEN", 2.0, None, 0, None),
        "KRLE": ("GB", 1.0, None, 0, None),
        "KROV": ("GB", 2.0, None, 0, None),
        "KH": ("KE", 2.0, None, 0, None),
    },
    "8C": {
        "MA": ("ANW", 3.0, "NO", 2.0, "USIKKER: rekkefølge lærer/timetall i kilden ga ikke opplagt totalsum, byttet om"),
        "EN": ("LEN", 2.0, "MWJ", 2.0, None),
        "UV": ("EB", 1.0, None, 0, "USIKKER: celle vanskelig å lese i kilden (EB(1)/KE)"),
        "NAT": ("ANW", 2.5, None, 0, None),
        "SAM": ("LEN", 2.0, None, 0, None),
        "KRLE": ("EB", 1.0, None, 0, None),
        "KROV": ("GB", 2.0, None, 0, None),
        "KH": ("KE", 2.0, None, 0, None),
    },
    "9A": {
        "MA": ("EHK", 3.0, "BTS", 2.0, None),
        "EN": ("AS", 2.0, "KA", 1.0, None),
        "UV": ("EHK", 1.0, None, 0, None),
        "SAM": ("AS", 2.5, None, 0, None),
        "KRLE": ("TSS", 1.5, None, 0, None),
        "KROV": ("MC", 2.0, None, 0, None),
        # NB: no plain NAT entry here -- 9A's Naturfag hours are delivered
        # via the split-parallel pattern below (shared slot with M&H).
    },
    "9B": {
        "MA": ("EHK", 3.0, "BTS", 2.0, None),
        "EN": ("KA", 2.0, "AS", 1.0, None),
        "UV": ("LH", 1.0, None, 0, None),
        "NAT": ("EHK", 2.0, "ANW", 1.0, None),
        "SAM": ("TSS", 2.5, None, 0, None),
        "KRLE": ("LH", 1.5, None, 0, None),
        "KROV": ("ADI", 2.0, None, 0, None),
    },
    "9C": {
        "MA": ("BTS", 3.0, "EHK", 2.0, None),
        "EN": ("AS", 2.0, "KA", 1.0, None),
        "UV": ("AS", 1.0, None, 0, None),
        "NAT": ("BTS", 2.0, "EHK", 1.0, None),
        "SAM": ("AS", 2.5, None, 0, None),
        "KRLE": ("AS", 1.5, None, 0, None),
        "KROV": ("MC", 2.0, None, 0, None),
    },
    "10A": {
        "NO": ("AB", 3.0, "AT", 2.0, None),
        "MA": ("MC", 3.0, "TS", 2.5, None),
        "EN": ("MWJ", 2.0, "TC", 1.0, None),
        "UV": ("AB", 0.5, None, 0, None),
        "NAT": ("MC", 2.0, "TS", 1.0, None),
        "SAM": ("AB", 2.0, None, 0, None),
        "KRLE": ("MWJ", 1.5, None, 0, None),
        "KROV": ("TS", 1.5, None, 0, None),
        "MUS": ("ER", 2.0, None, 0, None),
        "KH": ("KE", 2.0, None, 0, None),
    },
    "10B": {
        "NO": ("AT", 3.0, "TL", 1.5, "USIKKER: kilden viste en delt samundervisning TL(1,5)+AB(0,5), forenklet til TL(1,5)"),
        "MA": ("MC", 3.0, "TS", 2.0, None),
        "EN": ("TC", 2.0, "MWJ", 1.0, None),
        "UV": ("AB", 0.5, None, 0, None),
        "NAT": ("MC", 2.0, "TS", 1.0, None),
        "SAM": ("AT", 2.0, None, 0, None),
        "KRLE": ("TL", 1.5, None, 0, None),
        "KROV": ("TS", 1.5, None, 0, None),
        "MUS": ("ER", 2.0, None, 0, None),
        "KH": ("KE", 2.0, None, 0, None),
    },
    "10C": {
        "NO": ("TL", 3.0, "AB", 2.0, None),
        "MA": ("TS", 3.0, "MC", 1.5, "USIKKER: kilden viste MC(1,5)+TL(1) samtidig, forenklet til MC(1,5)"),
        "EN": ("TC", 2.0, "MWJ", 1.0, None),
        "UV": ("TL", 0.5, None, 0, None),
        "NAT": ("MC", 2.0, "TS", 1.0, None),
        "SAM": ("AT", 2.0, None, 0, None),
        "KRLE": ("TL", 1.5, None, 0, None),
        "KROV": ("TS", 1.5, None, 0, None),
        "MUS": ("ER", 2.0, None, 0, None),
        "KH": ("KE", 2.0, None, 0, None),
    },
}

# Trinnfag: (subject_code, [(class_or_None, teacher), ...]) per trinn.
# Fremmedspraak and Valgfag both regroup students trinn-wide -- see
# ActivityLeg docstring for why a 4th group can have class_group=None.
TRINNFAG_MATRIX: dict[int, list[tuple[str, list[tuple[str | None, str]]]]] = {
    8: [
        ("SPRAK", [("8A", "AB"), ("8B", "KA"), ("8C", "ER"), (None, "MWJ")]),
        ("VALG", [("8A", "KE"), ("8B", "ANW"), ("8C", "TSS")]),
    ],
    9: [
        ("SPRAK", [("9A", "LH"), ("9B", "KA"), ("9C", "ER"), (None, "AS")]),
        ("VALG", [("9A", "TSS"), ("9B", "AS"), ("9C", "EHK")]),
    ],
    10: [
        ("SPRAK", [("10A", "AB"), ("10B", "KA"), ("10C", "ER"), (None, "TC")]),
        ("VALG", [("10A", "TS"), ("10B", "AS"), ("10C", "AT"), (None, "ER")]),
    ],
}


def _decompose_hours(total_hours: float, co_hours: float = 0.0, keep_half: bool = False) -> list[tuple[int, bool]]:
    """Splits total_hours into a list of (duration_ticks, is_co_taught)
    sessions, in 60-min (2-tick) chunks plus at most one 30-min (1-tick)
    remainder.

    A lone 30-min session (or any other ODD tick-count, e.g. a 90-min
    session spanning period 1+2 or 3+4) can only ever touch ONE of period
    2/period 3 -- never both, never neither, since those are the only two
    splittable (30-min) periods and sit back-to-back mid-week. That's
    structurally infeasible under the half-hour adjacency rule (see
    app/solver/model_builder.py) *unless* something else independently
    fills the other half on the same day.

    So: by default (keep_half=False) a .5h remainder is rounded up to a
    full hour, to guarantee this subject alone can never strand a half
    hour. But rounding up EVERY fractional subject in a class inflates
    that class's total weekly hours past the official total (and past
    the school's actual tick capacity) once several subjects have .5h
    remainders. The caller is expected to instead set keep_half=True for
    all but one of a class's fractional subjects (see
    seed_school_example_data), so their genuine 30-min remainders can
    pair with EACH OTHER on the same day -- any two independent 1-tick
    sessions for the same class satisfy the adjacency rule together, it
    doesn't have to be the same subject on both sides.
    """
    total_ticks = round(total_hours * 2)
    if total_ticks <= 0:
        return []
    has_half = total_ticks % 2 == 1
    if has_half and not keep_half:
        total_ticks += 1  # round up -- see docstring

    co_ticks = round(co_hours * 2)
    sessions: list[tuple[int, bool]] = []
    while total_ticks >= 2:
        is_co = co_ticks >= 2
        sessions.append((2, is_co))
        total_ticks -= 2
        if is_co:
            co_ticks -= 2
    if total_ticks == 1:
        sessions.append((1, co_ticks >= 1))
    return sessions


def seed_school_example_data(db: Session) -> dict:
    school_year = SchoolYear(label="2025/2026")
    db.add(school_year)
    db.flush()

    for day, periods in [
        (DayOfWeek.MON, _FULL_DAY_PERIODS),
        (DayOfWeek.TUE, _SHORT_DAY_PERIODS),
        (DayOfWeek.WED, _FULL_DAY_PERIODS),
        (DayOfWeek.THU, _FULL_DAY_PERIODS),
        (DayOfWeek.FRI, _FULL_DAY_PERIODS),
    ]:
        for number, start, end, splittable in periods:
            db.add(
                PeriodDefinition(
                    school_year_id=school_year.id,
                    day_of_week=day,
                    period_number=number,
                    start_time=start,
                    end_time=end,
                    is_splittable=splittable,
                    is_before_lunch=number <= 4,
                )
            )

    trinn_by_level = {}
    for level in (8, 9, 10):
        t = Trinn(school_year_id=school_year.id, level=level)
        db.add(t)
        db.flush()
        trinn_by_level[level] = t

    classes = {}
    class_groups = {}
    class_to_level = {}
    for level, names in ((8, ["8A", "8B", "8C"]), (9, ["9A", "9B", "9C"]), (10, ["10A", "10B", "10C"])):
        for name in names:
            c = SchoolClass(trinn_id=trinn_by_level[level].id, name=name)
            db.add(c)
            db.flush()
            classes[name] = c
            class_to_level[name] = level
            whole = ClassGroup(school_class_id=c.id, label="whole")
            db.add(whole)
            db.flush()
            class_groups[f"{name}-whole"] = whole

    # 9A additionally needs half-groups for the Mat&Helse/Naturfag split.
    for label in ("half1", "half2"):
        g = ClassGroup(school_class_id=classes["9A"].id, label=label)
        db.add(g)
        db.flush()
        class_groups[f"9A-{label}"] = g

    teachers = {}
    for initials in TEACHER_INITIALS:
        t = Teacher(initials=initials, full_name=initials)
        db.add(t)
        db.flush()
        teachers[initials] = t

    subjects = {}
    for name, short_code, h8, h9, h10 in SUBJECT_HOUR_TABLE:
        subj = Subject(
            school_year_id=school_year.id,
            name=name,
            short_code=short_code,
            is_trinnfag=short_code in ("SPRAK", "VALG"),
            is_krov=short_code == "KROV",
            uses_hall=short_code == "VALG",  # Valgfag uses the hall; Fremmedspraak does not.
            avoid_consecutive=short_code == "MUS",
            prefer_before_lunch=short_code == "MA",
            needs_consecutive_periods=short_code in ("MH", "KH"),
        )
        db.add(subj)
        db.flush()
        subjects[short_code] = subj

        for level, hours in ((8, h8), (9, h9), (10, h10)):
            if hours is not None:
                db.add(
                    SubjectHourAllocation(
                        subject_id=subj.id, trinn_id=trinn_by_level[level].id, weekly_hours=hours
                    )
                )

    db.add(SolverSettings(school_year_id=school_year.id))

    def add_activity(
        activity_type: ActivityType,
        duration_ticks: int,
        occurrences_per_week: int,
        legs: list[tuple[str | None, str, list[str]]],
        notes: str,
    ) -> Activity:
        """legs: list of (class_group_key_or_None, subject_short_code, [teacher_initials])"""
        activity = Activity(
            school_year_id=school_year.id,
            activity_type=activity_type,
            duration_ticks=duration_ticks,
            occurrences_per_week=occurrences_per_week,
            notes=notes,
        )
        db.add(activity)
        db.flush()
        for class_group_key, subject_code, teacher_list in legs:
            leg = ActivityLeg(
                activity_id=activity.id,
                class_group_id=class_groups[class_group_key].id if class_group_key else None,
                subject_id=subjects[subject_code].id,
            )
            db.add(leg)
            db.flush()
            for initials in teacher_list:
                db.add(ActivityLegTeacher(activity_leg_id=leg.id, teacher_id=teachers[initials].id))
        return activity

    # --- Co-teaching pattern: Norsk 8A/8B/8C, co-taught most sessions, one
    # teacher solo for the remainder (see docs/domain-notes.md). Kept as
    # explicit named activities (rather than folded into
    # NORMAL_SUBJECT_MATRIX) since existing tests assert on these notes. ---
    for class_name, co_teachers, solo_teacher in (
        ("8A", ["GB", "EB"], "GB"),
        ("8B", ["LEN", "GB"], "LEN"),
        ("8C", ["EB", "KE"], "EB"),
    ):
        add_activity(
            ActivityType.NORMAL,
            duration_ticks=2,  # 60 min
            occurrences_per_week=3,
            legs=[(f"{class_name}-whole", "NO", co_teachers)],
            notes=f"{class_name} Norsk co-taught",
        )
        add_activity(
            ActivityType.NORMAL,
            duration_ticks=2,  # 60 min
            occurrences_per_week=1,
            legs=[(f"{class_name}-whole", "NO", [solo_teacher])],
            notes=f"{class_name} Norsk solo",
        )

    # --- Split-class parallel pattern: half of 9A does Mat&Helse while the
    # other half does Naturfag, then the groups swap -- each half-group
    # ends up with the full 2h M&H + 2h Naturfag over the week, not just
    # one subject each. ---
    add_activity(
        ActivityType.SPLIT_PARALLEL,
        duration_ticks=2,  # 60 min
        occurrences_per_week=2,
        legs=[
            ("9A-half1", "MH", ["BTS"]),
            ("9A-half2", "NAT", ["EHK"]),
        ],
        notes="9A Mat&Helse / Naturfag split",
    )
    add_activity(
        ActivityType.SPLIT_PARALLEL,
        duration_ticks=2,  # 60 min
        occurrences_per_week=2,
        legs=[
            ("9A-half1", "NAT", ["EHK"]),
            ("9A-half2", "MH", ["BTS"]),
        ],
        notes="9A Naturfag / Mat&Helse split (swap)",
    )

    # --- Remaining ordinary subjects for every class, from
    # NORMAL_SUBJECT_MATRIX, using the agreed co-teaching decomposition.
    # Fractional (.5h) subjects keep their genuine 30-min remainder rather
    # than each independently rounding up (which would inflate a class's
    # total hours past its weekly tick capacity) -- but keeping an ODD
    # number of them per class would leave one unpairable, so if a class
    # has an odd count of fractional subjects, exactly one (deterministic,
    # first by subject code) is rounded up instead; the rest pair with
    # each other via the solver's half-hour adjacency rule. ---
    for class_name, subject_map in NORMAL_SUBJECT_MATRIX.items():
        fractional_subjects = sorted(
            code for code, (_, hours, _, _, _) in subject_map.items() if round(hours * 2) % 2 == 1
        )
        round_up_subject = fractional_subjects[0] if len(fractional_subjects) % 2 == 1 else None

        for subject_code, (primary, total_hours, co_teacher, co_hours, note) in subject_map.items():
            keep_half = subject_code in fractional_subjects and subject_code != round_up_subject
            sessions = _decompose_hours(total_hours, co_hours, keep_half=keep_half)
            for duration_ticks, is_co in sessions:
                teacher_list = [primary, co_teacher] if (is_co and co_teacher) else [primary]
                base_note = f"{class_name} {subject_code} ({'co' if is_co else 'solo'})"
                add_activity(
                    ActivityType.NORMAL,
                    duration_ticks=duration_ticks,
                    occurrences_per_week=1,
                    legs=[(f"{class_name}-whole", subject_code, teacher_list)],
                    notes=f"{base_note} [{note}]" if note else base_note,
                )

    # --- Trinnfag pattern: Valgfag and Fremmedspraak for all three trinn,
    # blocking all home classes at once as parallel teacher-led groups. 10th
    # trinn Fremmedspraak additionally gets a fixed placement (Wed periods
    # 5-6) resolved by the solver via SolverSettings, not here. ---
    for level, entries in TRINNFAG_MATRIX.items():
        class_names = {8: ["8A", "8B", "8C"], 9: ["9A", "9B", "9C"], 10: ["10A", "10B", "10C"]}[level]
        for subject_code, group_assignments in entries:
            is_fixed_10th_sprak = level == 10 and subject_code == "SPRAK"
            duration = 4 if is_fixed_10th_sprak else 2  # 10th Fremmedspraak = 2h block; others 1h
            legs = [
                (f"{cls}-whole" if cls else None, subject_code, [teacher])
                for cls, teacher in group_assignments
            ]
            label = "Fremmedspraak" if subject_code == "SPRAK" else "Valgfag"
            suffix = " (fixed: Wed periods 5-6)" if is_fixed_10th_sprak else ""
            add_activity(
                ActivityType.TRINNFAG,
                duration_ticks=duration,
                occurrences_per_week=1,
                legs=legs,
                notes=f"{level}th trinn {label}{suffix}",
            )

    db.commit()

    return {
        "school_year": school_year,
        "trinn_by_level": trinn_by_level,
        "classes": classes,
        "class_groups": class_groups,
        "teachers": teachers,
        "subjects": subjects,
    }
