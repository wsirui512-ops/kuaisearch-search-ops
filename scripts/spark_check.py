"""Compute the headline metrics with Apache Spark (local mode) and compare with DuckDB.

Purpose: prove the same numbers survive a different engine, and record what Spark costs
on this machine. It is an engineering check, not an argument that 3 GB needs a cluster.

Run:
    python scripts/spark_check.py            # both jobs
    python scripts/spark_check.py --light    # only the sessions-level job
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPARK_HOME = ROOT / ".spark" / "spark-4.3.0-bin-hadoop3"
PARQUET = ROOT / "exports" / "parquet"
# JAVA_HOME is optional: fall back to `java` on PATH when it is not set.
for candidate in (os.environ.get("JAVA_HOME"), r"D:\Java\jdk-21.0.12.1"):
    if candidate and Path(candidate, "bin", "java.exe").exists():
        os.environ["JAVA_HOME"] = candidate
        break

os.environ.setdefault("SPARK_HOME", str(SPARK_HOME))
os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)
os.environ.setdefault("SPARK_LOCAL_IP", "127.0.0.1")
sys.path.insert(0, str(ROOT / ".localdeps"))  # py4j (offline install)
sys.path.insert(0, str(SPARK_HOME / "python"))

TMP = ROOT / ".work" / "spark-tmp"
TMP.mkdir(parents=True, exist_ok=True)
os.environ["TEMP"] = str(TMP)
os.environ["TMP"] = str(TMP)

# On this Windows sandbox the gateway temp directory cannot always be removed; failing
# to clean it up must not abort the JVM connection.
import shutil  # noqa: E402
import tempfile  # noqa: E402
import uuid  # noqa: E402

_rmtree = shutil.rmtree


def _tolerant_rmtree(path, *args, **kwargs):
    try:
        _rmtree(path, *args, **kwargs)
    except PermissionError:
        pass


shutil.rmtree = _tolerant_rmtree


def _portable_mkdtemp(suffix: str = "", prefix: str = "tmp", dir: str | None = None) -> str:
    """tempfile.mkdtemp() creates a directory with a restrictive DACL that the sandboxed
    process cannot write into; os.makedirs() keeps the inherited permissions."""
    path = os.path.join(dir or tempfile.gettempdir(), f"{prefix}{uuid.uuid4().hex[:10]}{suffix}")
    os.makedirs(path, exist_ok=True)
    return path


tempfile.mkdtemp = _portable_mkdtemp

from pyspark.sql import SparkSession  # noqa: E402


def build_session() -> SparkSession:
    return (
        SparkSession.builder.appName("kuaisearch-check")
        .master("local[4]")
        .config("spark.driver.memory", "2g")
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.ui.enabled", "false")
        .config("spark.local.dir", str(TMP / "local"))
        .config("spark.sql.warehouse.dir", str(TMP / "warehouse"))
        .config("spark.driver.extraJavaOptions", f"-Djava.io.tmpdir={TMP.as_posix()}")
        .config("spark.sql.execution.arrow.pyspark.enabled", "false")
        .getOrCreate()
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--light", action="store_true")
    args = parser.parse_args()

    started = time.perf_counter()
    spark = build_session()
    spark.sparkContext.setLogLevel("ERROR")
    startup = time.perf_counter() - started
    print(f"spark {spark.version} started in {startup:.1f}s", flush=True)

    sessions = spark.read.parquet((PARQUET / "sessions.parquet").as_posix())
    sessions.createOrReplaceTempView("sessions")

    query_started = time.perf_counter()
    row = spark.sql(
        """
        SELECT
          sum(impressions) AS exposures,
          sum(clicks) AS clicks,
          sum(clicks) / sum(impressions) AS item_ctr,
          sum(CASE WHEN clicks > 0 THEN 1 ELSE 0 END) / count(*) AS request_click_rate,
          sum(CASE WHEN length_stratum = '100+' THEN impressions ELSE 0 END)
            / sum(impressions) AS long_list_exposure_share
        FROM sessions
        """
    ).first()
    light_seconds = time.perf_counter() - query_started
    values = {
        "exposures": float(row["exposures"]),
        "clicks": float(row["clicks"]),
        "item_ctr": float(row["item_ctr"]),
        "request_click_rate": float(row["request_click_rate"]),
        "long_list_exposure_share": float(row["long_list_exposure_share"]),
    }
    print(f"sessions job: {light_seconds:.1f}s", flush=True)
    for name, value in values.items():
        print(f"  {name:26s} {value}")

    result = {
        "spark_version": spark.version,
        "master": "local[4]",
        "startup_seconds": round(startup, 1),
        "sessions_job_seconds": round(light_seconds, 1),
        "values": values,
    }

    if not args.light:
        fact = spark.read.parquet((PARQUET / "fact.parquet").as_posix())
        fact.createOrReplaceTempView("fact")
        heavy_started = time.perf_counter()
        top = spark.sql(
            """
            WITH baseline AS (
              SELECT length_stratum, sum(clicks) / sum(impressions) AS ctr
              FROM sessions WHERE split = 'train'
              GROUP BY length_stratum
            ),
            mix AS (
              SELECT f.category, f.length_stratum, count(*) AS exposures, sum(f.is_clicked) AS clicks
              FROM fact f WHERE f.split = 'train'
              GROUP BY f.category, f.length_stratum
            )
            SELECT m.category, sum(m.exposures) AS exposures,
                   sum(m.clicks) AS clicks,
                   sum(m.clicks) / sum(m.exposures) AS item_ctr,
                   sum(m.exposures * b.ctr) / sum(m.exposures) AS expected_ctr
            FROM mix m JOIN baseline b USING (length_stratum)
            GROUP BY m.category
            ORDER BY exposures DESC
            LIMIT 5
            """
        ).collect()
        heavy_seconds = time.perf_counter() - heavy_started
        print(f"category job: {heavy_seconds:.1f}s", flush=True)
        for item in top:
            print(
                f"  {item['category']:<14} exp={item['exposures']:>9,} "
                f"ctr={item['item_ctr'] * 100:.3f}% expected={item['expected_ctr'] * 100:.3f}%"
            )
        result["category_job_seconds"] = round(heavy_seconds, 1)
        result["category_top5"] = [
            {
                "category": item["category"],
                "exposures": int(item["exposures"]),
                "clicks": int(item["clicks"]),
                "item_ctr": float(item["item_ctr"]),
                "expected_ctr": float(item["expected_ctr"]),
            }
            for item in top
        ]

    spark.stop()

    expected_path = ROOT / "outputs_public" / "engine_check.json"
    if expected_path.exists():
        expected = json.loads(expected_path.read_text(encoding="utf-8"))["metrics"]
        failures = []
        for name, value in values.items():
            reference = expected[name]["value"]
            if abs(value - reference) > max(1e-9, abs(reference) * 1e-9):
                failures.append(f"{name}: spark={value} duckdb={reference}")
        result["failed_checks"] = failures
        print("\nreconciliation vs engine_check.json:", "PASS" if not failures else failures)
    else:
        result["failed_checks"] = ["engine_check.json missing"]

    (ROOT / "outputs_public" / "spark_check.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("wrote outputs_public/spark_check.json")


if __name__ == "__main__":
    main()
