/**
 * Carbon dioxide the astronaut breathes out, derived from the oxygen line of the replay (display only).
 *
 * The replay carries oxygen, not CO2. Breathing turns consumed O2 into exhaled CO2 at the respiratory quotient
 * RQ = CO2 out / O2 in (by volume), about 0.85 on a mixed diet at work rates like walking (assumed here, pending
 * scientific review). The suit's CO2 removal capacity is not modelled, so this is the load the suit has to clear,
 * not what is left of a scrubber.
 */
export const RESPIRATORY_QUOTIENT = 0.85;

export interface Co2Line {
  /** CO2 exhaled since the first sample (L). */
  exhaledL: number;
  /** CO2 the whole oxygen budget would produce (L): the bar's full scale. */
  budgetL: number | null;
  /** Current rate (L/h), or null when oxygen is not being consumed. */
  perHour: number | null;
  /** CO2 the route in force adds (L), or null. */
  routeAddsL: number | null;
}

export function co2FromOxygen(
  oxygen: { remaining: number | null; perHour: number | null; routeNeeds: number | null },
  oxygenBudgetL: number | null,
  rq = RESPIRATORY_QUOTIENT,
): Co2Line | null {
  if (oxygen.remaining == null || oxygenBudgetL == null || !(oxygenBudgetL > 0)) return null;
  const used = Math.max(0, oxygenBudgetL - oxygen.remaining);
  return {
    exhaledL: used * rq,
    budgetL: oxygenBudgetL * rq,
    perHour: oxygen.perHour == null ? null : oxygen.perHour * rq,
    routeAddsL: oxygen.routeNeeds == null ? null : oxygen.routeNeeds * rq,
  };
}
