"""Build the report's audited tables from public aggregates; no manual labels inferred."""
import csv
from pathlib import Path
from experiment_contract import ACTIONS, N_PER_ARM

ROOT = Path(__file__).resolve().parents[1]
def read(name):
    with (ROOT / "outputs_public" / name).open(encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))

def main():
    strata = [r for r in read("length_strata.csv") if r["split"] == "train"]
    strata.sort(key=lambda r: ["01-10","11-20","21-30","31-40","41-60","61-100","100+"].index(r['length_stratum']))
    cats = {r["category"]:r for r in read("category_residuals.csv")}
    comparisons = {r["category"]:r for r in read("category_comparison.csv")}
    queries = read("opportunities_top30.csv")
    validation = {r["reference"]:r for r in read("validation_baselines.csv")}
    report = '''# 搜索需求与点击效率诊断

KuaiSearch-Lite：555,553 次请求、17,800,904 次商品曝光、102,086 名用户。分析主线是找出值得搜索运营核查的需求，公开数据不支持估算策略增量。

## 1. 问题与决策

运营每周只有有限的词包和商家治理人力。直接按曝光与点击率排清单，会把列表长度不同的需求混在一起。我选择先统一比较条件，再按描述性差额排查词；暂不把差额换算成收益。

训练段有 539,012 次请求，测试段有 16,541 次，测试的相对时间索引严格晚于训练。购买是行为标签，不是订单；1,438 个购买商品不在同次点击列表，约占购买标签的 2.82%。因此没有构建严格交易漏斗。

## 2. 先分开两个分母

商品点击率 = 点击商品 / 曝光商品；请求点击率 = 有点击的请求 / 请求。前者衡量单条结果被点的频率，后者记录一次搜索是否至少有一次点击，不把点击当作满意度。

| 条数段 | 请求数 | 曝光数 | 商品点击率 | 请求点击率 |
| --- | ---: | ---: | ---: | ---: |
'''
    for r in strata:
        report += f"| {r['length_stratum']} | {int(r['requests']):,} | {int(r['exposures']):,} | {float(r['item_ctr']):.2%} | {float(r['request_click_rate']):.1%} |\n"
    report += '''
100+ 条组只占训练请求的 6.9%，贡献 40.3% 曝光。两种点击率方向相反，是采用条数分层比较的依据；观察性分组没有识别增加列表长度的效果。

## 3. 校准前后的差距与相邻名次

训练基准：`期望点击 = Σ(各条数段曝光 × 训练段该段CTR)`；`gap_pp = (期望CTR − 实际CTR) × 100`；`gap_clicks = 期望点击 − 实际点击`。

下面只比较相同的六个高曝光类目。“总体差”相对训练总体 CTR 3.83%，“分层差”相对该类目的同条数期望。两者回答不同问题，不能把调整后的差距当成因果解释。

| 类目 | 实际CTR | 总体差 | 分层差 |
| --- | ---: | ---: | ---: |
'''
    names = ["女装","男装","箱包/饰品","女鞋","男鞋","运动户外鞋服"]
    for name in names:
        r = comparisons[name]
        report += f"| {name} | {float(r['item_ctr']):.2%} | {float(r['raw_gap_pp']):.2f}pp | {float(r['adjusted_gap_pp']):.2f}pp |\n"
    report += '''
女装从 0.78pp 收窄到 0.25pp；男鞋校准前后都低于女装，没有发生二者排序反转。调整后的六类中，男装略高于女鞋，说明构成调整确实可能改变相邻名次。8.96% 是 1–10 条组的点击率，不是全样本基准。

| 类目 | 曝光 | 实际CTR | 期望CTR | 分层差 | 差额点击 |
| --- | ---: | ---: | ---: | ---: | ---: |
'''
    for name in names + ["家居生活"]:
        r = cats[name]
        report += f"| {name} | {int(r['exposures']):,} | {float(r['item_ctr']):.2%} | {float(r['expected_ctr']):.2%} | {float(r['gap_pp']):.2f}pp | {float(r['gap_clicks']):,.0f} |\n"
    report += '''
女装的差额总量较大，适合核查大词包；男鞋单位曝光差较大，适合先定位问题。没有把它们直接转成项目 ROI：治理成本、可触达商家数和策略成功概率尚未取得。

## 4. 哪些结论经得住换一种比较

把召回位置也纳入基准（条数 × 1–5/6–10/11–20/21–40/41+ 位置段），Top 30 缺口变化最大 0.009pp。按差额点击重排，第 12/13 与 24/25 名互换；头部方向相近，完整排名并非不变。结果见 `sensitivity_position.csv`。召回位置不等于真实展示位。

需求标签的分层残差范围为 −0.34pp 至 +0.20pp。这里只报告范围，未设业务等效阈值，也未检验“无关联”；36.8% 请求落在“无品类信号”，规则标签要先抽样核查，不能据此做精细人群投放。

## 5. 从124个候选缩小到本周清单

训练门槛为请求≥100、用户≥30、曝光≥1,000，且低于同条数基准，共 124 个候选。Top 30 汇总如下：

| 曝光 | 实际点击 | 期望点击 | 描述性差额 |
| ---: | ---: | ---: | ---: |
'''
    exposure = sum(int(r["exposures"]) for r in queries)
    clicks = sum(int(r["clicks"]) for r in queries)
    gap = sum(float(r["gap_clicks"]) for r in queries)
    report += f"| {exposure:,} | {clicks:,} | {clicks+gap:,.0f} | {gap:,.0f} |\n\n"
    report += "| 测试参照 | 候选数 | 测试曝光≥100 | 方向一致 | 未复现 |\n| --- | ---: | ---: | ---: | ---: |\n"
    for key, label in [("test_period","测试期自身基准"),("frozen_train","冻结训练基准")]:
        r = validation[key]
        report += f"| {label} | {r['candidates']} | {r['eligible']} | {r['consistent']} | {int(r['eligible'])-int(r['consistent'])} |\n"
    triage = read('opportunity_triage_top30.csv')
    tier_counts = {tier:sum(r['review_tier']==tier for r in triage) for tier in ['both','neither','insufficient','disagree']}
    report += f"\nTop30中，两参照均同向{tier_counts['both']}词、均未复现{tier_counts['neither']}词、样本不足{tier_counts['insufficient']}词、参照分歧{tier_counts['disagree']}词。逐词分层见`opportunity_triage_top30.csv`。\n"
    report += '''
测试期自身基准检查“在当期同条数条件下是否仍落后”，冻结训练基准检查跨期方向。两者都复用了训练期筛选的候选，未做独立确认性检验；另有38个词测试曝光不足。该比较只改变验证参照，不改原124个候选或Top30排序。

周一搜索运营先处理10个词：优先选择两种复核均同向且可定位商品的问题，其次查两种参照意见不一致的词；没有复现的词先观察。再按商家触达可行性和预计处理工时排队。每词记录问题、owner、预计工时、关闭标准，周五核对处置而不追认“增长”。详见运营手册。

## 6. 商品级证据的当前状态

10个词各取曝光前10件商品，二字覆盖率用于安排核查。鞋子平均覆盖率0.20、衣服0.00，但标题可以通过“板鞋”“卫衣”等具体品类表达需求，字面覆盖不是相关性。

本地30条既有标注计数为26/4/0；4条部分相关分布为“鞋子”1条、“鞋子女潮流ins百搭学生党”3条。上传清单与标注来源存在冲突，来源待作者确认，当前不作为人工抽检证据公开。原记录保留在本地，不推测或补写人工判断。

相同二级类目只说明分类相同，不能据此认定同款、风格同质或缺少有效选择。下一步人工核查标题中的型号、季节、版型信息，记录具体缺失项；只有核查通过的词才进入属性补全实验。

## 7. 运营动作：一次只验证一项

三项均采用稳定的用户随机分流；每用户只取实验期内首次合格搜索，主指标为该次搜索是否发生商品点击。使用同一指标方便比较方案，后续请求留作辅助分析。

| 动作 | 处理 | 主指标 | Owner | 每臂样本 |
| --- | --- | --- | --- | --- |
'''
    for action in ACTIONS:
        report += "| " + " | ".join(action) + " |\n"
    report += f'''
样本估算：基线53%、目标56%、MDE3pp、双侧α=0.05、power=80%，正态近似为每臂{N_PER_ARM:,}名独立用户。53%来自请求口径，只作规划假设；上线预观察期须重估首次合格搜索基线，再锁定样本。C仅改变展示属性，不修改共享索引，避免对照组也获得补全内容。

购买请求率、覆盖商品数、曝光<5条请求占比为护栏。达到预设样本与完整业务周期后，主指标差的95%区间下界>0、且护栏通过预设非劣界才进入扩大；具体停机规则和样本量公式见实验方案。未观测线上流量，不换算虚构实验天数。

## 8. 取舍与口径边界

- Lite抽样机制未公开，相对时间索引不对应日期；本报告只描述样本。
- 召回顺序不对应真实展示位；购买标签非订单，没有GMV与策略增量。
- 候选筛选与p/q统计共用训练数据，同请求曝光相关；p/q保留为探索列，不参与本版筛选或显著性结论。
- 主线用DuckDB，Spark只交叉对账。没有运行官方107GB全量；当前规模不值得再引入服务型分析引擎。

## 9. 复现

直接查看：`dashboards/preview.html`、PDF和截图。重算需Python3.13及四份固定revision的Lite JSONL，数据不随仓库分发。

```powershell
python -m pip install -r requirements.txt
python scripts/download_data.py
python run.py
powershell -ExecutionPolicy Bypass -File scripts/check_all.ps1 -SkipBuild -SkipRender
```

重建PNG/PDF另需Windows和已安装的Microsoft PowerPoint：移除`-SkipRender`即可。两条路线均校验公开数字和现有看板。管道将数据库与聚合导出暂存后一起发布，普通异常回滚旧文件；突然断电不保证跨文件原子性。
'''
    (ROOT / "docs/analysis-report.md").write_text(report, encoding="utf-8")
    print("Built report tables from public aggregates")

if __name__ == "__main__":
    main()
