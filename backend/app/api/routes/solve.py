from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.models.timetable import GeneratedTimetable, TimetableSlot
from app.schemas.timetable import GeneratedTimetableRead
from app.solver.solve_service import solve_school_year_variants

router = APIRouter(prefix="/api", tags=["solve"], dependencies=[Depends(get_current_user)])


class SolveRequest(BaseModel):
    school_year_id: int
    time_limit_seconds: float = 60.0
    optimize: bool = True
    # How many distinct, equally-valid alternative plans to generate (see
    # solve_school_year_variants docstring for why this needs an explicit
    # "exclude and re-solve" loop rather than just varying a random seed).
    # Capped to keep worst-case request latency bounded.
    variant_count: int = 1


class VariantSummary(BaseModel):
    generated_timetable_id: int
    status: str
    placement_count: int
    is_active: bool


class SolveResponse(BaseModel):
    generated_timetable_id: int | None
    status: str
    infeasible_sessions: list[str]
    placement_count: int
    variants: list[VariantSummary] = []


@router.post("/solve", response_model=SolveResponse)
def solve(payload: SolveRequest, db: Session = Depends(get_db)):
    variant_count = max(1, min(payload.variant_count, 5))
    results = solve_school_year_variants(
        db,
        payload.school_year_id,
        time_limit_seconds=payload.time_limit_seconds,
        optimize=payload.optimize,
        variant_count=variant_count,
    )

    first = results[0]
    if first.status not in ("OPTIMAL", "FEASIBLE"):
        generated = GeneratedTimetable(
            school_year_id=payload.school_year_id,
            created_at=datetime.now(UTC),
            solver_status=first.status,
            objective_value=None,
            is_active=False,
        )
        db.add(generated)
        db.commit()
        db.refresh(generated)
        return SolveResponse(
            generated_timetable_id=generated.id,
            status=first.status,
            infeasible_sessions=first.infeasible_sessions,
            placement_count=0,
        )

    # Deactivate any previously active timetable for this school year before
    # persisting the new ones -- the first variant becomes active by default.
    db.execute(
        update(GeneratedTimetable)
        .where(GeneratedTimetable.school_year_id == payload.school_year_id)
        .values(is_active=False)
    )

    variants: list[VariantSummary] = []
    for i, result in enumerate(results):
        generated = GeneratedTimetable(
            school_year_id=payload.school_year_id,
            created_at=datetime.now(UTC),
            solver_status=result.status,
            objective_value=None,
            is_active=(i == 0),
        )
        db.add(generated)
        db.flush()

        for placement in result.placements:
            db.add(
                TimetableSlot(
                    generated_timetable_id=generated.id,
                    activity_id=placement.activity_id,
                    occurrence_index=placement.occurrence_index,
                    day_of_week=placement.day_of_week,
                    start_tick=placement.start_tick,
                    duration_ticks=placement.duration_ticks,
                )
            )
        variants.append(
            VariantSummary(
                generated_timetable_id=generated.id,
                status=result.status,
                placement_count=len(result.placements),
                is_active=(i == 0),
            )
        )

    db.commit()

    return SolveResponse(
        generated_timetable_id=variants[0].generated_timetable_id,
        status=first.status,
        infeasible_sessions=[],
        placement_count=variants[0].placement_count,
        variants=variants,
    )


@router.post("/generated-timetables/{generated_timetable_id}/activate", response_model=VariantSummary)
def activate_generated_timetable(generated_timetable_id: int, db: Session = Depends(get_db)):
    generated = db.get(GeneratedTimetable, generated_timetable_id)
    if generated is None:
        raise HTTPException(404, "Generated timetable not found")

    db.execute(
        update(GeneratedTimetable)
        .where(GeneratedTimetable.school_year_id == generated.school_year_id)
        .values(is_active=False)
    )
    generated.is_active = True
    db.commit()

    count = len(
        db.scalars(select(TimetableSlot).where(TimetableSlot.generated_timetable_id == generated.id)).all()
    )
    return VariantSummary(
        generated_timetable_id=generated.id,
        status=generated.solver_status,
        placement_count=count,
        is_active=True,
    )


@router.get("/school-years/{school_year_id}/timetable/active", response_model=GeneratedTimetableRead)
def get_active_timetable(school_year_id: int, db: Session = Depends(get_db)):
    stmt = select(GeneratedTimetable).where(
        GeneratedTimetable.school_year_id == school_year_id, GeneratedTimetable.is_active.is_(True)
    )
    generated = db.scalars(stmt).first()
    if generated is None:
        raise HTTPException(404, "No active generated timetable for this school year")
    slots = db.scalars(
        select(TimetableSlot).where(TimetableSlot.generated_timetable_id == generated.id)
    ).all()
    return GeneratedTimetableRead(
        id=generated.id,
        school_year_id=generated.school_year_id,
        created_at=generated.created_at,
        solver_status=generated.solver_status,
        objective_value=generated.objective_value,
        is_active=generated.is_active,
        slots=list(slots),
    )
