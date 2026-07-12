from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, zone_membership_for_school_year
from app.db.models.solver_settings import SolverSettings
from app.db.models.user import User
from app.schemas.solver_settings import SolverSettingsRead, SolverSettingsUpsert

router = APIRouter(prefix="/api", tags=["constraints"])


@router.get("/solver-settings", response_model=SolverSettingsRead)
def get_solver_settings(school_year_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    zone_membership_for_school_year(db, user, school_year_id)
    stmt = select(SolverSettings).where(SolverSettings.school_year_id == school_year_id)
    obj = db.scalars(stmt).first()
    if obj is None:
        raise HTTPException(404, "No solver settings for this school year yet")
    return obj


@router.put("/solver-settings", response_model=SolverSettingsRead)
def upsert_solver_settings(
    payload: SolverSettingsUpsert, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    zone_membership_for_school_year(db, user, payload.school_year_id)
    stmt = select(SolverSettings).where(SolverSettings.school_year_id == payload.school_year_id)
    obj = db.scalars(stmt).first()
    if obj is None:
        obj = SolverSettings(**payload.model_dump())
        db.add(obj)
    else:
        for key, value in payload.model_dump().items():
            setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj
