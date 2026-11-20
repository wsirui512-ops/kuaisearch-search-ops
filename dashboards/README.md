# 看板目录

Power BI 看板按 [docs/powerbi.md](../docs/powerbi.md) 搭建。当前已交付：

| 文件 | 说明 |
| --- | --- |
| `preview.html` | **静态看板预览**：双击即可打开，5 页 + 相对时间附录，样式即 Power BI 的目标版式 |
| `data/kuaisearch_dashboard.xlsx` | **Power BI 单文件数据源**：12 个 sheet（说明 + 11 张表），一次连接全部导入 |
| `README.md` | 本文件 |

生成命令：

```powershell
python scripts/build_dashboard_data.py     # 重新生成 xlsx（需要 openpyxl）
python scripts/build_dashboard_preview.py  # 重新生成 preview.html（零依赖）
```

## 完成 Power BI 后的目录约定

```
dashboards/
├── 看板.pdf            # 5 页导出的 PDF
├── images/             # 每页 PNG 截图（1600×900）
├── data/kuaisearch_dashboard.xlsx
├── preview.html
└── README.md
```

`.pbix` 工程文件体积大且 GitHub 无法预览，上传到仓库的 Release，并在根 README 添加下载链接。
