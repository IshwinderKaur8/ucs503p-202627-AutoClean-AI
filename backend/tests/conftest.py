import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture
def messy_df() -> pd.DataFrame:
    return pd.DataFrame({
        "id": [1, 2, 3, 4, 5, 6, 7, 8],
        "age": ["25", "30", None, "45", "1000", "29", "31", "28"],
        "city": ["NYC", "LA", "NYC", None, "SF", "LA", "NYC", "SF"],
        "signup_date": ["2023-01-01", "2023-02-15", None, "2023-03-10", "2023-01-20", "2023-04-05", "2023-02-28", "2023-01-11"],
        "is_active": ["true", "false", "true", "true", "false", "true", "true", "false"],
    })
