// src/utils/generator.ts

import { addDays, differenceInCalendarDays, format } from 'date-fns';
import type { PlanInputs } from '../components/InputForm';

/** Represents one row in the generated plan */
export interface PlanRow {
  date: string;        // formatted display date, e.g. "Wed, Jun 4 2025"
  session: string;     // human-readable session description
  // future: possible “tweaks” field or HR target field
}

const fmt = (d: Date) => format(d, 'EEE, MMM d yyyy');

/** Linear interpolation helper */
function lerp(start: number, end: number, t: number) {
  return start + (end - start) * t;
}

/**
 * Main generator: creates a multi-week pyramidal plan based on PlanInputs.
 */
export function generatePlan(inputs: PlanInputs): PlanRow[] {
  const today = new Date();
  let totalWeeks: number;
  if (inputs.planType === 'race') {
    // Calculate number of weeks until race (at least 4)
    const raceDate = inputs.raceDate ? new Date(inputs.raceDate) : today;
    const daysUntil = differenceInCalendarDays(raceDate, today);
    totalWeeks = Math.max(4, Math.ceil(daysUntil / 7));
  } else {
    // Maintenance & Maintenance Plus default to 12 weeks
    totalWeeks = 12;
  }

  // User’s volume inputs (hours/week). If missing, supply defaults.
  const curHrs = inputs.currentHours || 5;
  const maxHrs =
    inputs.maxHours ||
    (inputs.planType === 'race'
      ? Math.max(curHrs + 2, 10)
      : Math.max(curHrs + 2, 8));

  // Base long-run: 90 min at week 0 if race, 60 min if maintenance
  const longSeed = inputs.planType === 'race' ? 90 : 60;

  const rows: PlanRow[] = [];

  for (let w = 0; w < totalWeeks; w++) {
    // Week start (Monday of that week)
    const weekStart = addDays(today, w * 7);

    // Linear ramp factor (0 .. 1 across plan)
    const t =
      totalWeeks > 1 ? w / (totalWeeks - 1) : 1; // avoid division by zero

    // Compute weekly target hours (not used directly here, but for future refinements)
    const targetHrs = lerp(curHrs, maxHrs, t);

    // 1) Long run on Sunday (day index 6)
    const longRunMin = longSeed + w * 10; // +10 min each week
    const longRunDate = addDays(weekStart, 6);
    rows.push({
      date: fmt(longRunDate),
      session: `Long run – ${longRunMin} min easy`,
    });

    // 2) Threshold or hill-tempo on Wednesday (day index 2)
    const wednesdayDate = addDays(weekStart, 2);
    let thrSession = '';
    if (inputs.courseProfile === 'flat') {
      thrSession = 'Threshold 20 min continuous';
    } else {
      // Alternate Hill-Tempo every other week if rolling/hilly/ultra
      thrSession = w % 2 === 0 ? 'Uphill-Tempo 6×5 min' : 'Threshold 20 min continuous';
    }
    rows.push({
      date: fmt(wednesdayDate),
      session: thrSession,
    });

    // 3) VO₂ intervals on Friday (day index 4), except every 4th week is a down-week (skip)
    if (w % 4 !== 3) {
      const fridayDate = addDays(weekStart, 4);
      rows.push({
        date: fmt(fridayDate),
        session: 'VO₂max 4×4 min',
      });
    }

    // 4) Heat-block placement
    if (inputs.planType === 'race' && inputs.heatBlock !== 'none') {
      if (inputs.heatBlock === 'monoblock' && w >= totalWeeks - 2) {
        // Last 2 weeks: slot HWI on Tuesday (day 1)
        const tuesday = addDays(weekStart, 1);
        rows.push({
          date: fmt(tuesday),
          session: 'HWI 19 min @ 40°C',
        });
      }
      if (
        inputs.heatBlock === 'biphasic' &&
        (w < 2 || w >= totalWeeks - 2)
      ) {
        // Primer in weeks 0–1 on Tuesday; Peak in last 2 weeks on Tuesday
        const blkDay = addDays(weekStart, 1);
        rows.push({
          date: fmt(blkDay),
          session: 'HWI 19 min @ 40°C',
        });
      }
    }

    // 5) Maintenance-plus: add extra VO₂ every other week
    if (
      inputs.planType === 'maintenance_plus' &&
      w % 2 === 1 &&
      w % 4 !== 3
    ) {
      const saturdayDate = addDays(weekStart, 5);
      rows.push({
        date: fmt(saturdayDate),
        session: 'Additional VO₂ 4×4 min',
      });
    }

    // 6) (Future) firefighter logic placeholder
    //    if (inputs.firefighter) { … skip or shift sessions based on shiftPattern & nextShiftISO … }
  }

  // Sort rows by date to ensure chronological output
  return rows.sort(
    (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
  );
}
