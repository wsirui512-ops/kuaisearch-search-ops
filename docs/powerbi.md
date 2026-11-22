# Power BI 看板搭建与交付说明

> **现状**：发布物是八页静态报告（`dashboards/静态看板.pptx` + `看板.pdf` + 8 张截图），由 `scripts/build_static_dashboard.py` 与 `scripts/export_dashboard.py` 生成。Power BI 文件 `dashboards/kuaisearch-search-ops.pbix` 存在，但当前环境未安装 Power BI，**未做打开验证**；下文是重建 Power BI 版的操作说明。
> `.pbix` 含 Top 30 搜索词，不含用户级明细；暂只在本机供审阅，不上传 GitHub Release。

## 1. 安装与准备

1. 打开 Microsoft Store 搜 **Power BI Desktop**（免费）安装；或官网下载 `.msi`。
2. 打开后关闭登录弹窗（本地文件不需要账号）。
3. 建议把 `outputs_public/` 整个目录复制到 `dashboards/data/`（不要直接引用 `outputs/`，那份含 query 明细）。

## 2. 导入数据

### 2.1 最快路径：用现成的工作簿

仓库已生成 **`dashboards/data/kuaisearch_dashboard.xlsx`**（13 个 sheet：说明 + 12 张表，列类型与百分比格式已设好）。

`主页 → 获取数据 → Excel 工作簿`，选择除「说明」外的 12 张数据表，点击「转换数据」。在 Power Query 中按下表重命名，然后「关闭并应用」。这样下面的 DAX 可直接复制。

| 工作簿 sheet | Power BI 表名 |
| --- | --- |
| 总览 | `overview` |
| 条数分层 | `length_strata` |
| 条数基准 | `stratum_baseline` |
| 类目 | `category_metrics` |
| 类目残差 | `category_residuals` |
| 需求标签 | `intent_metrics` |
| 需求残差 | `intent_residuals` |
| 机会清单 | `opportunities_top30` |
| 相对时间 | `relative_time_metrics` |
| 年龄 | `age_metrics` |
| 相关性覆盖 | `relevance_coverage` |
| 标题预筛 | `review_coverage_summary`（仅自动二字覆盖率） |

### 2.2 或者逐表导入 CSV

| 文件 | 用途 |
| --- | --- |
| `overview.csv` | 总览卡片 |
| `length_strata.csv` | 条数效率（核心页） |
| `category_metrics.csv` + `category_residuals.csv` | 类目效率与缺口 |
| `intent_metrics.csv` + `intent_residuals.csv` | 需求结构 |
| `opportunities_top30.csv` | 机会清单 |
| `relative_time_metrics.csv` | 相对时间 |
| `age_metrics.csv` | 可选：人群结构（标注"字段可信度低"） |
| `quality.json` | 可选：质量说明（或直接写文字） |

### 2.3 先看目标样式

打开 `dashboards/preview.html`（双击即可，无需任何软件），里面是同一份数据的 5 页静态版：KPI 卡片、条数效率双图、类目缺口、需求残差、机会清单。Power BI 版按这个版式做即可，做完后用它的数字逐项核对。
> 需要 PDF 时：在浏览器里 `Ctrl+P` → 目标选"另存为 PDF"（已加打印样式，每页自动分页），存成 `dashboards/看板.pdf`。

导入时：

- `split`、`category`、`intent`、`validation`、`length_stratum` → 文本
- `requests`、`users`、`exposures`、`clicks`、`purchases` → 整数
- `item_ctr`、`request_click_rate`、`request_purchase_rate`、`expected_ctr`、`wilson_low/high` → 小数，格式化为百分比（2 位）
- `gap_pp` 是**百分点数值**（如 1.47 表示 1.47pp），不要设成百分比

## 3. 数据模型

最简可用模型（不需要星型建模训练）：

- 建一张仅含 `train`、`test` 两行的 `dim_split`，由 `dim_split[split]` 分别一对多连接 `overview`、`length_strata`、`category_metrics`、`intent_metrics`、`relative_time_metrics`；**不要把多张聚合表直接用重复的 `split` 值互连**。
- `category_residuals` 与 `intent_residuals` 仅含训练段数据，单独使用，不接 `split` 切片器。两个残差页在标题上明确写「训练段」。
- `opportunities_top30` 不做关系，单独一页用（避免筛选器互相干扰）。

> 关系只用于同步筛选 `split`；所有比例都必须用 DAX 重新计算，不能直接对百分比列求平均。

`建模 → 新建表` 创建切片维度：

```DAX
dim_split = DATATABLE("split", STRING, {{"train"}, {"test"}})
```

## 4. 度量值（复制到"建模 → 新建度量值"）

```DAX
曝光数 = SUM(overview[exposures])
点击数 = SUM(overview[clicks])
商品点击率 = DIVIDE([点击数], [曝光数])
请求点击率 = DIVIDE(SUM(overview[clicked_requests]), SUM(overview[requests]))
购买请求率 = DIVIDE(SUM(overview[purchased_requests]), SUM(overview[requests]))
平均展示条数 = DIVIDE([曝光数], SUM(overview[requests]))
去重用户（单段） = IF(HASONEVALUE(dim_split[split]), SUM(overview[users]), BLANK())

-- 条数分层页：按层重算，禁止直接平均
分层商品点击率 = DIVIDE(SUM(length_strata[clicks]), SUM(length_strata[exposures]))
-- 单一条数段可直接展示 length_strata[request_click_rate]；
-- 该表没有 clicked_requests，跨条数段聚合不应伪装成精确重算。

-- 机会页
同条数期望点击 = SUMX(opportunities_top30, opportunities_top30[expected_ctr] * opportunities_top30[exposures])
缺口点击 = SUM(opportunities_top30[gap_clicks])
缺口百分点 = DIVIDE([同条数期望点击] - SUM(opportunities_top30[clicks]), SUM(opportunities_top30[exposures])) * 100
```

## 5. 五个页面

### 页 1｜总览
- 卡片：请求数、曝光、点击、商品点击率、请求点击率（分 train/test 两张表或一个切片器）。`users` 在两段之间可能重复，不能把两段人数相加当去重用户数。
- 一句话结论文本框："约 7% 的请求贡献约 40% 的曝光；列表条数与商品点击率密切相关"
- 切片器：`split`

### 页 2｜条数效率（核心）
- 柱状图：`length_stratum` × 商品点击率（排序按条数段）
- 折线/柱：`length_stratum` × 原表 `request_click_rate`（每一条数段恰好一行；不要跨层求平均）
- 表格：请求数、曝光数、两种点击率（提示"曝光集中度"）
- 一句话："不同条数段的样本商品点击率为 8.96% 与 2.19%；这不是同一批用户的对照实验"

### 页 3｜类目效率
- 横条：类目曝光量（Top 15）+ 商品点击率标签
- 散点/表格：`category` × 实际 CTR vs 期望 CTR，气泡大小=曝光
- 表格：`category_residuals`（缺口点击降序）
- 提示："女装缺口总量第一，但每曝光差距只有 0.25pp"

### 页 4｜需求结构
- 柱状图：`intent` × 请求占比
- 表格：`intent_residuals`（实际/期望/差距）
- 一句话："按同条数校准后，规则标签之间的描述性差距缩小；标签尚未人工校核"

### 页 5｜机会清单
- 表格：`opportunities_top30` 的 rank、query、请求、曝光、实际/期望 CTR、gap_pp、缺口点击、请求点击率、validation
- 条件格式：gap_pp 越大越红；`validation=验证样本不足` 灰显
- 说明："query 为脱敏后的高频泛词；完整 query 明细保留在本地"

### 可选页 6｜相对时间
- 折线：`time_bucket` × 请求数 / 商品点击率
- 标题必须写"相对时间区间（不可还原为日期/星期）"

## 5.1 字段映射速查

| 页 | 视觉对象 | 类别 / X 轴 | 值 / Y 轴 | 备注 |
| --- | --- | --- | --- | --- |
| 1 总览 | 卡片 ×6 | — | 请求数、曝光、商品点击率、请求点击率、100+ 曝光占比、机会候选数 | 用 `overview` + `length_strata` 度量值 |
| 1 总览 | 表 | `split` | 请求、用户、曝光、两种点击率 | 显式对比 train/test |
| 2 条数 | 簇状柱形图 | `length_stratum` | 商品点击率、请求点击率 | 两条系列，第二轴可选 |
| 2 条数 | 表 | `length_stratum` | 请求数、曝光数、两种点击率 | 曝光占比一列能讲清结构 |
| 3 类目 | 条形图（Top N=10） | `category` | `exposures` | 按曝光降序 |
| 3 类目 | 条形图 | `category` | `gap_pp` | 数据来自 `category_residuals`（仅 train） |
| 3 类目 | 表 | `category` | 实际 CTR、期望 CTR、缺口点击 | 缺口降序 |
| 4 需求 | 条形图 | `intent` | `requests` | 标签占比 |
| 4 需求 | 条形图 | `intent` | `gap_pp` | 负值表示好于期望 |
| 5 机会 | 表 | `rank` | query、请求、曝光、实际/期望 CTR、gap_pp、缺口点击、validation | 条件格式：gap_pp 越大越红 |
| 6 时间 | 折线图 | `time_bucket` | 请求数、商品点击率 | 标题写"相对区间" |

切片器：`split`（页 1–4）、`category`（页 3）、`intent`（页 4）。**每个视觉对象旁显示样本量**（请求数或曝光数）。

## 6. 导出与入库

导出前先做四件事，否则截图会带上应用界面、空页和默认字段名：

1. **消除"自动恢复"横幅**：另存为新文件 → 关闭 Power BI → 重新打开该文件（不要点"查看已恢复文件"）。
2. **切到阅读视图**：`视图 → 阅读视图`，关闭网格线；确认没有选中框（选中时会出现斜纹）。
3. **改标题**：把 `item_ctr 的总和(按 length_stratum 和 split)` 这类默认标题改成业务标题（如"各列表长度段的商品点击率"）。
4. **检查空页**：第 6 页当前只有一段小字，若保留需补一张"10 个词覆盖率"表，否则删除该页并重排页码。

然后：

1. `文件 → 导出 → 导出为 PDF`，命名 `dashboards/看板.pdf`。
2. 每页在**阅读视图**下截图，存 `dashboards/images/page01.png … page08.png`，统一 1600×900。
3. 运行 `python scripts/check_dashboard_assets.py`：校验页数、尺寸、空白页，并检测 8 张截图是否带同一条应用界面栏；退出码 1 表示还不能发布。
4. 本机 `.pbix` 已保存到 `dashboards/kuaisearch-search-ops.pbix`。该文件含 Top 30 搜索词，**不要提交到 git**；公开版本先确认许可（[数据许可](data-license.md)）并审阅词级内容。
5. 在 README 里嵌 2–3 张关键页截图（不要贴 6 张）。

## 7. 常见坑

| 坑 | 正确做法 |
| --- | --- |
| 对 `item_ctr` 列求平均 | 用 `DIVIDE(SUM(clicks), SUM(exposures))` |
| 把 `gap_pp` 再乘 100 | `gap_pp` 已是百分点数值 |
| 用全局 CTR 比不同长度 | 用"条数分层"页或 `expected_ctr` |
| 把购买请求率写成转化率 | 写"样本购买请求率"，不写"下单率/GMV" |
| 时间轴写成"近 30 天" | 写"相对时间区间" |
| 图表没样本量 | 每个视觉对象旁边加请求数/曝光数 |

## 8. 验收清单

- [ ] 总览、条数和原始结构图能按 `split` 过滤；训练段残差页明确标注训练段；每页有样本量
- [ ] 所有比率用 DAX 重算，未对百分比列求平均
- [ ] 有 PDF + 至少 3 张 PNG 入库
- [ ] `.pbix` 在 Release，不在仓库
- [ ] 每页有一句话结论，且与 [分析报告](analysis-report.md) 数字一致
