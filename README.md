# 快手电商搜索需求与转化效率诊断

用 KuaiSearch-Lite 的真实搜索行为，回答一个运营问题：**哪些搜索需求有曝光、有需求，却没被结果页接住？**

> 555,553 次真实搜索 · 17,800,904 次商品曝光 · 102,086 名用户 · 278,615 个去重搜索词
> 数据来源：[KuaiSearch-Lite](https://huggingface.co/datasets/benchen4395/KuaiSearch)（2025 年 6 月后的快手电商搜索行为样本，Lite 为采样数据）

## 30 秒结论

**"高曝光低点击"多数不是搜索词的问题，而是结果列表太长。**

- 6.9% 的请求展示 ≥100 条商品，贡献 **40.3% 的曝光**；这些请求单件点击率只有 **2.19%**，但请求点击率高达 **84.1%**——用户点得到东西，大量商品在陪跑。
- 按"同展示条数"校准后，品类和需求标签之间的效率差距基本消失（女装差距从 0.78pp 收窄到 **0.25pp**）。
- 仍有 **124 个搜索词**在同条数基准下显著偏低（74 个 FDR 校正后 q<0.05），集中在泛品类词：鞋子、衣服、外套、裤子、手机壳、卫衣、上衣。Top 30 合计缺口约 **6,400 次点击**（约 1.0% 曝光）。

![结果条数与商品点击率](docs/images/chart_length_ctr.svg)

![点击缺口最大的搜索词](docs/images/chart_top_gap.svg)

## 关键数字

| 指标 | 训练段 | 测试段（时间外） |
| --- | --- | --- |
| 搜索请求 | 539,012 | 16,541 |
| 商品曝光 | 17,306,633 | 494,271 |
| 商品点击率（点击商品/曝光） | 3.83% | 3.80% |
| 请求点击率（有点击的请求/请求） | 53.16% | 51.12% |
| 购买请求率（有购买的请求/请求） | 8.81% | 8.83% |
| 平均展示条数 | 32.1 | 29.9 |

| 结构发现 | 数值 |
| --- | --- |
| 100+ 条列表的请求占比 | 6.9% |
| 100+ 条列表的曝光占比 | 40.3% |
| 1–10 条 vs 100+ 条的商品点击率 | 8.96% vs 2.19% |
| 通过样本门槛且存在正缺口的搜索词 | 124 个（74 个 q<0.05） |
| Top 30 缺口点击 | ~6,416 次 / 64.6 万曝光（~1.0%） |

## 已完成的验证

- **质量断言**：39 项对账（请求=会话、曝光=求和、位置越界 0、意图覆盖 100%），任一失败 `run.py` 中止且不覆盖旧库。
- **三路对账**：同一批数字用 DuckDB(库) / DuckDB(Parquet) / 纯 Python(聚合 CSV) 各算一遍，5 个核心指标全部一致（`outputs_public/engine_check.json`）。
- **确定性导出**：导出统一保留 10 位有效数字并加稳定排序键，连续两次全量重建的 14 个公开 CSV 哈希完全一致（耗时类字段除外）。
- **位置敏感性**：把位置也放进基准（条数 × 位置两层）后，Top 30 的缺口变化最大 0.009pp（`outputs_public/sensitivity_position.csv`）——"低点击是因为排在后面"这个解释被排除。
- **第四引擎（Spark）**：Apache Spark 4.3.0 本地模式复算同一批指标，结果与 DuckDB 完全一致（`outputs_public/spark_check.json`）；启动 5.8s、聚合 1.4s/2.2s。详见 [技术栈](docs/tech-stack.md)。
- **证据链**：Top 10 搜索词 × 10 个高曝光商品的审阅表已生成（`outputs/review_table.csv`，含标题、位置、点击与自动预筛），方法与判读见 [承接证据审阅](docs/evidence-review.md)。
- **看板**：静态预览版 `dashboards/preview.html` 可直接打开，与 Power BI 目标版式一致。

## 方法：先校准口径，再谈机会

1. **两个分母严格分开**：商品点击率（点击/曝光）≠ 请求点击率（有点击的请求/请求）。
2. **按结果条数分层**：同一份数据，列表越长单件越难被点，用"同条数段期望点击"当基准，算残差而不是直接比总体。
3. **需求标签规则化**：品牌/店铺、品类+修饰、纯品类、属性/场景、无品类信号，规则在 `config/intent_rules.csv`，可审计、可替换。
4. **机会表带统计**：Wilson 区间 + 双比例检验 + BH-FDR，测试段只做方向复核（时间外，不是 A/B）。
5. **动作带实验设计**：每个动作有主指标、护栏指标、最小样本量（[实验方案](docs/experiment-design.md)）。

完整口径见 [指标口径](docs/metrics.md)，数据质量见 [数据字典](docs/data-dictionary.md)。

## 仓库结构

```
.
├── run.py                      # 一键重建：读原始 JSONL → DuckDB → 聚合导出
├── sql/
│   ├── 01_staging.sql          # 原始表清洗 + 质量审计
│   ├── 02_intermediate.sql     # 请求层、曝光层（含位置）、维度、需求标签
│   ├── 03_marts.sql            # 总览、条数分层、类目、需求、机会、时间、年龄
│   ├── 04_quality.sql          # 对账断言（任一失败即中止）
│   └── clickhouse/             # ClickHouse 建表 / 装载 / 校验 SQL（环境就绪即可跑）
├── src/
│   ├── pipeline.py             # 临时库构建 + 原子替换 + 导出
│   └── stats.py                # Wilson / 双比例检验 / BH-FDR
├── config/intent_rules.csv     # 需求标签规则
├── scripts/
│   ├── download_data.py        # 官方文件下载 + SHA-256 校验
│   ├── export_parquet.py       # 导出 fact/sessions 到 Parquet（跨引擎对账用）
│   ├── verify_engines.py       # 三路对账 + 耗时，写 engine_check.json
│   ├── setup_spark.ps1         # 免管理员安装 Spark 并修复 Windows 启动器
│   ├── spark_check.py          # Spark 本地模式复算 + 与 DuckDB 对账
│   ├── position_sensitivity.py # 条数 × 位置双层基准的敏感性复核
│   ├── build_review_workbook.py# 生成带下拉勾选的审阅工作簿（xlsx）
│   ├── build_review.py         # Top 10 词 × 10 商品审阅表
│   ├── build_dashboard_data.py # 生成 Power BI 单文件数据源（xlsx）
│   ├── build_dashboard_preview.py # 生成静态看板预览（html）
│   └── make_charts.py          # README 图表（无第三方依赖）
├── outputs/                    # 本地全量（含 query 明细与商品标题，不发布）
├── outputs_public/             # 可公开的聚合结果 + 对账 JSON
├── exports/                    # Parquet 中间产物（不发布）
├── dashboards/                 # preview.html + Power BI 数据源 + 手册
└── docs/                       # 报告、口径、字典、证据、实验、技术栈、面试
```

## 快速开始

```powershell
python -m pip install -r requirements.txt
python scripts/download_data.py    # 下载官方 4 份 Lite 文件并校验 SHA-256（约 3.1 GB）
python run.py                      # 重建数据库 + 导出聚合结果（本机约 40 秒）

# 可选：验证与展示
python scripts/verify_engines.py   # 三路对账（DuckDB / Parquet / Python），写出 engine_check.json
powershell -ExecutionPolicy Bypass -File scripts/setup_spark.ps1  # 可选：装 Spark（免管理员）
python scripts/spark_check.py      # 可选：Spark 复算并与 DuckDB 对账
python scripts/build_review.py     # Top 10 词 × 10 商品的承接审阅表
python scripts/position_sensitivity.py    # 位置敏感性复核（条数 × 位置双层基准）
python scripts/export_parquet.py   # 导出 Parquet（ClickHouse 对账或免重建查询用）
python scripts/build_dashboard_data.py    # Power BI 单文件数据源（需要 openpyxl）
python scripts/build_dashboard_preview.py # 静态看板预览
python scripts/make_charts.py      # 重新生成 README 图表
```

运行后：

- `data/processed/kuaisearch.duckdb`：本地分析库（不发布）
- `outputs/`：全量结果（含 query 明细与商品标题，不发布）
- `outputs_public/`：可公开聚合结果（看板数据源）
- `outputs/quality.json`：质量审计结果（任一断言失败，`run.py` 会中止且不覆盖旧库）

## 看板

Power BI 5 页：总览 / 条数效率 / 类目效率 / 需求结构 / 机会清单。搭建步骤、数据模型与 DAX 见 [Power BI 手册](docs/powerbi.md)。

- 先看 `dashboards/preview.html`（双击打开，无需安装任何软件）：这是同一份数据的静态版，版式即目标。
- 数据源：`dashboards/data/kuaisearch_dashboard.xlsx`（12 个 sheet，一次导入）。
- 需要 PDF：浏览器打开预览后 `Ctrl+P` 另存为 PDF 即可（已加打印分页样式）。

## 限制（请先读这里）

- **观察性数据**：所有差距都是"同条数条件下的相关"，不是因果，也没有线上实验结果。
- **购买标签 ≠ 订单**：没有金额字段，不计算 GMV、不报"转化率提升"。
- **列表顺序 ≠ 平台真实排序位**：只用于位置/条数描述，不推断排序算法。
- **`time_index` 是相对编码**：不能还原日期、小时、星期，不做分时/周末分析。
- **Lite 是采样数据**：绝对值不代表平台真实水平。
- **年龄字段异常**：12–17 岁占 17.1% 请求，只做结构描述，不做人群结论。
- **相关性标注覆盖极低**（46,422 对 / 46,325 个 query，多为 1 对/query）：不支撑"相关性差导致低点击"的定量结论。

## 文档

| 文档 | 内容 |
| --- | --- |
| [分析报告](docs/analysis-report.md) | 完整业务报告：结论、证据、动作、限制 |
| [承接证据审阅](docs/evidence-review.md) | 商品级审阅表怎么读、怎么填、能得出什么 |
| [指标口径](docs/metrics.md) | 每个指标的分母、公式与使用边界 |
| [数据字典](docs/data-dictionary.md) | 字段、规模、质量审计、已知问题 |
| [实验方案](docs/experiment-design.md) | 3 个动作的假设、分流、主/护栏指标、样本量 |
| [Power BI 手册](docs/powerbi.md) | 导入、模型、DAX、5 页布局、导出 |
| [技术栈](docs/tech-stack.md) | DuckDB 取舍、ClickHouse 对账资产、Spark 实测与选型建议 |
| [面试材料](docs/interview.md) | 30 秒/2 分钟讲法、10 个追问、简历表述 |
| [路线图](docs/roadmap.md) | 阶段计划、当前进度与验收标准 |
| [交接说明](docs/handoff-codex.md) | 给优化方的完整交接：结论、口径、文件地图、已知弱点与优化任务 |

## 许可

代码 MIT。原始数据版权与许可归数据集作者，本项目不再分发原始文件与用户级数据。
