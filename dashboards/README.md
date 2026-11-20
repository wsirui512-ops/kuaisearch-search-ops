# 看板目录

Power BI 看板为 P4 阶段的交付物，当前版本已提供：

- **数据源**：`outputs_public/`（聚合、可公开，无用户级数据）
- **搭建手册**：[docs/powerbi.md](../docs/powerbi.md)（导入、模型、DAX、5 页布局、导出）
- **占位图表**：`docs/images/chart_*.svg`（README 使用，看板完成后可替换为看板截图）

## 完成后的目录约定

```
dashboards/
├── 看板.pdf            # 5 页导出的 PDF
├── images/             # 每页 PNG 截图（1600×900）
└── README.md
```

`.pbix` 工程文件体积大且 GitHub 无法预览，上传到仓库的 Release，并在根 README 添加下载链接。
