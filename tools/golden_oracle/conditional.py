"""T4 ``conditional_evaluate`` -- RFC 9110 §13.2.2 precedence.

The four preconditions are evaluated in the order the specification fixes:
If-Match, If-Unmodified-Since, If-None-Match, If-Modified-Since. Only the
first applicable one decides the status; ``rule_applied`` records which.
"""

from .errors import invalid_header_value, invalid_input
from .inputs import first_value, normalise_headers, normalise_method
from .timeparse import parse_time

__all__ = ["evaluate_conditional", "strong_compare", "weak_compare", "split_etags"]

IF_MATCH = "if-match"
IF_NONE_MATCH = "if-none-match"
IF_MODIFIED_SINCE = "if-modified-since"
IF_UNMODIFIED_SINCE = "if-unmodified-since"


def _parse_etag(raw, field):
    """Return ``(weak, opaque_tag)``; opaque tag keeps its quotes."""
    if not isinstance(raw, str):
        raise invalid_header_value(field, "entity tag must be a string")
    text = raw.strip(" \t")
    weak = False
    if text.startswith("W/"):
        weak = True
        text = text[2:]
    elif text.startswith("w/"):
        raise invalid_header_value(field, "weak prefix must be exactly W/ (uppercase)")
    if len(text) < 2 or text[0] != '"' or text[-1] != '"':
        raise invalid_header_value(field, "entity tag must be a quoted opaque-tag")
    if '"' in text[1:-1]:
        raise invalid_header_value(field, "opaque-tag must not contain a quote")
    return weak, text


def split_etags(values, field):
    """Split ``*`` or a comma-separated entity-tag list."""
    items = []
    for value in values:
        for piece in value.split(","):
            trimmed = piece.strip(" \t")
            if trimmed:
                items.append(trimmed)
    if items == ["*"]:
        return "*"
    return [_parse_etag(item, field) for item in items]


def strong_compare(left, right):
    """RFC 9110 §8.8.3.2: both non-weak and opaque-tags byte-identical."""
    return left[0] is False and right[0] is False and left[1] == right[1]


def weak_compare(left, right):
    """RFC 9110 §8.8.3.2: opaque-tags byte-identical, weakness ignored."""
    return left[1] == right[1]


def _finding(catalog, code, **params):
    record = catalog["codes"][code]
    return {
        "code": code,
        "spec_ref": record["spec_ref"],
        "detail": record["template"].format(**params),
    }


def _sorted(findings):
    unique = {}
    for finding in findings:
        unique[(finding["code"], finding["detail"])] = finding
    return [unique[key] for key in sorted(unique)]


def _resource_etag(resource, field):
    if "etag" not in resource:
        return None
    raw = resource.get("etag")
    if raw is None:
        return None
    return _parse_etag(raw, field)


def _resource_last_modified(resource, field):
    raw = resource.get("last_modified")
    if raw is None:
        return None
    try:
        _, value = parse_time(raw, field)
    except Exception:
        raise invalid_input(field, "last_modified must be an ISO 8601 or HTTP-date literal")
    return value


def evaluate_conditional(arguments, catalog):
    method = normalise_method(arguments.get("method"), "method")
    request_headers = normalise_headers(arguments.get("request_headers"), "request_headers")
    resource = arguments.get("resource")
    if not isinstance(resource, dict):
        raise invalid_input("resource", "resource must be an object with etag and last_modified")

    current = _resource_etag(resource, "resource.etag")
    modified = _resource_last_modified(resource, "resource.last_modified")

    findings = []
    status = 200
    rule = "none"
    weak_used = False

    if_match = request_headers.get(IF_MATCH)
    if_none_match = request_headers.get(IF_NONE_MATCH)
    if_modified_since = request_headers.get(IF_MODIFIED_SINCE)
    if_unmodified_since = request_headers.get(IF_UNMODIFIED_SINCE)

    if if_match:
        candidates = split_etags(if_match, "request_headers.if-match")
        if candidates == "*":
            matched = current is not None
        else:
            matched = current is not None and any(strong_compare(item, current) for item in candidates)
        rule = "if_match"
        if not matched:
            status = 412
            findings.append(_finding(catalog, "COND_IF_MATCH_FAILED"))
    elif if_unmodified_since:
        raw = first_value(request_headers, IF_UNMODIFIED_SINCE)
        try:
            _, since = parse_time(raw, "request_headers.if-unmodified-since")
            applicable = True
        except Exception:
            applicable = False
            findings.append(_finding(catalog, "COND_IGNORED_INVALID_DATE", header=IF_UNMODIFIED_SINCE))
        if applicable:
            rule = "if_unmodified_since"
            if modified is not None and modified > since:
                status = 412
                findings.append(_finding(catalog, "COND_IF_UNMODIFIED_SINCE_FAILED", date=raw))
        else:
            rule = "none"
    elif if_none_match:
        candidates = split_etags(if_none_match, "request_headers.if-none-match")
        weak_used = True
        rule = "if_none_match"
        if candidates == "*":
            matched = current is not None
        else:
            matched = current is not None and any(weak_compare(item, current) for item in candidates)
        findings.append(_finding(catalog, "COND_WEAK_COMPARISON_USED"))
        if matched:
            status = 304 if method in ("GET", "HEAD") else 412
            findings.append(_finding(catalog, "COND_IF_NONE_MATCH_MATCHED"))
    elif if_modified_since and method in ("GET", "HEAD"):
        raw = first_value(request_headers, IF_MODIFIED_SINCE)
        try:
            _, since = parse_time(raw, "request_headers.if-modified-since")
            applicable = True
        except Exception:
            applicable = False
            findings.append(_finding(catalog, "COND_IGNORED_INVALID_DATE", header=IF_MODIFIED_SINCE))
        if applicable:
            rule = "if_modified_since"
            if modified is not None and modified <= since:
                status = 304
                findings.append(
                    _finding(catalog, "COND_IF_MODIFIED_SINCE_NOT_MODIFIED", date=raw)
                )

    return {
        "status": status,
        "rule_applied": rule,
        "weak_comparison_used": weak_used,
        "explain": _sorted(findings),
    }
