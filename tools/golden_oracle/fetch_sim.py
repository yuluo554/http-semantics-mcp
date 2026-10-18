"""T2 ``cors_simulate_fetch`` -- hop-by-hop simulation over redirects.

Reference points: Fetch §CORS protocol, §CORS check, §CORS-preflight fetch,
§HTTP fetch, §HTTP-redirect fetch. ``data/README.md`` §4.7 fixes the preflight
cache key; plan/03 §2.3 fixes the event order.

Mode handling is deliberately explicit:

* ``cors``        -- every hop is judged with the CORS check; a cross-origin
                     redirect appends ``origin_set_to_null`` and, with
                     ``credentials=include``, ``credentials_dropped``.
* ``same-origin`` -- a cross-origin redirect is not followable.
* ``no-cors``     -- the response is opaque; CORS headers are not consulted and
                     nothing is visible to the caller.
"""

from .errors import invalid_input
from .cors import evaluate_cors, needs_preflight
from .inputs import (
    canonical_header_name_list,
    normalise_headers,
    normalise_method,
    serialise_origin,
    sha256_hex,
)

__all__ = ["evaluate_fetch", "EVENTS", "REDIRECT_STATUSES"]

EVENTS = ("origin_set_to_null", "credentials_dropped")
REDIRECT_STATUSES = (301, 302, 303, 307, 308)


def _max_age(headers):
    values = headers.get("access-control-max-age")
    if not values:
        return 0
    text = values[0].strip(" \t")
    return int(text) if text.isdigit() else 0


def _visible_headers(mode, response_headers, credentials):
    if mode == "no-cors":
        return []
    if mode == "same-origin":
        return canonical_header_name_list(response_headers)
    expose = []
    for value in response_headers.get("access-control-expose-headers", []):
        for piece in value.split(","):
            name = piece.strip(" \t").lower()
            if name and (name != "*" or credentials != "include"):
                expose.append(name)
    return canonical_header_name_list(list(response_headers) + expose)


def _finding(catalog, code, **params):
    record = catalog["codes"][code]
    return {
        "code": code,
        "spec_ref": record["spec_ref"],
        "detail": record["template"].format(**params),
    }


def _origin_value(raw):
    if raw is None:
        return None
    text = raw.strip(" \t")
    if text.lower() == "null":
        return "null"
    return serialise_origin(text, "origin")


def evaluate_fetch(arguments, catalog):
    method = normalise_method(arguments.get("method"), "method")
    if "url" not in arguments:
        raise invalid_input("url", "url is required")
    start_origin = serialise_origin(arguments.get("url"), "url")
    origin_key = _origin_value(arguments.get("origin"))

    credentials = arguments.get("credentials", "omit")
    if credentials not in ("omit", "include"):
        raise invalid_input("credentials", "credentials must be omit or include")
    request_headers = normalise_headers(arguments.get("request_headers"), "request_headers")

    mode = arguments.get("mode", "cors")
    if mode not in ("cors", "no-cors", "same-origin"):
        raise invalid_input("mode", "mode must be cors, no-cors or same-origin")

    response = arguments.get("response")
    if not isinstance(response, dict):
        raise invalid_input("response", "response must be an object")
    if not isinstance(response.get("status"), int) or isinstance(response.get("status"), bool):
        raise invalid_input("response.status", "status must be an integer")

    is_preflight = arguments.get("is_preflight", False)
    if not isinstance(is_preflight, bool):
        raise invalid_input("is_preflight", "is_preflight must be a boolean")

    redirects = arguments.get("redirects", [])
    if not isinstance(redirects, list):
        raise invalid_input("redirects", "redirects must be an array")
    hops_input = []
    for index, redirect in enumerate(redirects):
        field = "redirects[" + str(index) + "]"
        if not isinstance(redirect, dict):
            raise invalid_input(field, "redirect must be an object")
        if redirect.get("status") not in REDIRECT_STATUSES:
            raise invalid_input(field + ".status", "status must be a 3xx redirect status")
        if "url" not in redirect:
            raise invalid_input(field + ".url", "url is required")
        hops_input.append(
            {
                "url": serialise_origin(redirect.get("url"), field + ".url"),
                "status": redirect.get("status"),
                "headers": normalise_headers(redirect.get("headers"), field + ".headers"),
            }
        )

    events = []
    hops = []
    blocked = False
    current_origin = start_origin
    current_origin_key = origin_key

    for hop in hops_input:
        # ``hop`` is the response served by ``current_origin`` that redirects to
        # ``hop["url"]``, so it is judged against the request that produced it.
        if mode == "cors":
            hop_result = evaluate_cors(
                {
                    "method": method,
                    "origin": current_origin_key,
                    "url": current_origin,
                    "credentials": credentials,
                    "request_headers": request_headers,
                    "response": {"status": hop["status"], "headers": hop["headers"]},
                    "is_preflight": False,
                },
                catalog,
            )
            decision = hop_result["decision"]
            violations = hop_result["violations"]
        else:
            decision = "allow"
            violations = []

        hops.append(
            {
                "url": current_origin,
                "status": hop["status"],
                "decision": decision,
                "violations": violations,
            }
        )
        if decision == "block":
            blocked = True
            break

        if hop["url"] != current_origin:
            if mode == "same-origin":
                hops.append(
                    {
                        "url": hop["url"],
                        "status": hop["status"],
                        "decision": "block",
                        "violations": [
                            _finding(catalog, "CORS_REDIRECT_NOT_SAME_ORIGIN", target=hop["url"])
                        ],
                    }
                )
                blocked = True
                break
            if mode == "cors":
                events.append("origin_set_to_null")
                if credentials == "include":
                    events.append("credentials_dropped")
                current_origin_key = "null"
            current_origin = hop["url"]

    if not blocked:
        final_headers = normalise_headers(response.get("headers"), "response.headers")
        if mode == "cors":
            final = evaluate_cors(
                {
                    "method": method,
                    "origin": current_origin_key,
                    "url": arguments.get("url"),
                    "credentials": credentials,
                    "request_headers": request_headers,
                    "response": response,
                    "is_preflight": is_preflight,
                },
                catalog,
            )
            decision = final["decision"]
            violations = final["violations"]
        else:
            decision = "allow"
            violations = []

        if mode == "no-cors":
            violations = list(violations) + [_finding(catalog, "CORS_MODE_OPAQUE")]
            violations.sort(key=lambda item: (item["code"], item["detail"]))

        hops.append(
            {
                "url": current_origin,
                "status": response["status"],
                "decision": decision,
                "violations": violations,
            }
        )
        last_headers = final_headers
    else:
        decision = "block"
        last_headers = hops_input[-1]["headers"]

    return {
        "decision": "block" if blocked or decision == "block" else "allow",
        "hops": hops,
        "final_type": {"cors": "cors", "no-cors": "opaque", "same-origin": "basic"}[mode],
        "visible_headers": _visible_headers(mode, last_headers, credentials),
        "preflight_occurred": bool(is_preflight)
        or (mode == "cors" and needs_preflight(method, request_headers)),
        "preflight_cache_key": sha256_hex(
            (origin_key or "null") + "\n" + start_origin,
            catalog["preflight_cache_key"]["hex_prefix"],
        ),
        "max_age_effective": _max_age(last_headers),
        "events": events,
    }
