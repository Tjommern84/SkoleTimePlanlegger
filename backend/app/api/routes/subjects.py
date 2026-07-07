from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.models.subject import Subject, SubjectHourAllocation
from app.schemas.subject import (
    SubjectCreate,
    SubjectHourAllocationCreate,
    SubjectHourAllocationRead,
    SubjectRead,
)

router = APIRouter(prefix="/api", tags=["subjects"], dependencies=[Depends(get_current_user)])


@router.get("/subjects", response_model=list[SubjectRead])
def list_subjects(school_year_id: int, db: Session = Depends(get_db)):
    stmt = select(Subject).where(Subject.school_year_id == school_year_id)
    return db.scalars(stmt).all()


@router.post("/subjects", response_model=SubjectRead, status_code=201)
def create_subject(payload: SubjectCreate, db: Session = Depends(get_db)):
    obj = Subject(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/subjects/{subject_id}", status_code=204)
def delete_subject(subject_id: int, db: Session = Depends(get_db)):
    obj = db.get(Subject, subject_id)
    if obj is None:
        raise HTTPException(404, "Subject not found")
    db.delete(obj)
    db.commit()


@router.get("/subject-hour-allocations", response_model=list[SubjectHourAllocationRead])
def list_subject_hour_allocations(subject_id: int, db: Session = Depends(get_db)):
    stmt = select(SubjectHourAllocation).where(SubjectHourAllocation.subject_id == subject_id)
    return db.scalars(stmt).all()


@router.post("/subject-hour-allocations", response_model=SubjectHourAllocationRead, status_code=201)
def create_subject_hour_allocation(payload: SubjectHourAllocationCreate, db: Session = Depends(get_db)):
    obj = SubjectHourAllocation(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj
