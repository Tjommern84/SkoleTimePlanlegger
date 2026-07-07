"""Builds the week's half-hour "tick" grid from a school year's
PeriodDefinition rows.

One tick = 30 minutes. A splittable period (2/3 in the school's schedule,
each already only 30 min) contributes exactly one tick. A non-splittable
period (1/4/5/6, each 60 min) contributes two ticks that must always be
occupied identically -- see `non_splittable_pairs` -- since it's already a
single indivisible 60-min block, not two independently placeable halves.

Ticks are numbered globally across the week in day order
(Mon, Tue, Wed, Thu, Fri), each day's ticks contiguous and in period order.
"""

from dataclasses import dataclass, field

from app.db.models.period import DayOfWeek, PeriodDefinition

WEEK_ORDER = [DayOfWeek.MON, DayOfWeek.TUE, DayOfWeek.WED, DayOfWeek.THU, DayOfWeek.FRI]


@dataclass(frozen=True)
class TickInfo:
    day: DayOfWeek
    period_number: int
    is_before_lunch: bool


@dataclass
class TickGrid:
    ticks: list[TickInfo]
    day_range: dict[DayOfWeek, tuple[int, int]]  # [start, end) global tick index
    non_splittable_pairs: list[tuple[int, int]]
    lunch_boundary: dict[DayOfWeek, int]  # first tick index of the after-lunch block, per day
    period2_tick: dict[DayOfWeek, int] = field(default_factory=dict)
    period3_tick: dict[DayOfWeek, int] = field(default_factory=dict)

    @property
    def total_ticks(self) -> int:
        return len(self.ticks)

    def valid_start_ticks(self, duration_ticks: int) -> list[int]:
        """All global start-tick indices where a session of this duration
        can be placed without crossing a day boundary, splitting a
        non-splittable period, or spanning the lunch break.
        """
        starts: list[int] = []
        for day, (day_start, day_end) in self.day_range.items():
            for s in range(day_start, day_end - duration_ticks + 1):
                window = range(s, s + duration_ticks)
                if self._crosses_lunch(day, window):
                    continue
                if self._splits_non_splittable_period(window):
                    continue
                starts.append(s)
        return starts

    def _crosses_lunch(self, day: DayOfWeek, window: range) -> bool:
        boundary = self.lunch_boundary.get(day)
        if boundary is None:
            return False
        before = any(t < boundary for t in window)
        after = any(t >= boundary for t in window)
        return before and after

    def _splits_non_splittable_period(self, window: range) -> bool:
        window_set = set(window)
        for a, b in self.non_splittable_pairs:
            in_a, in_b = a in window_set, b in window_set
            if in_a != in_b:
                return True
        return False

    def ticks_for_period_range(
        self, day: DayOfWeek, start_period: int | None, end_period: int | None
    ) -> list[int]:
        """Global tick indices for an ordinal (start_period..end_period)
        range on one day. Both None means the whole day.
        """
        if day not in self.day_range:
            return []
        day_start, day_end = self.day_range[day]
        if start_period is None and end_period is None:
            return list(range(day_start, day_end))
        return [
            i
            for i in range(day_start, day_end)
            if start_period <= self.ticks[i].period_number <= end_period
        ]

    def day_and_local_tick(self, global_tick: int) -> tuple[DayOfWeek, int]:
        for day, (start, end) in self.day_range.items():
            if start <= global_tick < end:
                return day, global_tick - start
        raise ValueError(f"tick {global_tick} not in grid")

    def touched_periods(self, day: DayOfWeek, local_start_tick: int, duration_ticks: int) -> list[int]:
        """Ordered, de-duplicated period numbers covered by a placement
        given as (day, local-to-day start tick, duration in ticks).
        """
        day_start, _day_end = self.day_range[day]
        global_start = day_start + local_start_tick
        periods: list[int] = []
        for t in range(global_start, global_start + duration_ticks):
            p = self.ticks[t].period_number
            if not periods or periods[-1] != p:
                periods.append(p)
        return periods

    def fixed_start_tick(self, day: DayOfWeek, start_period: int) -> int | None:
        """The global tick index at which start_period begins on this day,
        for pinning a fixed-placement activity (e.g. Fremmedspraak 10th
        trinn -> Wed period 5).
        """
        if day not in self.day_range:
            return None
        day_start, day_end = self.day_range[day]
        for i in range(day_start, day_end):
            if self.ticks[i].period_number == start_period:
                return i
        return None


def build_tick_grid(periods: list[PeriodDefinition]) -> TickGrid:
    by_day: dict[DayOfWeek, list[PeriodDefinition]] = {}
    for p in periods:
        by_day.setdefault(p.day_of_week, []).append(p)
    for day_periods in by_day.values():
        day_periods.sort(key=lambda p: p.period_number)

    ticks: list[TickInfo] = []
    day_range: dict[DayOfWeek, tuple[int, int]] = {}
    non_splittable_pairs: list[tuple[int, int]] = []
    lunch_boundary: dict[DayOfWeek, int] = {}
    period2_tick: dict[DayOfWeek, int] = {}
    period3_tick: dict[DayOfWeek, int] = {}

    for day in WEEK_ORDER:
        day_periods = by_day.get(day, [])
        if not day_periods:
            continue
        start = len(ticks)
        prev_before_lunch = True
        for p in day_periods:
            tick_count = 1 if p.is_splittable else 2
            first_tick_idx = len(ticks)
            for _ in range(tick_count):
                ticks.append(TickInfo(day=day, period_number=p.period_number, is_before_lunch=p.is_before_lunch))
            if tick_count == 2:
                non_splittable_pairs.append((first_tick_idx, first_tick_idx + 1))
            if p.period_number == 2:
                period2_tick[day] = first_tick_idx
            if p.period_number == 3:
                period3_tick[day] = first_tick_idx
            if prev_before_lunch and not p.is_before_lunch and day not in lunch_boundary:
                lunch_boundary[day] = first_tick_idx
            prev_before_lunch = p.is_before_lunch
        day_range[day] = (start, len(ticks))

    return TickGrid(
        ticks=ticks,
        day_range=day_range,
        non_splittable_pairs=non_splittable_pairs,
        lunch_boundary=lunch_boundary,
        period2_tick=period2_tick,
        period3_tick=period3_tick,
    )
