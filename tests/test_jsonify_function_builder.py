# External
from __future__ import annotations
import numpy as np
import pandas as pd
import pytest
from typing import Any, Dict, List, Tuple

# Own
from pathjson import JsonifyFunctionBuilder


@pytest.fixture
def dataframe_and_output() -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
    converted = [
        {
            "A": 1,
            "B": [
                {"c": 1, "d": 1},
                {"c": 2, "d": 2},
            ],
            "C": [1, 2],
        },
        {
            "A": 2,
            "B": [
                {"c": 3, "d": 3},
            ],
            "C": [4, 5, 6],
        },
    ]

    df: pd.DataFrame = pd.DataFrame(
        [
            {
                "$.A": 1,
                "$.B[0].c": 1,
                "$.B[0].d": 1,
                "$.B[1].c": 2,
                "$.B[1].d": 2,
                "$.C[0]": 1,
                "$.C[1]": 2,
            },
            {
                "$.A": 2,
                "$.B[0].c": 3,
                "$.B[0].d": 3,
                "$.C[0]": 4,
                "$.C[1]": 5,
                "$.C[2]": 6,
            },
        ],
    )

    df.replace(np.nan, None, inplace=True)

    return df, converted


def test_jsonify_function_builder_functional(
    dataframe_and_output: Tuple[pd.DataFrame, List[Dict[str, Any]]],
) -> None:
    df, expected_output = dataframe_and_output

    jsonify_function = JsonifyFunctionBuilder[pd.Series](df.columns).build()

    result = list(map(lambda t: jsonify_function(t[1]), df.iterrows()))

    assert result == expected_output
