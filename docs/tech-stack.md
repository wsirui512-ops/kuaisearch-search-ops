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

## 4. Spark：为什么不做

- 3 GB 数据用 Spark 属于过度设计，面试官第一个问题就是"为什么不用 DuckDB/单机"。
- Windows 上跑 PySpark 需要 Java 17 + winutils/hadoop.dll，环境成本高、收益低。
- 数据运营岗的 JD 里 Spark 出现频率远低于 SQL / BI 工具。

**如果未来一定要写 Spark**：只有一条合理路径——处理官方全量（约 107 GB）而不是 Lite。届时用 Parquet 分区（`split` / 相对时间段）+ Spark SQL 重跑同一套 marts，并给出"全量 vs Lite 的指标差异与耗时"。在此之前不碰。

## 5. 面试怎么讲这段（30 秒版）

> "数据 3GB、1700 万行曝光，我用 DuckDB 单机跑完整管道，几分钟能重建，保证别人 clone 下来能复现。没有为了简历硬上 Spark——3GB 上 Spark 是负分。ClickHouse 我留了明确的升级路径：结果要做成并发看板服务时再上，并且要求两边指标对账为 0。"
