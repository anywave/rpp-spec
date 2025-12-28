"""
RPP Visual Output Module

ASCII art and optional ANSI visualizations for RPP operations.
Designed for terminal-based feedback that works in any environment.

Two modes:
  - Default (ASCII): Works everywhere (SSH, PuTTY, serial, emulators)
  - Fancy (ANSI): Color and styling for modern terminals (opt-in)
"""

from typing import Optional

# ANSI color codes (only used when fancy=True)
ANSI = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "green": "\033[32m",
    "red": "\033[31m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "cyan": "\033[36m",
    "magenta": "\033[35m",
    "bg_green": "\033[42m",
    "bg_red": "\033[41m",
    "bg_blue": "\033[44m",
    "bg_yellow": "\033[43m",
}


def _c(text: str, color: str, fancy: bool) -> str:
    """Apply color if fancy mode is enabled."""
    if fancy and color in ANSI:
        return f"{ANSI[color]}{text}{ANSI['reset']}"
    return text


def _bold(text: str, fancy: bool) -> str:
    """Apply bold if fancy mode is enabled."""
    if fancy:
        return f"{ANSI['bold']}{text}{ANSI['reset']}"
    return text


def bit_layout_diagram(shell: int, theta: int, phi: int, harmonic: int,
                       raw: int, fancy: bool = False) -> str:
    """
    Generate ASCII diagram showing the 28-bit address layout.

    Uses ASCII-only characters for Windows compatibility.

    Example output:
    +-------------------------------------------------------------+
    |  28-bit RPP Address: 0x0018A041                             |
    +------+----------+----------+----------+--------------------+
    | Rsrv |  Shell   |  Theta   |   Phi    |     Harmonic       |
    | 4bit |   2bit   |   9bit   |   9bit   |       8bit         |
    +------+----------+----------+----------+--------------------+
    | 0000 |    00    | 000001100| 100101000|     01000001       |
    |  (0) |   (0)    |   (12)   |  (296)   |       (65)         |
    |      |   Hot    |   Gene   | Abstract |                    |
    +------+----------+----------+----------+--------------------+
    """
    # Convert to binary strings
    shell_bin = f"{shell:02b}"
    theta_bin = f"{theta:09b}"
    phi_bin = f"{phi:09b}"
    harmonic_bin = f"{harmonic:08b}"

    # Get semantic names
    shell_names = {0: "Hot", 1: "Warm", 2: "Cold", 3: "Frozen"}
    shell_name = shell_names[shell]

    if theta < 64:
        sector = "Gene"
    elif theta < 128:
        sector = "Memory"
    elif theta < 192:
        sector = "Witness"
    elif theta < 256:
        sector = "Dream"
    elif theta < 320:
        sector = "Bridge"
    elif theta < 384:
        sector = "Guardian"
    elif theta < 448:
        sector = "Emergence"
    else:
        sector = "Meta"

    if phi < 128:
        grounding = "Grounded"
    elif phi < 256:
        grounding = "Transit"
    elif phi < 384:
        grounding = "Abstract"
    else:
        grounding = "Ethereal"

    # Color the header and key values
    header = _c(f"28-bit RPP Address: 0x{raw:07X}", "cyan", fancy)
    shell_val = _c(shell_name, "green" if shell == 0 else "yellow" if shell < 3 else "red", fancy)
    sector_val = _c(sector, "blue", fancy)
    ground_val = _c(grounding, "magenta", fancy)

    lines = [
        "+-------------------------------------------------------------+",
        f"|  {header:<58} |",
        "+------+----------+----------+----------+--------------------+",
        "| Rsrv |  Shell   |  Theta   |   Phi    |     Harmonic       |",
        "| 4bit |   2bit   |   9bit   |   9bit   |       8bit         |",
        "+------+----------+----------+----------+--------------------+",
        f"| 0000 |    {shell_bin}    | {theta_bin}| {phi_bin}|     {harmonic_bin}       |",
        f"|  (0) |   ({shell})    |   ({theta:^3})   |  ({phi:^3})   |       ({harmonic:^3})        |",
        f"|      | {shell_val:^8} | {sector_val:^8} | {ground_val:^8} |                    |",
        "+------+----------+----------+----------+--------------------+",
    ]

    return "\n".join(lines)


def routing_diagram(shell: int, allowed: bool, route: Optional[str],
                    reason: str, fancy: bool = False) -> str:
    """
    Generate ASCII diagram showing routing decision.

    Uses ASCII-only characters for Windows compatibility.

    Example output:
    +-----------------------------------------+
    |           ROUTING DECISION              |
    +-----------------------------------------+
    |   +-----+                               |
    |   | REQ | --> [RESOLVER] --> [ALLOWED]  |
    |   +-----+         |                     |
    |                   v                     |
    |              +---------+                |
    |              |   HOT   |                |
    |              | STORAGE |                |
    |              +---------+                |
    +-----------------------------------------+
    """
    shell_names = {0: "HOT", 1: "WARM", 2: "COLD", 3: "FROZEN"}
    shell_name = shell_names.get(shell, "???")

    if allowed:
        status_ascii = _c("[ALLOWED]", "green", fancy)
    else:
        status_ascii = _c("[DENIED]", "red", fancy)

    route_display = route if route else "null"
    shell_box = _c(shell_name, "cyan", fancy)

    lines = [
        "+-----------------------------------------+",
        "|           ROUTING DECISION              |",
        "+-----------------------------------------+",
        "|   +-----+                               |",
        f"|   | REQ | --> [RESOLVER] --> {status_ascii:<10}|",
        "|   +-----+         |                     |",
        "|                   v                     |",
        "|              +---------+                |",
        f"|              | {shell_box:^7} |                |",
        "|              | STORAGE |                |",
        "|              +---------+                |",
        "+-----------------------------------------+",
        f"|  Route:  {route_display:<30}|",
        f"|  Reason: {reason:<30}|",
        "+-----------------------------------------+",
    ]

    return "\n".join(lines)


def consent_meter(phi: int, fancy: bool = False) -> str:
    """
    Generate ASCII consent/grounding meter based on phi value.

    Uses ASCII-only characters for Windows compatibility.

    Example output:
    Consent Level: [########............] 40/511 (Grounded)
    """
    # Normalize to 20-char bar
    filled = int((phi / 511) * 20)
    empty = 20 - filled

    if phi < 128:
        level = "Grounded"
        color = "green"
    elif phi < 256:
        level = "Transitional"
        color = "yellow"
    elif phi < 384:
        level = "Abstract"
        color = "yellow"
    else:
        level = "Ethereal"
        color = "red"

    bar_filled = _c("#" * filled, color, fancy)
    bar_empty = "." * empty
    level_text = _c(level, color, fancy)

    return f"Consent Level: [{bar_filled}{bar_empty}] {phi}/511 ({level_text})"


def shell_tier_visual(shell: int, fancy: bool = False) -> str:
    """
    Generate ASCII representation of shell tier.

    Uses ASCII-only characters for Windows compatibility.

    Example output:
        o Frozen (3)
        o Cold (2)
        o Warm (1)
      > * Hot (0) < ACTIVE
    """
    lines = []
    shell_info = [
        (0, "Hot", "In-memory, immediate access"),
        (1, "Warm", "Fast storage, quick retrieval"),
        (2, "Cold", "Archive storage, slower access"),
        (3, "Frozen", "Deep archive, consent required"),
    ]

    for s, name, desc in reversed(shell_info):
        if s == shell:
            marker = _c("*", "green", fancy)
            arrow = _c(">", "cyan", fancy)
            suffix = _c("< ACTIVE", "cyan", fancy)
            lines.append(f"  {arrow} {marker} {name} ({s}) {suffix}")
        else:
            marker = "o"
            lines.append(f"    {marker} {name} ({s})")

    return "\n".join(lines)


def theta_wheel(theta: int, fancy: bool = False) -> str:
    """
    Generate ASCII representation of theta sectors as a wheel.

    Uses ASCII-only characters for Windows compatibility.
    Shows the 8 semantic sectors with the active one highlighted.
    """
    sectors = [
        (0, 63, "Gene"),
        (64, 127, "Memory"),
        (128, 191, "Witness"),
        (192, 255, "Dream"),
        (256, 319, "Bridge"),
        (320, 383, "Guardian"),
        (384, 447, "Emergence"),
        (448, 511, "Meta"),
    ]

    # Find active sector
    active_idx = 0
    for i, (start, end, name) in enumerate(sectors):
        if start <= theta <= end:
            active_idx = i
            break

    # Simple linear representation
    parts = []
    for i, (start, end, name) in enumerate(sectors):
        if i == active_idx:
            parts.append(_c(f"[{name}]", "cyan", fancy))
        else:
            parts.append(f" {name} ")

    wheel = " -> ".join(parts[:4]) + "\n" + " -> ".join(parts[4:])
    header = f"Theta Sector: {theta}/511"

    return f"{header}\n{wheel}"


def operation_status(operation: str, success: bool, fancy: bool = False) -> str:
    """
    Generate operation status indicator.

    Example: [ENCODE] OK / [ENCODE] FAIL
    """
    op_text = _c(f"[{operation.upper()}]", "bold", fancy)

    if success:
        # Use ASCII-safe symbols for Windows compatibility
        check = "[OK]" if not fancy else "OK"
        status = _c(check, "green", fancy)
    else:
        cross = "[FAIL]" if not fancy else "FAIL"
        status = _c(cross, "red", fancy)

    return f"{op_text} {status}"


def spinner_frame(frame: int) -> str:
    """
    Get a spinner animation frame.

    Uses ASCII-only characters for Windows compatibility.
    For use in fancy mode with animation.
    """
    frames = ["|", "/", "-", "\\"]
    return frames[frame % len(frames)]


def demo_banner(fancy: bool = False) -> str:
    """
    Generate RPP demo banner.

    Uses ASCII-only characters for Windows compatibility.
    """
    if fancy:
        banner = f"""{ANSI['cyan']}{ANSI['bold']}
+===========================================================+
|                                                           |
|   RRRR   PPPP   PPPP                                      |
|   R   R  P   P  P   P   Rotational Packet Protocol        |
|   RRRR   PPPP   PPPP    28-bit Semantic Addressing        |
|   R  R   P      P                                         |
|   R   R  P      P       Consent-Aware Routing             |
|                                                           |
+===========================================================+
{ANSI['reset']}"""
    else:
        banner = """
+===========================================================+
|                                                           |
|   RRRR   PPPP   PPPP                                      |
|   R   R  P   P  P   P   Rotational Packet Protocol        |
|   RRRR   PPPP   PPPP    28-bit Semantic Addressing        |
|   R  R   P      P                                         |
|   R   R  P      P       Consent-Aware Routing             |
|                                                           |
+===========================================================+
"""
    return banner


def address_mini(addr_hex: str, shell_name: str, sector: str,
                 grounding: str, fancy: bool = False) -> str:
    """
    Generate compact single-line address summary.

    Uses ASCII-only characters for Windows compatibility.

    Example: 0x0018A041 | Hot | Gene | Abstract
    """
    parts = [
        _c(addr_hex, "cyan", fancy),
        _c(shell_name, "green", fancy),
        _c(sector, "blue", fancy),
        _c(grounding, "magenta", fancy),
    ]
    return " | ".join(parts)


def success_box(message: str, fancy: bool = False) -> str:
    """Generate a success message box. Uses ASCII-only characters."""
    width = len(message) + 4
    border = "=" * width

    if fancy:
        return f"""{ANSI['green']}+{border}+
|  {message}  |
+{border}+{ANSI['reset']}"""
    else:
        return f"""+{border}+
|  {message}  |
+{border}+"""


def error_box(message: str, fancy: bool = False) -> str:
    """Generate an error message box. Uses ASCII-only characters."""
    width = len(message) + 4
    border = "=" * width

    if fancy:
        return f"""{ANSI['red']}+{border}+
|  {message}  |
+{border}+{ANSI['reset']}"""
    else:
        return f"""+{border}+
|  {message}  |
+{border}+"""
