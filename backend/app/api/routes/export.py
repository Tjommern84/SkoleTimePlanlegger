from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, zone_membership_for_school_year
from app.db.models.timetable import GeneratedTimetable
from app.db.models.user import User
from app.export.excel_export import export_generated_timetable

router = APIRouter(prefix="/api", tags=["export"])


@router.get("/generated-timetables/{generated_timetable_id}/export.xlsx")
def export_timetable_excel(
    generated_timetable_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    # Deliberately no X-Zone-Id header requirement here: this endpoint is
    # opened via a plain browser navigation (an <a href>, see
    # frontend/src/pages/SolvePage.tsx), which can't send custom headers.
    # The zone is instead derived from the generated_timetable_id itself.
    generated = db.get(GeneratedTimetable, generated_timetable_id)
    if generated is None:
        raise HTTPException(404, "Generated timetable not found")
    zone_membership_for_school_year(db, user, generated.school_year_id)

    try:
        workbook = export_generated_timetable(db, generated_timetable_id)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e

    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=timeplan_{generated_timetable_id}.xlsx"},
    )
