"""Fetch small public benchmark snapshots, never execute upstream code."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    'nl4opt/nl4opt-competition': ['LICENSE', 'README.md',
        'generation_data/train.jsonl', 'generation_data/dev.jsonl', 'generation_data/test.jsonl'],
    'yangzhch6/ReSocratic': ['LICENSE', 'README.md', 'data/OptiBench.json', 'data/NL4OPT-E.json'],
    'Minw913/AlphaOPT': ['LICENSE', 'README.md',
        'data/optimization_tasks/clean/industryor.json',
        'data/optimization_tasks/clean/mamo_complex.json',
        'data/optimization_tasks/clean/nlp4lp.json',
        'data/optimization_tasks/clean/nl4opt.json'],
}


def fetch_repo(repo, revision=None):
    s = requests.Session()
    meta = s.get(f'https://api.github.com/repos/{repo}', timeout=(6, 30))
    meta.raise_for_status()
    metadata = meta.json()
    if revision is None:
        commit = s.get(f'https://api.github.com/repos/{repo}/commits/{metadata["default_branch"]}', timeout=(6, 30))
        commit.raise_for_status()
        revision = commit.json()['sha']
    records = []
    for path in SOURCES[repo]:
        url = f'https://raw.githubusercontent.com/{repo}/{revision}/{path}'
        response = s.get(url, timeout=(6, 40))
        response.raise_for_status()
        dest = ROOT / 'data/raw' / repo.replace('/', '__') / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            if dest.read_bytes() != response.content:
                raise FileExistsError('Existing source snapshot differs; do not overwrite it')
        else:
            dest.write_bytes(response.content)
            dest.chmod(0o444)
        rows = None
        if path.endswith('.jsonl'):
            rows = sum(1 for line in response.content.splitlines() if line.strip())
        elif path.endswith('.json'):
            parsed = response.json()
            rows = len(parsed) if isinstance(parsed, (list, dict)) else None
        records.append({'repo': repo, 'revision': revision, 'upstream_path': path,
            'url': url, 'local_path': str(dest.relative_to(ROOT)),
            'bytes': len(response.content), 'sha256': hashlib.sha256(response.content).hexdigest(),
            'top_level_items_or_rows': rows,
            'repository_license': (metadata.get('license') or {}).get('spdx_id'),
            'data_license_note': 'Repository license is not a blanket relicense of upstream datasets; review provenance before redistribution.'})
    return records


def main():
    records, failures = [], []
    manifest_path = ROOT / 'data/manifests/source_manifest.json'
    existing = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    pins = {r['repo']: r['revision'] for r in existing.get('records', [])}
    with ThreadPoolExecutor(max_workers=3) as pool:
        tasks = {pool.submit(fetch_repo, r, pins.get(r)): r for r in SOURCES}
        for future in as_completed(tasks):
            repo = tasks[future]
            try:
                batch = future.result()
                records.extend(batch)
                print(f'Fetched {repo}: {len(batch)} files', flush=True)
            except Exception as error:
                failures.append({'repo': repo, 'error_type': type(error).__name__})
                print(f'Fetch failed: {repo}: {type(error).__name__}', flush=True)
    manifest = {'retrieved_at_utc': datetime.now(timezone.utc).isoformat(),
        'records': sorted(records, key=lambda x: (x['repo'], x['upstream_path'])),
        'failures': failures,
        'notes': ['These are source snapshots, not yet a locked or audited experimental dataset.',
                  'Hugging Face API connectivity timed out locally; official cards were checked through web search.',
                  'AlphaOPT clean files are derivative benchmark versions and must not be called original releases.']}
    if failures and existing:
        (ROOT / 'data/manifests/fetch_failure.json').write_text(json.dumps(manifest, indent=2))
    elif not existing:
        manifest_path.write_text(json.dumps(manifest, indent=2))
    else:
        print('Pinned source snapshots verified; original manifest preserved.', flush=True)
    return int(bool(failures))


if __name__ == '__main__':
    raise SystemExit(main())
