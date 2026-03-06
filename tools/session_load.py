#!/usr/bin/env python3
"""
RPP Session Load — UserPromptSubmit hook script.

Reads RPP-addressed memories from ~/.claude/rpp-memory/ and outputs
formatted context. Output is injected into every Claude Code session
as a <user-prompt-submit-hook> system-reminder.

Called automatically by Claude Code before every user message.
Should complete in < 200ms. Fails silently (no output) on any error.
"""

import sys
import os

# Force UTF-8 on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Resolve the rpp package path — this script lives in rpp-spec-fix/tools/
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RPP_ROOT = os.path.dirname(SCRIPT_DIR)
if RPP_ROOT not in sys.path:
    sys.path.insert(0, RPP_ROOT)

try:
    from rpp.memory_bridge import RPPMemoryBridge

    bridge = RPPMemoryBridge()
    output = bridge.format_context()
    if output:
        print(output)
except Exception:
    # Never crash the hook — silently skip if anything goes wrong
    pass
