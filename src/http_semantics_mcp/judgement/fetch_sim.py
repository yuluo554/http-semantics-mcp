"""T2 ``cors_simulate_fetch``: walk a redirect chain one hop at a time.

Algorithm source: ``plan/03`` section 2. Two things in here are contract, not
implementation detail:

* ``events[]`` is *ordered* and never sorted: ``origin_set_to_null`` first, then
  ``credentials_dropped`` for the same hop (plan/03 section 2.3). Both are
  appended once per cross-origin redirect, never folded together.
* ``hops[]`` carries the URL that was *requested* for that hop, and is also in
  occurrence order (data/README.md section 4.3 item 3).

Modes are explicit rather than inferred: ``cors`` judges every hop with the CORS
check, ``same-origin`` refuses to follow a cross-origin redirect, and ``no-cors``
consults no CORS header at all because the response is opaque.
"""

from ..rules import CORS_MODE_OPAQUE, CORS_REDIRECT_NOT_SAME_ORIGIN
from .cors import evaluate_cors, needs_preflight
from .errors import invalid_input
from .normalise import (
    NULL_ORIGIN,
    first_value,
    header_name_list,
    normalise_headers,
    normalise_method,
    origin_key,
    serialise_origin,
    sha256_prefix,
    split_comma_list,
)

__all__ = ["EVENTS", "REDIRECT_STATUSES", "evaluate_fetch"]

# Occurrence-order event names; the order inside a hop is fixed by plan/03 2.3.
EVENTS = ("origin_set_to_null", "credentials_dropped")

REDIRECT_STATUSES = (301, 302, 303, 307, 308)

MODES = ("cors", "no-cors", "same-origin")

FINAL_TYPES = {"cors": "cors", "no-cors": "opaque", "same-origin": "basic"}

ALLOW_MAX_AGE = "access-control-max-age"
EXPOSE_HEADERS = "access-control-expose-headers"


def _finding(catalog, code, **parameters):
    record = catalog["codes"][code]
    return {
        "code": code,
        "spec_ref": record["spec_ref"],
        "detail": record["template"].format(**parameters),
    }


def _max_age(response_headers):
    """Declared ``Access-Control-Max-Age``, or 0. Never capped (plan/03 2.6)."""
    value = first_value(response_headers, ALLOW_MAX_AGE)
    if value is None or not value.isdigit():
        return 0
    return int(value)


def _visible_headers(mode, response_headers, credentials):
    """Which response headers the caller can read, lowercased and sorted."""
    if mode == "no-cors":
        return []
    if mode == "same-origin":
        return header_name_list(response_headers)
    exposed = []
    for value in response_headers.get(EXPOSE_HEADERS, []):
        for piece in split_comma_list([value]):
            name = piece.lower()
            # With credentials the wildcard exposes nothing; it is not a name.
            if name != "*" or credentials != "include":
                exposed.append(name)
    return header_name_list(list(response_headers) + exposed)


def _read_redirects(redirects):
    """Normalise the redirect chain, naming the offending entry on error."""
    if not isinstance(redirects, list):
        raise invalid_input("redirects", "redirects must be an array")
    hops = []
    for index, redirect in enumerate(redirects):
        field = "redirects[" + str(index) + "]"
        if not isinstance(redirect, dict):
            raise invalid_input(field, "redirect must be an object")
        status = redirect.get("status")
        if not isinstance(status, int) or isinstance(status, bool) or status not in REDIRECT_STATUSES:
            raise invalid_input(field + ".status", "status must be a 3xx redirect status")
        if "url" not in redirect:
            raise invalid_input(field + ".url", "url is required")
        hops.append(
            {
                "url": serialise_origin(redirect.get("url"), field + ".url"),
                "status": status,
                "headers": normalise_headers(redirect.get("headers"), field + ".headers"),
            }
        )
    return hops


def _read_request(arguments):
    method = normalise_method(arguments.get("method"), "method")
    if "url" not in arguments:
        raise invalid_input("url", "url is required")
    start = serialise_origin(arguments.get("url"), "url")
    origin = origin_key(arguments.get("origin"), "origin")

    credentials = arguments.get("credentials", "omit")
    if credentials not in ("omit", "include"):
        raise invalid_input("credentials", "credentials must be omit or include")
    request_headers = normalise_headers(arguments.get("request_headers"), "request_headers")

    mode = arguments.get("mode", "cors")
    if mode not in MODES:
        raise invalid_input("mode", "mode must be cors, no-cors or same-origin")

    response = arguments.get("response")
    if not isinstance(response, dict):
        raise invalid_input("response", "response must be an object with status and headers")
    if not isinstance(response.get("status"), int) or isinstance(response.get("status"), bool):
        raise invalid_input("response.status", "status must be an integer")

    is_preflight = arguments.get("is_preflight", False)
    if not isinstance(is_preflight, bool):
        raise invalid_input("is_preflight", "is_preflight must be a boolean")

    return {
        "method": method,
        "start": start,
        "origin": origin,
        "credentials": credentials,
        "request_headers": request_headers,
        "mode": mode,
        "response": response,
        "is_preflight": is_preflight,
        "redirects": _read_redirects(arguments.get("redirects", [])),
    }


def _judge_hop(request, catalog, url, origin, response, is_preflight=False):
    """Run the T1 check for one hop, reusing the single CORS implementation.

    A redirect hop is never a preflight response; the final hop is, when the
    caller says so -- that is the one place ``is_preflight`` reaches T1 here.
    """
    return evaluate_cors(
        {
            "method": request["method"],
            "origin": origin,
            "url": url,
            "credentials": request["credentials"],
            "request_headers": request["request_headers"],
            "response": response,
            "is_preflight": is_preflight,
        },
        catalog,
    )


def evaluate_fetch(arguments, catalog):
    """Simulate the redirect chain, then judge the final response. Pure."""
    request = _read_request(arguments)

    mode = request["mode"]
    credentials = request["credentials"]
    events = []
    hops = []
    current_origin = request["start"]
    current_origin_key = request["origin"]
    blocked = False

    for redirect in request["redirects"]:
        # The redirect response belongs to the request that produced it, so it
        # is judged against the *current* URL and the current Origin.
        if mode == "cors":
            hop = _judge_hop(
                request,
                catalog,
                current_origin,
                current_origin_key,
                {"status": redirect["status"], "headers": redirect["headers"]},
            )
            decision = hop["decision"]
            violations = hop["violations"]
        else:
            decision = "allow"
            violations = []
        hops.append(
            {
                "url": current_origin,
                "status": redirect["status"],
                "decision": decision,
                "violations": violations,
            }
        )
        if decision == "block":
            blocked = True
            break

        if redirect["url"] != current_origin:
            if mode == "same-origin":
                hops.append(
                    {
                        "url": redirect["url"],
                        "status": redirect["status"],
                        "decision": "block",
                        "violations": [
                            _finding(catalog, CORS_REDIRECT_NOT_SAME_ORIGIN, target=redirect["url"])
                        ],
                    }
                )
                blocked = True
                break
            if mode == "cors":
                events.append("origin_set_to_null")
                if credentials == "include":
                    events.append("credentials_dropped")
                current_origin_key = NULL_ORIGIN
            current_origin = redirect["url"]

    if blocked:
        decision = "block"
        final_headers = request["redirects"][-1]["headers"]
    else:
        final_headers = normalise_headers(request["response"].get("headers"), "response.headers")
        if mode == "cors":
            final = _judge_hop(
                request,
                catalog,
                current_origin,
                current_origin_key,
                request["response"],
                request["is_preflight"],
            )
            decision = final["decision"]
            violations = final["violations"]
        else:
            decision = "allow"
            violations = []
        if mode == "no-cors":
            violations = sorted(
                violations + [_finding(catalog, CORS_MODE_OPAQUE)],
                key=lambda item: (item["code"], item["detail"]),
            )
        hops.append(
            {
                "url": current_origin,
                "status": request["response"]["status"],
                "decision": decision,
                "violations": violations,
            }
        )

    return {
        "decision": "block" if blocked or decision == "block" else "allow",
        "hops": hops,
        "final_type": FINAL_TYPES[mode],
        "visible_headers": _visible_headers(mode, final_headers, credentials),
        "preflight_occurred": bool(request["is_preflight"])
        or (mode == "cors" and needs_preflight(request["method"], request["request_headers"])),
        "preflight_cache_key": sha256_prefix(
            (request["origin"] if request["origin"] is not None else NULL_ORIGIN)
            + "\n"
            + request["start"],
            catalog["preflight_cache_key"]["hex_prefix"],
        ),
        "max_age_effective": _max_age(final_headers),
        "events": events,
    }
