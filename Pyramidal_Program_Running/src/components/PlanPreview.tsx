import type { PlanRow } from '../utils/generator';

export default function PlanPreview({ rows }: { rows: PlanRow[] }) {
  if (!rows.length) return null;

  return (
    <div style={{ border: '1px solid #ccc', borderRadius: 6, padding: 16 }}>
      <h2 style={{ fontWeight: 600, marginBottom: 8 }}>Plan preview</h2>

      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <tbody>
          {rows.map((row, i) => (
            /*  <--  the colour is applied here  */
            <tr key={i} style={{ background: row.color }}>
              <td style={{ padding: 8, fontFamily: 'monospace' }}>{row.date}</td>
              <td style={{ padding: 8 }}>{row.session}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
