# 看板目录

八页静态报告，全部由 `outputs_public/` 的聚合数据生成；改口径后重跑两条命令即可同步。

| 文件 | 说明 |
| --- | --- |
| `静态看板.pptx` | 八页报告源文件（可编辑，16:9） |
| `看板.pdf` | 由 PPTX 渲染的 PDF，8 页 |
| `images/page01–08.png` | 1600×900 截图，README 与 Release 使用 |
| `preview.html` | 网页版静态看板，双击即可打开，无需安装软件 |
| `data/kuaisearch_dashboard.xlsx` | 单文件聚合数据源（12 个 sheet），供二次分析或 Excel 查看 |

## 重新生成

```powershell
python scripts/build_static_dashboard.py   # 从 outputs_public 生成 PPTX
python scripts/export_dashboard.py         # 渲染 8 张 PNG + PDF（PowerPoint COM）
python scripts/check_dashboard_assets.py   # 校验页数、尺寸、空白页、应用界面条
```

`check_dashboard_assets.py` 退出码 0 才算可以发布；它会拦下空白页和带应用界面灰带的截图。
