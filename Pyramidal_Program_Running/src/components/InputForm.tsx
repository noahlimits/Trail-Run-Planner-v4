import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { format } from 'date-fns';

// Generate today’s date in ISO format for default values
const todayISO = format(new Date(), 'yyyy-MM-dd');

const PlanSchema = z.object({
  /* Required fields */
  planType: z.enum(['race', 'maintenance', 'maintenance_plus']),
  maxHR: z.number().min(100).max(230),
  courseProfile: z.enum(['flat', 'rolling', 'hilly', 'ultra']),

  /* Race-specific (only if planType === 'race') */
  raceDate: z.string().optional(), // ISO yyyy-MM-dd
  raceDistance: z.enum(['10k', 'half', 'marathon', '50k', 'custom']),
  customDistanceKm: z.number().positive().optional(),

  /* Physiology fields */
  vt1: z.number().min(60).max(200).optional(),
  vo2max: z.number().min(20).max(90).optional(),

  /* Volume fields */
  currentHours: z.number().positive().optional(),
  maxHours: z.number().positive().optional(),

  /* Toggles */
  firefighter: z.boolean().optional(),
  shiftPattern: z.string().optional(),
  nextShiftISO: z.string().optional(),
  heatBlock: z.enum(['none', 'monoblock', 'biphasic']),
  strength: z.boolean(),
  timeVsDistance: z.enum(['time', 'distance']),
});

export type PlanInputs = z.infer<typeof PlanSchema>;

export default function InputForm({
  onGenerate,
}: {
  onGenerate: (data: PlanInputs) => void;
}) {
  const {
    register,
    control,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<PlanInputs>({
    resolver: zodResolver(PlanSchema),
    defaultValues: {
      planType: 'race',
      courseProfile: 'rolling',
      raceDate: todayISO,
      raceDistance: '50k',
      heatBlock: 'none',
      strength: false,
      firefighter: false,
      timeVsDistance: 'time',
    },
  });

  const planType = watch('planType');
  const firefighter = watch('firefighter');
  const raceDistance = watch('raceDistance');

  return (
    <form onSubmit={handleSubmit(onGenerate)} style={{ padding: 16 }}>
      {/* ── Plan Type Radios ── */}
      <div style={{ display: 'flex', gap: 24, marginBottom: 16 }}>
        <label>
          <input type="radio" value="race" {...register('planType')} />
          &nbsp;Race build
        </label>
        <label>
          <input
            type="radio"
            value="maintenance"
            {...register('planType')}
          />
          &nbsp;Maintenance
        </label>
        <label>
          <input
            type="radio"
            value="maintenance_plus"
            {...register('planType')}
          />
          &nbsp;Maintenance +
        </label>
      </div>

      {/* ── Race-Specific Fields ── */}
      {planType === 'race' && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ marginBottom: 8 }}>
            <label>
              Race date:&nbsp;
              <input
                type="date"
                {...register('raceDate')}
                style={{ padding: 4, borderRadius: 4, border: '1px solid #ccc' }}
              />
            </label>
            {errors.raceDate && (
              <span style={{ color: 'red', marginLeft: 8 }}>
                {errors.raceDate.message}
              </span>
            )}
          </div>

          <div style={{ marginBottom: 8 }}>
            <label>
              Distance:&nbsp;
              <select
                {...register('raceDistance')}
                style={{ padding: 4, borderRadius: 4, border: '1px solid #ccc' }}
              >
                <option value="10k">10 km</option>
                <option value="half">Half-Marathon</option>
                <option value="marathon">Marathon</option>
                <option value="50k">50 km</option>
                <option value="custom">Custom</option>
              </select>
            </label>
            {errors.raceDistance && (
              <span style={{ color: 'red', marginLeft: 8 }}>
                {errors.raceDistance.message}
              </span>
            )}
          </div>

          {raceDistance === 'custom' && (
            <div>
              <label>
                Custom km:&nbsp;
                <input
                  type="number"
                  {...register('customDistanceKm', { valueAsNumber: true })}
                  placeholder="e.g. 42.2"
                  style={{ width: 80, padding: 4, borderRadius: 4, border: '1px solid #ccc' }}
                />
              </label>
              {errors.customDistanceKm && (
                <span style={{ color: 'red', marginLeft: 8 }}>
                  {errors.customDistanceKm.message}
                </span>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Physiology Fields ── */}
      <div style={{ display: 'flex', gap: 24, marginBottom: 16 }}>
        <div>
          <label>
            Max HR:&nbsp;
            <input
              type="number"
              {...register('maxHR', { valueAsNumber: true })}
              placeholder="e.g. 183"
              style={{ width: 80, padding: 4, borderRadius: 4, border: '1px solid #ccc' }}
            />
          </label>
          {errors.maxHR && (
            <span style={{ color: 'red', marginLeft: 8 }}>
              {errors.maxHR.message}
            </span>
          )}
        </div>
        <div>
          <label>
            VT₁:&nbsp;
            <input
              type="number"
              {...register('vt1', { valueAsNumber: true })}
              placeholder="e.g. 133"
              style={{ width: 80, padding: 4, borderRadius: 4, border: '1px solid #ccc' }}
            />
          </label>
          {errors.vt1 && (
            <span style={{ color: 'red', marginLeft: 8 }}>
              {errors.vt1.message}
            </span>
          )}
        </div>
        <div>
          <label>
            VO₂max:&nbsp;
            <input
              type="number"
              {...register('vo2max', { valueAsNumber: true })}
              placeholder="e.g. 54"
              style={{ width: 80, padding: 4, borderRadius: 4, border: '1px solid #ccc' }}
            />
          </label>
          {errors.vo2max && (
            <span style={{ color: 'red', marginLeft: 8 }}>
              {errors.vo2max.message}
            </span>
          )}
        </div>
      </div>

      {/* ── Course Profile ── */}
      <div style={{ marginBottom: 16 }}>
        <label>
          Course profile:&nbsp;
          <select
            {...register('courseProfile')}
            style={{ padding: 4, borderRadius: 4, border: '1px solid #ccc' }}
          >
            <option value="flat">Flat</option>
            <option value="rolling">Rolling</option>
            <option value="hilly">Hilly</option>
            <option value="ultra">Mountain/Ultra</option>
          </select>
        </label>
        {errors.courseProfile && (
          <span style={{ color: 'red', marginLeft: 8 }}>
            {errors.courseProfile.message}
          </span>
        )}
      </div>

      {/* ── Volume Controls ── */}
      <div style={{ display: 'flex', gap: 24, marginBottom: 16 }}>
        <div>
          <label>
            Current h/wk:&nbsp;
            <input
              type="number"
              {...register('currentHours', { valueAsNumber: true })}
              placeholder="e.g. 5"
              style={{ width: 80, padding: 4, borderRadius: 4, border: '1px solid #ccc' }}
            />
          </label>
          {errors.currentHours && (
            <span style={{ color: 'red', marginLeft: 8 }}>
              {errors.currentHours.message}
            </span>
          )}
        </div>
        <div>
          <label>
            Max avail h/wk:&nbsp;
            <input
              type="number"
              {...register('maxHours', { valueAsNumber: true })}
              placeholder="e.g. 12"
              style={{ width: 80, padding: 4, borderRadius: 4, border: '1px solid #ccc' }}
            />
          </label>
          {errors.maxHours && (
            <span style={{ color: 'red', marginLeft: 8 }}>
              {errors.maxHours.message}
            </span>
          )}
        </div>
      </div>

      {/* ── Toggles ── */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 16 }}>
        <label>
          <input type="checkbox" {...register('strength')} />
          &nbsp;Strength / mobility micro-doses
        </label>
        <label>
          <input type="checkbox" {...register('firefighter')} />
          &nbsp;Firefighter shift pattern
        </label>

        {firefighter && (
          <div style={{ display: 'flex', gap: 24, marginTop: 8 }}>
            <div>
              <label>
                Pattern:&nbsp;
                <input
                  type="text"
                  {...register('shiftPattern')}
                  placeholder="e.g. 1-2-1-4"
                  style={{ width: 80, padding: 4, borderRadius: 4, border: '1px solid #ccc' }}
                />
              </label>
              {errors.shiftPattern && (
                <span style={{ color: 'red', marginLeft: 8 }}>
                  {errors.shiftPattern.message}
                </span>
              )}
            </div>
            <div>
              <label>
                Next shift start:&nbsp;
                <input
                  type="datetime-local"
                  {...register('nextShiftISO')}
                  style={{ padding: 4, borderRadius: 4, border: '1px solid #ccc' }}
                />
              </label>
              {errors.nextShiftISO && (
                <span style={{ color: 'red', marginLeft: 8 }}>
                  {errors.nextShiftISO.message}
                </span>
              )}
            </div>
          </div>
        )}

        <div>
          <label>
            Heat block:&nbsp;
            <select
              {...register('heatBlock')}
              style={{ padding: 4, borderRadius: 4, border: '1px solid #ccc' }}
            >
              <option value="none">None</option>
              <option value="monoblock">Monoblock (last 2 weeks)</option>
              <option value="biphasic">Biphasic</option>
            </select>
          </label>
          {errors.heatBlock && (
            <span style={{ color: 'red', marginLeft: 8 }}>
              {errors.heatBlock.message}
            </span>
          )}
        </div>

        <div>
          <label>
            Plan basis:&nbsp;
            <select
              {...register('timeVsDistance')}
              style={{ padding: 4, borderRadius: 4, border: '1px solid #ccc' }}
            >
              <option value="time">Time + HR (default)</option>
              <option value="distance">Distance + pace</option>
            </select>
          </label>
          {errors.timeVsDistance && (
            <span style={{ color: 'red', marginLeft: 8 }}>
              {errors.timeVsDistance.message}
            </span>
          )}
        </div>
      </div>

      {/* ── Submit Button ── */}
      <button
        type="submit"
        style={{
          background: '#4f46e5',
          color: 'white',
          padding: '8px 16px',
          borderRadius: 4,
          border: 'none',
          cursor: 'pointer',
        }}
      >
        Generate plan
      </button>
    </form>
  );
}
