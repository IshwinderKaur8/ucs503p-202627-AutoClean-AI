import type { DatasetSummary } from "../types";

interface Props {
  datasets: DatasetSummary[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  checkedIds: Set<string>;
  onToggleChecked: (id: string) => void;
}

export default function DatasetList({ datasets, selectedId, onSelect, checkedIds, onToggleChecked }: Props) {
  if (datasets.length === 0) {
    return <p className="hint">No datasets yet — upload a file to get started.</p>;
  }

  return (
    <table className="dataset-table">
      <thead>
        <tr>
          <th></th>
          <th>Name</th>
          <th>Rows</th>
          <th>Cols</th>
          <th>Source</th>
        </tr>
      </thead>
      <tbody>
        {datasets.map((d) => (
          <tr
            key={d.dataset_id}
            className={d.dataset_id === selectedId ? "selected-row" : ""}
            onClick={() => onSelect(d.dataset_id)}
          >
            <td onClick={(e) => e.stopPropagation()}>
              <input
                type="checkbox"
                checked={checkedIds.has(d.dataset_id)}
                onChange={() => onToggleChecked(d.dataset_id)}
              />
            </td>
            <td>{d.name}</td>
            <td>{d.rows}</td>
            <td>{d.columns}</td>
            <td>{d.parent_id ? "derived" : "uploaded"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
