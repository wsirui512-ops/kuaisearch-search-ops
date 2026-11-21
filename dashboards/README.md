# 看板交付

| 文件 | 用途 |
| --- | --- |
| `kuaisearch-search-ops.pbix` | 本机 Power BI Desktop 八页报告：总览、条数效率、品类残差、需求标签、机会清单、标题审阅、相对时间、运营动作 |
| `preview.html` | 可直接打开的静态业务预览，版式与 Power BI 报告分别维护 |
| `data/kuaisearch_dashboard.xlsx` | 生成 `.pbix` 所用的工作簿，报告导入了其中 11 张数据表 |

`.pbix` 已在 Power BI Desktop 创建并保存，含聚合表及 Top 30 搜索词。文件被 `.gitignore` 排除，仅供本机审阅；确认数据再分发范围前，不上传 GitHub Release。八页 PDF 与截图尚待在安装 Power BI Desktop 的电脑导出。项目边界见 [面试展示版](../docs/interview-release-v1.md)，搭建方法见 [Power BI 手册](../docs/powerbi.md)。

若重新生成 `data/kuaisearch_dashboard.xlsx`，在 Power BI Desktop 内刷新并逐页核对指标；当前 `.pbix` 是截至 2026-11-21 的已保存快照。
