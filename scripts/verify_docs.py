"""Check the headline portfolio figures against the published aggregates.

This deliberately checks only claims that are used in the README and interview
summary. It does not turn the exploratory report into a generated document.
"""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "outputs_public"


def rows(name: str) -> list[dict[str, str]]:
    with (PUBLIC / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def require(path: str, *claims: str) -> None:
    content = (ROOT / path).read_text(encoding="utf-8")
    for claim in claims:
        if claim not in content:
            raise AssertionError(f"{path}: missing or stale claim {claim!r}")


def main() -> None:
    overview = {row["split"]: row for row in rows("overview.csv")}
    strata = {row["length_stratum"]: row for row in rows("length_strata.csv") if row["split"] == "train"}
    opportunities = rows("opportunities_top30.csv")
    category = {row["category"]: row for row in rows("category_residuals.csv")}

    total_requests = sum(int(row["requests"]) for row in overview.values())
    total_exposures = sum(int(row["exposures"]) for row in overview.values())
    total_clicks = sum(int(row["clicks"]) for row in overview.values())
    train_requests = int(overview["train"]["requests"])
    train_exposures = int(overview["train"]["exposures"])
    long = strata["100+"]
    short = strata["01-10"]
    long_request_share = int(long["requests"]) / train_requests
    long_exposure_share = int(long["exposures"]) / train_exposures
    opportunity_gap = sum(float(row["gap_clicks"]) for row in opportunities)

    require(
        "README.md",
        f"{total_requests:,}",
        f"{total_exposures:,}",
        f"{long_request_share:.1%}",
        f"{long_exposure_share:.1%}",
        f"{int(short['clicks']) / int(short['exposures']):.2%}",
        f"{int(long['clicks']) / int(long['exposures']):.2%}",
        f"{opportunity_gap:,.0f}",
    )
    require(
        "docs/interview-release-v1.md",
        f"{total_requests:,}",
        f"{total_exposures:,}",
        f"{total_clicks:,}",
        f"{opportunity_gap:,.0f}",
    )
    require(
        "docs/analysis-report.md",
        f"{train_requests:,}",
        f"{long_request_share:.1%}",
        f"{long_exposure_share:.1%}",
        f"{float(category['女装']['gap_pp']):.2f}pp",
    )
    print("Headline figures match the public aggregates.")


if __name__ == "__main__":
    main()
