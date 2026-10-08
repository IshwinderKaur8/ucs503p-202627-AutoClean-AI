import { useState } from "react";
import type { AuditTrail } from "../types";

interface Props {
  trail: AuditTrail;
  explanations?: { step_name: string; explanation: string }[];
}

export default function AuditTrailView({ trail, explanations }: Props) {
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  const toggle = (i: number) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });

  return (
    <div className="audit-trail">
      <div className="audit-summary">
        Started with <strong>{trail.original.rows}</strong> rows, <strong>{trail.original.columns}</strong> columns,{" "}
        <strong>{trail.original.nulls}</strong> missing values.
      </div>
      <ol className="audit-steps">
        {trail.steps.map((step, i) => {
          const explanation = explanations?.find((e) => e.step_name === step.step_name)?.explanation;
          return (
            <li key={i} className="audit-step">
              <div className="audit-step-header" onClick={() => toggle(i)}>
                <span className="step-name">{step.step_name}</span>
                <span className="step-deltas">
                  {step.rows_changed !== 0 && (
                    <span className={step.rows_changed < 0 ? "delta-neg" : "delta-pos"}>rows {step.rows_changed > 0 ? "+" : ""}{step.rows_changed}</span>
                  )}
                  {step.columns_changed !== 0 && <span className="delta-pos">cols +{step.columns_changed}</span>}
                  {step.nulls_before !== step.nulls_after && (
                    <span className="delta-neutral">nulls {step.nulls_before} → {step.nulls_after}</span>
                  )}
                  {step.warnings.length > 0 && <span className="delta-warn">{step.warnings.length} warning(s)</span>}
                </span>
              </div>
              {explanation && <p className="step-explanation">{explanation}</p>}
              {expanded.has(i) && (
                <div className="audit-step-details">
                  {step.warnings.length > 0 && (
                    <ul className="warnings-list">
                      {step.warnings.map((w, wi) => (
                        <li key={wi}>{w}</li>
                      ))}
                    </ul>
                  )}
                  <pre>{JSON.stringify(step.details, null, 2)}</pre>
                </div>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
