"""Execute the actual Linux Flow A workflow fragment with disposable mock tools."""

from pathlib import Path
import os
import subprocess
import textwrap


def flow_a_fragment():
    workflow = Path(__file__).resolve().parents[2] / ".github/workflows/consent-gate.yml"
    body = workflow.read_text(encoding="utf-8").split("          # Reset status markers", 1)[1]
    body = "          # Reset status markers" + body.split("          # Flow B", 1)[0]
    return textwrap.dedent(body)


def run_flow_a(directory, yosys_status, nextpnr_status, fragment=None):
    directory.mkdir(parents=True, exist_ok=True)
    commands = directory / "commands"
    commands.mkdir()
    (directory / "flow_A.status").write_text("ok\n", encoding="utf-8")
    (directory / "flow_B.status").write_text("ok\n", encoding="utf-8")
    for name, body in (
        ("yosys", 'printf "status-at-yosys:\\n"\ncat "$out/flow_A.status" "$out/flow_B.status"\n'
         f"exit {yosys_status}\n"),
        ("nextpnr-ecp5", f'printf "TRELLIS_COMB: 124/1000\\n"\nexit {nextpnr_status}\n'),
    ):
        tool = commands / name
        tool.write_text("#!/bin/sh\n" + body, encoding="utf-8")
        tool.chmod(0o755)
    return subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", fragment if fragment is not None else flow_a_fragment()],
        cwd=directory,
        env={**os.environ, "PATH": str(commands) + os.pathsep + os.environ.get("PATH", ""), "out": str(directory)},
        text=True, encoding="utf-8", capture_output=True, check=False,
    )
