from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_zone_header, zone_membership_for_school_year
from app.db.models import PeriodDefinition, SchoolClass, Trinn
from app.db.models.school_year import SchoolYear
from app.db.models.user import User
from app.db.models.zone import ZoneMembership
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

router = APIRouter(prefix="/api", tags=["school-structure"])


def _zone_membership_for_trinn(db: Session, user: User, trinn_id: int) -> ZoneMembership:
    trinn = db.get(Trinn, trinn_id)
    if trinn is None:
        raise HTTPException(404, "Trinn not found")
    return zone_membership_for_school_year(db, user, trinn.school_year_id)


def _zone_membership_for_school_class(db: Session, user: User, school_class_id: int) -> ZoneMembership:
    school_class = db.get(SchoolClass, school_class_id)
    if school_class is None:
        raise HTTPException(404, "School class not found")
    return _zone_membership_for_trinn(db, user, school_class.trinn_id)


def _zone_membership_for_class_group(db: Session, user: User, class_group_id: int) -> ZoneMembership:
    group = db.get(ClassGroup, class_group_id)
    if group is None:
        raise HTTPException(404, "Class group not found")
    return _zone_membership_for_school_class(db, user, group.school_class_id)


@router.get("/school-years", response_model=list[SchoolYearRead])
def list_school_years(db: Session = Depends(get_db), membership: ZoneMembership = Depends(require_zone_header)):
    return db.scalars(select(SchoolYear).where(SchoolYear.zone_id == membership.zone_id)).all()


@router.post("/school-years", response_model=SchoolYearRead, status_code=201)
def create_school_year(
    payload: SchoolYearCreate,
    db: Session = Depends(get_db),
    membership: ZoneMembership = Depends(require_zone_header),
):
    obj = SchoolYear(zone_id=membership.zone_id, **payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/school-years/{school_year_id}", response_model=SchoolYearRead)
def get_school_year(school_year_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    zone_membership_for_school_year(db, user, school_year_id)
    return db.get(SchoolYear, school_year_id)


@router.patch("/school-years/{school_year_id}", response_model=SchoolYearRead)
def update_school_year(
    school_year_id: int,
    payload: SchoolYearCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    zone_membership_for_school_year(db, user, school_year_id)
    obj = db.get(SchoolYear, school_year_id)
    obj.label = payload.label
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/school-years/{school_year_id}", status_code=204)
def delete_school_year(school_year_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    zone_membership_for_school_year(db, user, school_year_id)
    obj = db.get(SchoolYear, school_year_id)
    db.delete(obj)
    db.commit()


@router.get("/periods", response_model=list[PeriodDefinitionRead])
def list_periods(school_year_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    zone_membership_for_school_year(db, user, school_year_id)
    stmt = select(PeriodDefinition).where(PeriodDefinition.school_year_id == school_year_id)
    return db.scalars(stmt).all()


@router.post("/periods", response_model=PeriodDefinitionRead, status_code=201)
def create_period(
    payload: PeriodDefinitionCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    zone_membership_for_school_year(db, user, payload.school_year_id)
    obj = PeriodDefinition(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/periods/{period_id}", response_model=PeriodDefinitionRead)
def update_period(
    period_id: int,
    payload: PeriodDefinitionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    obj = db.get(PeriodDefinition, period_id)
    if obj is None:
        raise HTTPException(404, "Period not found")
    zone_membership_for_school_year(db, user, obj.school_year_id)
    zone_membership_for_school_year(db, user, payload.school_year_id)
    for key, value in payload.model_dump().items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/periods/{period_id}", status_code=204)
def delete_period(period_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    obj = db.get(PeriodDefinition, period_id)
    if obj is None:
        raise HTTPException(404, "Period not found")
    zone_membership_for_school_year(db, user, obj.school_year_id)
    db.delete(obj)
    db.commit()


@router.get("/trinn", response_model=list[TrinnRead])
def list_trinn(school_year_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    zone_membership_for_school_year(db, user, school_year_id)
    stmt = select(Trinn).where(Trinn.school_year_id == school_year_id)
    return db.scalars(stmt).all()


@router.post("/trinn", response_model=TrinnRead, status_code=201)
def create_trinn(payload: TrinnCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    zone_membership_for_school_year(db, user, payload.school_year_id)
    obj = Trinn(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/trinn/{trinn_id}", response_model=TrinnRead)
def update_trinn(
    trinn_id: int, payload: TrinnCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    obj = db.get(Trinn, trinn_id)
    if obj is None:
        raise HTTPException(404, "Trinn not found")
    zone_membership_for_school_year(db, user, obj.school_year_id)
    zone_membership_for_school_year(db, user, payload.school_year_id)
    obj.level = payload.level
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/trinn/{trinn_id}", status_code=204)
def delete_trinn(trinn_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _zone_membership_for_trinn(db, user, trinn_id)
    obj = db.get(Trinn, trinn_id)
    db.delete(obj)
    db.commit()


@router.get("/classes", response_model=list[SchoolClassRead])
def list_classes(trinn_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _zone_membership_for_trinn(db, user, trinn_id)
    stmt = select(SchoolClass).where(SchoolClass.trinn_id == trinn_id)
    return db.scalars(stmt).all()


@router.post("/classes", response_model=SchoolClassRead, status_code=201)
def create_class(payload: SchoolClassCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _zone_membership_for_trinn(db, user, payload.trinn_id)
    obj = SchoolClass(**payload.model_dump())
    db.add(obj)
    db.flush()
    # Every class needs at least a "whole" class-group to be usable by
    # activities -- create it automatically so the user doesn't have to
    # separately manage this for the common (non-split) case.
    db.add(ClassGroup(school_class_id=obj.id, label="whole"))
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/classes/{class_id}", response_model=SchoolClassRead)
def update_class(
    class_id: int, payload: SchoolClassCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    obj = db.get(SchoolClass, class_id)
    if obj is None:
        raise HTTPException(404, "School class not found")
    _zone_membership_for_school_class(db, user, class_id)
    _zone_membership_for_trinn(db, user, payload.trinn_id)
    obj.name = payload.name
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/classes/{class_id}", status_code=204)
def delete_class(class_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _zone_membership_for_school_class(db, user, class_id)
    obj = db.get(SchoolClass, class_id)
    db.delete(obj)
    db.commit()


@router.get("/class-groups", response_model=list[ClassGroupRead])
def list_class_groups(school_class_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _zone_membership_for_school_class(db, user, school_class_id)
    stmt = select(ClassGroup).where(ClassGroup.school_class_id == school_class_id)
    return db.scalars(stmt).all()


@router.post("/class-groups", response_model=ClassGroupRead, status_code=201)
def create_class_group(
    payload: ClassGroupCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    _zone_membership_for_school_class(db, user, payload.school_class_id)
    obj = ClassGroup(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/class-groups/{class_group_id}", response_model=ClassGroupRead)
def update_class_group(
    class_group_id: int,
    payload: ClassGroupCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    obj = db.get(ClassGroup, class_group_id)
    if obj is None:
        raise HTTPException(404, "Class group not found")
    _zone_membership_for_class_group(db, user, class_group_id)
    _zone_membership_for_school_class(db, user, payload.school_class_id)
    obj.label = payload.label
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/class-groups/{class_group_id}", status_code=204)
def delete_class_group(class_group_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _zone_membership_for_class_group(db, user, class_group_id)
    obj = db.get(ClassGroup, class_group_id)
    db.delete(obj)
    db.commit()
