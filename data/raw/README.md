# 原始数据存放说明

运行 `python scripts/download_data.py`，从官方固定版本下载 KuaiSearch-Lite JSONL 至 `data/raw/kuaisearch/`。脚本核验文件大小及 SHA-256。原始数据与下载清单保留本地，不提交 GitHub。

项目使用 `recall_lite/train.jsonl`、`items_lite/train.jsonl`、`users_lite/train.jsonl`、`relevance/train.jsonl`。`train.jsonl` 是官方文件名；搜索记录内部有 `split` 字段。
