# Power BI 看板搭建手册（Power BI Desktop，免费）

> 目标：用 `outputs_public/` 里的聚合结果做出 5 页看板，导出 PDF + PNG 放进仓库；`.pbix` 体积大且 GitHub 不能预览，放在 GitHub Release。
> 数据只有聚合指标，不含用户级记录。

## 1. 安装与准备

1. 打开 Microsoft Store 搜 **Power BI Desktop**（免费）安装；或官网下载 `.msi`。
2. 打开后关闭登录弹窗（本地文件不需要账号）。
3. 建议把 `outputs_public/` 整个目录复制到 `dashboards/data/`（不要直接引用 `outputs/`，那份含 query 明细）。

## 2. 导入数据

`主页 → 获取数据 → 文本/CSV`，依次导入：

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

导入时：

- `split`、`category`、`intent`、`validation`、`length_stratum` → 文本
- `requests`、`users`、`exposures`、`clicks`、`purchases` → 整数
- `item_ctr`、`request_click_rate`、`request_purchase_rate`、`expected_ctr`、`wilson_low/high` → 小数，格式化为百分比（2 位）
- `gap_pp` 是**百分点数值**（如 1.47 表示 1.47pp），不要设成百分比

## 3. 数据模型

最简可用模型（不需要星型建模训练）：

- `overview`、`length_strata`、`intent_metrics`、`relative_time_metrics`、`category_metrics`、`opportunities_top30` 之间**只通过 `split` 建立关系**（多对一，单选）。
- `category_metrics` 与 `category_residuals` 通过 `category_id` 关联（`category_residuals` 只有 train）。
- `opportunities_top30` 不做关系，单独一页用（避免筛选器互相干扰）。

> 关系只用于同步筛选 `split`；所有比例都必须用 DAX 重新计算，不能直接对百分比列求平均。

## 4. 度量值（复制到"建模 → 新建度量值"）

```DAX
曝光数 = SUM(overview[exposures])
点击数 = SUM(overview[clicks])
商品点击率 = DIVIDE([点击数], [曝光数])
请求点击率 = DIVIDE(SUM(overview[clicked_requests]), SUM(overview[requests]))
购买请求率 = DIVIDE(SUM(overview[purchased_requests]), SUM(overview[requests]))
平均展示条数 = DIVIDE([曝光数], SUM(overview[requests]))

-- 条数分层页：按层重算，禁止直接平均
分层商品点击率 = DIVIDE(SUM(length_strata[clicks]), SUM(length_strata[exposures]))
分层请求点击率 = DIVIDE(
    SUMX(length_strata, length_strata[request_click_rate] * length_strata[requests]),
    SUM(length_strata[requests])
)

-- 机会页
同条数期望点击 = SUM(opportunities_top30[expected_ctr] * opportunities_top30[exposures])
缺口点击 = SUM(opportunities_top30[gap_clicks])
缺口百分点 = DIVIDE([同条数期望点击] - SUM(opportunities_top30[clicks]), SUM(opportunities_top30[exposures])) * 100
```

## 5. 五个页面

### 页 1｜总览
- 卡片：请求数、去重用户、曝光、点击、商品点击率、请求点击率（分 train/test 两张表或一个切片器）
- 一句话结论文本框："7% 的请求贡献 40% 的曝光，长列表拉低单件点击率"
- 切片器：`split`

### 页 2｜条数效率（核心）
- 柱状图：`length_stratum` × 商品点击率（排序按条数段）
- 折线/柱：`length_stratum` × 请求点击率
- 表格：请求数、曝光数、两种点击率（提示"曝光集中度"）
- 一句话："同一批用户，1–10 条时 8.96%，100+ 条时 2.19%"

### 页 3｜类目效率
- 横条：类目曝光量（Top 15）+ 商品点击率标签
- 散点/表格：`category` × 实际 CTR vs 期望 CTR，气泡大小=曝光
- 表格：`category_residuals`（缺口点击降序）
- 提示："女装缺口总量第一，但每曝光差距只有 0.25pp"

### 页 4｜需求结构
- 柱状图：`intent` × 请求占比
- 表格：`intent_residuals`（实际/期望/差距）
- 一句话："按同条数校准后，需求标签之间几乎没有效率差异"

### 页 5｜机会清单
- 表格：`opportunities_top30` 的 rank、query、请求、曝光、实际/期望 CTR、gap_pp、缺口点击、请求点击率、validation
- 条件格式：gap_pp 越大越红；`validation=验证样本不足` 灰显
- 说明："query 为脱敏后的高频泛词；完整 query 明细保留在本地"

### 可选页 6｜相对时间
- 折线：`time_bucket` × 请求数 / 商品点击率
- 标题必须写"相对时间区间（不可还原为日期/星期）"

## 6. 导出与入库

1. `文件 → 导出 → 导出为 PDF`，命名 `dashboards/看板.pdf`。
2. 每页 `视图 → 截图` 或 Windows 截图，存 `dashboards/images/page1.png` …（建议 1600×900）。
3. `文件 → 另存为` 得到 `.pbix`，**不要提交到 git**（`.gitignore` 已排除），上传到 GitHub Release，README 里给下载链接。
4. 在 README 里嵌 2–3 张关键页截图（不要贴 6 张）。

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

- [ ] 5 页能按 `split` 过滤，且每页有样本量
- [ ] 所有比率用 DAX 重算，未对百分比列求平均
- [ ] 有 PDF + 至少 3 张 PNG 入库
- [ ] `.pbix` 在 Release，不在仓库
- [ ] 每页有一句话结论，且与 [分析报告](analysis-report.md) 数字一致
