"""T5 ``vary_match``: can a stored response be reused for this request?

Algorithm source: ``plan/03`` section 5 (steps V1-V4), which follows RFC 9111
section 4.1 (Calculating Cache Keys with the Vary Header Field). The
normalisation policy is **data**: it is read from
``catalog["vary_normalization"]``, one row per field, so "Accept compares
case-insensitively and order-blind" is a table entry rather than a branch here.

Three rules worth naming:

* ``Vary: *`` never matches, and it is decided before any field comparison --
  an entry that varies on everything cannot be proven reusable, whatever the
  request looks like.
* "absent" and "present but empty" compare the same and report differently: a
  field only one side carried is still a ``VARY_FIELD_MISSING`` even when both
  sides normalise to the empty string.
* A field may be a cache key only once. The first member repeated in the source
  order is reported once: the catalogue sentence names a single field, and a
  later repeat is the same mistake about the same ``Vary`` value.
"""

import re

from ..rules import (
    VARY_DUPLICATE_FIELD,
    VARY_FIELD_MISMATCH,
    VARY_FIELD_MISSING,
    VARY_STAR_NEVER_MATCHES,
)
from .errors import invalid_input
from .normalise import OWS, first_value, normalise_headers

__all__ = ["evaluate_vary", "normalise_vary_value"]

MATCH_HIT = "hit"
MATCH_MISS = "miss"

WILDCARD = "*"

NOT_A_VARY_VALUE = "vary must be a string or an array of strings"

# Runs of optional whitespace, RFC 9110 section 5.6.3.
_OWS_RUNS = re.compile("[ \t]+")


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


def _outcome(match, differing, members, findings):
    return {
        "differing_headers": differing,
        "match": match,
        "normalized_vary": members,
        "reasons": _sorted_findings(findings),
    }


def _members(vary):
    """Return ``(members_sorted, first_repeat)`` for a ``Vary`` value.

    Members are trimmed, lowercased, de-duplicated and sorted -- a header name
    is case-insensitive and the field list has no order semantics (RFC 9111
    section 4.1). ``first_repeat`` is the first member seen twice in the order
    it was written, or ``None``; it is the one the ``VARY_DUPLICATE_FIELD``
    sentence can name.
    """
    if vary is None:
        return [], None
    if isinstance(vary, str):
        values = [vary]
    elif isinstance(vary, list):
        values = vary
    else:
        raise invalid_input("cached.vary", NOT_A_VARY_VALUE)

    seen = set()
    order = []
    repeat = None
    for value in values:
        if not isinstance(value, str):
            raise invalid_input("cached.vary", NOT_A_VARY_VALUE)
        for piece in value.split(","):
            member = piece.strip(OWS).lower()
            if not member:
                continue
            if member in seen:
                if repeat is None:
                    repeat = member
                continue
            seen.add(member)
            order.append(member)
    return sorted(order), repeat


def normalise_vary_value(value, policy):
    """Apply one row of ``vary_normalization`` to one header value.

    The four booleans are the whole policy: trim, fold internal whitespace,
    case sensitivity and whether comma-separated segments are order-blind. A
    missing header arrives as ``None`` and normalises like an empty value --
    the two are only distinguishable through ``VARY_FIELD_MISSING``.
    """
    text = "" if value is None else value
    if policy["trim"]:
        text = text.strip(OWS)
    if policy["fold_whitespace"]:
        text = _OWS_RUNS.sub(" ", text)
    if not policy["case_sensitive"]:
        text = text.lower()
    if policy["sort_comma_segments"]:
        segments = [segment.strip(OWS) for segment in text.split(",")]
        text = ",".join(sorted(segment for segment in segments if segment))
    return text


def evaluate_vary(arguments, catalog):
    """Judge one stored entry against one incoming request. Pure function."""
    cached = arguments.get("cached")
    if not isinstance(cached, dict):
        raise invalid_input("cached", "cached must be an object with vary and request_headers_at_store")
    incoming = arguments.get("incoming")
    if not isinstance(incoming, dict):
        raise invalid_input("incoming", "incoming must be an object with request_headers")

    # Input validation runs before the ``*`` check: a malformed header map is a
    # caller mistake even when the verdict itself is already decided.
    stored_headers = normalise_headers(
        cached.get("request_headers_at_store"), "cached.request_headers_at_store"
    )
    incoming_headers = normalise_headers(incoming.get("request_headers"), "incoming.request_headers")
    members, repeated = _members(cached.get("vary"))

    findings = []

    # V2: "varies on everything" answers the question on its own, so neither a
    # field comparison nor the duplicate notice below can change the verdict.
    if WILDCARD in members:
        findings.append(_finding(catalog, VARY_STAR_NEVER_MATCHES))
        return _outcome(MATCH_MISS, [], members, findings)

    if repeated is not None:
        findings.append(_finding(catalog, VARY_DUPLICATE_FIELD, header=repeated))

    # V3-V4: one pass over the stored field list; the policy row decides how
    # each value is compared.
    policies = catalog["vary_normalization"]
    differing = []
    for member in members:
        policy = policies["fields"].get(member, policies["default"])
        stored = normalise_vary_value(first_value(stored_headers, member), policy)
        incoming_value = normalise_vary_value(first_value(incoming_headers, member), policy)
        if (member in stored_headers) != (member in incoming_headers):
            findings.append(_finding(catalog, VARY_FIELD_MISSING, header=member))
        if stored != incoming_value:
            differing.append(member)
            findings.append(_finding(catalog, VARY_FIELD_MISMATCH, header=member))

    return _outcome(MATCH_MISS if differing else MATCH_HIT, differing, members, findings)
