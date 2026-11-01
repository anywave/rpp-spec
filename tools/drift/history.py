"""Review the last 30 commits reachable from a fixed master snapshot, locally."""

import argparse
import json
from pathlib import Path

from .checker import check, git, resolve


def run(root, revision):
    revision = resolve(root, revision)
    commits = git(root, "rev-list", "--max-count=30", revision).decode("utf-8").splitlines()
    rows = []
    for commit in commits:
        parents = git(root, "show", "-s", "--format=%P", commit).decode("utf-8").split()
        if not parents:
            raise ValueError("history window includes a root commit without a parent")
        report = check(root, parents[0], commit)
        rows.append(dict(commit=commit, parent=parents[0], summary=report["summary"],
                         findings=report["findings"], baseline_events=report["baseline_events"],
                         steward_items=report["steward_items"], advisories=report["advisories"],
                         catalog_sha256=report["catalog_sha256"]))
    return dict(master_snapshot=revision, selection="git rev-list --max-count=30; merges against first parent",
                commits=rows)


def render(result):
    lines = ["# Historical drift review", "", f"Master snapshot: `{result['master_snapshot']}`.", "",
             "Selection: last 30 reachable commits in Git rev-list order (including merges). Each is",
             "compared with its first parent. Merged changes can therefore appear more than once.",
             "Current coordinator rules apply retrospectively; findings are syntactic review candidates,",
             "not adjudicated defects. Existing specifications and historical commits were not changed.", "",
             "| Commit | Parent | HIGH | MEDIUM | LOW |", "|---|---|---:|---:|---:|"]
    if result["commits"]:
        summary = result["commits"][0]["summary"]
        lines[4:4] = [f"Open baseline: {summary['open_baselines']}; open steward items: {summary['open_steward_items']}; "
                      f"open LOW advisory groups: {summary['open_advisories']}. Open counts exclude ruled/decided entries.", ""]
    for row in result["commits"]:
        s = row["summary"]
        lines.append(f"| {row['commit'][:12]} | {row['parent'][:12]} | {s['high']} | {s['medium']} | {s['low']} |")
    lines += ["", "## Every HIGH/MEDIUM finding", "",
              "Full exact diff excerpts and source references are retained in `history.json`.", "",
              "| Commit | Severity | Rule | Path | Line | Source | Tag |",
              "|---|---|---|---|---:|---|---|"]
    for row in result["commits"]:
        for f in row["findings"]:
            if f["severity"] in {"HIGH", "MEDIUM"}:
                # Repository history paths here are ordinary text, but escape delimiters.
                def safe(value):
                    return str(value).replace("|", "&#124;").replace("<", "&lt;").replace("\n", " ")
                lines.append("| " + " | ".join(map(safe, [row["commit"][:12], f["severity"], f["rule_id"],
                                                           f["path"], f["line"], f["source"], f["tag"]])) + " |")
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = run(Path.cwd(), args.master)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "history.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")
    (args.output_dir / "HISTORY.md").write_text(render(result), encoding="utf-8", newline="\n")
    high = sum(r["summary"]["high"] for r in result["commits"])
    medium = sum(r["summary"]["medium"] for r in result["commits"])
    low = sum(r["summary"]["low"] for r in result["commits"])
    print(f"SUMMARY commits={len(result['commits'])} high={high} medium={medium} low={low}")
    if result["commits"]:
        summary = result["commits"][0]["summary"]
        print("open: baselines={open_baselines} steward_items={open_steward_items} "
              "advisories={open_advisories}; unresolved - steward decision (RADIX)".format(**summary))


if __name__ == "__main__":
    main()
