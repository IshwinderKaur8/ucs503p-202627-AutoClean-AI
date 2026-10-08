from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PipelineConfigIn(BaseModel):
    coerce_types: bool = True

    numeric_impute_strategy: str = "median"
    categorical_impute_strategy: str = "mode"
    datetime_impute_strategy: str = "ffill_bfill"
    impute_overrides: dict[str, str] = Field(default_factory=dict)

    dedupe: bool = False
    dedupe_subset: list[str] | None = None

    outlier_default_strategy: Literal["flag", "clip", "remove", "skip"] = "flag"
    outlier_overrides: dict[str, Literal["flag", "clip", "remove", "skip"]] = Field(default_factory=dict)

    encode: bool = True
    one_hot_max_cardinality: int = 15
    encoding_overrides: dict[str, Literal["onehot", "label", "skip"]] = Field(default_factory=dict)

    engineer_features: bool = True

    scale_method: Literal["standard", "minmax", "robust", "none"] = "standard"
    scale_columns: list[str] | None = None


class RunPipelineRequest(BaseModel):
    dataset_id: str
    config: PipelineConfigIn = Field(default_factory=PipelineConfigIn)
    result_name: str | None = None


class CombineRequest(BaseModel):
    dataset_ids: list[str]
    mode: Literal["concat", "merge"] = "concat"
    on: list[str] | None = None
    how: Literal["outer", "left", "right", "inner"] = "outer"
    result_name: str | None = None


class SyntheticRequest(BaseModel):
    dataset_id: str
    n_rows: int = 100
    seed: int | None = None
    augment: bool = False  # False = standalone synthetic dataset, True = append to source
    result_name: str | None = None
