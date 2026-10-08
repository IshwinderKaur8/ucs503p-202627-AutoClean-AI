"""Load raw uploaded files into a pandas DataFrame without guessing away data.

Ingestion is deliberately conservative: it only figures out *how to parse*
the file (encoding, delimiter, sheet). It does not coerce types or drop
rows/columns — that is cleaning's job, and it must be auditable.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

SUPPORTED_EXTENSIONS = {".csv", ".tsv", ".xlsx", ".xls", ".json"}

# Encodings tried in order; utf-8-sig handles BOM-prefixed Excel exports.
_CANDIDATE_ENCODINGS = ["utf-8-sig", "utf-8", "cp1252", "latin1"]


class UnsupportedFileType(ValueError):
    pass


class IngestionError(RuntimeError):
    pass


@dataclass
class IngestResult:
    dataframe: pd.DataFrame
    source_format: str
    encoding_used: str | None
    delimiter_used: str | None
    sheet_used: str | None
    warnings: list[str]


def _detect_encoding(raw: bytes) -> str:
    for enc in _CANDIDATE_ENCODINGS:
        try:
            raw.decode(enc)
            return enc
        except (UnicodeDecodeError, LookupError):
            continue
    raise IngestionError(
        "Could not decode file with any of the supported encodings: "
        f"{_CANDIDATE_ENCODINGS}"
    )


def _sniff_delimiter(sample_text: str) -> str:
    try:
        dialect = csv.Sniffer().sniff(sample_text, delimiters=[",", ";", "\t", "|"])
        return dialect.delimiter
    except csv.Error:
        return ","


def _load_csv(raw: bytes, warnings: list[str]) -> tuple[pd.DataFrame, str, str]:
    encoding = _detect_encoding(raw)
    text = raw.decode(encoding)
    sample = text[:8192]
    delimiter = _sniff_delimiter(sample)
    df = pd.read_csv(io.StringIO(text), sep=delimiter, dtype=str, keep_default_na=True)
    if df.shape[1] == 1 and delimiter != ",":
        warnings.append(
            f"Delimiter sniffing chose '{delimiter}' but result has a single column; "
            "verify the file is not malformed."
        )
    return df, encoding, delimiter


def _load_excel(raw: bytes, filename: str, warnings: list[str]) -> tuple[pd.DataFrame, str]:
    excel_file = pd.ExcelFile(io.BytesIO(raw))
    sheet = excel_file.sheet_names[0]
    if len(excel_file.sheet_names) > 1:
        warnings.append(
            f"Workbook has {len(excel_file.sheet_names)} sheets; only the first "
            f"sheet ('{sheet}') was loaded. Other sheets: {excel_file.sheet_names[1:]}"
        )
    df = excel_file.parse(sheet_name=sheet, dtype=str)
    return df, sheet


def _load_json(raw: bytes, warnings: list[str]) -> tuple[pd.DataFrame, str]:
    encoding = _detect_encoding(raw)
    text = raw.decode(encoding)
    df = pd.read_json(io.StringIO(text), dtype=False)
    return df, encoding


def ingest(filename: str, raw: bytes) -> IngestResult:
    """Parse an uploaded file's raw bytes into a DataFrame.

    All columns are loaded as strings/object dtype on purpose: forcing a
    guessed numeric/datetime dtype here can silently mangle values (e.g.
    leading zeros in IDs, mixed-format dates). Type inference happens later
    in cleaning.infer_and_coerce_types, where every coercion is reported.
    """
    if not raw:
        raise IngestionError("Uploaded file is empty.")

    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileType(
            f"Unsupported file extension '{ext}'. Supported: {sorted(SUPPORTED_EXTENSIONS)}"
        )

    warnings: list[str] = []

    if ext in (".csv", ".tsv"):
        df, encoding, delimiter = _load_csv(raw, warnings)
        source_format = "csv"
        sheet = None
    elif ext in (".xlsx", ".xls"):
        df, sheet = _load_excel(raw, filename, warnings)
        source_format = "excel"
        encoding = None
        delimiter = None
    elif ext == ".json":
        df, encoding = _load_json(raw, warnings)
        source_format = "json"
        delimiter = None
        sheet = None
    else:  # pragma: no cover - guarded by SUPPORTED_EXTENSIONS check above
        raise UnsupportedFileType(ext)

    if df.empty:
        warnings.append("Parsed dataframe has zero rows.")
    if len(df.columns) != len(set(df.columns)):
        dupes = df.columns[df.columns.duplicated()].tolist()
        warnings.append(f"Duplicate column names detected and will confuse downstream steps: {dupes}")

    # Normalize genuinely blank strings to NaN so missing-value detection
    # downstream is consistent, without touching any non-blank content.
    df = df.replace(r"^\s*$", pd.NA, regex=True)

    return IngestResult(
        dataframe=df,
        source_format=source_format,
        encoding_used=encoding,
        delimiter_used=delimiter,
        sheet_used=sheet,
        warnings=warnings,
    )
