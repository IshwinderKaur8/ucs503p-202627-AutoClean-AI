import { downloadUrl } from "../api/client";

interface Props {
  datasetId: string;
}

export default function DownloadResult({ datasetId }: Props) {
  return (
    <div className="download-row">
      <span>Download cleaned data:</span>
      <a className="download-link" href={downloadUrl(datasetId, "csv")} download>
        CSV
      </a>
      <a className="download-link" href={downloadUrl(datasetId, "xlsx")} download>
        Excel
      </a>
      <a className="download-link" href={downloadUrl(datasetId, "json")} download>
        JSON
      </a>
    </div>
  );
}
