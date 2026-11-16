import { describe, expect, it } from 'vitest';
import { RESPIRATORY_QUOTIENT, co2FromOxygen } from '../src/lib/co2';

describe('CO2 derived from the oxygen line', () => {
  it('turns consumed oxygen into exhaled CO2 at the respiratory quotient', () => {
    const c = co2FromOxygen({ remaining: 15, perHour: 4, routeNeeds: 6 }, 25)!;
    expect(c.exhaledL).toBeCloseTo(10 * RESPIRATORY_QUOTIENT); // 25 L budget, 15 L left: 10 L used
    expect(c.budgetL).toBeCloseTo(25 * RESPIRATORY_QUOTIENT);
    expect(c.perHour).toBeCloseTo(4 * RESPIRATORY_QUOTIENT);
    expect(c.routeAddsL).toBeCloseTo(6 * RESPIRATORY_QUOTIENT);
  });

  it('starts at zero and never goes negative', () => {
    expect(co2FromOxygen({ remaining: 25, perHour: null, routeNeeds: null }, 25)!.exhaledL).toBe(0);
    expect(co2FromOxygen({ remaining: 30, perHour: null, routeNeeds: null }, 25)!.exhaledL).toBe(0);
  });

  it('shows nothing without an oxygen reading or budget (not an astronaut)', () => {
    expect(co2FromOxygen({ remaining: null, perHour: null, routeNeeds: null }, 25)).toBeNull();
    expect(co2FromOxygen({ remaining: 10, perHour: 1, routeNeeds: null }, null)).toBeNull();
  });
});
