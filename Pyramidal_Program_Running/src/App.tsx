import { useState } from 'react';
import type { PlanRow } from './utils/generator';          // ← type-only
import type { PlanInputs } from './components/InputForm';  // ← type-only

import InputForm from './components/InputForm';
import PlanPreview from './components/PlanPreview';
import { generatePlan } from './utils/generator';
import DownloadButtons from './components/DownloadButtons';

export default function App() {
  const [rows, setRows] = useState<PlanRow[]>([]);

  const handleGenerate = (data: PlanInputs) => {
    setRows(generatePlan(data));
  };

  return (
    <div style={{ maxWidth: 960, margin: '0 auto', padding: 16 }}>
      <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 16 }}>
        PyraPro – Pyramidal Plan Generator
      </h1>

      <InputForm onGenerate={handleGenerate} />

      <PlanPreview rows={rows} />

      {/* ↓ Buttons show only when rows exist */}
      <DownloadButtons rows={rows} />
    </div>
  );
}
