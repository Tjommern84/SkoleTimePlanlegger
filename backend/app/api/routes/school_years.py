from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.models import PeriodDefinition, SchoolClass, Trinn
from app.db.models.school_year import SchoolYear
from app.schemas.school import (
    ClassGroupCreate,
    ClassGroupRead,
    PeriodDefinitionCreate,
    PeriodDefinitionRead,
    SchoolClassCreate,
    SchoolClassRead,
    SchoolYearCreate,
    SchoolYearRead,
    TrinnCreate,
    TrinnRead,
)
from app.db.models.trinn_class import ClassGroup

router = APIRouter(prefix="/api", tags=["school-structure"], dependencies=[Depends(get_current_user)])


@router.get("/school-years", response_model=list[SchoolYearRead])
def list_school_years(db: Session = Depends(get_db)):
    return db.scalars(select(SchoolYear)).all()


@router.post("/school-years", response_model=SchoolYearRead, status_code=201)
def create_school_year(payload: SchoolYearCreate, db: Session = Depends(get_db)):
    obj = SchoolYear(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/school-years/{school_year_id}", response_model=SchoolYearRead)
def get_school_year(school_year_id: int, db: Session = Depends(get_db)):
    obj = db.get(SchoolYear, school_year_id)
    if obj is None:
        raise HTTPException(404, "School year not found")
    return obj


@router.delete("/school-years/{school_year_id}", status_code=204)
def delete_school_year(school_year_id: int, db: Session = Depends(get_db)):
    obj = db.get(SchoolYear, school_year_id)
    if obj is None:
        raise HTTPException(404, "School year not found")
    db.delete(obj)
    db.commit()


@router.get("/periods", response_model=list[PeriodDefinitionRead])
def list_periods(school_year_id: int, db: Session = Depends(get_db)):
    stmt = select(PeriodDefinition).where(PeriodDefinition.school_year_id == school_year_id)
    return db.scalars(stmt).all()


@router.post("/periods", response_model=PeriodDefinitionRead, status_code=201)
def create_period(payload: PeriodDefinitionCreate, db: Session = Depends(get_db)):
    obj = PeriodDefinition(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/trinn", response_model=list[TrinnRead])
def list_trinn(school_year_id: int, db: Session = Depends(get_db)):
    stmt = select(Trinn).where(Trinn.school_year_id == school_year_id)
    return db.scalars(stmt).all()


@router.post("/trinn", response_model=TrinnRead, status_code=201)
def create_trinn(payload: TrinnCreate, db: Session = Depends(get_db)):
    obj = Trinn(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/classes", response_model=list[SchoolClassRead])
def list_classes(trinn_id: int, db: Session = Depends(get_db)):
    stmt = select(SchoolClass).where(SchoolClass.trinn_id == trinn_id)
    return db.scalars(stmt).all()


@router.post("/classes", response_model=SchoolClassRead, status_code=201)
def create_class(payload: SchoolClassCreate, db: Session = Depends(get_db)):
    obj = SchoolClass(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/class-groups", response_model=list[ClassGroupRead])
def list_class_groups(school_class_id: int, db: Session = Depends(get_db)):
    stmt = select(ClassGroup).where(ClassGroup.school_class_id == school_class_id)
    return db.scalars(stmt).all()


@router.post("/class-groups", response_model=ClassGroupRead, status_code=201)
def create_class_group(payload: ClassGroupCreate, db: Session = Depends(get_db)):
    obj = ClassGroup(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj
