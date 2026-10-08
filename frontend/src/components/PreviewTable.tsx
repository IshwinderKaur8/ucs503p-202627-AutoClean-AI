import type { PreviewResult } from "../types";

interface Props {
  preview: PreviewResult;
}

export default function PreviewTable({ preview }: Props) {
  return (
    <div className="preview-wrap">
      <p className="hint">
        Showing {preview.returned_rows} of {preview.total_rows} rows
      </p>
      <table className="preview-table">
        <thead>
          <tr>
            {preview.columns.map((c) => (
              <th key={c}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {preview.rows.map((row, i) => (
            <tr key={i}>
              {preview.columns.map((c) => (
                <td key={c}>{row[c] === null || row[c] === undefined ? <em>null</em> : String(row[c])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
