import { utils, writeFile } from 'xlsx';
import { saveAs } from 'file-saver';
import type { PlanRow } from '../utils/generator';

export default function DownloadButtons({ rows }: { rows: PlanRow[] }) {
  if (!rows.length) return null;

  const toSheet = () => {
    const ws = utils.json_to_sheet(rows);
    const wb = utils.book_new();
    utils.book_append_sheet(wb, ws, 'PyraPro');
    return wb;
  };

  const dlXLSX = () => writeFile(toSheet(), 'PyraPro_plan.xlsx');
  const dlCSV = () =>
    saveAs(
      new Blob([utils.sheet_to_csv(toSheet().Sheets['PyraPro'])], {
        type: 'text/csv;charset=utf-8;',
      }),
      'PyraPro_plan.csv'
    );

  return (
    <div style={{ display: 'flex', gap: 12, marginTop: 16 }}>
      <button onClick={dlXLSX}>Download XLSX</button>
      <button onClick={dlCSV}>Download CSV</button>
    </div>
  );
}
