from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_zone_header
from app.db.models.activity import Activity, ActivityLeg, ActivityLegTeacher
from app.db.models.period import PeriodDefinition
from app.db.models.school_year import SchoolYear
from app.db.models.subject import Subject, SubjectHourAllocation
from app.db.models.teacher import Teacher
from app.db.models.trinn_class import ClassGroup, Trinn
from app.db.models.zone import ZoneMembership
from app.domain.activity_rules import leg_count_error
from app.schemas.import_ import ImportIssue, ImportResultRead, SchoolImport
from app.services.school_structure import create_class_with_whole_group

router = APIRouter(prefix="/api", tags=["import"])


def _parse_class_ref(class_ref: str) -> tuple[str, str]:
    """"9A" -> ("9A", "whole"); "9A:half1" -> ("9A", "half1")."""
    if ":" in class_ref:
        name, label = class_ref.split(":", 1)
        return name, label
    return class_ref, "whole"


@router.post("/import/school", response_model=ImportResultRead, status_code=201)
def import_school(
    payload: SchoolImport,
    db: Session = Depends(get_db),
    membership: ZoneMembership = Depends(require_zone_header),
):
    errors: list[ImportIssue] = []
    warnings: list[ImportIssue] = []

    # --- Phase 1: pure payload-internal validation, no DB access ----------

    trinn_levels = [t.level for t in payload.trinn]
    if len(trinn_levels) != len(set(trinn_levels)):
        errors.append(ImportIssue(path="trinn", message="Duplikate trinn-nivåer i nyttelasten."))
    trinn_level_set = set(trinn_levels)

    class_labels_by_name: dict[str, set[str]] = {}
    all_class_names: set[str] = set()
    for t_idx, trinn in enumerate(payload.trinn):
        for c_idx, klass in enumerate(trinn.classes):
            path = f"trinn[{t_idx}].classes[{c_idx}]"
            if klass.name in all_class_names:
                errors.append(
                    ImportIssue(path=path, message=f"Klassenavn '{klass.name}' er brukt flere ganger i nyttelasten.")
                )
            all_class_names.add(klass.name)

            labels = ["whole", *klass.extra_groups]
            if len(labels) != len(set(labels)):
                errors.append(
                    ImportIssue(
                        path=f"{path}.extra_groups",
                        message=(
                            f"Duplikate eller reserverte gruppenavn for klasse '{klass.name}' "
                            "(ikke oppgi 'whole' selv, den lages automatisk)."
                        ),
                    )
                )
            class_labels_by_name[klass.name] = set(labels)

    teacher_initials_list = [t.initials for t in payload.teachers]
    if len(teacher_initials_list) != len(set(teacher_initials_list)):
        errors.append(ImportIssue(path="teachers", message="Duplikate lærerinitialer i nyttelasten."))
    teacher_initials_set = set(teacher_initials_list)

    subject_code_list = [s.short_code for s in payload.subjects]
    if len(subject_code_list) != len(set(subject_code_list)):
        errors.append(ImportIssue(path="subjects", message="Duplikate fagkoder i nyttelasten."))
    subject_code_set = set(subject_code_list)

    for s_idx, subject in enumerate(payload.subjects):
        seen_levels: set[int] = set()
        for h_idx, alloc in enumerate(subject.hour_allocations):
            path = f"subjects[{s_idx}].hour_allocations[{h_idx}]"
            if alloc.trinn_level not in trinn_level_set:
                errors.append(
                    ImportIssue(path=path, message=f"Trinn-nivå {alloc.trinn_level} finnes ikke i 'trinn'-listen.")
                )
            if alloc.trinn_level in seen_levels:
                errors.append(
                    ImportIssue(path=path, message=f"Trinn-nivå {alloc.trinn_level} er oppgitt flere ganger.")
                )
            seen_levels.add(alloc.trinn_level)

    for a_idx, activity in enumerate(payload.activities):
        path = f"activities[{a_idx}]"
        leg_error = leg_count_error(activity.activity_type, len(activity.legs))
        if leg_error is not None:
            errors.append(ImportIssue(path=path, message=leg_error))

        if activity.duration_minutes <= 0 or activity.duration_minutes % 30 != 0:
            errors.append(ImportIssue(path=path, message="duration_minutes må være et positivt multiplum av 30."))
        elif (activity.duration_minutes // 30) % 2 != 0:
            warnings.append(
                ImportIssue(
                    path=path,
                    message=(
                        "Varigheten er et oddetall antall halvtimer (30/90/... min). En enslig halvtime kan bli "
                        "umulig å plassere med mindre en annen aktivitet fyller den andre halvtimen i samme "
                        "periode samme dag."
                    ),
                )
            )

        for l_idx, leg in enumerate(activity.legs):
            leg_path = f"{path}.legs[{l_idx}]"
            if leg.subject_code not in subject_code_set:
                errors.append(
                    ImportIssue(path=leg_path, message=f"Fagkode '{leg.subject_code}' finnes ikke i 'subjects'-listen.")
                )
            if leg.class_ref is not None:
                name, label = _parse_class_ref(leg.class_ref)
                if name not in class_labels_by_name:
                    errors.append(ImportIssue(path=leg_path, message=f"Klasse '{name}' finnes ikke."))
                elif label not in class_labels_by_name[name]:
                    errors.append(
                        ImportIssue(path=leg_path, message=f"Gruppe '{label}' finnes ikke for klasse '{name}'.")
                    )
            for initials in leg.teacher_initials:
                if initials not in teacher_initials_set:
                    errors.append(
                        ImportIssue(path=leg_path, message=f"Lærerinitialer '{initials}' finnes ikke i 'teachers'-listen.")
                    )

    # --- Phase 2: one DB-dependent pre-check --------------------------------
    existing_year = db.scalars(
        select(SchoolYear).where(
            SchoolYear.zone_id == membership.zone_id, SchoolYear.label == payload.school_year_label
        )
    ).first()
    if existing_year is not None:
        errors.append(
            ImportIssue(
                path="school_year_label",
                message=f"Et skoleår med navnet '{payload.school_year_label}' finnes allerede i denne sonen.",
            )
        )

    if errors:
        raise HTTPException(
            422,
            detail={
                "errors": [e.model_dump() for e in errors],
                "warnings": [w.model_dump() for w in warnings],
            },
        )

    # --- Phase 3: creation (only reached with zero errors) ------------------
    school_year = SchoolYear(zone_id=membership.zone_id, label=payload.school_year_label)
    db.add(school_year)
    db.flush()

    for p in payload.periods:
        db.add(PeriodDefinition(school_year_id=school_year.id, **p.model_dump()))

    trinn_by_level: dict[int, Trinn] = {}
    class_group_by_ref: dict[tuple[str, str], int] = {}
    for trinn_import in payload.trinn:
        trinn = Trinn(school_year_id=school_year.id, level=trinn_import.level)
        db.add(trinn)
        db.flush()
        trinn_by_level[trinn_import.level] = trinn

        for klass in trinn_import.classes:
            school_class, whole_group = create_class_with_whole_group(db, trinn.id, klass.name)
            class_group_by_ref[(klass.name, "whole")] = whole_group.id
            for label in klass.extra_groups:
                group = ClassGroup(school_class_id=school_class.id, label=label)
                db.add(group)
                db.flush()
                class_group_by_ref[(klass.name, label)] = group.id

    teacher_by_initials: dict[str, Teacher] = {}
    for t in payload.teachers:
        existing_teacher = db.scalars(
            select(Teacher).where(Teacher.zone_id == membership.zone_id, Teacher.initials == t.initials)
        ).first()
        if existing_teacher is not None:
            if existing_teacher.full_name != t.full_name:
                warnings.append(
                    ImportIssue(
                        path=f"teachers (initials={t.initials})",
                        message=(
                            f"Lærer '{t.initials}' finnes allerede som '{existing_teacher.full_name}' — beholder "
                            f"eksisterende navn, ignorerer '{t.full_name}' fra importen."
                        ),
                    )
                )
            teacher_by_initials[t.initials] = existing_teacher
        else:
            new_teacher = Teacher(zone_id=membership.zone_id, initials=t.initials, full_name=t.full_name)
            db.add(new_teacher)
            db.flush()
            teacher_by_initials[t.initials] = new_teacher

    subject_by_code: dict[str, Subject] = {}
    for s in payload.subjects:
        subject = Subject(
            school_year_id=school_year.id,
            name=s.name,
            short_code=s.short_code,
            is_trinnfag=s.is_trinnfag,
            is_krov=s.is_krov,
            uses_hall=s.uses_hall,
            avoid_consecutive=s.avoid_consecutive,
            prefer_before_lunch=s.prefer_before_lunch,
            needs_consecutive_periods=s.needs_consecutive_periods,
        )
        db.add(subject)
        db.flush()
        subject_by_code[s.short_code] = subject
        for alloc in s.hour_allocations:
            trinn = trinn_by_level[alloc.trinn_level]
            db.add(SubjectHourAllocation(subject_id=subject.id, trinn_id=trinn.id, weekly_hours=alloc.weekly_hours))

    activity_count = 0
    for a in payload.activities:
        activity = Activity(
            school_year_id=school_year.id,
            activity_type=a.activity_type,
            duration_ticks=a.duration_minutes // 30,
            occurrences_per_week=a.occurrences_per_week,
            notes=a.notes,
        )
        db.add(activity)
        db.flush()
        activity_count += 1
        for leg in a.legs:
            class_group_id = (
                class_group_by_ref[_parse_class_ref(leg.class_ref)] if leg.class_ref is not None else None
            )
            activity_leg = ActivityLeg(
                activity_id=activity.id,
                class_group_id=class_group_id,
                subject_id=subject_by_code[leg.subject_code].id,
            )
            db.add(activity_leg)
            db.flush()
            for initials in leg.teacher_initials:
                db.add(
                    ActivityLegTeacher(
                        activity_leg_id=activity_leg.id, teacher_id=teacher_by_initials[initials].id
                    )
                )

    db.commit()

    counts = {
        "trinn": len(payload.trinn),
        "classes": sum(len(t.classes) for t in payload.trinn),
        "class_groups": len(class_group_by_ref),
        "teachers": len(teacher_by_initials),
        "subjects": len(subject_by_code),
        "activities": activity_count,
    }
    return ImportResultRead(school_year_id=school_year.id, counts=counts, warnings=warnings)
