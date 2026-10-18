"""T3 ``cache_evaluate`` -- RFC 9111 age and freshness arithmetic.

Reference points: RFC 9111 §4.2, §4.2.1, §4.2.2, §4.2.3, §4.2.4, §5.1, §5.2.2,
§5.3; RFC 5861 §3 for stale-while-revalidate. Integer seconds only.
"""

from .errors import invalid_input
from .inputs import first_value, normalise_headers
from .timeparse import parse_time

__all__ = ["evaluate_cache", "parse_directives", "MAX_HEURISTIC_SECONDS"]

MAX_HEURISTIC_SECONDS = 86400
HEURISTIC_FRACTION = 10


def _split_directives(values):
    """Split Cache-Control values on commas that are outside quoted strings."""
    pieces = []
    for value in values:
        buffer = []
        quoted = False
        escaped = False
        for character in value:
            if escaped:
                buffer.append(character)
                escaped = False
                continue
            if character == "\\" and quoted:
                buffer.append(character)
                escaped = True
                continue
            if character == '"':
                quoted = not quoted
                buffer.append(character)
                continue
            if character == "," and not quoted:
                pieces.append("".join(buffer))
                buffer = []
                continue
            buffer.append(character)
        pieces.append("".join(buffer))
    return [piece.strip(" \t") for piece in pieces if piece.strip(" \t")]


def parse_directives(headers):
    """Return ``{lowercase_directive: first_argument_or_True}``."""
    directives = {}
    for piece in _split_directives(headers.get("cache-control", [])):
        name, separator, argument = piece.partition("=")
        key = name.strip(" \t").lower()
        if not key:
            continue
        if separator:
            value = argument.strip(" \t")
            if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
                value = value[1:-1]
            directives.setdefault(key, value)
        else:
            directives.setdefault(key, True)
    return directives


def _delta_seconds(raw):
    """Return ``None`` when the value is not a non-negative integer."""
    if raw is True:
        return None
    text = str(raw).strip(" \t")
    if not text.isdigit():
        return None
    return int(text)


def _add(findings, catalog, code, **params):
    record = catalog["codes"][code]
    findings.append(
        {
            "code": code,
            "spec_ref": record["spec_ref"],
            "detail": record["template"].format(**params),
        }
    )


def _sorted_findings(findings):
    unique = {}
    for finding in findings:
        unique[(finding["code"], finding["detail"])] = finding
    return [unique[key] for key in sorted(unique)]


def evaluate_cache(arguments, catalog):
    request_headers = normalise_headers(arguments.get("request_headers"), "request_headers")
    response_headers = normalise_headers(arguments.get("response_headers"), "response_headers")

    stored = arguments.get("stored")
    if not isinstance(stored, dict):
        raise invalid_input("stored", "stored must be an object with stored_at, age, headers")
    if "stored_at" not in stored:
        raise invalid_input("stored.stored_at", "stored_at is required")
    _, response_time = parse_time(stored.get("stored_at"), "stored.stored_at")
    stored_headers = normalise_headers(stored.get("headers"), "stored.headers")

    if "now" not in arguments:
        raise invalid_input("now", "now is required; the cache never reads a clock")
    _, now = parse_time(arguments.get("now"), "now")

    findings = []
    directives = parse_directives(response_headers)

    if "no-store" in directives:
        _add(findings, catalog, "CACHE_NO_STORE")
        return {
            "freshness_lifetime": 0,
            "current_age": 0,
            "is_fresh": False,
            "action": "miss",
            "stale_while_revalidate_window": 0,
            "must_revalidate": "must-revalidate" in directives,
            "reasons": _sorted_findings(findings),
        }

    date_raw = first_value(response_headers, "date")
    if date_raw is None:
        date_value = response_time
    else:
        _, date_value = parse_time(date_raw, "response_headers.date")

    # RFC 9111 §4.2.3: apparent_age, corrected_age_value, corrected_initial_age.
    apparent_age = max(0, response_time - date_value)
    age_raw = stored.get("age")
    if age_raw is None:
        age_raw = first_value(response_headers, "age")
    if age_raw is None:
        age_value = 0
    else:
        age_value = _delta_seconds(str(age_raw))
        if age_value is None:
            _add(findings, catalog, "CACHE_INVALID_AGE", age=age_raw)
            age_value = 0
    corrected_initial_age = max(apparent_age, age_value)

    resident_time = now - response_time
    current_age = corrected_initial_age + resident_time

    if "s-maxage" in directives:
        freshness_lifetime = _delta_seconds(directives["s-maxage"])
        if freshness_lifetime is None:
            _add(findings, catalog, "CACHE_INVALID_MAX_AGE", max_age=directives["s-maxage"])
            freshness_lifetime = None
        else:
            if freshness_lifetime == 0:
                _add(findings, catalog, "CACHE_MAX_AGE_ZERO")
    else:
        freshness_lifetime = None

    if freshness_lifetime is None and "max-age" in directives:
        freshness_lifetime = _delta_seconds(directives["max-age"])
        if freshness_lifetime is None:
            _add(findings, catalog, "CACHE_INVALID_MAX_AGE", max_age=directives["max-age"])
        elif freshness_lifetime == 0:
            _add(findings, catalog, "CACHE_MAX_AGE_ZERO")

    if freshness_lifetime is None:
        expires_raw = first_value(response_headers, "expires")
        if expires_raw is not None:
            _, expires_value = parse_time(expires_raw, "response_headers.expires")
            freshness_lifetime = expires_value - date_value
            if freshness_lifetime <= 0:
                freshness_lifetime = 0
                _add(
                    findings,
                    catalog,
                    "CACHE_EXPIRES_IN_PAST",
                    expires=expires_raw,
                    date=date_raw if date_raw is not None else stored.get("stored_at"),
                )

    if freshness_lifetime is None:
        last_modified_raw = first_value(response_headers, "last-modified")
        if last_modified_raw is None:
            heuristic = 0
        else:
            _, last_modified = parse_time(last_modified_raw, "response_headers.last-modified")
            heuristic = max(0, (date_value - last_modified) // HEURISTIC_FRACTION)
            heuristic = min(heuristic, MAX_HEURISTIC_SECONDS)
        freshness_lifetime = heuristic
        _add(
            findings,
            catalog,
            "CACHE_HEURISTIC_FRESHNESS",
            freshness_lifetime=freshness_lifetime,
        )

    is_fresh = current_age < freshness_lifetime
    must_revalidate = "must-revalidate" in directives
    swr_raw = directives.get("stale-while-revalidate")
    swr_window = _delta_seconds(swr_raw) if swr_raw is not None else 0
    if swr_window is None:
        swr_window = 0

    if "no-cache" in directives:
        action = "revalidate"
        _add(findings, catalog, "CACHE_NO_CACHE")
    elif is_fresh:
        action = "serve"
    elif must_revalidate:
        action = "revalidate"
        _add(findings, catalog, "CACHE_MUST_REVALIDATE_STALE")
    elif swr_window > 0 and (current_age - freshness_lifetime) <= swr_window:
        action = "serve"
        _add(findings, catalog, "CACHE_STALE_WHILE_REVALIDATE", window=swr_window)
    else:
        action = "revalidate"
        _add(
            findings,
            catalog,
            "CACHE_AGE_EXCEEDS_LIFETIME",
            current_age=current_age,
            freshness_lifetime=freshness_lifetime,
        )

    return {
        "freshness_lifetime": freshness_lifetime,
        "current_age": current_age,
        "is_fresh": is_fresh,
        "action": action,
        "stale_while_revalidate_window": swr_window,
        "must_revalidate": must_revalidate,
        "reasons": _sorted_findings(findings),
    }
