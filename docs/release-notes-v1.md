# v1 发布说明

版本：v1.0（发布准备稿，尚未推送或创建 Release）。

数据集：`benchen4395/KuaiSearch`，revision `16f555af360f6a86209f60eb1f12462f9e25be2c`，KuaiSearch-Lite 四份 JSONL。SHA-256：

| 文件 | SHA-256 |
| --- | --- |
| recall_lite/train.jsonl | `8949ed6b5cf685bb69067710ac70da12fd7999f66e66bafea4b9d8d78bfefe8a` |
| users_lite/train.jsonl | `9853a69555ae52508200ce7855502fa52ad2e1875662193091b9993005f29554` |
| relevance/train.jsonl | `b26c79a3ae6fde4aadc756c7b9eda9f6dcc6e112b725db603def868ab9f9c720` |
| items_lite/train.jsonl | `5c04e031324a37636afb2f822a4d862378d7f54eada93875d686fa8f31bd2621` |

包含：DuckDB SQL 管道、聚合 CSV、质量与跨引擎对账、分析报告、运营手册、实验设计、静态看板与抽检脚手架。人工标题抽检尚未完成，公开产物不含商品级抽检判断。

已知限制：Lite 为采样数据；`time_index` 不是日历时间；召回位置不是实际展示位；购买标签不是订单；机会词差额是描述性指标，现有 p/q 值不用于确认性推断。数据集再分发许可及公开 query 内容尚待人工确认。

复现：

```powershell
python -m pip install -r requirements.txt
python scripts/download_data.py
python run.py
powershell -ExecutionPolicy Bypass -File scripts/check_all.ps1 -SkipBuild
```

看板：仓库内 `dashboards/preview.html` 和 `docs-site/index.html` 可直接查看。八页 `.pbix` 的 PDF 与截图尚未导出。`.pbix` 被 `.gitignore` 排除；仅在确认许可与词级内容后，通过 GitHub Release 附件或个人网盘提供下载地址。
