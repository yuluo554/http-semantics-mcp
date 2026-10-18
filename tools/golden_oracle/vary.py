"""T5 ``vary_match`` -- RFC 9111 §4.1 cache-key matching.

Normalisation is data, not code (data/README.md §4.8): the policy table is
read from ``codes.json`` so that the tool and the oracle cannot drift apart by
accident.
"""

from .errors import invalid_input
from .inputs import canonical_header_name_list, normalise_headers

__all__ = ["evaluate_vary", "normalise_value"]


def _collapse(value):
    out = []
    previous_space = False
    for character in value:
        if character in (" ", "\t"):
            if not previous_space:
                out.append(" ")
            previous_space = True
            continue
        out.append(character)
        previous_space = False
    return "".join(out)


def normalise_value(value, policy):
    text = value if policy.get("trim", True) else value
    if policy.get("trim", True):
        text = text.strip(" \t")
    if policy.get("fold_whitespace", True):
        text = _collapse(text)
    if not policy.get("case_sensitive", True):
        text = text.lower()
    if policy.get("sort_comma_segments", False):
        parts = [part.strip(" \t") for part in text.split(",")]
        text = ",".join(sorted(part for part in parts if part))
    return text


def _policy_for(name, table):
    return table["fields"].get(name, table["default"])


def evaluate_vary(arguments, catalog):
    cached = arguments.get("cached")
    if not isinstance(cached, dict):
        raise invalid_input("cached", "cached must be an object with vary and request_headers_at_store")
    incoming = arguments.get("incoming")
    if not isinstance(incoming, dict):
        raise invalid_input("incoming", "incoming must be an object with request_headers")

    cached_headers = normalise_headers(cached.get("request_headers_at_store"), "cached.request_headers_at_store")
    incoming_headers = normalise_headers(incoming.get("request_headers"), "incoming.request_headers")

    vary_raw = cached.get("vary")
    if vary_raw is None:
        vary_values = []
    elif isinstance(vary_raw, str):
        vary_values = [vary_raw]
    elif isinstance(vary_raw, list) and all(isinstance(item, str) for item in vary_raw):
        vary_values = vary_raw
    else:
        raise invalid_input("cached.vary", "vary must be a string or an array of strings")

    listed = []
    for value in vary_values:
        for piece in value.split(","):
            name = piece.strip(" \t").lower()
            if name:
                listed.append(name)

    table = catalog["vary_normalization"]
    normalized = canonical_header_name_list(listed)
    findings = []

    def add(code, **params):
        record = catalog["codes"][code]
        findings.append(
            {
                "code": code,
                "spec_ref": record["spec_ref"],
                "detail": record["template"].format(**params),
            }
        )

    if "*" in normalized:
        add("VARY_STAR_NEVER_MATCHES")
        return {
            "match": "miss",
            "differing_headers": [],
            "normalized_vary": normalized,
            "reasons": findings,
        }

    for name in listed:
        if listed.count(name) > 1:
            add("VARY_DUPLICATE_FIELD", header=name)
            break

    differing = []
    for name in normalized:
        policy = _policy_for(name, table)
        left_present = name in cached_headers
        right_present = name in incoming_headers
        left = normalise_value(cached_headers[name][0], policy) if left_present else ""
        right = normalise_value(incoming_headers[name][0], policy) if right_present else ""
        if left_present != right_present:
            add("VARY_FIELD_MISSING", header=name)
        if left != right:
            differing.append(name)
            add("VARY_FIELD_MISMATCH", header=name)

    return {
        "match": "miss" if differing else "hit",
        "differing_headers": canonical_header_name_list(differing),
        "normalized_vary": normalized,
        "reasons": sorted(findings, key=lambda item: (item["code"], item["detail"])),
    }
