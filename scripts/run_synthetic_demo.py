# Copyright (c) 2026 Salesforce, Inc.
# SPDX-License-Identifier: CC-BY-NC-4.0
#
# Licensed under the Creative Commons Attribution-NonCommercial 4.0
# International License. See LICENSE.txt in the repository root.

"""Run the public synthetic demonstration without network access."""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from interviewsim.demo import run_synthetic_demo  # noqa: E402


PREPARED_INPUT = (
    ROOT
    / "examples"
    / "synthetic_examples"
    / "personalities"
    / "PERSONALITY_001"
    / "prepared_input.json"
)


def main() -> None:
    """Print a compact deterministic JSON summary."""

    summary = run_synthetic_demo(PREPARED_INPUT)
    print(json.dumps(summary, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
