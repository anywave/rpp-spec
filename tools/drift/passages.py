"""Passage extraction and lexical Boundary F predicates from TR's verified ruling."""

import ast
from dataclasses import dataclass
import hashlib
import io
import re
import tokenize
import unicodedata


# T2 and t2_ns are case-sensitive, including occurrences in identifier names.
# Other alternatives are case-insensitive literal terms or the specified stems.
PHYSICS = re.compile(
    r"(?i:\bspintronics?\b|\bspin state\b|\bdecoher\w*|\bthermaliz\w*|\bthermodynam\w*|"
    r"\bHamiltonian\b|\bphysics\b|\bphysically\b|\bphysical invariant\b|\bmaterial property\b|"
    r"\bhologra\w*|\bwave interference\b)|(?<![A-Za-z0-9])(?:T2|t2_ns)(?![A-Za-z0-9])"
)
NORMATIVE = re.compile(
    r"\b(?:MUST|SHALL|REQUIRED)(?: NOT)?\b|\bnot a valid\b|"
    r"\bmust be rejected\b|\brefuse\b|\bABORT\b"
)
QUALIFIER = re.compile(
    r"\bon spintronics?(?:\s+(?:hardware|platforms|substrates))?\b|\(spintronic\)", re.I
)


def normalize(text):
    """Git blob text, LF, Unicode NFC, collapsed whitespace, trimmed."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", text)).strip()


def digest(text):
    return hashlib.sha256(normalize(text).encode("utf-8")).hexdigest()


def in_scope(path):
    return (path.endswith(".md") and ("/" not in path or path.startswith("spec/"))) or (
        path.startswith("rpp/") and path.endswith(".py")
    )


@dataclass(frozen=True)
class Passage:
    path: str
    line: int
    end: int
    kind: str
    text: str

    @property
    def sha256(self):
        return digest(self.text)


def markdown_passages(path, text):
    """One paragraph, list item, table row or complete code fence per passage."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    buffer = []
    start = 0
    kind = "paragraph"
    fence = None
    for n, line in enumerate(lines, 1):
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if fence:
            buffer.append(line)
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= fence[1]:
                yield Passage(path, start, n, "code_fence", "\n".join(buffer))
                buffer = []
                fence = None
            continue
        if marker:
            if buffer:
                yield Passage(path, start, n - 1, kind, "\n".join(buffer))
            buffer, start, kind = [line], n, "code_fence"
            fence = (marker[1][0], len(marker[1]))
            continue
        boundary = not line.strip() or re.match(r"^\s*(?:#{1,6}\s|[-*_]{3,}\s*$)", line)
        item = bool(re.match(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)", line))
        row = line.lstrip().startswith("|")
        if boundary or item or row:
            if buffer:
                yield Passage(path, start, n - 1, kind, "\n".join(buffer))
                buffer = []
            if boundary:
                continue
        if row:
            if not re.fullmatch(r"[\s|:\-]+", line):
                yield Passage(path, n, n, "table_row", line)
            continue
        if not buffer:
            start, kind = n, "list_item" if item else "paragraph"
        buffer.append(line)
    if buffer:
        yield Passage(path, start, len(lines), kind, "\n".join(buffer))


def python_passages(path, text):
    """Actual COMMENT tokens and module/class/function docstrings, never code strings."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    tree = ast.parse(text)
    result = []
    for token in tokenize.generate_tokens(io.StringIO(text).readline):
        if token.type == tokenize.COMMENT:
            result.append(Passage(path, token.start[0], token.end[0], "comment", token.string))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.body and isinstance(node.body[0], ast.Expr):
                expr = node.body[0]
                if isinstance(expr.value, ast.Constant) and isinstance(expr.value.value, str):
                    source = ast.get_source_segment(text, expr)
                    result.append(Passage(path, expr.lineno, expr.end_lineno, "docstring", source))
    return sorted(result, key=lambda p: (p.line, p.end, p.kind))


def extract(path, text):
    if not in_scope(path):
        return []
    if path.endswith(".py"):
        return python_passages(path, text)
    return list(markdown_passages(path, text))


def classify(passage):
    """Lexical candidate class only. No disclaimer, metaphor or efficacy inference."""
    text = normalize(passage.text)
    if not PHYSICS.search(text):
        return None
    if NORMATIVE.search(text) and not QUALIFIER.search(text):
        return "BND-F-1"
    return "BND-F-2"
