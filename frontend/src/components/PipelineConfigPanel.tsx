import type { PipelineConfigIn } from "../types";

interface Props {
  config: PipelineConfigIn;
  onChange: (config: PipelineConfigIn) => void;
  onRun: () => void;
  running: boolean;
}

export default function PipelineConfigPanel({ config, onChange, onRun, running }: Props) {
  const set = <K extends keyof PipelineConfigIn>(key: K, value: PipelineConfigIn[K]) =>
    onChange({ ...config, [key]: value });

  return (
    <div className="config-panel">
      <div className="config-grid">
        <label>
          Numeric missing-value strategy
          <select value={config.numeric_impute_strategy} onChange={(e) => set("numeric_impute_strategy", e.target.value)}>
            <option value="median">Median</option>
            <option value="mean">Mean</option>
            <option value="skip">Leave missing</option>
          </select>
        </label>

        <label>
          Categorical missing-value strategy
          <select value={config.categorical_impute_strategy} onChange={(e) => set("categorical_impute_strategy", e.target.value)}>
            <option value="mode">Most frequent (mode)</option>
            <option value="skip">Leave missing</option>
          </select>
        </label>

        <label>
          Outlier handling
          <select
            value={config.outlier_default_strategy}
            onChange={(e) => set("outlier_default_strategy", e.target.value as PipelineConfigIn["outlier_default_strategy"])}
          >
            <option value="flag">Flag only (keep all rows)</option>
            <option value="clip">Clip to bounds</option>
            <option value="remove">Remove rows</option>
            <option value="skip">Skip detection</option>
          </select>
        </label>

        <label>
          Scaling method
          <select value={config.scale_method} onChange={(e) => set("scale_method", e.target.value as PipelineConfigIn["scale_method"])}>
            <option value="standard">Standard (z-score)</option>
            <option value="minmax">Min-Max (0-1)</option>
            <option value="robust">Robust (median/IQR)</option>
            <option value="none">None</option>
          </select>
        </label>

        <label>
          One-hot max cardinality
          <input
            type="number"
            min={2}
            max={200}
            value={config.one_hot_max_cardinality}
            onChange={(e) => set("one_hot_max_cardinality", Number(e.target.value))}
          />
        </label>

        <label className="checkbox-label">
          <input type="checkbox" checked={config.dedupe} onChange={(e) => set("dedupe", e.target.checked)} />
          Remove exact duplicate rows
        </label>

        <label className="checkbox-label">
          <input type="checkbox" checked={config.encode} onChange={(e) => set("encode", e.target.checked)} />
          Encode categorical columns
        </label>

        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={config.engineer_features}
            onChange={(e) => set("engineer_features", e.target.checked)}
          />
          Add derived features (datetime parts, text length)
        </label>
      </div>

      <button className="primary-button" onClick={onRun} disabled={running}>
        {running ? "Running pipeline..." : "Run cleaning pipeline"}
      </button>
    </div>
  );
}
