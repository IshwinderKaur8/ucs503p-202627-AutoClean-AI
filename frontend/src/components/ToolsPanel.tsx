import { useState } from "react";

interface Props {
  checkedCount: number;
  onCombine: (mode: "concat" | "merge", on: string | null) => Promise<void>;
  selectedId: string | null;
  onSynthetic: (nRows: number, augment: boolean) => Promise<void>;
  busy: boolean;
}

export default function ToolsPanel({ checkedCount, onCombine, selectedId, onSynthetic, busy }: Props) {
  const [mode, setMode] = useState<"concat" | "merge">("concat");
  const [joinKey, setJoinKey] = useState("");
  const [nRows, setNRows] = useState(100);

  return (
    <div className="tools-panel">
      <div className="tool-block">
        <h4>Combine datasets</h4>
        <p className="hint">Check 2+ datasets in the list above, then combine them into one.</p>
        <div className="tool-controls">
          <select value={mode} onChange={(e) => setMode(e.target.value as "concat" | "merge")}>
            <option value="concat">Stack rows (concat)</option>
            <option value="merge">Join on key (merge)</option>
          </select>
          {mode === "merge" && (
            <input placeholder="join column name" value={joinKey} onChange={(e) => setJoinKey(e.target.value)} />
          )}
          <button
            disabled={checkedCount < 2 || busy || (mode === "merge" && !joinKey)}
            onClick={() => void onCombine(mode, mode === "merge" ? joinKey : null)}
          >
            Combine {checkedCount >= 2 ? `(${checkedCount} selected)` : ""}
          </button>
        </div>
      </div>

      <div className="tool-block">
        <h4>Generate synthetic data</h4>
        <p className="hint">
          {selectedId ? "Sample new rows from the selected dataset's per-column distributions." : "Select a dataset first."}
        </p>
        <div className="tool-controls">
          <input
            type="number"
            min={1}
            max={10000}
            value={nRows}
            onChange={(e) => setNRows(Number(e.target.value))}
          />
          <button disabled={!selectedId || busy} onClick={() => void onSynthetic(nRows, false)}>
            Generate standalone
          </button>
          <button disabled={!selectedId || busy} onClick={() => void onSynthetic(nRows, true)}>
            Augment selected dataset
          </button>
        </div>
      </div>
    </div>
  );
}
