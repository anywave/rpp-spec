"""Turn nextpnr-ecp5 logs into a Markdown table for the CI job summary.

Usage: python3 tools/ci_synth_summary.py <synth_dir> <oss_cad_date>
Reads <synth_dir>/pnr_A.log, pnr_B.log, flow_B.status. Prints Markdown. Never fails on the numbers.
"""
import pathlib
import re
import sys

REF = {"LUT": 124, "FF": 99, "DP16KD": 1, "Fmax": 90.2}  # RPP_CONSENT_GATE.md


def parse(path):
    p = pathlib.Path(path)
    if not p.exists():
        return None
    t = p.read_text(errors="replace")

    def last(rx):
        m = re.findall(rx, t)
        return m[-1] if m else "?"

    fm = re.findall(r"Max frequency for clock\s+'[^']*':\s*([\d.]+) MHz", t)
    return {"LUT": last(r"TRELLIS_COMB:\s+(\d+)/"), "FF": last(r"TRELLIS_FF:\s+(\d+)/"),
            "DP16KD": last(r"DP16KD:\s+(\d+)/"), "Fmax": fm[-1] if fm else "?"}


def main():
    d, date = pathlib.Path(sys.argv[1]), sys.argv[2]
    a, b = parse(d / "pnr_A.log"), parse(d / "pnr_B.log")
    sp = d / "flow_B.status"
    st = sp.read_text().strip() if sp.exists() else "n/a"
    print("## Consent gate synthesis (Yosys + nextpnr-ecp5, LFE5U-12F CABGA256, target 90 MHz)\n")
    print(f"OSS CAD Suite release `{date}` (pinned, sha256-checked). Synthesis and place-and-route only; "
          "nothing is run on a board.\n")
    print("| Resource | Published (RPP_CONSENT_GATE.md) | CI flow A (documented, `abc -lut 4`) "
          "| CI flow B (standard `synth_lattice`) |")
    print("|---|---|---|---|")
    for k, label in (("LUT", "LUTs (TRELLIS_COMB)"), ("FF", "Flip-flops"),
                     ("DP16KD", "Block RAM (DP16KD)"), ("Fmax", "Max clock (MHz)")):
        print(f"| {label} | {REF[k]} | {a[k] if a else 'n/a'} | {b[k] if b else 'n/a (' + st + ')'} |")
    print("\nDifferences are recorded, not failed on: tool versions, seed and placement vary the numbers slightly.")


if __name__ == "__main__":
    main()
