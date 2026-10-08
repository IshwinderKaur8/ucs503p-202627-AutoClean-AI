import type { ColumnProfile } from "../types";

interface Props {
  profile: ColumnProfile[];
}

const KIND_COLORS: Record<string, string> = {
  numeric: "#2563eb",
  boolean: "#7c3aed",
  datetime: "#059669",
  categorical: "#d97706",
  text: "#6b7280",
  identifier: "#dc2626",
  empty: "#9ca3af",
};

export default function ColumnProfileTable({ profile }: Props) {
  if (profile.length === 0) return null;
  return (
    <table className="profile-table">
      <thead>
        <tr>
          <th>Column</th>
          <th>Type</th>
          <th>Missing</th>
          <th>Unique</th>
          <th>Outliers</th>
          <th>Sample values</th>
        </tr>
      </thead>
      <tbody>
        {profile.map((col) => (
          <tr key={col.name}>
            <td>{col.name}</td>
            <td>
              <span className="kind-badge" style={{ background: KIND_COLORS[col.kind] ?? "#9ca3af" }}>
                {col.kind}
              </span>
            </td>
            <td>
              {col.null_count} ({(col.null_ratio * 100).toFixed(1)}%)
            </td>
            <td>{col.unique_count}</td>
            <td>{col.outlier_count > 0 ? col.outlier_count : "-"}</td>
            <td className="sample-values">{col.sample_values.join(", ")}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
