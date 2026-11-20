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

**阻塞原因（已逐项核实，2026-11-20）**

1. **ClickHouse 没有官方 Windows 原生版**：官方只提供 Linux / macOS / Docker / Cloud。实测两个下载入口都被拒：`builds.clickhouse.com/master/win64/clickhouse.exe` → 403，GitHub Release 的 `clickhouse-windows-amd64.exe` → 404。把 ClickHouse 嵌进 Python 的 `chdb` 也**没有任何 Windows wheel**（扫过全部版本）。
2. **本机没有容器/虚拟化层**：未安装 Docker；`wsl` 命令存在，但 `wsl -l -v` 返回 **E_ACCESSDENIED**（WSL 功能未启用）。
3. **当前会话无管理员权限**：`IsInRole(Administrator) = False`，`Get-CimInstance` 同样被拒绝。启用 WSL2/Hyper-V、安装 Docker Desktop 都需要管理员 + 重启。

所以不是"安装包下载失败"，而是**缺一层 Linux 运行环境，而补上它需要管理员权限**。

**解决方案（按成本排序）**

| 方案 | 成本 | 说明 |
| --- | --- | --- |
| A. 启用 WSL2 + 官方单文件二进制（推荐） | 管理员 + 1 次重启，约 40–60 分钟 | `wsl --install -d Ubuntu` → 进 Ubuntu 执行 `curl https://clickhouse.com/ | sh` → 直接 `clickhouse local` 读 Parquet，**不需要 Docker** |
| B. GitHub Codespaces | 0 安装，浏览器即可 | 云端 Linux 里装 ClickHouse，上传 `exports/parquet` 或现场生成，跑同一套 SQL |
| C. ClickHouse Cloud 免费试用 | 注册账号（可能要信用卡） | 走 HTTP 接口把 Parquet POST 进去；`file()` 在 Cloud 被禁用，需改用 HTTP 上传 |
| D. 保持现状 | 0 | 三路对账已通过；简历不写 ClickHouse，只写"SQL 与对账脚本已备好，环境受限未部署" |

方案 A 的对账命令（不需要建表，直接读 Parquet）：

```bash
cd /mnt/c/Users/26431/Documents/ChatGPT/项目二
./clickhouse local --query "
SELECT sum(impressions), sum(clicks), sum(clicks)/sum(impressions),
       countIf(clicks>0)/count(),
       sumIf(impressions, length_stratum='100+')/sum(impressions)
FROM file('exports/parquet/sessions.parquet','Parquet')"
```

预期：`17800904 / 680790 / 0.038245 / 0.531033 / 0.402566`。

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

## 4. Spark：本机已跑通，但不当主线

### 4.1 实测结果（2026-11-20，local[4]）

| 项 | 值 |
| --- | --- |
| 环境 | Java 21.0.12.1 + Apache Spark 4.3.0（bin-hadoop3）+ py4j 0.10.9.9 |
| 启动耗时 | 5.8 s |
| sessions 聚合（556k 行） | 1.4 s |
| 类目 × 条数分层（17.8M 曝光） | 2.2 s |
| 5 个核心指标与 DuckDB 对账 | **PASS（完全一致）** |
| 结果文件 | `outputs_public/spark_check.json` |

**反直觉但重要**：这台机器装不了 ClickHouse（缺容器/管理员），却**能跑 Spark**——它只需要 Java，不需要 Docker、不需要 WSL、不需要管理员。所以"用 Spark 替代 ClickHouse"在环境上是成立的。

### 4.2 但仍然不建议把它当主线

- 3 GB 数据用 Spark 是过度设计：DuckDB 从原始 JSONL 重建全部 marts 只要 40 秒，Spark 光启动就 5.8 秒、还要额外 1.6 GB 磁盘。
- 上面的耗时**不能直接比较**：DuckDB 那 40 秒包含解析 3 GB JSONL、建 17.8M 行曝光表和全部导出；Spark 只是在已转好的 Parquet 上做聚合。
- 面试官会问"为什么这么小的数据用 Spark"，答不好是负分。

### 4.3 什么时候真该用 Spark

- 处理官方**全量 107 GB**（而不是 Lite）：Parquet 分区（`split` / 相对时间段）+ Spark SQL 重跑同一套 marts，给出"全量 vs Lite"的差异与耗时；
- 目标 JD 明确写了 Spark / Hive / 离线数仓；
- 需要多机横向扩展或已有集群。

### 4.4 Windows 踩坑记录（已解决，可复现）

| 坑 | 现象 | 解决 |
| --- | --- | --- |
| SPARK_HOME 含中文 | `spark-submit.cmd` → `ClassNotFoundException: SparkSubmit` | 用直接调用 `java -cp "%SPARK_HOME%\jars\*"` 的 wrapper 替换 `bin/spark-submit.cmd`（`scripts/setup_spark.ps1` 自动处理） |
| py4j 不再自带 | `ModuleNotFoundError: py4j` | 单独安装 py4j |
| `tempfile.mkdtemp` 目录不可写 | 启动时报 `Permission denied` | 用 `os.makedirs` 替代 mkdtemp（脚本内已处理） |
| 缺 winutils | 启动 WARN | 本地读写 Parquet 不需要，可忽略 |
| 内存/分区 | 默认配置偏大 | `driver 2g`、`shuffle.partitions=4` |

### 4.5 结论：怎么选

| 想要的东西 | 选什么 | 理由 |
| --- | --- | --- |
| 面试讲"服务层/并发查询" | ClickHouse（等 Docker/WSL） | 列存服务端、点查快，链路完整 |
| 面试讲"离线大数据/数仓" | Spark（本机即可跑） | 只要 Java；能讲分区、shuffle、对账 |
| 只想把项目做扎实 | 都不加 | DuckDB + SQL + 看板已经够用，硬加反而稀释重点 |

如果只能加一个、且环境不改：**加 Spark**（能真正跑起来、能出对账结果），但必须按 4.3 的框架讲，不能吹"大数据量"。

## 5. 面试怎么讲这段（30 秒版）

> "数据 3GB、1700 万行曝光，我用 DuckDB 单机跑完整管道，几分钟能重建，保证别人 clone 下来能复现。没有为了简历硬上 Spark——3GB 上 Spark 是负分。ClickHouse 我留了明确的升级路径：结果要做成并发看板服务时再上，并且要求两边指标对账为 0。"
