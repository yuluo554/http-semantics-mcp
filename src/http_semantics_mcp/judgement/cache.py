"""T3 ``cache_evaluate``: can this stored response be served as-is?

Algorithm source: ``plan/03`` section 3 (steps C1-C11), which follows RFC 9111
section 4.2 (Freshness), 4.2.1 (freshness lifetime), 4.2.2 (heuristic
freshness), 4.2.3 (age) and 4.2.4 (serving stale), plus RFC 5861 section 3 for
the ``stale-while-revalidate`` extension. Every sentence emitted here is read
from the generated catalogue; this module picks a rule and supplies its
parameters.

Discipline worth naming, because it is easy to violate by accident:

* **No clock.** ``now`` is an argument (decision D7). The cache age is a
  subtraction of two caller-supplied instants.
* **Integer seconds.** No float ever enters the arithmetic, so ``10.5`` is not
  a "slightly stale" entry -- it is an unparsable directive.
* **Stale is not fresh.** ``is_fresh`` is a strict ``<``; ``current_age ==
  freshness_lifetime`` is stale (plan/03 section 3.2).
"""

from ..rules import (
    CACHE_AGE_EXCEEDS_LIFETIME,
    CACHE_EXPIRES_IN_PAST,
    CACHE_HEURISTIC_FRESHNESS,
    CACHE_INVALID_AGE,
    CACHE_INVALID_MAX_AGE,
    CACHE_MAX_AGE_ZERO,
    CACHE_MUST_REVALIDATE_STALE,
    CACHE_NO_CACHE,
    CACHE_NO_STORE,
    CACHE_STALE_WHILE_REVALIDATE,
)
from .errors import invalid_input
from .normalise import first_value, normalise_headers
from .timeparse import parse_time

__all__ = ["evaluate_cache", "parse_directives", "MAX_HEURISTIC_SECONDS", "HEURISTIC_DIVISOR"]

# RFC 9111 section 4.2.2 caps a heuristic lifetime at 24 hours; the 10% rule is
# the conventional fraction of the Date - Last-Modified distance.
MAX_HEURISTIC_SECONDS = 86400
HEURISTIC_DIVISOR = 10


def _split_directives(values):
    """Split Cache-Control values on commas that are *outside* a quoted string.

    ``no-cache="set-cookie, x-foo"`` is one directive with a list argument, not
    two directives; splitting naively on every comma would invent ``x-foo``.
    """
    pieces = []
    for value in values:
        current = []
        quoted = False
        escaped = False
        for character in value:
            if escaped:
                current.append(character)
                escaped = False
            elif character == "\\" and quoted:
                current.append(character)
                escaped = True
            elif character == '"':
                quoted = not quoted
                current.append(character)
            elif character == "," and not quoted:
                pieces.append("".join(current))
                current = []
            else:
                current.append(character)
        pieces.append("".join(current))
    return [piece.strip(" \t") for piece in pieces if piece.strip(" \t")]


def parse_directives(headers):
    """Return ``{lowercase_directive: first_argument_or_True}``.

    The first occurrence of a directive wins, matching how a cache is expected
    to treat a duplicated directive, and the argument keeps its quotes stripped
    (``max-age="60"`` is the same as ``max-age=60``).
    """
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
    """Return the value as a non-negative int, or ``None`` when it is not one.

    A bare directive (``max-age`` with no ``=``) parses to ``True`` and is
    therefore invalid, not zero -- "declared without a value" is a different
    mistake from "declared as 0".
    """
    if raw is True:
        return None
    text = str(raw).strip(" \t")
    if not text.isdigit():
        return None
    return int(text)


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


def _freshness_lifetime(headers, directives, date_value, date_raw, stored_at_raw, findings, catalog):
    """Resolve the freshness lifetime in RFC 9111 section 4.2.1 priority order.

    ``s-maxage`` > ``max-age`` > ``Expires - Date`` > heuristic. Each invalid
    or informational step appends its finding and falls through to the next
    source rather than aborting, which is why a malformed ``max-age`` can still
    end up fresh via ``Expires``.

    ``date_raw`` / ``stored_at_raw`` are only used to render the
    ``CACHE_EXPIRES_IN_PAST`` sentence: it quotes the header as written, so a
    missing Date falls back to the stored-at literal the caller supplied.
    """
    from_sharing = None
    if "s-maxage" in directives:
        from_sharing = _delta_seconds(directives["s-maxage"])
        if from_sharing is None:
            findings.append(_finding(catalog, CACHE_INVALID_MAX_AGE, max_age=directives["s-maxage"]))
        elif from_sharing == 0:
            findings.append(_finding(catalog, CACHE_MAX_AGE_ZERO))
    if from_sharing is not None:
        return from_sharing

    from_private = None
    if "max-age" in directives:
        from_private = _delta_seconds(directives["max-age"])
        if from_private is None:
            findings.append(_finding(catalog, CACHE_INVALID_MAX_AGE, max_age=directives["max-age"]))
        elif from_private == 0:
            findings.append(_finding(catalog, CACHE_MAX_AGE_ZERO))
    if from_private is not None:
        return from_private

    expires_raw = first_value(headers, "expires")
    if expires_raw is not None:
        _, expires_value = parse_time(expires_raw, "response_headers.expires")
        remaining = expires_value - date_value
        if remaining <= 0:
            findings.append(
                _finding(
                    catalog,
                    CACHE_EXPIRES_IN_PAST,
                    expires=expires_raw,
                    date=date_raw if date_raw is not None else stored_at_raw,
                )
            )
            return 0
        return remaining

    last_modified_raw = first_value(headers, "last-modified")
    if last_modified_raw is None:
        heuristic = 0
    else:
        _, last_modified = parse_time(last_modified_raw, "response_headers.last-modified")
        heuristic = (date_value - last_modified) // HEURISTIC_DIVISOR
        if heuristic < 0:
            heuristic = 0
        elif heuristic > MAX_HEURISTIC_SECONDS:
            heuristic = MAX_HEURISTIC_SECONDS
    findings.append(_finding(catalog, CACHE_HEURISTIC_FRESHNESS, freshness_lifetime=heuristic))
    return heuristic


def evaluate_cache(arguments, catalog):
    """Judge a stored response against RFC 9111 freshness. Pure function."""
    response_headers = normalise_headers(arguments.get("response_headers"), "response_headers")
    normalise_headers(arguments.get("request_headers"), "request_headers")

    stored = arguments.get("stored")
    if not isinstance(stored, dict):
        raise invalid_input("stored", "stored must be an object with stored_at, age, headers")
    if "stored_at" not in stored:
        raise invalid_input("stored.stored_at", "stored_at is required")
    _, response_time = parse_time(stored.get("stored_at"), "stored.stored_at")
    normalise_headers(stored.get("headers"), "stored.headers")

    if "now" not in arguments:
        raise invalid_input("now", "now is required; the cache never reads a clock")
    _, now = parse_time(arguments.get("now"), "now")

    directives = parse_directives(response_headers)
    findings = []

    # C2: no-store short-circuits. Nothing is computed afterwards, so a
    # ``max-age`` next to it can never make the entry usable.
    if "no-store" in directives:
        findings.append(_finding(catalog, CACHE_NO_STORE))
        return {
            "action": "miss",
            "current_age": 0,
            "freshness_lifetime": 0,
            "is_fresh": False,
            "must_revalidate": "must-revalidate" in directives,
            "stale_while_revalidate_window": 0,
            "reasons": _sorted_findings(findings),
        }

    # C3-C4: the reference date is the Date header, or the store's own clock
    # when the origin omitted it (RFC 9111 section 4.2.3).
    date_raw = first_value(response_headers, "date")
    if date_raw is None:
        date_value = response_time
    else:
        _, date_value = parse_time(date_raw, "response_headers.date")

    apparent_age = response_time - date_value
    if apparent_age < 0:
        apparent_age = 0

    # C5-C6: the Age header is the origin/cache's declaration; ``stored.age``
    # is that value as it was recorded at store time and takes precedence over a
    # (usually identical) Age header.
    age_raw = stored.get("age")
    if age_raw is None:
        age_raw = first_value(response_headers, "age")
    if age_raw is None:
        age_value = 0
    else:
        age_value = _delta_seconds(age_raw)
        if age_value is None:
            findings.append(_finding(catalog, CACHE_INVALID_AGE, age=age_raw))
            age_value = 0

    corrected_initial_age = apparent_age if apparent_age > age_value else age_value

    # C7-C8: resident time is what the entry has been sitting in this store.
    resident_time = now - response_time
    current_age = corrected_initial_age + resident_time

    # C9: freshness lifetime, in priority order.
    freshness_lifetime = _freshness_lifetime(
        response_headers,
        directives,
        date_value,
        date_raw,
        stored.get("stored_at"),
        findings,
        catalog,
    )

    # C10-C11.
    is_fresh = current_age < freshness_lifetime
    must_revalidate = "must-revalidate" in directives
    swr_raw = directives.get("stale-while-revalidate")
    swr_window = _delta_seconds(swr_raw) if swr_raw is not None else 0
    if swr_window is None:
        swr_window = 0

    if "no-cache" in directives:
        # A fresh no-cache entry still has to be revalidated: freshness is a
        # necessary condition, not a sufficient one.
        action = "revalidate"
        findings.append(_finding(catalog, CACHE_NO_CACHE))
    elif is_fresh:
        action = "serve"
    elif must_revalidate:
        action = "revalidate"
        findings.append(_finding(catalog, CACHE_MUST_REVALIDATE_STALE))
    elif swr_window > 0 and current_age - freshness_lifetime <= swr_window:
        action = "serve"
        findings.append(_finding(catalog, CACHE_STALE_WHILE_REVALIDATE, window=swr_window))
    else:
        action = "revalidate"
        findings.append(
            _finding(
                catalog,
                CACHE_AGE_EXCEEDS_LIFETIME,
                current_age=current_age,
                freshness_lifetime=freshness_lifetime,
            )
        )

    return {
        "action": action,
        "current_age": current_age,
        "freshness_lifetime": freshness_lifetime,
        "is_fresh": is_fresh,
        "must_revalidate": must_revalidate,
        "stale_while_revalidate_window": swr_window,
        "reasons": _sorted_findings(findings),
    }
