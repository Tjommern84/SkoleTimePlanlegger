from sqlalchemy.orm import Session

from app.db.models.trinn_class import ClassGroup, SchoolClass


def create_class_with_whole_group(db: Session, trinn_id: int, name: str) -> tuple[SchoolClass, ClassGroup]:
    """Every class needs at least a "whole" class-group to be usable by
    activities -- create it automatically alongside the class so callers
    don't have to separately manage this for the common (non-split) case.
    Shared by the single-class create route and the bulk school import.
    """
    school_class = SchoolClass(trinn_id=trinn_id, name=name)
    db.add(school_class)
    db.flush()
    whole_group = ClassGroup(school_class_id=school_class.id, label="whole")
    db.add(whole_group)
    db.flush()
    return school_class, whole_group
