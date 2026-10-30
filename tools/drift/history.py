"""Review the last 30 commits reachable from a fixed master snapshot, locally."""

import argparse
import json
from pathlib import Path

from .checker import check, git, resolve


def run(root, revision):
    revision = resolve(root, revision)
    commits = git(root, "rev-list", "--max-count=30", revision).decode().splitlines()
    rows = []
    for commit in commits:
        parents = git(root, "show", "-s", "--format=%P", commit).decode().split()
        if not parents:
            raise ValueError("history window includes a root commit without a parent")
        report = check(root, parents[0], commit)
        rows.append(dict(commit=commit, parent=parents[0], summary=report["summary"],
                         findings=report["findings"], catalog_sha256=report["catalog_sha256"]))
    return dict(master_snapshot=revision, selection="git rev-list --max-count=30; merges against first parent",
                commits=rows)


def render(result):
    lines = ["# Historical drift review", "", f"Master snapshot: `{result['master_snapshot']}`.", "",
             "Selection: last 30 reachable commits in Git rev-list order (including merges). Each is",
             "compared with its first parent. Merged changes can therefore appear more than once.",
             "Current coordinator rules apply retrospectively; findings are syntactic review candidates,",
             "not adjudicated defects. Existing specifications and historical commits were not changed.", "",
             "| Commit | Parent | HIGH | MEDIUM | LOW |", "|---|---|---:|---:|---:|"]
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
                safe = lambda s: str(s).replace("|", "&#124;").replace("<", "&lt;").replace("\n", " ")
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
    (args.output_dir / "history.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    (args.output_dir / "HISTORY.md").write_text(render(result))
    high = sum(r["summary"]["high"] for r in result["commits"])
    medium = sum(r["summary"]["medium"] for r in result["commits"])
    low = sum(r["summary"]["low"] for r in result["commits"])
    print(f"SUMMARY commits={len(result['commits'])} high={high} medium={medium} low={low}")


if __name__ == "__main__":
    main()
