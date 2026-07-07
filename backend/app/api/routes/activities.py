from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, get_db
from app.db.models.activity import Activity, ActivityLeg, ActivityLegTeacher
from app.schemas.activity import ActivityCreate, ActivityRead

router = APIRouter(prefix="/api", tags=["activities"], dependencies=[Depends(get_current_user)])


def _to_read(obj: Activity) -> ActivityRead:
    return ActivityRead(
        id=obj.id,
        school_year_id=obj.school_year_id,
        activity_type=obj.activity_type,
        duration_ticks=obj.duration_ticks,
        occurrences_per_week=obj.occurrences_per_week,
        notes=obj.notes,
        legs=[
            {
                "id": leg.id,
                "class_group_id": leg.class_group_id,
                "subject_id": leg.subject_id,
                "teacher_ids": [lt.teacher_id for lt in leg.leg_teachers],
            }
            for leg in obj.legs
        ],
    )


def _load(db: Session, activity_id: int) -> Activity:
    stmt = (
        select(Activity)
        .where(Activity.id == activity_id)
        .options(selectinload(Activity.legs).selectinload(ActivityLeg.leg_teachers))
    )
    obj = db.scalars(stmt).first()
    if obj is None:
        raise HTTPException(404, "Activity not found")
    return obj


@router.get("/activities", response_model=list[ActivityRead])
def list_activities(school_year_id: int, db: Session = Depends(get_db)):
    stmt = (
        select(Activity)
        .where(Activity.school_year_id == school_year_id)
        .options(selectinload(Activity.legs).selectinload(ActivityLeg.leg_teachers))
    )
    return [_to_read(a) for a in db.scalars(stmt).all()]


@router.post("/activities", response_model=ActivityRead, status_code=201)
def create_activity(payload: ActivityCreate, db: Session = Depends(get_db)):
    obj = Activity(
        school_year_id=payload.school_year_id,
        activity_type=payload.activity_type,
        duration_ticks=payload.duration_ticks,
        occurrences_per_week=payload.occurrences_per_week,
        notes=payload.notes,
    )
    db.add(obj)
    db.flush()

    for leg_payload in payload.legs:
        leg = ActivityLeg(
            activity_id=obj.id,
            class_group_id=leg_payload.class_group_id,
            subject_id=leg_payload.subject_id,
        )
        db.add(leg)
        db.flush()
        for teacher_id in leg_payload.teacher_ids:
            db.add(ActivityLegTeacher(activity_leg_id=leg.id, teacher_id=teacher_id))

    db.commit()
    return _to_read(_load(db, obj.id))


@router.get("/activities/{activity_id}", response_model=ActivityRead)
def get_activity(activity_id: int, db: Session = Depends(get_db)):
    return _to_read(_load(db, activity_id))


@router.delete("/activities/{activity_id}", status_code=204)
def delete_activity(activity_id: int, db: Session = Depends(get_db)):
    obj = db.get(Activity, activity_id)
    if obj is None:
        raise HTTPException(404, "Activity not found")
    db.delete(obj)
    db.commit()
