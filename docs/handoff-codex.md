# 项目交接说明（给优化方 / Codex）

> 读完这一份就能接手：背景、结论、口径、文件地图、已验证事项、已知弱点、可执行的优化任务与验收标准。
> 最后更新：2026-11-21（commit `f2557f0`）

## 0. 一句话

用 KuaiSearch-Lite 的真实电商搜索行为（555,553 次搜索 / 17,800,904 次商品曝光 / 102,086 名用户），诊断"哪些搜索需求有曝光却没被结果页接住"，产出可复算的分析、业务报告、Power BI 看板与实验方案，面向**数据运营实习**求职。

## 1. 目标与"完成"的判定

| 维度 | 达成标准 | 现状 |
| --- | --- | --- |
| 可复现 | 一条命令从原始数据重建全部结果 | ✅ `python run.py`，40.3 秒 |
| 口径可辩护 | 每个指标有分母、公式、边界说明 | ✅ `docs/metrics.md` |
| 结论有证据 | 每个结论有样本量、基准、区间 | 🟡 商品级人工审阅未完成 |
| 动作可执行 | 每个动作有主/护栏指标与样本量 | ✅ `docs/experiment-design.md` |
| 可视化 | 能过滤、显示样本量的看板 | 🟡 静态预览 + 单文件数据源已就绪，`.pbix` 未做 |
| 工程规范 | 分层、断言、CI、确定性 | ✅ 39 项断言 + 三路对账 + CI 产物校验 |

## 2. 数据与环境

**数据**（官方 KuaiSearch-Lite，revision `16f555af360f6a86209f60eb1f12462f9e25be2c`，SHA-256 校验）：

| 文件 | 行数 | 大小 |
| --- | --- | --- |
| `recall_lite/train.jsonl` | 555,553 | 258 MB |
| `items_lite/train.jsonl` | 5,548,777 | 2.79 GB |
| `users_lite/train.jsonl` | 102,086 | 13 MB |
| `relevance/train.jsonl` | 46,422 | 15.8 MB |

**环境事实（重要，会限制方案选择）**

| 项 | 值 |
| --- | --- |
| OS | Windows 10 Home China，build 26200 |
| Python | 3.13.14 |
| DuckDB | 2.0.0（因沙箱限制 pip 不可写临时目录，wheel 解包在 `.localdeps/`） |
| Spark | 4.3.0（`.spark/`，0.58 GB，Java 21 在 `D:\Java\jdk-21.0.12.1`） |
| Docker / WSL | ❌ 无 Docker；`wsl` 返回 E_ACCESSDENIED；当前会话非管理员 |
| Power BI | ❌ 未安装（`.pbix` 需在用户机器上做） |
| 数据规模 | 原始 3.08 GB；DuckDB 681 MB；Parquet 164 MB（均不入 Git） |

## 3. 文件地图

```
run.py                      一键重建（临时库构建→断言→原子替换→导出）
sql/01_staging.sql          原始表清洗 + 源数据质量审计
sql/02_intermediate.sql     请求层、曝光层（含 position）、维度、需求标签
sql/03_marts.sql            总览/条数分层/类目/需求/机会/时间/年龄/相关性
sql/04_quality.sql          39 项对账断言（任一失败即中止，不覆盖旧库）
sql/clickhouse/*.sql        建表 / 装载 / 校验（环境就绪即可跑，当前阻塞）
src/pipeline.py             编排 + 导出（10 位有效数字 + 稳定排序键）
src/stats.py                Wilson 区间、双比例检验、BH-FDR（零依赖）
config/intent_rules.csv     需求标签规则（brand/attr/scene/category 四类信号）
scripts/                    download / export_parquet / verify_engines /
                            position_sensitivity / build_review / build_review_workbook /
                            build_dashboard_data / build_dashboard_preview / make_charts /
                            spark_check / setup_spark.ps1 / check_all.ps1
outputs/                    本地全量（含 query 明细与商品标题，不发布）
outputs_public/             可公开聚合（14 CSV + 4 JSON/MD）
dashboards/                 preview.html（5 页静态看板）、data/*.xlsx（12 sheet）、README
docs/                       analysis-report / metrics / data-dictionary / evidence-review /
                            experiment-design / powerbi / tech-stack / interview / roadmap
```

Git：8 个 commit，63 个受版本控制文件。`.gitignore` 排除 `data/raw`、`data/processed`、`outputs/`、`exports/`、`.localdeps`、`.spark`、`.work`、`*.pbix`。

## 4. 核心结论（全部可复算）

**总览**

| 指标 | 训练段 | 测试段（时间外） |
| --- | --- | --- |
| 请求 / 用户 | 539,012 / 100,182 | 16,541 / 6,211 |
| 曝光 / 点击 / 购买 | 17,306,633 / 662,020 / 49,418 | 494,271 / 18,770 / 1,501 |
| 商品点击率 | 3.825% | 3.798% |
| 请求点击率 | 53.16% | 51.12% |
| 平均展示条数 | 32.1 | 29.9 |

**发现一：曝光结构偏斜**

- 6.9% 的请求展示 ≥100 条 → 贡献 40.3% 曝光。
- 条数 1–10 → 100+，商品点击率 8.96% → 2.19%；请求点击率 36.6% → 84.1%。

**发现二：控制条数后，品类/需求差异基本消失**

- 女装缺口从 0.78pp 收窄到 0.25pp（同条数期望 3.30% vs 实际 3.05%）。
- 需求标签残差全部在 ±0.2pp 内；品牌/店铺词反而好 0.34pp。

**发现三：仍有 124 个真实缺口词（74 个 q<0.05）**

- Top 30：64.6 万曝光，实际 14,828 点击，期望 21,244 → 缺口 ≈6,416 次（≈1.0% 曝光）。
- Top 5：鞋子 1.47pp/528、衣服 2.24pp/387、外套 0.75pp/381、裤子 1.18pp/369、手机壳 0.74pp/363。
- 服饰鞋包占候选约 70%（女装 22%、男装 17%、箱包 11%、女鞋 8%）。

**发现四：点击不在首屏**

- 位置 1–5 占 24.9% 点击，41+ 仍占 26.6%；候选词平均点击位置 35–74 位。
- 因此动作 A 从"首屏收敛"改为"结果分区（不减量）"，护栏是请求点击率。

**稳健性**

- 条数 × 位置双层基准：Top 30 缺口变化最大 0.009pp → 缺口不是位置造成的。

## 5. 方法论要点（改动前请读）

1. **两个分母**：商品点击率（点击/曝光）≠ 请求点击率（有点击请求/请求），任何聚合都用 `SUM(分子)/SUM(分母)`。
2. **条数分层基准**：`期望点击 = Σ(条数段曝光 × 该段训练段 CTR)`；`gap_clicks = 期望 − 实际`，是描述性差距，不是可回收量。
3. **需求标签**是规则（`config/intent_rules.csv`），5 个主标签：品牌/店铺、品类+修饰、纯品类、属性/场景（无品类）、无品类信号；不是模型。
4. **机会表统计**：Wilson 区间 + 对期望率的双比例检验（期望率视为固定，偏乐观）+ BH-FDR；样本量大时 p 极小，看 `gap_pp` 与置信区间。
5. **时间不可还原**：`time_index` 是相对值，禁止写日期/星期/分时；train/test 是时间切分（1–936,724 / 936,726–965,265）。
6. **不建严格漏斗**：1,438 个购买商品不在同次点击列表（2.82%）。
7. **导出确定性**：10 位有效数字 + 稳定排序键；两次重建 14/14 CSV 哈希一致。

## 6. 已验证事项

| 验证 | 结果 | 证据文件 |
| --- | --- | --- |
| 质量断言 | 39 项全过（曝光=求和、位置越界 0、意图覆盖 100%…） | `outputs/quality.json` |
| 三路对账 | DuckDB(库) / DuckDB(Parquet) / Python 全部一致 | `outputs_public/engine_check.json` |
| 第四引擎 | Spark 4.3 local[4]：5.8s 启动、1.4s/2.2s 聚合，0 差异 | `outputs_public/spark_check.json` |
| 位置敏感性 | Top 30 变化 ≤0.009pp | `outputs_public/sensitivity_position.csv` |
| 确定性 | 两次全量重建 14 个 CSV 哈希一致 | 会话内实测 |
| CI | 图表/预览与提交物不一致即失败 | `.github/workflows/checks.yml` |

## 7. 已知弱点与优化任务（这是交接重点）

### P0（影响可信度/交付完整度）

| # | 问题 | 建议做法 | 验收 |
| --- | --- | --- | --- |
| 1 | **报告数字是硬编码**，改口径后容易与 CSV 漂移 | 用脚本从 `outputs_public/` 生成报告里的表格与关键数字（模板占位），或加 `scripts/verify_docs.py` 断言文档数字与 CSV 一致 | CI 里能拦住"数字对不上" |
| 2 | **需求标签未人工校核**，`无品类信号` 占 36.8% | 抽 200 条标注（`outputs/intent_review_sample.csv` 已有模板），记录准确率，规则版本化 | 报告写明准确率与抽样方法 |
| 3 | **商品级审阅未完成**（P3） | 填 `outputs/review_workbook.xlsx` 的 100 行（1/0.5/0），回读后写进报告 §7 | 每个 Top 词有 3 条商品证据 |
| 4 | **显著性偏乐观**：期望率当固定值 | 改成按条数分层的 CMH 检验，或 bootstrap 置信区间 | 报告给出方法说明 |
| 5 | **`.pbix` 缺失** | 在用户机器用 `dashboards/data/*.xlsx` 搭 5 页；仓库放 PDF + 截图 + Release 链接 | 看板可过滤且显示样本量 |

### P1（提升分析深度/工程规范）

| # | 问题 | 建议做法 |
| --- | --- | --- |
| 6 | Lite 采样机制未知，外推缺讨论 | 加"采样偏差"小节；按用户/时间子样本重算主要指标做敏感性 |
| 7 | 时间维度几乎没用 | 做时间桶稳定性检验（CTR 漂移、候选词排名稳定性） |
| 8 | 类目只到一/二级（三级多为 UNKNOWN） | 用标题 token 做细类目代理，验证"细类目分区"动作的可行性 |
| 9 | 年龄字段可疑（12–17 岁占 17.1%） | 报告标注或从看板移除，避免人群结论 |
| 10 | 无单元测试 | pytest 覆盖 `stats.py`（Wilson/BH/p 值）+ SQL 断言 |
| 11 | CI 不跑管道（需 3.1 GB 数据） | 生成 1,000 行合成 JSONL 的冒烟测试，跑通 staging→marts→断言 |
| 12 | 术语/命名不统一（中英混排、`item_ctr` vs "商品点击率"） | 加 `docs/glossary.md`，代码列名与文档术语对照 |
| 13 | README 只有 3 张 SVG，无看板截图 | 补齐看板截图（1600×900）与 1 张类目缺口图 |
| 14 | `check_all.ps1` 仅 Windows | 提供跨平台 `make` 或 Python orchestrator |

### P2（发布/长期维护）

| # | 问题 | 建议做法 |
| --- | --- | --- |
| 15 | 数据集许可未核实、无 `CITATION.cff` | 核对 Hugging Face 数据卡许可，补引用文件 |
| 16 | `query_key`（md5）未在文档解释 | 在数据字典补一段"为什么不用自增 ID" |
| 17 | 缺 `CHANGELOG.md` | 按 v1/v2 补两次变更 |
| 18 | 仓库根目录残留不可删目录 `tmpiffoks7y/` | 用户手动改权限删除（本会话被 ACL 挡住） |

## 8. 红线（不要做）

- 不要为了"更好看"改口径而不更新所有下游文档与 CSV（数字漂移是这类项目最大的信任问题）。
- 不要声称用过 ClickHouse、跑过全量 107 GB、做过线上 A/B、算过 GMV。
- 不要公开 `data/raw`、`data/processed`、`outputs/`（含 query 明细与商品标题）、`exports/`。
- 不要用"平均各行的百分比"代替 `SUM/SUM`。
- 不要把 `time_index` 解释成日期/小时/星期。
- 不要把购买标签写成订单或转化率。

## 9. 常用命令

```powershell
python -m pip install -r requirements.txt
python scripts/download_data.py          # 3.1 GB，SHA-256 校验
python run.py                            # 40 秒，重建库与 14 个导出

powershell -ExecutionPolicy Bypass -File scripts/check_all.ps1 -SkipBuild   # 全量验证
python scripts/verify_engines.py         # 三路对账
python scripts/position_sensitivity.py   # 位置敏感性
python scripts/build_review.py           # 100 行审阅表
python scripts/build_review_workbook.py  # Excel 审阅包（需 openpyxl）
python scripts/spark_check.py            # Spark 对账（需先 setup_spark.ps1）
python scripts/build_dashboard_preview.py# 静态看板（零依赖）
```

## 10. 接手检查清单

- [ ] `python run.py` 跑通且 `outputs/quality.json` 无失败
- [ ] `python scripts/verify_engines.py` 输出 `failed checks: 0`
- [ ] 打开 `dashboards/preview.html` 能看到 5 页且数字与 CSV 一致
- [ ] 改动口径时同步更新：`sql/`、`outputs_public/`、`docs/metrics.md`、报告、README
- [ ] 提交前跑 `scripts/check_all.ps1`，确认图表与预览无 diff
