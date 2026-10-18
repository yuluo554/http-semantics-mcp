"""T4 ``conditional_evaluate``: which precondition decides the status?

Algorithm source: ``plan/03`` section 4 (steps E1-E5), which follows RFC 9110
section 13.2.2 (Precedence of Preconditions) with the individual rules from
13.1.1-13.1.4 and the comparison rules from 8.8.3.2. Every sentence emitted
here is read from the generated catalogue; this module only picks a rule and
supplies its parameters.

Four disciplines that are easy to lose by accident:

* **Order is the answer.** The first applicable precondition decides and the
  later ones are never read. ``If-Match`` therefore outranks
  ``If-Unmodified-Since`` even when the latter is unparsable, and a passing
  ``If-Match`` is what explains why ``If-Modified-Since`` never ran.
* **Two comparison functions, not one with a flag.** ``strong_compare`` is for
  ``If-Match`` (both tags strong and byte-identical), ``weak_compare`` for
  ``If-None-Match`` (the ``W/`` marker is dropped before comparing).
* **A bad resource field is a caller mistake; a bad request date is ignored.**
  ``resource.last_modified`` / ``resource.etag`` are caller-supplied metadata
  and are validated up front. An unparsable ``If-Modified-Since`` only cancels
  its own condition and is reported in ``explain[]`` -- ``cond-012`` answers
  200, not a tool error.
* **``*`` needs a current representation.** ``If-Match: *`` passes only when the
  resource carries an entity tag, and ``If-None-Match: *`` matches only then.
"""

from ..rules import (
    COND_IF_MATCH_FAILED,
    COND_IF_MODIFIED_SINCE_NOT_MODIFIED,
    COND_IF_NONE_MATCH_MATCHED,
    COND_IF_UNMODIFIED_SINCE_FAILED,
    COND_IGNORED_INVALID_DATE,
    COND_WEAK_COMPARISON_USED,
)
from .errors import JudgementError, invalid_header_value, invalid_input
from .normalise import OWS, first_value, normalise_headers, normalise_method
from .timeparse import parse_time

__all__ = ["evaluate_conditional", "strong_compare", "weak_compare"]

# ``rule_applied`` values (data/README.md section 4.10: a closed enumeration).
RULE_NONE = "none"
RULE_IF_MATCH = "if_match"
RULE_IF_UNMODIFIED_SINCE = "if_unmodified_since"
RULE_IF_NONE_MATCH = "if_none_match"
RULE_IF_MODIFIED_SINCE = "if_modified_since"

# A precondition that decides 304 is the pair of retrieval methods; a failed
# precondition on any other method is a 412 (RFC 9110 section 13.1.2).
SAFE_METHODS = ("GET", "HEAD")

STATUS_OK = 200
STATUS_NOT_MODIFIED = 304
STATUS_PRECONDITION_FAILED = 412

IF_MATCH = "if-match"
IF_UNMODIFIED_SINCE = "if-unmodified-since"
IF_NONE_MATCH = "if-none-match"
IF_MODIFIED_SINCE = "if-modified-since"

REQUEST_FIELDS = "request_headers"

NOT_A_TAG = "entity tag must be a quoted opaque-tag"
NOT_AN_UPPERCASE_WEAK_MARKER = "weak prefix must be exactly W/ (uppercase)"


def _finding(catalog, code, **parameters):
    record = catalog["codes"][code]
    return {
        "code": code,
        "spec_ref": record["spec_ref"],
        "detail": record["template"].format(**parameters),
    }


def _sorted_findings(findings):
    unique = {}
    for finding in findings:
        unique[(finding["code"], finding["detail"])] = finding
    return [unique[key] for key in sorted(unique)]


def _result(rule, status, findings, weak_used):
    return {
        "explain": _sorted_findings(findings),
        "rule_applied": rule,
        "status": status,
        "weak_comparison_used": weak_used,
    }


def parse_entity_tag(raw, field):
    """Parse one ``entity-tag`` (RFC 9110 section 8.8.3), or raise.

    The ``W/`` prefix is accepted in exactly one spelling. A lowercase ``w/``
    is not a weak marker with a typo -- it is a different token, and reading it
    as weak would let a malformed request satisfy ``If-Match`` (``cond-014``
    freezes this as a tool error rather than a guess).

    The opaque-tag keeps its quotes: comparison is byte-for-byte over the
    quoted form, which is why the quotes are part of the returned string.
    """
    text = raw.strip(OWS)
    weak = False
    if text[:2] in ("w/", "W/"):
        if text[:2] != "W/":
            raise invalid_header_value(field, NOT_AN_UPPERCASE_WEAK_MARKER)
        weak = True
        text = text[2:]
    if len(text) < 2 or text[0] != '"' or text[-1] != '"' or '"' in text[1:-1]:
        raise invalid_header_value(field, NOT_A_TAG)
    return {"weak": weak, "tag": text}


def parse_condition_value(raw, field):
    """Return ``(is_wildcard, tags)`` for one ``If-Match`` / ``If-None-Match``.

    ``*`` means "any current representation" only as the whole field value. A
    ``*`` inside a list is not an entity-tag and is rejected rather than
    dropped, because dropping it would silently change what the list asserts.
    An empty value carries no tags at all, which is not the same as ``*``.
    """
    text = raw.strip(OWS)
    if text == "*":
        return True, []
    tags = []
    for piece in text.split(","):
        piece = piece.strip(OWS)
        if not piece:
            continue
        tags.append(parse_entity_tag(piece, field))
    return False, tags


def strong_compare(left, right):
    """RFC 9110 section 8.8.3.2 strong comparison: both strong, byte-equal."""
    return not left["weak"] and not right["weak"] and left["tag"] == right["tag"]


def weak_compare(left, right):
    """Weak comparison: the ``W/`` marker was dropped at parse time."""
    return left["tag"] == right["tag"]


def _read_resource(arguments):
    """Return ``(etag, last_modified_timestamp)``; either may be ``None``.

    Both fields describe the *current* representation, so both are validated
    before any rule runs: a garbage date here is a caller mistake, not a
    condition to ignore (which is how ``If-Modified-Since: not a date`` differs
    from ``resource.last_modified: not a date``). The error codes are the ones
    ``data/README.md`` section 4.6 already assigns -- a malformed entity tag is
    an ``INVALID_HEADER_VALUE``, an unparsable time literal is an
    ``INVALID_TIME_FORMAT`` -- so ``parse_time`` is called without a wrapper.
    """
    resource = arguments.get("resource")
    if not isinstance(resource, dict):
        raise invalid_input("resource", "resource must be an object with etag and last_modified")

    etag = None
    raw_etag = resource.get("etag")
    if raw_etag is not None:
        if not isinstance(raw_etag, str):
            raise invalid_input("resource.etag", "etag must be a string or null")
        etag = parse_entity_tag(raw_etag, "resource.etag")

    modified = None
    raw_modified = resource.get("last_modified")
    if raw_modified is not None:
        _, modified = parse_time(raw_modified, "resource.last_modified")
    return etag, modified


def _header_date(raw, header, findings, catalog):
    """Parse a request-header date, or record that the condition is ignored.

    ``None`` is the signal that this condition must not be evaluated at all --
    not that the date was the epoch. RFC 9110 lets a malformed date be ignored,
    and plan/03 section 4.2 chooses to say so in ``explain[]`` instead of
    failing the call.
    """
    try:
        _, value = parse_time(raw, REQUEST_FIELDS + "." + header)
    except JudgementError:
        findings.append(_finding(catalog, COND_IGNORED_INVALID_DATE, header=header))
        return None
    return value


def _if_match_holds(wildcard, tags, etag):
    if etag is None:
        return False
    if wildcard:
        return True
    return any(strong_compare(tag, etag) for tag in tags)


def _if_none_match_holds(wildcard, tags, etag):
    if etag is None:
        return False
    if wildcard:
        return True
    return any(weak_compare(tag, etag) for tag in tags)


def evaluate_conditional(arguments, catalog):
    """Judge the preconditions of one request. Pure function."""
    method = normalise_method(arguments.get("method"), "method")
    if "request_headers" not in arguments:
        raise invalid_input(REQUEST_FIELDS, "request_headers is required")
    headers = normalise_headers(arguments.get(REQUEST_FIELDS), REQUEST_FIELDS)
    etag, modified = _read_resource(arguments)

    findings = []

    # E1: If-Match decides on its own, whether it passes or fails. Nothing
    # below it is even parsed.
    if_match = first_value(headers, IF_MATCH)
    if if_match is not None:
        wildcard, tags = parse_condition_value(if_match, REQUEST_FIELDS + "." + IF_MATCH)
        if not _if_match_holds(wildcard, tags, etag):
            findings.append(_finding(catalog, COND_IF_MATCH_FAILED))
            return _result(RULE_IF_MATCH, STATUS_PRECONDITION_FAILED, findings, False)
        return _result(RULE_IF_MATCH, STATUS_OK, findings, False)

    # E2: only reached when If-Match is absent. An unparsable date cancels this
    # condition and falls through to E3, leaving rule_applied at "none".
    if_unmodified = first_value(headers, IF_UNMODIFIED_SINCE)
    if if_unmodified is not None:
        limit = _header_date(if_unmodified, IF_UNMODIFIED_SINCE, findings, catalog)
        if limit is not None:
            if modified is not None and modified > limit:
                findings.append(
                    _finding(catalog, COND_IF_UNMODIFIED_SINCE_FAILED, date=if_unmodified)
                )
                return _result(RULE_IF_UNMODIFIED_SINCE, STATUS_PRECONDITION_FAILED, findings, False)
            return _result(RULE_IF_UNMODIFIED_SINCE, STATUS_OK, findings, False)

    # E3: If-None-Match outranks If-Modified-Since, and it is the one condition
    # evaluated with weak comparison.
    if_none_match = first_value(headers, IF_NONE_MATCH)
    if if_none_match is not None:
        wildcard, tags = parse_condition_value(if_none_match, REQUEST_FIELDS + "." + IF_NONE_MATCH)
        findings.append(_finding(catalog, COND_WEAK_COMPARISON_USED))
        if _if_none_match_holds(wildcard, tags, etag):
            findings.append(_finding(catalog, COND_IF_NONE_MATCH_MATCHED))
            status = STATUS_NOT_MODIFIED if method in SAFE_METHODS else STATUS_PRECONDITION_FAILED
            return _result(RULE_IF_NONE_MATCH, status, findings, True)
        return _result(RULE_IF_NONE_MATCH, STATUS_OK, findings, True)

    # E4: the cache-validator rule, meaningful only for retrieval methods.
    if_modified = first_value(headers, IF_MODIFIED_SINCE)
    if if_modified is not None and method in SAFE_METHODS:
        limit = _header_date(if_modified, IF_MODIFIED_SINCE, findings, catalog)
        if limit is not None:
            if modified is not None and modified <= limit:
                findings.append(
                    _finding(catalog, COND_IF_MODIFIED_SINCE_NOT_MODIFIED, date=if_modified)
                )
                return _result(RULE_IF_MODIFIED_SINCE, STATUS_NOT_MODIFIED, findings, False)
            return _result(RULE_IF_MODIFIED_SINCE, STATUS_OK, findings, False)

    # E5: no precondition applies (or the only one present was ignored).
    return _result(RULE_NONE, STATUS_OK, findings, False)
