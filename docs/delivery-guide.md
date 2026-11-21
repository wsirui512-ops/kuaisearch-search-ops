# 项目交付与审阅指南（2026-11-21）

## 这是一个什么项目

主题是**电商搜索需求与点击效率诊断**，面向搜索运营、数据运营实习岗位。项目用 KuaiSearch-Lite 的真实行为样本，把搜索请求、商品曝光、点击和购买标签整理成可复算指标，找出值得人工核查的搜索词，并提出可检验的运营动作。它是一套**分析项目作品集**，不是一个上线运营平台。

## 建议按这个顺序审阅

1. [面试展示版](interview-release-v1.md)：先看业务问题、三条发现、动作和不能声称的结论。
2. [Power BI 报告](../dashboards/kuaisearch-search-ops.pbix)：用本机 Power BI Desktop 打开，依次看总览、条数效率、品类残差、需求标签、机会清单、标题审阅、相对时间、运营动作八页。文件是本机交付，不在 Git 仓库中。
3. [静态看板](../dashboards/preview.html)：浏览器可直接打开，便于快速预览与展示。
4. [完整分析报告](analysis-report.md)、[指标口径](metrics.md)、[实验方案](experiment-design.md)：核对每条业务判断如何从数据走到动作。
5. `outputs/spotcheck_30.xlsx`：本机 30 行空白标题抽检表，每词 3 条，由项目作者填写判断和理由。

## 交付文件分别起什么作用

| 文件或目录 | 用途 | 可公开性 |
| --- | --- | --- |
| `run.py`、`src/`、`sql/`、`scripts/` | 下载、清洗、建模、质量检查和导出 | 代码可公开 |
| `outputs_public/` | 聚合指标、机会词 Top 30、引擎对账 | 发布前复核 query 文本与数据许可 |
| `dashboards/data/kuaisearch_dashboard.xlsx` | Power BI 导入数据源 | 含 Top 30 query，发布前复核 |
| `dashboards/kuaisearch-search-ops.pbix` | 可交互的 Power BI 面试展示报告 | 仅本机审阅，当前不上传 GitHub |
| `dashboards/preview.html` | 无需 Power BI 的静态预览 | 含 Top 30 query，发布前复核 |
| `outputs/spotcheck_30.xlsx` | 30 行空白人工抽检表 | 含商品标题，仅本机保存 |
| `docs/` | 报告、口径、证据、实验和面试材料 | 按数据许可与 query 复核结果发布 |

## 本版已经验证什么

- 555,553 次搜索、17,800,904 次曝光、680,790 次点击与 102,086 名去重用户来自固定版本四份 JSONL；下载清单记录 SHA-256。
- `python run.py` 构建分析库和聚合结果；39 项数据质量断言通过。
- DuckDB 数据库、DuckDB Parquet 和纯 Python 聚合三路核心指标一致；Spark 4.3 本地模式复算核心指标一致。
- 100 行标题二字覆盖率属于自动预筛；尚未人工抽检，不据此判断相关性。
- Power BI `.pbix` 文件已在 Desktop 中制作并保存。文件结构校验通过，包含八页、15 个可视元素与嵌入数据模型；本机报告不是 CI 自动重建的产物。
- `powershell -ExecutionPolicy Bypass -File scripts/check_all.ps1 -SkipBuild` 校验聚合对账、静态看板、数据源和文档关键数字。

## 需要你重点提意见的三处

1. **业务叙事**：三条发现和对应动作能否用于你想投的岗位？是否需要更聚焦搜索运营、流量运营或商品运营？
2. **Power BI 页面**：八页的阅读顺序、图表密度和文字解释是否适合面试时在 2–3 分钟内讲完？
3. **标题抽检**：填写 `outputs/spotcheck_30.xlsx` 的 30 行判断与理由，再运行 `python scripts/apply_spotcheck.py`。

## 当前结论边界

机会词的“点击缺口”是分层基准下的**描述性差额**，不等于可回收点击，也不证明运营动作会带来增长。现有 p/q 值有基准估计、请求内相关和先筛后验的问题，不用于显著性结论。没有真实页面展示位、滚动日志、订单金额或线上随机实验。Lite 的采样机制与原始数据再分发许可尚需核实；在核实前，保持 `.pbix`、原始数据和商品级审阅表本地使用。
