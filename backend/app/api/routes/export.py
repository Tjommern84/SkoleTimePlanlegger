from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.export.excel_export import export_generated_timetable

router = APIRouter(prefix="/api", tags=["export"], dependencies=[Depends(get_current_user)])


@router.get("/generated-timetables/{generated_timetable_id}/export.xlsx")
def export_timetable_excel(generated_timetable_id: int, db: Session = Depends(get_db)):
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
