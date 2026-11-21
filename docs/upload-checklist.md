# 上传清单

## A 已完成（自动可验证）

- [x] `python scripts/verify_docs.py` 通过；`check_all.ps1 -SkipBuild` 通过。
- [x] `.gitignore` 排除原始数据、DuckDB、Parquet、`outputs/`、`.pbix`；公开聚合与看板文件可跟踪。
- [x] `git status --short` 中无 `data/raw`、`data/processed`、`outputs/`、`exports/` 文件。
- [x] `python scripts/apply_spotcheck.py` 对未填表报错，且无公开抽检汇总。

## B 需要项目作者人工确认

- [ ] 核实数据集许可是否允许公开聚合结果和示例搜索词；记录许可页与核实日期。
- [ ] 审阅 `outputs_public/`、`dashboards/preview.html`、PDF、截图、数据源 XLSX 中的 query，确认不含敏感词。
- [ ] 决定 `.pbix` 是否公开；若公开，先检查其嵌入模型与附件内容。
- [ ] 在安装 Power BI Desktop 的电脑打开本地 `.pbix`，导出八页 PDF 与 1600×900 截图，并检查 Top 30 词是否需要脱敏。
- [ ] 填 `outputs/spotcheck_30.xlsx` 的 30 行判断与理由（约 20 分钟）；运行 `python scripts/apply_spotcheck.py` 后再将人工结果写入报告 §7。

## C 手动发布步骤

1. 在 GitHub 新建空仓库；本地运行 `git remote add origin <仓库 URL>`。
2. 检查 `git status` 与待推送 commit，再运行 `git push -u origin <分支名>`。
3. 将 `docs-site/index.html` 复制到发布分支的 `docs/index.html`；在仓库 Settings → Pages → Build and deployment 选择 Deploy from a branch / `docs`。访问 `https://<用户名>.github.io/<仓库名>/`，核对图表与词级内容。也可用 GitHub Actions 工作流直接发布 `docs-site/`。
4. 创建 v1.0 Release，复制 `docs/release-notes-v1.md`；若已获许可且审阅通过，再附 `.pbix` 或网盘链接。
5. 添加 topics，例如 `search-analytics`、`data-operations`、`duckdb`、`power-bi`。
