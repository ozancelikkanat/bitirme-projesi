"""Run wrinkle risk analysis from the command line."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from wrinkle_life_risk.pipeline import AnalysisOptions, run_analysis
from wrinkle_life_risk.sample_data import make_sample_dataframe


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if len(sys.argv) > 1:
        input_path = Path(sys.argv[1])
        data = pd.read_csv(input_path)
    else:
        data = make_sample_dataframe()

    result = run_analysis(
        data,
        AnalysisOptions(),
    )

    print(result.data.to_string(index=False))
    print()
    print("Summary:")
    for key, value in result.summary.items():
        print(f"- {key}: {value}")
    print(
        f"- thresholds: medium_min={result.thresholds.medium_min:.6g}, "
        f"high_min={result.thresholds.high_min:.6g}, "
        f"critical_min={result.thresholds.critical_min:.6g}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
