from pydantic import BaseModel, ConfigDict


class SolverSettingsUpsert(BaseModel):
    school_year_id: int
    max_concurrent_krov: int = 2
    preferred_concurrent_krov: int = 1
    krov10_preferred_periods: str = "3,4"
    fremmedspraak10_fixed_day: str = "WED"
    fremmedspraak10_fixed_periods: str = "5,6"
    weight_musikk_spread: int = 10
    weight_matte_before_lunch: int = 10
    weight_mat_helse_placement: int = 10
    weight_krov_prefer_one: int = 5


class SolverSettingsRead(SolverSettingsUpsert):
    model_config = ConfigDict(from_attributes=True)
    id: int
