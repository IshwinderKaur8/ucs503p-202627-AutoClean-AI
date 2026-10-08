import { useRef, useState } from "react";

interface Props {
  onUpload: (files: File[]) => Promise<void>;
}

export default function FileUpload({ onUpload }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const handleFiles = async (fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return;
    setBusy(true);
    try {
      await onUpload(Array.from(fileList));
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  return (
    <div
      className={`upload-dropzone ${dragOver ? "drag-over" : ""}`}
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragOver(false);
        void handleFiles(e.dataTransfer.files);
      }}
      onClick={() => inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        multiple
        accept=".csv,.tsv,.xlsx,.xls,.json"
        style={{ display: "none" }}
        onChange={(e) => void handleFiles(e.target.files)}
      />
      <p>{busy ? "Uploading..." : "Drop CSV / Excel / JSON files here, or click to browse"}</p>
      <p className="hint">Multiple files supported — combine them later if needed.</p>
    </div>
  );
}
