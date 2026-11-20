# 技术栈选型与验证记录

原则：**只写实际跑过、能解释取舍的技术**。没跑过的不进简历，也不写进"已完成"。

## 1. 实际运行的技术栈

| 组件 | 版本 | 角色 | 是否已验证 |
| --- | --- | --- | --- |
| Python | 3.13 | 下载校验、管道编排、统计与导出 | ✅ 已运行 |
| DuckDB | 2.0.0 | 单机列存分析库，17.8M 曝光聚合 | ✅ 已运行 |
| SQL | DuckDB 方言 | staging / intermediate / marts 三层 | ✅ 已运行 |
| Power BI Desktop | 最新 | 展示层（5 页看板） | ⏳ 待制作（本仓库已给出导入数据与搭建手册） |
| ClickHouse | — | 服务层复算与耗时对比 | ⛔ 未安装（本机无 Docker/WSL2） |
| Spark | — | 未使用 | ⛔ 不做 |

## 2. 为什么主引擎是 DuckDB

- 数据 3.08 GB、17.8M 曝光行，单机足够；DuckDB 直接读 JSONL、列存、无需部署。
- 全量重建（读 3GB JSONL + 建 17.8M 行曝光表 + 全部聚合 + 导出）在 4 线程、3GB 内存上限下**约 40 秒**（实测），开发迭代可以接受。
- 成本：没有集群、没有服务、没有运维，作品集复现门槛低。

**取舍说明（面试会被问）**：DuckDB 不适合多用户并发查询和高频点查；如果要把结果做成在线看板服务，需要 ClickHouse / Doris 这类 OLAP 引擎。这正是下面 ClickHouse 的位置。

## 3. ClickHouse：为什么不在这版里

**阻塞原因**：本机没有 Docker，也没有 WSL2；Windows 原生安装 ClickHouse 需要额外环境，属于本次交付之外的成本。

**计划（P5，1.5 人天，装好 Docker 后）**

1. 把 `fact`（曝光级）导出成 Parquet，`clickhouse-local` 或容器内 `clickhouse-server` 建表导入。
2. 用同一批 SQL 口径复算 5 个核心指标：总曝光、总点击、商品点击率、请求点击率、Top 10 机会的期望点击。
3. 与 DuckDB 结果逐项对账，要求**差异为 0**（或仅浮点尾差）。
4. 记录 3 个典型查询的耗时（如"按类目 × 条数分层"），做一张 DuckDB vs ClickHouse 对比表。
5. 在报告里写清楚：ClickHouse 在这里的价值是**服务层/并发**，不是"数据大到 DuckDB 跑不动"。

**如果最终装不上 Docker**：如实降级——用 `EXPLAIN ANALYZE` + 纯 Python 聚合做交叉校验（同样能证明数字可复现），并在 README 写明"未使用 ClickHouse"。**不要把没跑过的技术写进简历。**

## 3.1 本版实际完成的验证（2026-11-20）

ClickHouse 仍未运行（环境阻塞已核实：无 Docker、WSL 被系统禁用、Windows 单文件二进制下载被拒）。但把"可验证"的部分做了，并留下 30 分钟可跑完的资产：

**已生成**

| 资产 | 说明 |
| --- | --- |
| `exports/parquet/sessions.parquet` | 555,553 行，4.9 MB |
| `exports/parquet/fact.parquet` | 17,800,904 行，159.2 MB（ZSTD） |
| `sql/clickhouse/01_create.sql` | ClickHouse 建库建表 DDL（MergeTree） |
| `sql/clickhouse/02_load.sql` | 从 Parquet 装载 |
| `sql/clickhouse/03_verify.sql` | 5 个核心指标的 ClickHouse 版本 SQL + 期望值 |
| `scripts/verify_engines.py` | 三路对账：DuckDB(库) / DuckDB(Parquet) / Python(聚合 CSV) |
| `outputs_public/engine_check.json` | 对账结果与耗时（可公开） |

**对账结果**：5 个指标（曝光、点击、商品点击率、请求点击率、100+ 条曝光占比）三路完全一致，**failed_checks = 0**。

| 指标 | 值 | DuckDB(库) | DuckDB(Parquet) |
| --- | --- | --- | --- |
| exposures | 17,800,904 | 0.8 ms | 2.5 ms |
| clicks | 680,790 | 0.8 ms | 2.5 ms |
| item_ctr | 3.8245% | 1.3 ms | 3.3 ms |
| request_click_rate | 53.103% | 2.0 ms | 4.0 ms |
| long_list_exposure_share | 40.257% | 1.7 ms | 4.4 ms |

> 说明：这是已预热的小查询，Parquet 反而略慢（多一层反序列化），**不构成引擎对比结论**。真正的对比要等 ClickHouse 装载后按同一 SQL 计 3 次取中位数。

**装好 Docker 后的收尾（30–60 分钟）**

```powershell
docker run -d --name ch -p 8123:8123 -p 9000:9000 clickhouse/clickhouse-server:latest
python scripts/export_parquet.py
docker exec -i ch clickhouse-client --multiquery < sql/clickhouse/01_create.sql
docker exec -i ch clickhouse-client --multiquery < sql/clickhouse/02_load.sql
docker exec -i ch clickhouse-client --multiquery < sql/clickhouse/03_verify.sql
```

把第 5 步的结果与 `outputs_public/engine_check.json` 对比，差异为 0 后，再把"ClickHouse 交叉校验"写进简历。

## 4. Spark：为什么不做

- 3 GB 数据用 Spark 属于过度设计，面试官第一个问题就是"为什么不用 DuckDB/单机"。
- Windows 上跑 PySpark 需要 Java 17 + winutils/hadoop.dll，环境成本高、收益低。
- 数据运营岗的 JD 里 Spark 出现频率远低于 SQL / BI 工具。

**如果未来一定要写 Spark**：只有一条合理路径——处理官方全量（约 107 GB）而不是 Lite。届时用 Parquet 分区（`split` / 相对时间段）+ Spark SQL 重跑同一套 marts，并给出"全量 vs Lite 的指标差异与耗时"。在此之前不碰。

## 5. 面试怎么讲这段（30 秒版）

> "数据 3GB、1700 万行曝光，我用 DuckDB 单机跑完整管道，几分钟能重建，保证别人 clone 下来能复现。没有为了简历硬上 Spark——3GB 上 Spark 是负分。ClickHouse 我留了明确的升级路径：结果要做成并发看板服务时再上，并且要求两边指标对账为 0。"
