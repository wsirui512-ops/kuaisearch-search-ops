# 上传清单

## A 已完成（自动可验证）

- [x] `python scripts/verify_docs.py` 通过；`check_all.ps1 -SkipBuild` 通过。
- [x] `.gitignore` 排除原始数据、DuckDB、Parquet、`outputs/`、`.pbix`；公开聚合与看板文件可跟踪。
- [x] `git status --short` 中无 `data/raw`、`data/processed`、`outputs/`、`exports/` 文件。
- [x] `python scripts/apply_spotcheck.py` 对未填表、未勾选确认均报错，且无公开抽检汇总。
- [x] 数据集许可已核查：Hugging Face 标注 **MIT**（2026-11-22，`license:mit`），记录见 [数据许可](data-license.md)。
- [x] 搜索词敏感性已扫描：Top 30 无手机号/身份证/联系方式，仅 2 个长词（促销/长尾表达）。
- [x] 抽检表已预填建议值并加 `已核对（填 Y）` 列：`outputs/spotcheck_30.xlsx`。
- [x] 看板资源检查脚本 `scripts/check_dashboard_assets.py` 已就绪（当前退出码 1，见 B）。

## B 需要项目作者人工确认（按优先级）

- [ ] **重新导出看板（约 10 分钟）**：当前 8 张截图都带同一条应用界面栏，第 6 页接近空白，第 5 页表头被遮挡。
      按 [Power BI 手册](powerbi.md) 第 6 节操作后运行 `python scripts/check_dashboard_assets.py`，退出码为 0 才算通过。
- [ ] 逐条确认 `outputs/spotcheck_30.xlsx` 的 30 行（约 5–15 分钟）：H/I 列是工具预填建议，核对后在 L 列填 Y，
      再运行 `python scripts/apply_spotcheck.py`；不确认则不会生成任何汇总。
- [ ] 决定 `.pbix` 是否公开；若公开，先检查其嵌入模型与附件内容，再放 Release 或网盘。
- [ ] 复核 PDF/截图中的 Top 30 词（第 5 页）；如需更保守，可把两个长词替换为“长尾泛词 A/B”。

## C 手动发布步骤

1. 在 GitHub 新建空仓库；本地运行 `git remote add origin <仓库 URL>`。
2. 检查 `git status` 与待推送 commit，再运行 `git push -u origin <分支名>`。
3. 在仓库 Settings → Pages → Build and deployment 选择 Deploy from a branch / `docs`；
   访问 `https://<用户名>.github.io/<仓库名>/`，核对图表与词级内容。
4. 创建 v1.0 Release，复制 `docs/release-notes-v1.md`；许可已核实（MIT），可附 `.pbix` 或网盘链接。
5. 添加 topics，例如 `search-analytics`、`data-operations`、`duckdb`、`power-bi`。
