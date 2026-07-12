from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, zone_membership_for_school_year
from app.db.models.subject import Subject, SubjectHourAllocation
from app.db.models.trinn_class import Trinn
from app.db.models.user import User
from app.schemas.subject import (
    SubjectCreate,
    SubjectHourAllocationCreate,
    SubjectHourAllocationRead,
    SubjectRead,
)

router = APIRouter(prefix="/api", tags=["subjects"])


@router.get("/subjects", response_model=list[SubjectRead])
def list_subjects(school_year_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    zone_membership_for_school_year(db, user, school_year_id)
    stmt = select(Subject).where(Subject.school_year_id == school_year_id)
    return db.scalars(stmt).all()


@router.post("/subjects", response_model=SubjectRead, status_code=201)
def create_subject(payload: SubjectCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    zone_membership_for_school_year(db, user, payload.school_year_id)
    obj = Subject(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/subjects/{subject_id}", response_model=SubjectRead)
def update_subject(
    subject_id: int, payload: SubjectCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    obj = db.get(Subject, subject_id)
    if obj is None:
        raise HTTPException(404, "Subject not found")
    zone_membership_for_school_year(db, user, obj.school_year_id)
    zone_membership_for_school_year(db, user, payload.school_year_id)
    for key, value in payload.model_dump().items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/subjects/{subject_id}", status_code=204)
def delete_subject(subject_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    obj = db.get(Subject, subject_id)
    if obj is None:
        raise HTTPException(404, "Subject not found")
    zone_membership_for_school_year(db, user, obj.school_year_id)
    # Hour allocations have no meaning without their subject -- clean them
    # up here rather than leaving them orphaned or blocking the delete.
    db.execute(delete(SubjectHourAllocation).where(SubjectHourAllocation.subject_id == subject_id))
    db.delete(obj)
    db.commit()


@router.get("/subject-hour-allocations", response_model=list[SubjectHourAllocationRead])
def list_subject_hour_allocations(
    subject_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    subject = db.get(Subject, subject_id)
    if subject is None:
        raise HTTPException(404, "Subject not found")
    zone_membership_for_school_year(db, user, subject.school_year_id)
    stmt = select(SubjectHourAllocation).where(SubjectHourAllocation.subject_id == subject_id)
    return db.scalars(stmt).all()


@router.post("/subject-hour-allocations", response_model=SubjectHourAllocationRead, status_code=201)
def create_subject_hour_allocation(
    payload: SubjectHourAllocationCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    subject = db.get(Subject, payload.subject_id)
    if subject is None:
        raise HTTPException(404, "Subject not found")
    subject_membership = zone_membership_for_school_year(db, user, subject.school_year_id)

    trinn = db.get(Trinn, payload.trinn_id)
    if trinn is None:
        raise HTTPException(404, "Trinn not found")
    trinn_membership = zone_membership_for_school_year(db, user, trinn.school_year_id)

    if subject_membership.zone_id != trinn_membership.zone_id:
        raise HTTPException(404, "Trinn not found")

    obj = SubjectHourAllocation(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def _zone_membership_for_hour_allocation(db: Session, user: User, allocation_id: int) -> SubjectHourAllocation:
    obj = db.get(SubjectHourAllocation, allocation_id)
    if obj is None:
        raise HTTPException(404, "Hour allocation not found")
    subject = db.get(Subject, obj.subject_id)
    zone_membership_for_school_year(db, user, subject.school_year_id)
    return obj


@router.patch("/subject-hour-allocations/{allocation_id}", response_model=SubjectHourAllocationRead)
def update_subject_hour_allocation(
    allocation_id: int,
    payload: SubjectHourAllocationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    obj = _zone_membership_for_hour_allocation(db, user, allocation_id)
    subject = db.get(Subject, payload.subject_id)
    if subject is None:
        raise HTTPException(404, "Subject not found")
    zone_membership_for_school_year(db, user, subject.school_year_id)
    trinn = db.get(Trinn, payload.trinn_id)
    if trinn is None:
        raise HTTPException(404, "Trinn not found")
    zone_membership_for_school_year(db, user, trinn.school_year_id)

    obj.subject_id = payload.subject_id
    obj.trinn_id = payload.trinn_id
    obj.weekly_hours = payload.weekly_hours
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/subject-hour-allocations/{allocation_id}", status_code=204)
def delete_subject_hour_allocation(
    allocation_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    obj = _zone_membership_for_hour_allocation(db, user, allocation_id)
    db.delete(obj)
    db.commit()
