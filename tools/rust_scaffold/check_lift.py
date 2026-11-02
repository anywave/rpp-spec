"""Offline Rust lift guard; Python 3.11+, stdlib only, never invokes Cargo.

This conservative scanner accepts literal include paths and public macro aliases.
Dynamic/escaped paths and source symlinks require review, not silent acceptance.
It is not a Rust compiler or a general build-script/procedural-macro analyzer.
"""
import argparse
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import tomllib

MAX_FILES, MAX_FILE_BYTES, MAX_TOTAL_BYTES, MAX_DEPTH = 512, 1024 * 1024, 8 * 1024 * 1024, 64
IDENT = re.compile(r"(?:r#)?(?:[^\W\d]|_)\w*")
RAW = re.compile(r'(?:br|cr|r)(#*)"')
CHAR = re.compile(r"'(?:\\(?:u\{[0-9A-Fa-f_]+\}|x[0-9A-Fa-f]{2}|.)|[^'\\])'")


def tokens(text):
    result, i, line = [], 0, 1
    while i < len(text):
        start, at = i, line
        if text[i].isspace():
            line += text[i] == "\n"
            i += 1
            continue
        if text.startswith("//", i):
            end = text.find("\n", i)
            i = len(text) if end < 0 else end
            continue
        if text.startswith("/*", i):
            depth, i = 1, i + 2
            while depth and i < len(text):
                if text.startswith("/*", i):
                    depth, i = depth + 1, i + 2
                elif text.startswith("*/", i):
                    depth, i = depth - 1, i + 2
                else:
                    line += text[i] == "\n"
                    i += 1
                if depth > MAX_DEPTH:
                    raise ValueError("comment nesting limit")
            if depth:
                raise ValueError("unterminated block comment")
            continue
        raw = RAW.match(text, i)
        if raw:
            if len(raw[1]) > 32:
                raise ValueError("raw string delimiter limit")
            end = text.find('"' + raw[1], raw.end())
            if end < 0:
                raise ValueError("unterminated raw string")
            i = end + 1 + len(raw[1])
            kind = "string"
        elif text[i] == '"':
            i += 1
            while i < len(text) and text[i] != '"':
                i += 2 if text[i] == "\\" else 1
            if i >= len(text):
                raise ValueError("unterminated string")
            i, kind = i + 1, "string"
        elif text[i] == "'" and (char := CHAR.match(text, i)):
            i, kind = i + len(char[0]), "character"
        elif identifier := IDENT.match(text, i):
            i, kind = identifier.end(), "identifier"
        else:
            if ord(text[i]) > 127:
                raise ValueError("unsupported non-ASCII source token requires review")
            i, kind = i + 1, "punctuation"
        value = text[start:i]
        result.append((kind, value.removeprefix("r#") if kind == "identifier" else value, at))
        line += value.count("\n")
        if len(result) > 250000:
            raise ValueError("source token limit")
    return result


def closing(items, start):
    pairs, stack = {"(": ")", "[": "]", "{": "}"}, []
    for index in range(start, len(items)):
        value = items[index][1]
        if items[index][0] != "punctuation":
            continue
        if value in pairs:
            stack.append(pairs[value])
            if len(stack) > MAX_DEPTH:
                raise ValueError("delimiter nesting limit")
        elif value in pairs.values():
            if not stack or value != stack.pop():
                raise ValueError("unbalanced delimiters")
            if not stack:
                return index
    raise ValueError("unterminated delimiters")


def literal(token):
    if token[0] != "string":
        raise ValueError("dynamic path requires review")
    value = token[1]
    if value.startswith('"'):
        value = value[1:-1]
        if "\\" in value:
            raise ValueError("escaped path requires review")
    else:
        match = RAW.match(value)
        if not value.startswith("r"):
            raise ValueError("byte/C path literal requires review")
        value = value[match.end():len(value) - 1 - len(match[1])]
    if not value or any(char in value for char in "\r\n\0"):
        raise ValueError("invalid path literal")
    return value


def contained(root, parent, value, file_only=False):
    if not isinstance(value, str) or "\\" in value or PurePosixPath(value).is_absolute() or PureWindowsPath(value).drive:
        raise ValueError("absolute, Windows or non-string path requires review")
    target = (parent / value).resolve()
    if not target.is_relative_to(root):
        raise ValueError("path escapes rust/")
    if target.relative_to(root).parts and target.relative_to(root).parts[0] in {"target", ".git"}:
        raise ValueError("path references excluded build/VCS output")
    target.resolve(strict=True)
    if file_only and not target.is_file():
        raise ValueError("include/module target is not a file")


def manifest_paths(value, depth=0):
    if depth > MAX_DEPTH:
        raise ValueError("TOML nesting limit")
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "path":
                yield child
            else:
                yield from manifest_paths(child, depth + 1)
    elif isinstance(value, list):
        for child in value:
            yield from manifest_paths(child, depth + 1)


def macro_names(sources):
    names = {"include_bytes", "include_str", "include"}
    for _ in range(MAX_DEPTH):
        previous = len(names)
        for items in sources.values():
            for index, token in enumerate(items[:-2]):
                if token[0] == "identifier" and token[1] in names and items[index + 1][1] == "as" and items[index + 2][0] == "identifier":
                    names.add(items[index + 2][1])
        if len(names) == previous:
            return names
    raise ValueError("macro alias limit")


def source_paths(items, names):
    for index, (kind, value, line) in enumerate(items):
        if kind == "identifier" and value in names and index + 1 < len(items) and items[index + 1][1] == "!":
            start = index + 2
            if start >= len(items) or items[start][1] not in {"(", "[", "{"}:
                raise ValueError("unresolved include invocation")
            end = closing(items, start)
            args = items[start + 1:end]
            if args and args[-1][1] == ",":
                args = args[:-1]
            if len(args) != 1:
                raise ValueError("dynamic include requires one literal")
            yield line, literal(args[0])
        if kind == "punctuation" and value == "#":
            start = index + 1
            if start < len(items) and items[start][1] == "!":
                start += 1
            if start < len(items) and items[start][1] == "[":
                end = closing(items, start)
                for position in range(start + 1, end - 1):
                    if items[position][1] == "path" and items[position + 1][1] == "=":
                        yield items[position][2], literal(items[position + 2])


def check(root):
    errors, sources, manifests, total, visited, candidates = [], {}, [], 0, 0, 0
    counts = dict(manifests=0, rust_sources=0, references=0)
    def issue(path, line, error):
        errors.append(f"{path.relative_to(root).as_posix()}:{line}: {str(error)}")
    if not root.is_dir() or root.is_symlink() or getattr(root.lstat(), "st_file_attributes", 0) & 0x400:
        return counts, ["rust/:0: source root must be a regular directory"]
    root = root.resolve(strict=True)
    def walk_error(error):
        issue(Path(error.filename or root), 0, "directory traversal failed")
    for directory, dirs, files in os.walk(root, followlinks=False, onerror=walk_error):
        dirs[:] = sorted(name for name in dirs if Path(directory) != root or name not in {"target", ".git"})
        for name in [*dirs, *sorted(files)]:
            visited += 1
            if visited > 4096:
                return counts, [*errors, "rust/:0: source entry limit"]
            path = Path(directory) / name
            try:
                # Windows reparse points also cover junctions on Python 3.11.
                if path.is_symlink() or getattr(path.lstat(), "st_file_attributes", 0) & 0x400:
                    raise ValueError("source symlink/junction requires review")
                contained(root, path.parent, path.name)
                if len(path.relative_to(root).parts) > MAX_DEPTH:
                    raise ValueError("source depth limit")
                if path.name != "Cargo.toml" and path.suffix != ".rs":
                    continue
                candidates += 1
                if candidates > MAX_FILES:
                    return counts, [*errors, "rust/:0: source file count limit"]
                if path.stat().st_size > MAX_FILE_BYTES:
                    raise ValueError("source file exceeds 1 MiB")
                text = path.read_text(encoding="utf-8")
                total += path.stat().st_size
                if total > MAX_TOTAL_BYTES:
                    return counts, [*errors, "rust/:0: source total byte limit"]
                if path.name == "Cargo.toml":
                    manifests.append((path, tomllib.loads(text)))
                else:
                    sources[path] = tokens(text)
            except (OSError, ValueError, RuntimeError) as error:
                issue(path, 0, error)
                if name in dirs:
                    dirs.remove(name)
    try:
        names = macro_names(sources)
        for path, data in manifests:
            counts["manifests"] += 1
            for value in manifest_paths(data):
                try:
                    contained(root, path.parent, value)
                    counts["references"] += 1
                except (OSError, ValueError, RuntimeError) as error:
                    issue(path, 0, error)
        for path, items in sources.items():
            counts["rust_sources"] += 1
            try:
                for line, value in source_paths(items, names):
                    contained(root, path.parent, value, file_only=True)
                    counts["references"] += 1
            except (OSError, ValueError, RuntimeError) as error:
                issue(path, 0, error)
    except ValueError as error:
        errors.append("rust/:0: " + str(error))
    if not manifests or not sources:
        errors.append("rust/:0: no Cargo manifests or Rust sources discovered")
    return counts, sorted(errors)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rust-root", type=Path, default=Path("rust"))
    counts, errors = check(parser.parse_args().rust_root)
    for error in errors:
        print(error)
    print("lift guard: " + " ".join(f"{key}={value}" for key, value in counts.items()) + f" findings={len(errors)}")
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
