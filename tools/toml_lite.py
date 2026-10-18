"""Minimal TOML reader for the subset this project's ``pyproject.toml`` uses.

Why not ``tomllib``: the project's floor is Python 3.8 and ``tomllib`` arrived
in 3.11. Why not a dependency: the runtime has none, and a test-time dependency
for reading one file is not worth the install surface.

Supported: comments, ``[section]`` / ``[a.b]`` headers, basic and literal
strings, booleans, integers, bare keys, one-line and multi-line arrays, and
one-line inline tables. Anything outside that subset raises ``TomlSubsetError``
instead of being silently skipped -- a parser that returns a partial document
makes "the key is missing" and "the parser gave up" indistinguishable.
"""

import re

__all__ = ["loads", "load", "TomlSubsetError"]

_SECTION = re.compile(r"^\[([A-Za-z0-9_.\-]+)\]$")
_KEY_VALUE = re.compile(r"^([A-Za-z0-9_.\-]+)\s*=\s*(.*)$")
_BARE = re.compile(r"^[A-Za-z0-9_.\-+]+$")


class TomlSubsetError(ValueError):
    """The document uses syntax outside the supported subset."""


def _strip_comment(line):
    result = []
    in_string = None
    escaped = False
    for character in line:
        if in_string:
            result.append(character)
            if escaped:
                escaped = False
            elif character == "\\" and in_string == '"':
                escaped = True
            elif character == in_string:
                in_string = None
            continue
        if character in ('"', "'"):
            in_string = character
            result.append(character)
            continue
        if character == "#":
            break
        result.append(character)
    return "".join(result).strip()


def _parse_scalar(text):
    text = text.strip()
    if not text:
        raise TomlSubsetError("empty value")
    if text in ("true", "false"):
        return text == "true"
    if text.startswith("[") and text.endswith("]"):
        return [_parse_scalar(item) for item in _split_top_level(text[1:-1])]
    if text.startswith("{") and text.endswith("}"):
        table = {}
        for item in _split_top_level(text[1:-1]):
            if "=" not in item:
                raise TomlSubsetError("inline table entry without '='")
            key, value = item.split("=", 1)
            table[_parse_scalar(key)] = _parse_scalar(value)
        return table
    if text.startswith('"') and text.endswith('"') and len(text) >= 2:
        body = text[1:-1]
        return body.replace('\\"', '"').replace("\\\\", "\\")
    if text.startswith("'") and text.endswith("'") and len(text) >= 2:
        return text[1:-1]
    if re.match(r"^[+-]?[0-9]+$", text):
        return int(text)
    if _BARE.match(text):
        return text
    raise TomlSubsetError("unsupported value: " + text)


def _split_top_level(text):
    """Split on commas that are not inside brackets, braces or strings."""
    parts = []
    current = []
    depth = 0
    in_string = None
    escaped = False
    for character in text:
        if in_string:
            current.append(character)
            if escaped:
                escaped = False
            elif character == "\\" and in_string == '"':
                escaped = True
            elif character == in_string:
                in_string = None
            continue
        if character in ('"', "'"):
            in_string = character
            current.append(character)
            continue
        if character in "[{":
            depth += 1
        elif character in "]}":
            depth -= 1
        if character == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
            continue
        current.append(character)
    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return parts


def loads(text):
    document = {}
    current = document
    pending = None  # (key, accumulated array text) for multi-line arrays

    for raw in text.splitlines():
        line = _strip_comment(raw)
        if pending is not None:
            pending[1] += " " + line
            if line.endswith("]"):
                current[pending[0]] = _parse_scalar(pending[1])
                pending = None
            continue
        if not line:
            continue

        match = _SECTION.match(line)
        if match:
            current = document
            for part in match.group(1).split("."):
                current = current.setdefault(part, {})
            continue

        match = _KEY_VALUE.match(line)
        if not match:
            raise TomlSubsetError("unsupported line: " + line)
        key, value = match.group(1), match.group(2).strip()
        if value.startswith("[") and not value.endswith("]"):
            pending = [key, value]
            continue
        current[key] = _parse_scalar(value)

    if pending is not None:
        raise TomlSubsetError("unterminated array for key " + pending[0])
    return document


def load(path):
    with open(path, "r", encoding="utf-8") as handle:
        return loads(handle.read())
