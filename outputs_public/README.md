# 可公开聚合结果

本目录是仓库里唯一发布的数据层：全部为聚合指标，**不含用户级记录、不含完整 query 字典**。

| 文件 | 内容 | 主要用途 |
| --- | --- | --- |
| `overview.csv` | 按 split 的请求/用户/曝光/点击/购买与两种点击率 | 总览卡片 |
| `length_strata.csv` | 按每次展示条数分层的请求、曝光、点击率 | 核心分析页 |
| `stratum_baseline.csv` | 条数分层基准 CTR（仅 train） | 计算期望点击 |
| `category_metrics.csv` | 一级类目曝光/点击/购买/用户/请求 | 类目效率 |
| `category_residuals.csv` | 类目同条数期望 CTR、gap_pp、缺口点击（train） | 类目缺口排序 |
| `intent_metrics.csv` | 需求标签的请求/曝光/点击率/购买率 | 需求结构 |
| `intent_residuals.csv` | 需求标签的同条数残差（train） | 标签校准 |
| `opportunities_top30.csv` | Top 30 机会词（含 query 文本、置信区间、p/q、测试段复核） | 机会清单 |
| `relative_time_metrics.csv` | 20 个相对时间区间的量与点击率 | 相对时间页 |
| `age_metrics.csv` | 年龄段结构（字段可信度低，仅结构描述） | 可选页 |
| `relevance_coverage.csv` | 相关性标注 score 分布 | 说明覆盖不足 |
| `relevance_summary.csv` | 标注对数、覆盖 query 数 | 同上 |
| `review_coverage_summary.csv` | Top 10 词的审阅商品数、平均二字覆盖率、零覆盖占比 | 承接证据（不含标题） |
| `engine_check.json` | 三路对账结果（DuckDB / Parquet / Python）与耗时 | 数字可复现的证明 |
| `sensitivity_position.csv` | 条数 × 位置双层基准下 Top 30 的缺口变化 | 排除"位置造成缺口"的解释 |
| `spark_check.json` | Spark 本地模式复算结果、耗时与对账状态 | 第四引擎对账 |
| `quality.json` | 质量审计结果 | 数据可信度 |

重新生成：`python run.py`（会同时重建 `outputs/` 本地全量与 `data/processed/kuaisearch.duckdb`）。

## 发布规则

- 可以发布：聚合指标、脱敏后的高频泛词（Top 30）。
- 不发布：用户级明细、完整 query 字典（`outputs/query_metrics.csv`）、原始 JSONL、DuckDB 文件。
- 引用前请核对数据集许可，并确认 query 文本不含品牌名/联系方式。
