from __future__ import annotations

import math

import pandas as pd
import pytest

from wrinkle_life_risk.classification import classify_risk
from wrinkle_life_risk.config import RiskThresholds
from wrinkle_life_risk.pipeline import AnalysisOptions, run_analysis


def test_effective_measure_prefers_depth_then_height_over_two() -> None:
    data = pd.DataFrame(
        [
            {"length": 10.0, "width": 5.0, "depth": 0.4, "height": 2.0},
            {"length": 10.0, "width": 5.0, "depth": None, "height": 2.0},
        ]
    )

    result = run_analysis(data, AnalysisOptions(compute_fracture_life=False))

    assert result.data.loc[0, "effective_measure"] == 0.4
    assert result.data.loc[0, "effective_measure_source"] == "depth"
    assert result.data.loc[1, "effective_measure"] == 1.0
    assert result.data.loc[1, "effective_measure_source"] == "height/2"


def test_angle_and_risk_formula_uses_width() -> None:
    data = pd.DataFrame(
        [{"length": 10.0, "width": 5.0, "depth": 1.0, "height": None}]
    )

    result = run_analysis(data, AnalysisOptions(compute_fracture_life=False))

    expected_theta = math.degrees(math.atan(math.pi * 1.0 / 5.0))
    assert result.data.loc[0, "theta_degree"] == pytest.approx(expected_theta)
    assert result.data.loc[0, "risk_score"] == pytest.approx(expected_theta)


def test_default_risk_threshold_boundaries() -> None:
    frame = pd.DataFrame(
        {"risk_score": [0.49, 0.50, 2.99, 3.00, 14.99, 15.00, float("nan")]}
    )

    classified, _ = classify_risk(frame)

    assert classified["risk_class"].tolist() == [
        "LOW",
        "MEDIUM",
        "MEDIUM",
        "HIGH",
        "HIGH",
        "CRITICAL",
        "INCOMPLETE",
    ]


def test_only_medium_high_critical_receive_fracture_outputs() -> None:
    data = pd.DataFrame(
        [
            {"defect_id": "LOW", "length": 20.0, "width": 10.0, "depth": 0.10},
            {"defect_id": "MEDIUM", "length": 20.0, "width": 5.0, "depth": 0.20},
            {"defect_id": "HIGH", "length": 20.0, "width": 5.0, "depth": 0.50},
            {"defect_id": "CRITICAL", "length": 20.0, "width": 5.0, "depth": 1.00},
        ]
    )

    result = run_analysis(data)
    output = result.data.set_index("defect_id")

    assert output.loc["LOW", "fracture_status"] == "NOT_SELECTED_LOW_RISK"
    assert math.isnan(output.loc["LOW", "Delta_K_MPa_sqrt_m"])
    for defect_id in ("MEDIUM", "HIGH", "CRITICAL"):
        assert output.loc[defect_id, "fracture_status"] == "FRACTURE_SCREENING"
        assert output.loc[defect_id, "Delta_K_MPa_sqrt_m"] > 0


def test_delta_k_uses_effective_size_over_two_and_mm_to_m() -> None:
    data = pd.DataFrame(
        [{"defect_id": "C", "length": 20.0, "width": 5.0, "depth": 1.0}]
    )

    result = run_analysis(data)
    row = result.data.iloc[0]

    assert row["Assumed_Crack_mm"] == pytest.approx(0.5)
    assert row["Assumed_Crack_m"] == pytest.approx(0.0005)
    expected = 1.12 * 250.0 * math.sqrt(math.pi * 0.0005)
    assert row["Delta_K_MPa_sqrt_m"] == pytest.approx(expected)


def test_invalid_width_is_excluded() -> None:
    data = pd.DataFrame(
        [{"length": 10.0, "width": 0.0, "depth": 0.5, "height": None}]
    )

    result = run_analysis(data)

    assert not bool(result.data.loc[0, "is_complete_for_risk"])
    assert result.data.loc[0, "risk_class"] == "INCOMPLETE"
    assert "invalid_width" in result.data.loc[0, "data_quality_status"]


def test_threshold_order_is_validated() -> None:
    with pytest.raises(ValueError):
        RiskThresholds(medium_min=3.0, high_min=0.5, critical_min=15.0)
