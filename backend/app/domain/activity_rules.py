from app.db.models.activity import ActivityType

_EXPECTED_LEG_COUNT = {ActivityType.NORMAL: 1, ActivityType.SPLIT_PARALLEL: 2}


def leg_count_error(activity_type: ActivityType, leg_count: int) -> str | None:
    """NORMAL activities have exactly 1 leg, SPLIT_PARALLEL exactly 2,
    TRINNFAG at least 1. Returns a human-readable error message, or None if
    `leg_count` is valid for `activity_type`. Pure function shared by the
    single-activity create route (which raises 400 on a non-None result)
    and the bulk school import (which collects the string as one of
    potentially many validation issues)."""
    expected = _EXPECTED_LEG_COUNT.get(activity_type)
    if expected is not None and leg_count != expected:
        return f"{activity_type.value} activities must have exactly {expected} leg(s), got {leg_count}"
    if activity_type == ActivityType.TRINNFAG and leg_count < 1:
        return "TRINNFAG activities must have at least 1 leg"
    return None
