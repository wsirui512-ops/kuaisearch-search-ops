# 上传清单

## A 已完成（自动可验证）

- [x] `python scripts/verify_docs.py` 通过；`check_all.ps1 -SkipBuild` 通过。
- [x] `.gitignore` 排除原始数据、DuckDB、Parquet、`outputs/`；公开聚合与看板文件可跟踪。
- [x] `git status --short` 中无 `data/raw`、`data/processed`、`outputs/`、`exports/` 文件。
- [x] `python scripts/apply_spotcheck.py` 要求作者确认文件、逐行判断/理由/Y；未提供确认文件时拒绝公开汇总。
- [x] 数据集许可已核查：Hugging Face 标注 **MIT**（2026-11-22，`license:mit`），记录见 [数据许可](data-license.md)。
- [x] 搜索词敏感性已扫描：Top 30 无手机号/身份证/联系方式，仅 2 个长词（促销/长尾表达）。
- [x] 既有标注与Y列完整保留在本地，未核实来源的聚合已移回`outputs/`。
- [x] 八页静态报告已重做：`dashboards/静态看板.pptx` → 8 张 1600×900 PNG + `看板.pdf`，`check_dashboard_assets.py` 退出码 0（无应用界面条、无空白页）。

## B 需要项目作者人工确认（按优先级）

- [x] 看板产物已重建并通过检查：8 页 PDF、8 张 1600×900 截图，`check_dashboard_assets.py` 退出码 0。
- [ ] 逐条核实30行（约20分钟），由实际审阅者提供`outputs/reviewer_confirmation.json`后再汇总；详见[evidence-review.md](evidence-review.md)。
- [ ] 决定是否公开 `dashboards/静态看板.pptx` 源文件（当前随仓库发布，可编辑）。
- [ ] 复核 PDF/截图中的 Top 30 词（第 5 页）；如需更保守，可把两个长词替换为“长尾泛词 A/B”。

## C 手动发布步骤

1. 在 GitHub 新建空仓库；本地运行 `git remote add origin <仓库 URL>`。
2. 检查 `git status` 与待推送 commit，再运行 `git push -u origin <分支名>`。
3. 在仓库 Settings → Pages → Build and deployment 选择 Deploy from a branch / `docs`；
   访问 `https://<用户名>.github.io/<仓库名>/`，核对图表与词级内容。
4. 创建 v1.0 Release，复制 `docs/release-notes-v1.md`；许可已核实（MIT），可附 PDF 与看板源文件。
5. 添加 topics，例如 `search-analytics`、`data-operations`、`duckdb`、`static-dashboard`。
