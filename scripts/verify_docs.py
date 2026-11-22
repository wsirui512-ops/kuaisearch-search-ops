"""Validate scoped report cells, slide chart values and the shared experiment contract."""
import csv
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'.localdeps'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'.deps'))
from pptx import Presentation
from experiment_contract import ACTIONS, N_PER_ARM

ROOT=Path(__file__).resolve().parents[1]
def rows(name):
    with (ROOT/'outputs_public'/name).open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def table_rows(text,header):
    lines=text.splitlines();start=lines.index(header);result=[]
    for line in lines[start+2:]:
        if not line.startswith('|'):break
        result.append([v.strip() for v in line.strip().strip('|').split('|')])
    return result
def equal(actual,expected,label):
    if actual!=expected:raise AssertionError(f'{label}: actual={actual!r}; expected={expected!r}')

def main():
    report=(ROOT/'docs/analysis-report.md').read_text(encoding='utf-8')
    overview=rows('overview.csv')
    quality=json.loads((ROOT/'outputs_public/quality.json').read_text(encoding='utf-8'))
    total_requests=sum(int(r['requests']) for r in overview)
    total_exposures=sum(int(r['exposures']) for r in overview)
    headline=f"KuaiSearch-Lite：{total_requests:,} 次请求、{total_exposures:,} 次商品曝光、{int(quality['user_rows']):,} 名用户。"
    if not report.splitlines()[2].startswith(headline):raise AssertionError('report headline source mismatch')
    strata_report=[r for r in rows('length_strata.csv') if r['split']=='train']
    strata_report.sort(key=lambda r:['01-10','11-20','21-30','31-40','41-60','61-100','100+'].index(r['length_stratum']))
    expected_strata=[[r['length_stratum'],f"{int(r['requests']):,}",f"{int(r['exposures']):,}",f"{float(r['item_ctr']):.2%}",f"{float(r['request_click_rate']):.1%}"] for r in strata_report]
    equal(table_rows(report,'| 条数段 | 请求数 | 曝光数 | 商品点击率 | 请求点击率 |'),expected_strata,'report stratum cells')
    cats={r['category']:r for r in rows('category_residuals.csv')}
    names=['女装','男装','箱包/饰品','女鞋','男鞋','运动户外鞋服','家居生活']
    expected=[]
    for name in names:
        r=cats[name]
        expected.append([name,f"{int(r['exposures']):,}",f"{float(r['item_ctr']):.2%}",f"{float(r['expected_ctr']):.2%}",f"{float(r['gap_pp']):.2f}pp",f"{float(r['gap_clicks']):,.0f}"])
    equal(table_rows(report,'| 类目 | 曝光 | 实际CTR | 期望CTR | 分层差 | 差额点击 |'),expected,'category table')
    comparison={r['category']:r for r in rows('category_comparison.csv')}
    expected_comparison=[[n,f"{float(comparison[n]['item_ctr']):.2%}",f"{float(comparison[n]['raw_gap_pp']):.2f}pp",f"{float(comparison[n]['adjusted_gap_pp']):.2f}pp"] for n in names[:6]]
    equal(table_rows(report,'| 类目 | 实际CTR | 总体差 | 分层差 |'),expected_comparison,'comparison table')
    validation={r['reference']:r for r in rows('validation_baselines.csv')}
    expected_validation=[]
    for key,label in [('test_period','测试期自身基准'),('frozen_train','冻结训练基准')]:
        r=validation[key];expected_validation.append([label,r['candidates'],r['eligible'],r['consistent'],str(int(r['eligible'])-int(r['consistent']))])
    equal(table_rows(report,'| 测试参照 | 候选数 | 测试曝光≥100 | 方向一致 | 未复现 |'),expected_validation,'validation table')
    query=rows('opportunities_top30.csv');exposures=sum(int(r['exposures']) for r in query);clicks=sum(int(r['clicks']) for r in query);gap=sum(float(r['gap_clicks']) for r in query)
    equal(table_rows(report,'| 曝光 | 实际点击 | 期望点击 | 描述性差额 |'),[[f'{exposures:,}',f'{clicks:,}',f'{clicks+gap:,.0f}',f'{gap:,.0f}']],'Top30 totals')
    equal(table_rows(report,'| 动作 | 处理 | 主指标 | Owner | 每臂样本 |'),[list(a) for a in ACTIONS],'experiment contract')
    deck=Presentation(ROOT/'dashboards/静态看板.pptx');equal(len(deck.slides),8,'slide count')
    def tables(slide):return [[[c.text for c in row.cells] for row in s.table.rows] for s in slide.shapes if s.has_table]
    equal(tables(deck.slides[2])[0][1:],[[n[:5],*row[1:]] for n,row in zip(names[:6],expected_comparison)],'slide3 comparison')
    coverage=rows('review_coverage_summary.csv')
    mask={'鞋子女潮流ins百搭学生党':'长尾泛词 A','裤子女款爆款2025新款春秋款':'长尾泛词 B'}
    expected_coverage=[[mask.get(r['query'],r['query']),r['items_reviewed'],f"{float(r['avg_bigram_coverage']):.2f}",f"{float(r['pct_items_zero_coverage']):.0%}"] for r in coverage]
    equal(tables(deck.slides[5])[0][1:],expected_coverage,'slide6 automatic coverage')
    expected_queries=[[r['rank'],mask.get(r['query'],r['query']),f"{int(r['requests']):,}",f"{int(r['exposures']):,}",f"{float(r['item_ctr']):.2%}",f"{float(r['expected_ctr']):.2%}",f"{float(r['gap_pp']):.2f}pp",f"{float(r['gap_clicks']):,.0f}",r['validation']] for r in query[:15]]
    equal(tables(deck.slides[4])[0][1:],expected_queries,'slide5 Top15 values')
    strata=[r for r in rows('length_strata.csv') if r['split']=='train']
    strata.sort(key=lambda r:['01-10','11-20','21-30','31-40','41-60','61-100','100+'].index(r['length_stratum']))
    charts=[s.chart for s in deck.slides[1].shapes if s.has_chart]
    for chart,key,digits in [(charts[0],'item_ctr',3),(charts[1],'request_click_rate',1)]:
        equal(list(chart.series[0].values),[round(float(r[key])*100,digits) for r in strata],f'slide2 {key}')
    text8='\n'.join(s.text for s in deck.slides[7].shapes if s.has_text_frame)
    for a in ACTIONS:
        for field in a:
            if field not in text8:raise AssertionError(f'slide8 missing {field}')
    for path in ['dashboards/preview.html','docs/index.html','docs-site/index.html']:
        html=(ROOT/path).read_text(encoding='utf-8')
        for a in ACTIONS:
            if a[-1] not in html or a[2] not in html:raise AssertionError(f'{path}: experiment mismatch')
    print(f'PASS: report cells, dual validation, Top30 totals, slide2 charts, slide3 comparison, slide8 contract ({N_PER_ARM}/arm)')

if __name__=='__main__':main()
