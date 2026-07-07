from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.models.solver_settings import SolverSettings
from app.schemas.solver_settings import SolverSettingsRead, SolverSettingsUpsert

router = APIRouter(prefix="/api", tags=["constraints"], dependencies=[Depends(get_current_user)])


@router.get("/solver-settings", response_model=SolverSettingsRead)
def get_solver_settings(school_year_id: int, db: Session = Depends(get_db)):
    stmt = select(SolverSettings).where(SolverSettings.school_year_id == school_year_id)
    obj = db.scalars(stmt).first()
    if obj is None:
        raise HTTPException(404, "No solver settings for this school year yet")
    return obj


@router.put("/solver-settings", response_model=SolverSettingsRead)
def upsert_solver_settings(payload: SolverSettingsUpsert, db: Session = Depends(get_db)):
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
