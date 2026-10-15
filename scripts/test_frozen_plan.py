"""Run the local unit suite and bind its result to the current frozen plan."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from llm4or.schema import digest
from llm4or.pipeline import write_json


def main():
    plan=json.loads((ROOT/'experiments/full_run_plan.json').read_text());expected=digest(plan)
    logfile=ROOT/'results/full_preparation_tests.txt'
    with logfile.open('w') as log:
        result=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    if digest(json.loads((ROOT/'experiments/full_run_plan.json').read_text()))!=expected:raise ValueError('plan_changed_during_tests')
    write_json(ROOT/'results/test_run_binding.json',{'plan_sha256':expected,'exit_code':result.returncode,
               'test_log_sha256':hashlib.sha256(logfile.read_bytes()).hexdigest(),'actual_model_api_calls':0})
    print(json.dumps({'tests_exit_code':result.returncode,'plan_sha256':expected}))
    if result.returncode:raise SystemExit(result.returncode)


if __name__=='__main__':main()
