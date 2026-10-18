"""T1 ``cors_evaluate`` -- Fetch Standard CORS check, written from the spec text.

Reference points (data/README.md §4.2):
  Fetch §CORS check          -- the response check
  Fetch §CORS protocol       -- which requests need a preflight
  Fetch §CORS-preflight fetch -- Allow-Methods / Allow-Headers / Max-Age
"""

from .errors import invalid_input
from .inputs import canonical_header_name_list, normalise_headers, normalise_method, serialise_origin

__all__ = [
    "SAFELISTED_METHODS",
    "needs_preflight",
    "unsafe_request_headers",
    "evaluate_cors",
]

SAFELISTED_METHODS = ("GET", "HEAD", "POST")
SAFELISTED_HEADERS = ("accept", "accept-language", "content-language", "content-type", "range")

# CORS-unsafe request-header bytes: CTLs other than HTAB, plus the
# separators that make a value ambiguous to a server.
_UNSAFE_BYTES = set(range(0x00, 0x20)) - {0x09}
_UNSAFE_BYTES |= {0x22, 0x28, 0x29, 0x3A, 0x3C, 0x3E, 0x3F, 0x40, 0x5B, 0x5C, 0x5D, 0x7B, 0x7D, 0x7F}
_LANGUAGE_BYTES = set(range(0x30, 0x3A)) | set(range(0x41, 0x5B)) | set(range(0x61, 0x7B))
_LANGUAGE_BYTES |= {0x20, 0x2A, 0x2C, 0x2D, 0x2E, 0x3B, 0x3D}

CONTENT_TYPE_ESSENCES = (
    "application/x-www-form-urlencoded",
    "multipart/form-data",
    "text/plain",
)

DEFAULT_READABLE = (
    "cache-control",
    "content-language",
    "content-length",
    "content-type",
    "expires",
    "last-modified",
    "pragma",
)


def _has_unsafe_bytes(value):
    return any(ord(character) in _UNSAFE_BYTES for character in value)


def _is_safelisted_header(name, value):
    if name == "accept":
        return not _has_unsafe_bytes(value)
    if name in ("accept-language", "content-language"):
        return all(ord(character) in _LANGUAGE_BYTES for character in value)
    if name == "content-type":
        if _has_unsafe_bytes(value):
            return False
        essence = value.split(";", 1)[0].strip(" \t").lower()
        return essence in CONTENT_TYPE_ESSENCES
    if name == "range":
        return _is_simple_range(value)
    return False


def _is_simple_range(value):
    """``bytes=N-M`` with N <= M; the plan deliberately simplifies RFC 9110 ranges."""
    text = value.strip(" \t")
    if not text.lower().startswith("bytes="):
        return False
    spec = text[len("bytes=") :]
    if "," in spec:
        return False
    first, separator, last = spec.partition("-")
    if not separator or not first.isdigit() or not last.isdigit():
        return False
    return int(first) <= int(last)


def unsafe_request_headers(headers):
    """Names that force a preflight, in the request's own casing order."""
    unsafe = []
    for name in sorted(headers):
        if name == "authorization":
            unsafe.append(name)
            continue
        if name in SAFELISTED_HEADERS:
            if all(_is_safelisted_header(name, value) for value in headers[name]):
                continue
            unsafe.append(name)
            continue
        unsafe.append(name)
    return unsafe


def needs_preflight(method, headers):
    return method not in SAFELISTED_METHODS or bool(unsafe_request_headers(headers))


def _origin_key(value, field):
    """Normalise a request Origin. ``null`` is the opaque-origin literal."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise invalid_input(field, "origin must be a string or null")
    text = value.strip(" \t")
    if text.lower() == "null":
        return "null"
    try:
        return serialise_origin(text, field)
    except Exception:
        raise invalid_input(field, "origin must be scheme://host[:port] or the literal null")


def _allow_origin(headers):
    values = headers.get("access-control-allow-origin")
    if not values:
        return None
    return values[0].strip(" \t")


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


def _coverage_ok(methods, method, credentials):
    """Fetch §CORS-preflight fetch, method step, including the ``*`` exception."""
    if method in methods:
        return True
    if method in SAFELISTED_METHODS:
        return True
    return "*" in methods and credentials != "include"


def _header_coverage_ok(allow_headers, name, credentials):
    """Fetch §CORS-preflight fetch, header steps.

    ``authorization`` is the CORS non-wildcard request-header name: ``*``
    never covers it, whatever the credentials mode.
    """
    if any(item.lower() == name for item in allow_headers):
        return True
    if name == "authorization":
        return False
    if credentials == "include":
        return False
    return "*" in allow_headers


def evaluate_cors(arguments, catalog):
    method = normalise_method(arguments.get("method"), "method")
    if "url" not in arguments:
        raise invalid_input("url", "url is required")
    url_origin = serialise_origin(arguments.get("url"), "url")
    origin = _origin_key(arguments.get("origin"), "origin")

    credentials = arguments.get("credentials", "omit")
    if credentials not in ("omit", "include"):
        raise invalid_input("credentials", "credentials must be omit or include")
    request_headers = normalise_headers(arguments.get("request_headers"), "request_headers")

    response = arguments.get("response")
    if not isinstance(response, dict):
        raise invalid_input("response", "response must be an object with status and headers")
    status = response.get("status")
    if not isinstance(status, int) or isinstance(status, bool):
        raise invalid_input("response.status", "status must be an integer")
    response_headers = normalise_headers(response.get("headers"), "response.headers")

    is_preflight = arguments.get("is_preflight")
    if not isinstance(is_preflight, bool):
        raise invalid_input("is_preflight", "is_preflight must be a boolean")

    findings = []
    missing = []
    recommended = {}
    notes = {
        "wildcard_with_credentials": False,
        "allow_credentials_null_origin": False,
        "max_age_capped_by_client": False,
    }

    same_origin = origin is None or origin == url_origin
    allow_origin = _allow_origin(response_headers)
    allow_credentials = response_headers.get("access-control-allow-credentials")
    credentials_true = bool(allow_credentials) and allow_credentials[0].strip(" \t") == "true"

    if origin == "null":
        _add(findings, catalog, "CORS_NULL_ORIGIN")
        notes["allow_credentials_null_origin"] = credentials_true

    if origin is not None and not same_origin:
        unsafe = unsafe_request_headers(request_headers)

        if not is_preflight:
            if needs_preflight(method, request_headers):
                _add(findings, catalog, "CORS_PREFLIGHT_REQUIRED", method=method)
            if allow_origin is None:
                _add(findings, catalog, "CORS_MISSING_ALLOW_ORIGIN", origin=origin)
                missing.append("access-control-allow-origin")
                recommended["access-control-allow-origin"] = origin
            elif allow_origin == "*":
                if credentials == "include":
                    _add(findings, catalog, "CORS_WILDCARD_WITH_CREDENTIALS")
                    notes["wildcard_with_credentials"] = True
                    recommended["access-control-allow-origin"] = origin
            elif allow_origin != origin:
                _add(
                    findings,
                    catalog,
                    "CORS_ORIGIN_MISMATCH",
                    allow_origin=allow_origin,
                    origin=origin,
                )
                recommended["access-control-allow-origin"] = origin
        else:
            if allow_origin is None:
                _add(findings, catalog, "CORS_MISSING_ALLOW_ORIGIN", origin=origin)
                missing.append("access-control-allow-origin")
                recommended["access-control-allow-origin"] = origin
            elif allow_origin == "*":
                if credentials == "include":
                    _add(findings, catalog, "CORS_WILDCARD_WITH_CREDENTIALS")
                    notes["wildcard_with_credentials"] = True
                    recommended["access-control-allow-origin"] = origin
            elif allow_origin != origin:
                _add(
                    findings,
                    catalog,
                    "CORS_ORIGIN_MISMATCH",
                    allow_origin=allow_origin,
                    origin=origin,
                )
                recommended["access-control-allow-origin"] = origin

            methods = response_headers.get("access-control-allow-methods")
            method_list = []
            if methods:
                for value in methods:
                    for piece in value.split(","):
                        if piece.strip(" \t"):
                            method_list.append(piece.strip(" \t").upper())
            if not methods:
                _add(findings, catalog, "CORS_MISSING_ALLOW_METHODS", method=method)
                missing.append("access-control-allow-methods")
                recommended["access-control-allow-methods"] = method
            elif not _coverage_ok(method_list, method, credentials):
                _add(findings, catalog, "CORS_MISSING_ALLOW_METHODS", method=method)
                recommended["access-control-allow-methods"] = method

            header_values = response_headers.get("access-control-allow-headers")
            allow_headers = []
            if header_values:
                for value in header_values:
                    for piece in value.split(","):
                        if piece.strip(" \t"):
                            allow_headers.append(piece.strip(" \t"))
            if unsafe and not header_values:
                _add(findings, catalog, "CORS_MISSING_ALLOW_HEADERS", header=unsafe[0])
                missing.append("access-control-allow-headers")
                recommended["access-control-allow-headers"] = ", ".join(sorted(unsafe))
            else:
                for name in unsafe:
                    if not _header_coverage_ok(allow_headers, name, credentials):
                        _add(findings, catalog, "CORS_DISALLOWED_HEADER_NOT_EXPOSED", header=name)
                        recommended["access-control-allow-headers"] = ", ".join(sorted(unsafe))

        if credentials == "include" and not credentials_true:
            _add(findings, catalog, "CORS_MISSING_ALLOW_CREDENTIALS")
            recommended["access-control-allow-credentials"] = "true"

    findings = _sorted_findings(findings)
    decisive = any(
        catalog["codes"][finding["code"]]["severity"] == "decisive" for finding in findings
    )
    return {
        "decision": "block" if decisive else "allow",
        "violations": findings,
        "missing_headers": canonical_header_name_list(missing),
        "recommended_headers": recommended,
        "notes": notes,
    }
