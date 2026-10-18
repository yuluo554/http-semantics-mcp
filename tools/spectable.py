"""Read the numeric contract from ``data/README.md`` section 4.

``data/README.md`` section 4 is the single place where the ``code`` enum,
``spec_ref`` format, sorting, time parsing and serialisation are defined
(``plan/02`` section 3, decision K9). This module turns the human-readable
tables into Python data, so the generator, the tests and the release check all
read the same source instead of keeping a second copy.

Every reader raises :class:`SpecTableError` when a table is missing or has the
wrong shape. A silently empty table would render an empty ``codes.json`` and
make the coverage equality pass vacuously -- which is exactly the failure this
module must not allow.
"""

import os
import re

__all__ = [
    "SpecTableError",
    "read_section",
    "read_codes",
    "read_spec_refs",
    "read_error_codes",
    "read_preflight_cache_key",
    "read_vary_normalization",
    "read_notes",
    "read_output_fields",
    "VARY_COLUMNS",
]


class SpecTableError(Exception):
    """The contract section is missing or malformed."""


VARY_COLUMNS = {
    "trim": "trim",
    "折叠内部空白": "fold_whitespace",
    "大小写敏感": "case_sensitive",
    "逗号分段排序": "sort_comma_segments",
}

_CODE = re.compile(r"^[A-Z][A-Z0-9_]+$")
_PREFIXES = ("CORS_", "CACHE_", "COND_", "VARY_")
_BACKTICK = re.compile(r"`([^`]*)`")
_SEPARATOR = re.compile(r"^\|?[\s:|-]+\|?$")


def read_section(text, number):
    """Return the body of ``### <number> ...`` up to the next level-3 heading."""
    marker = "### " + number
    start = text.find(marker)
    if start < 0:
        raise SpecTableError("section " + number + " is missing from data/README.md")
    after = text.find("\n### ", start + len(marker))
    return text[start:] if after < 0 else text[start:after]


def _table_rows(section, minimum_columns, what):
    """Return the data rows of the first Markdown table in a section."""
    rows = []
    inside = False
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            if inside and rows:
                break
            continue
        inside = True
        if _SEPARATOR.match(stripped):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < minimum_columns:
            raise SpecTableError(
                what + " row has " + str(len(cells)) + " columns, expected at least "
                + str(minimum_columns) + ": " + stripped
            )
        rows.append(cells)
    if not rows:
        raise SpecTableError("no table found for " + what)
    return rows[1:]  # drop the header row


def _bare(cell):
    return cell.replace("`", "").strip()


def read_codes(text):
    """Return the ordered list of code records from section 4.1.

    Each record: ``{"code", "prefix", "severity", "spec_ref", "template", "meaning"}``.
    """
    section = read_section(text, "4.1")
    records = []
    seen = set()
    for cells in _table_rows(section, 6, "section 4.1"):
        prefix = _bare(cells[0])
        code = _bare(cells[1])
        severity = _bare(cells[2])
        specs = [_bare(token) for token in _BACKTICK.findall(cells[3]) if _bare(token)]
        template = cells[4].strip()
        meaning = cells[5].strip()

        if not _CODE.match(code):
            raise SpecTableError("section 4.1: malformed code " + repr(code))
        if not code.startswith(_PREFIXES):
            raise SpecTableError("section 4.1: code " + code + " has no known prefix")
        if not prefix.endswith("_"):
            raise SpecTableError("section 4.1: prefix cell " + prefix + " must end with '_'")
        if not code.startswith(prefix):
            raise SpecTableError("section 4.1: prefix cell " + prefix + " does not match " + code)
        if severity not in ("decisive", "informational"):
            raise SpecTableError("section 4.1: bad severity for " + code + ": " + severity)
        if not specs:
            raise SpecTableError("section 4.1: " + code + " has no spec_ref")
        if not template:
            raise SpecTableError("section 4.1: " + code + " has no detail template")
        if code in seen:
            raise SpecTableError("section 4.1: duplicate code " + code)
        seen.add(code)
        records.append(
            {
                "code": code,
                "prefix": prefix,
                "severity": severity,
                "spec_ref": sorted(specs),
                "template": template,
                "meaning": meaning,
            }
        )
    return records


def read_spec_refs(text):
    """Return ``{ref: title}`` for every verified row of section 4.2.

    The status column must carry the check mark; a registered but unverified
    clause is returned by :func:`read_unverified_refs` instead.
    """
    section = read_section(text, "4.2")
    verified = {}
    for cells in _table_rows(section, 4, "section 4.2"):
        doc = _bare(cells[0])
        locator = _bare(cells[1])
        title = cells[2].strip()
        status = cells[3].strip()
        if not doc or not locator:
            continue
        verified[doc + " " + locator] = {"title": title, "status": status}
    return verified


def read_error_codes(text):
    """Return ``{error_code: trigger}`` from section 4.6."""
    section = read_section(text, "4.6")
    codes = {}
    for cells in _table_rows(section, 2, "section 4.6"):
        name = _bare(cells[0])
        if not name:
            continue
        codes[name] = cells[1].strip()
    return codes


def read_preflight_cache_key(text):
    """Return the JSON object embedded in section 4.7."""
    import json

    section = read_section(text, "4.7")
    start = section.find("```json")
    if start < 0:
        raise SpecTableError("section 4.7 has no ```json block")
    end = section.find("```", start + len("```json"))
    if end < 0:
        raise SpecTableError("section 4.7 json block is not closed")
    payload = json.loads(section[start + len("```json") : end])
    for key in ("algorithm", "input", "canonical_url", "hex_prefix"):
        if key not in payload:
            raise SpecTableError("section 4.7 lacks " + key)
    if payload["algorithm"] != "sha256":
        raise SpecTableError("section 4.7 algorithm must be sha256")
    if not isinstance(payload["hex_prefix"], int) or payload["hex_prefix"] <= 0:
        raise SpecTableError("section 4.7 hex_prefix must be a positive integer")
    return payload


def read_vary_normalization(text):
    """Return ``{"default": {...}, "fields": {name: {...}}}`` from section 4.8."""
    section = read_section(text, "4.8")
    fields = {}
    default = None
    for cells in _table_rows(section, 5, "section 4.8"):
        name = _bare(cells[0].split("（")[0])
        if not name:
            continue
        policy = {}
        for index, column in enumerate(VARY_COLUMNS.values(), start=1):
            value = _bare(cells[index])
            if value not in ("是", "否"):
                raise SpecTableError(
                    "section 4.8: " + name + " column " + column + " must be 是/否"
                )
            policy[column] = value == "是"
        if name == "*":
            default = policy
        else:
            fields[name] = policy
    if default is None:
        raise SpecTableError("section 4.8 has no default (*) row")
    for name, policy in fields.items():
        fields[name] = dict(default, **policy)
    return {"default": default, "fields": fields}


def read_notes(text):
    """Return ``{key: {"type", "meaning"}}`` from section 4.9."""
    section = read_section(text, "4.9")
    notes = {}
    for cells in _table_rows(section, 3, "section 4.9"):
        key = _bare(cells[0])
        if not key:
            continue
        notes[key] = {"type": _bare(cells[1]), "meaning": cells[2].strip()}
    return notes


def read_output_fields(text):
    """Return ``{tool: sorted(keys)}`` from section 4.10.

    This is the schema contract: the key set of ``outputSchema.properties`` must
    equal the set declared here, for every tool. A row with no backticked keys,
    or two rows for one tool, is a malformed contract rather than an empty one.
    """
    section = read_section(text, "4.10")
    fields = {}
    for cells in _table_rows(section, 2, "section 4.10"):
        tool = _bare(cells[0])
        keys = [_bare(token) for token in _BACKTICK.findall(cells[1])]
        keys = [key for key in keys if key]
        if not tool:
            raise SpecTableError("section 4.10: a row has no tool name")
        if not keys:
            raise SpecTableError("section 4.10: " + tool + " has no output keys")
        if tool in fields:
            raise SpecTableError("section 4.10: duplicate tool " + tool)
        if len(keys) != len(set(keys)):
            raise SpecTableError("section 4.10: " + tool + " repeats an output key")
        fields[tool] = sorted(keys)
    return fields


def unverified_refs(text):
    """Return the spec refs used in 4.1 but not checked off in 4.2."""
    verified = read_spec_refs(text)
    used = set()
    for record in read_codes(text):
        used.update(record["spec_ref"])
    missing = []
    for ref in sorted(used):
        status = verified.get(ref, {}).get("status", "")
        if not status.startswith("✅"):
            missing.append(ref)
    extra = sorted(set(verified) - used)
    return missing, extra


def read_contract(root):
    """Read and validate the whole contract from ``<root>/data/README.md``."""
    path = os.path.join(root, "data", "README.md")
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()

    codes = read_codes(text)
    missing, extra = unverified_refs(text)
    if missing:
        raise SpecTableError(
            "section 4.1 uses clauses not verified in 4.2: " + ", ".join(missing)
        )
    return {
        "codes": codes,
        "verified_spec_refs": sorted(read_spec_refs(text)),
        "unused_spec_refs": extra,
        "error_codes": read_error_codes(text),
        "preflight_cache_key": read_preflight_cache_key(text),
        "vary_normalization": read_vary_normalization(text),
        "notes": read_notes(text),
        "output_fields": read_output_fields(text),
    }
