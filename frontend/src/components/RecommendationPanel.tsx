import { useState } from "react";
import type { RecommendationResult } from "../types";
import { getRecommendations } from "../api/client";
import AlgoCard from "./AlgoCard";

interface Props {
  datasetId: string;
  columnNames: string[];
}

const PROBLEM_TYPE_LABELS: Record<string, string> = {
  binary_classification: "binary classification",
  multiclass_classification: "multiclass classification",
  regression: "regression",
  clustering: "clustering (unsupervised)",
};

export default function RecommendationPanel({ datasetId, columnNames }: Props) {
  const [target, setTarget] = useState<string>("");
  const [result, setResult] = useState<RecommendationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchRecommendations = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getRecommendations(datasetId, target || null);
      setResult(res);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="recommend-controls">
        <select value={target} onChange={(e) => setTarget(e.target.value)}>
          <option value="">Auto-detect target column</option>
          {columnNames.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <button className="primary-button" onClick={() => void fetchRecommendations()} disabled={loading}>
          {loading ? "Analyzing..." : "Get algorithm recommendations"}
        </button>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {result && (
        <div>
          <p className="problem-type-banner">
            Detected problem type: <strong>{PROBLEM_TYPE_LABELS[result.problem_type] ?? result.problem_type}</strong>
            {result.target_column && (
              <>
                {" "}
                targeting <strong>{result.target_column}</strong>
                {result.target_auto_detected ? " (auto-detected)" : ""}
              </>
            )}
          </p>
          <div className="algo-grid">
            {result.recommendations.map((rec, i) => (
              <AlgoCard key={rec.algorithm} rec={rec} index={i} />
            ))}
          </div>
          {result.preprocessing_notes.length > 0 && (
            <ul className="preprocessing-notes">
              {result.preprocessing_notes.map((n, i) => (
                <li key={i}>{n}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
