from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.models.teacher import Teacher, TeacherSubjectQualification, TeacherUnavailability
from app.schemas.teacher import (
    TeacherCreate,
    TeacherRead,
    TeacherSubjectQualificationCreate,
    TeacherSubjectQualificationRead,
    TeacherSubjectQualificationUpdate,
    TeacherUnavailabilityCreate,
    TeacherUnavailabilityRead,
)

router = APIRouter(prefix="/api", tags=["teachers"], dependencies=[Depends(get_current_user)])


@router.get("/teachers", response_model=list[TeacherRead])
def list_teachers(db: Session = Depends(get_db)):
    return db.scalars(select(Teacher)).all()


@router.post("/teachers", response_model=TeacherRead, status_code=201)
def create_teacher(payload: TeacherCreate, db: Session = Depends(get_db)):
    obj = Teacher(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/teachers/{teacher_id}", response_model=TeacherRead)
def update_teacher(teacher_id: int, payload: TeacherCreate, db: Session = Depends(get_db)):
    obj = db.get(Teacher, teacher_id)
    if obj is None:
        raise HTTPException(404, "Teacher not found")
    obj.initials = payload.initials
    obj.full_name = payload.full_name
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/teachers/{teacher_id}", status_code=204)
def delete_teacher(teacher_id: int, db: Session = Depends(get_db)):
    obj = db.get(Teacher, teacher_id)
    if obj is None:
        raise HTTPException(404, "Teacher not found")
    db.delete(obj)
    db.commit()


@router.get("/teacher-unavailabilities", response_model=list[TeacherUnavailabilityRead])
def list_teacher_unavailabilities(teacher_id: int, db: Session = Depends(get_db)):
    stmt = select(TeacherUnavailability).where(TeacherUnavailability.teacher_id == teacher_id)
    return db.scalars(stmt).all()


@router.post("/teacher-unavailabilities", response_model=TeacherUnavailabilityRead, status_code=201)
def create_teacher_unavailability(payload: TeacherUnavailabilityCreate, db: Session = Depends(get_db)):
    obj = TeacherUnavailability(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/teacher-unavailabilities/{unavailability_id}", status_code=204)
def delete_teacher_unavailability(unavailability_id: int, db: Session = Depends(get_db)):
    obj = db.get(TeacherUnavailability, unavailability_id)
    if obj is None:
        raise HTTPException(404, "Unavailability not found")
    db.delete(obj)
    db.commit()


@router.get("/teacher-subject-qualifications", response_model=list[TeacherSubjectQualificationRead])
def list_teacher_subject_qualifications(teacher_id: int, db: Session = Depends(get_db)):
    stmt = select(TeacherSubjectQualification).where(TeacherSubjectQualification.teacher_id == teacher_id)
    return db.scalars(stmt).all()


@router.post("/teacher-subject-qualifications", response_model=TeacherSubjectQualificationRead, status_code=201)
def create_teacher_subject_qualification(
    payload: TeacherSubjectQualificationCreate, db: Session = Depends(get_db)
):
    obj = TeacherSubjectQualification(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/teacher-subject-qualifications/{qualification_id}", response_model=TeacherSubjectQualificationRead)
def update_teacher_subject_qualification(
    qualification_id: int, payload: TeacherSubjectQualificationUpdate, db: Session = Depends(get_db)
):
    obj = db.get(TeacherSubjectQualification, qualification_id)
    if obj is None:
        raise HTTPException(404, "Qualification not found")
    obj.weekly_hours = payload.weekly_hours
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/teacher-subject-qualifications/{qualification_id}", status_code=204)
def delete_teacher_subject_qualification(qualification_id: int, db: Session = Depends(get_db)):
    obj = db.get(TeacherSubjectQualification, qualification_id)
    if obj is None:
        raise HTTPException(404, "Qualification not found")
    db.delete(obj)
    db.commit()
