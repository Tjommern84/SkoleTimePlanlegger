// Mirrors the tick-layout logic in backend/app/solver/grid.py: a
// splittable period (2/3, each already 30 min) is 1 tick; a non-splittable
// period (1/4/5/6, each 60 min) is 2 ticks. Needed client-side to map a
// TimetableSlot's (day, local start_tick, duration_ticks) back to the
// period number(s) it covers, for grid rendering.

export interface PeriodInfo {
  day_of_week: string;
  period_number: number;
  is_splittable: boolean;
  start_time: string;
  end_time: string;
  is_before_lunch: boolean;
}

export function dayTickToPeriod(periodsForDay: PeriodInfo[]): number[] {
  const sorted = [...periodsForDay].sort((a, b) => a.period_number - b.period_number);
  const ticks: number[] = [];
  for (const p of sorted) {
    const count = p.is_splittable ? 1 : 2;
    for (let i = 0; i < count; i++) ticks.push(p.period_number);
  }
  return ticks; // index = local tick -> period_number
}

export function touchedPeriods(tickToPeriod: number[], startTick: number, durationTicks: number): number[] {
  const periods: number[] = [];
  for (let t = startTick; t < startTick + durationTicks; t++) {
    const p = tickToPeriod[t];
    if (periods[periods.length - 1] !== p) periods.push(p);
  }
  return periods;
}
