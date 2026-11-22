# 数据许可与发布边界

## 结论

`benchen4395/KuaiSearch` 在 Hugging Face 数据集卡上标注为 **MIT**。
核查时间：2026-11-22；核查方式：`https://huggingface.co/api/datasets/benchen4395/KuaiSearch` 返回
`tags: ["license:mit"]`、`cardData.license: "mit"`，`lastModified: 2026-04-07`。

MIT 允许复制、修改、再分发与商用，条件是**保留版权与许可声明**。因此：

- 可以公开：代码、SQL、口径文档、聚合指标、示例搜索词、看板内容；
- 本仓库仍**不发布**原始 JSONL、DuckDB 文件、Parquet、用户级明细（体积 + 再分发成本 + 隐私最小化），
  这是项目自己的选择，不是许可禁止；
- 公开聚合结果时，在 README 与本文档保留数据集名称、链接与 MIT 说明。

## 发布清单

| 内容 | 是否公开 | 理由 |
| --- | --- | --- |
| `src/`、`sql/`、`scripts/`、`config/` | ✅ | 代码与规则 |
| `docs/`、`outputs_public/` | ✅ | 文档与聚合指标 |
| `dashboards/preview.html`、`data/*.xlsx`、`看板.pdf`、`images/*.png` | ✅ | 展示物，含 Top 30 泛词 |
| 原始 `data/raw/*.jsonl` | ❌ | 3.1 GB，且无必要再分发 |
| `data/processed/*.duckdb`、`exports/*.parquet` | ❌ | 体积大，可由脚本重建 |
| `outputs/`（含 query 全量与商品标题） | ❌ | 用户级/明细级内容，保持本地 |
| `.pbix` | ⚠️ 建议不进仓库 | 含嵌入数据模型；放 Release 或网盘，README 说明获取方式 |

## 搜索词敏感性

对 `outputs_public/opportunities_top30.csv` 做了自动扫描（2026-11-22）：

- 30 个搜索词，**无手机号、身份证、联系方式、地址**等个人信息；
- 仅 2 个超过 12 字（`鞋子女潮流ins百搭学生党`、`裤子女款爆款2025新款春秋款`），属于促销/长尾表达；
- 结论：可以直接公开；若追求观感，可在看板截图中把这两个词替换为“长尾泛词 A/B”。

## 复查提醒

数据集卡可能更新；正式发布前重新核对一次许可页面，并在 README 保留来源链接。
