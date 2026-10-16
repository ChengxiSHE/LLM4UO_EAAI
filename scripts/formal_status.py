"""Show the formal run without reading credentials, prompts, or responses."""
import argparse
import json
from pathlib import Path
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))


def snapshot(directory):
    progress=directory/'progress.json'
    if progress.exists():return json.loads(progress.read_text())
    db=directory/'requests.sqlite3'
    if not db.exists():return {'state':'not_started'}
    with sqlite3.connect(db) as con:
        con.row_factory=sqlite3.Row
        states=dict(con.execute('SELECT status,count(*) FROM attempts GROUP BY status'))
        total=con.execute('SELECT * FROM totals WHERE id=1').fetchone()
        halt=con.execute('SELECT reason FROM halt WHERE id=1').fetchone()
    return {'state':'stopped' if halt else 'resumable','physical_attempts':total['physical_calls'],
            'reserved_or_reported_tokens':total['physical_tokens'],'failed_attempts':states.get('failed',0),
            'unknown':states.get('reserved',0),'halt':halt[0] if halt else None}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-directory');ap.add_argument('--json',action='store_true');args=ap.parse_args()
    if args.run_directory:directory=Path(args.run_directory)
    else:
        plan=json.loads((ROOT/'experiments/full_run_plan.json').read_text());directory=ROOT/plan['run_directory']
    value=snapshot(directory)
    if args.json:print(json.dumps(value,ensure_ascii=False));return
    print('LLM4UO 正式实验')
    for label,key in [('状态','state'),('模型','model'),('API并发','max_concurrent_requests'),('当前单元','current_scope'),('矩阵进度','test_percent'),
                      ('物理请求','physical_attempts'),('重试','retry_attempts'),('失败尝试','failed_attempts'),('熔断','halt')]:
        if key in value:print(f'{label}: {value[key]}')
    if (directory/'progress.html').exists():print('进度页面:',directory/'progress.html')


if __name__=='__main__':main()
