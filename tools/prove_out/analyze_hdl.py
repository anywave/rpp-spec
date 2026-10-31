"""Analyze actual three-module Icarus output against RPP's Python scorer."""
import argparse
import csv
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--log', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.repo.resolve()))
    from rpp.coherence import compute_coherence
    rows = []
    for line in args.log.read_text(encoding='utf-8').splitlines():
        if not line.startswith('POINT,'):
            continue
        e, c, a, b, d, av, bv, dv, flag = map(int, line.split(',')[1:])
        ref = compute_coherence(e / 31, c / 7)
        rows.append(dict(entropy=e, complecount=c, python_score=ref.score,
                         exact_hdl=a, approximate_hdl=b, lut_hdl=d,
                         python_binding=int(ref.is_binding_valid), exact_valid=av,
                         approximate_valid=bv, lut_valid=dv,
                         python_completion=int(ref.completion_flag), exact_completion=flag))
    expected = {(e, c) for e in range(32) for c in range(8)}
    if len(rows) != 256 or {(r['entropy'], r['complecount']) for r in rows} != expected:
        raise ValueError('Expected exactly the complete 32x8 input grid; data incomplete or duplicated')
    rows.sort(key=lambda r: (r['entropy'], r['complecount']))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / 'comparison.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    summary = dict(points=len(rows),
        score_mismatches={k: sum(r[k] != r['python_score'] for r in rows)
                          for k in ['exact_hdl', 'approximate_hdl', 'lut_hdl']},
        binding_mismatches_at_configured_137={k: sum(r[k] != r['python_binding'] for r in rows)
                                            for k in ['exact_valid', 'approximate_valid', 'lut_valid']},
        completion_flag_mismatches=sum(r['exact_completion'] != r['python_completion'] for r in rows))
    by_input = {(r['entropy'], r['complecount']): r for r in rows}
    for k in ['python_score', 'exact_hdl', 'approximate_hdl', 'lut_hdl']:
        summary[k + '_completion_decreases'] = sum(
            by_input[r['entropy'], r['complecount'] + 1][k] < r[k]
            for r in rows if r['complecount'] < 7)
    (args.output_dir / 'summary.json').write_text(json.dumps(summary, sort_keys=True, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(summary, sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
