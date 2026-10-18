"""T1 ``cors_evaluate``: does this response pass the Fetch CORS check?

Algorithm source: ``plan/03`` section 1 (branch order A1-A6 / P1-P6). The
wording of every finding is read from the generated catalogue, never written
here: this module selects a rule and supplies its parameters.

Reference points (``data/README.md`` section 4.2):

* ``Fetch section CORS check``            -- the response check itself
* ``Fetch section CORS protocol``         -- which requests need a preflight
* ``Fetch section CORS-preflight fetch``  -- Allow-Methods / Allow-Headers
* ``Fetch section CORS protocol and credentials`` -- the ``*`` exception
"""

from ..rules import (
    CORS_DISALLOWED_HEADER_NOT_EXPOSED,
    CORS_MISSING_ALLOW_CREDENTIALS,
    CORS_MISSING_ALLOW_HEADERS,
    CORS_MISSING_ALLOW_METHODS,
    CORS_MISSING_ALLOW_ORIGIN,
    CORS_NULL_ORIGIN,
    CORS_ORIGIN_MISMATCH,
    CORS_PREFLIGHT_REQUIRED,
    CORS_WILDCARD_WITH_CREDENTIALS,
)
from .errors import invalid_input
from .normalise import (
    NULL_ORIGIN,
    first_value,
    header_name_list,
    normalise_headers,
    normalise_method,
    origin_key,
    serialise_origin,
    split_comma_list,
)

__all__ = [
    "SAFELISTED_METHODS",
    "SAFELISTED_HEADERS",
    "unsafe_request_headers",
    "needs_preflight",
    "evaluate_cors",
]

# Fetch section CORS protocol: a simple request is GET/HEAD/POST with only
# CORS-safelisted request headers.
SAFELISTED_METHODS = ("GET", "HEAD", "POST")
SAFELISTED_HEADERS = ("accept", "accept-language", "content-language", "content-type", "range")

SAFELISTED_CONTENT_TYPES = (
    "application/x-www-form-urlencoded",
    "multipart/form-data",
    "text/plain",
)

ALLOW_ORIGIN = "access-control-allow-origin"
ALLOW_CREDENTIALS = "access-control-allow-credentials"
ALLOW_METHODS = "access-control-allow-methods"
ALLOW_HEADERS = "access-control-allow-headers"

# A CORS-unsafe request-header byte (Fetch): everything below SPACE except
# HTAB, plus the separators that make a value ambiguous to a server.
_UNSAFE_BYTES = frozenset(x for x in range(0x00, 0x20) if x != 0x09) | frozenset(
    (0x22, 0x28, 0x29, 0x3A, 0x3C, 0x3E, 0x3F, 0x40, 0x5B, 0x5C, 0x5D, 0x7B, 0x7D, 0x7F)
)

# The byte range a (language) value may use: alphanumerics plus `*,-.;= SPACE`.
_LANGUAGE_BYTES = (
    frozenset(range(0x30, 0x3A))
    | frozenset(range(0x41, 0x5B))
    | frozenset(range(0x61, 0x7B))
    | frozenset((0x20, 0x2A, 0x2C, 0x2D, 0x2E, 0x3B, 0x3D))
)


def _has_unsafe_byte(value):
    return any(ord(character) in _UNSAFE_BYTES for character in value)


def _is_simple_range(value):
    """``bytes=N-M`` with a single range and N <= M (deliberate simplification)."""
    text = value.strip(" \t")
    if not text.lower().startswith("bytes="):
        return False
    specification = text[len("bytes=") :]
    if "," in specification:
        return False
    first, dash, last = specification.partition("-")
    if not dash or not first.isdigit() or not last.isdigit():
        return False
    return int(first) <= int(last)


def _value_is_safelisted(name, value):
    if name == "accept":
        return not _has_unsafe_byte(value)
    if name in ("accept-language", "content-language"):
        return all(ord(character) in _LANGUAGE_BYTES for character in value)
    if name == "content-type":
        if _has_unsafe_byte(value):
            return False
        essence = value.split(";", 1)[0].strip(" \t").lower()
        return essence in SAFELISTED_CONTENT_TYPES
    if name == "range":
        return _is_simple_range(value)
    return False


def unsafe_request_headers(headers):
    """Names that force a preflight, ASCII-sorted (request order is irrelevant)."""
    unsafe = []
    for name in sorted(headers):
        # `authorization` is the CORS non-wildcard request-header name: it is
        # never safelisted, whatever the value.
        if name == "authorization":
            unsafe.append(name)
            continue
        if name in SAFELISTED_HEADERS and all(
            _value_is_safelisted(name, value) for value in headers[name]
        ):
            continue
        unsafe.append(name)
    return unsafe


def needs_preflight(method, headers):
    return method not in SAFELISTED_METHODS or bool(unsafe_request_headers(headers))


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


def _notes():
    # All three keys always appear, even when false: a field that is sometimes
    # absent cannot be pinned by a byte comparison (plan/03 section 1.4).
    return {
        "wildcard_with_credentials": False,
        "allow_credentials_null_origin": False,
        "max_age_capped_by_client": False,
    }


def _allow_origin(response_headers):
    value = first_value(response_headers, ALLOW_ORIGIN)
    return None if value is None else value


def _credentials_true(response_headers):
    value = first_value(response_headers, ALLOW_CREDENTIALS)
    return value == "true"


def _method_is_allowed(declared, method, credentials):
    """Fetch section CORS-preflight fetch, methods step."""
    if method in declared or method in SAFELISTED_METHODS:
        return True
    return "*" in declared and credentials != "include"


def _header_is_allowed(declared, name, credentials):
    """Fetch section CORS-preflight fetch, headers step.

    ``authorization`` is never covered by ``*``; with credentials the wildcard
    covers nothing at all.
    """
    if any(item.lower() == name for item in declared):
        return True
    if name == "authorization":
        return False
    if credentials == "include":
        return False
    return "*" in declared


def evaluate_cors(arguments, catalog):
    """Judge one response against the CORS check. Pure function."""
    method = normalise_method(arguments.get("method"), "method")
    if "url" not in arguments:
        raise invalid_input("url", "url is required")
    target = serialise_origin(arguments.get("url"), "url")
    origin = origin_key(arguments.get("origin"), "origin")

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
    notes = _notes()

    same_origin = origin is None or origin == target
    allow_origin = _allow_origin(response_headers)
    credentials_true = _credentials_true(response_headers)

    # The opaque origin is reported whenever it appears; it explains the branch
    # taken rather than deciding it (severity `informational`).
    if origin == NULL_ORIGIN:
        findings.append(_finding(catalog, CORS_NULL_ORIGIN))
        notes["allow_credentials_null_origin"] = credentials_true

    if origin is not None and not same_origin:
        if not is_preflight:
            if needs_preflight(method, request_headers):
                findings.append(_finding(catalog, CORS_PREFLIGHT_REQUIRED, method=method))

            if allow_origin is None:
                findings.append(_finding(catalog, CORS_MISSING_ALLOW_ORIGIN, origin=origin))
                missing.append(ALLOW_ORIGIN)
                recommended[ALLOW_ORIGIN] = origin
            elif allow_origin == "*":
                if credentials == "include":
                    findings.append(_finding(catalog, CORS_WILDCARD_WITH_CREDENTIALS))
                    notes["wildcard_with_credentials"] = True
                    recommended[ALLOW_ORIGIN] = origin
            elif allow_origin != origin:
                findings.append(
                    _finding(catalog, CORS_ORIGIN_MISMATCH, allow_origin=allow_origin, origin=origin)
                )
                recommended[ALLOW_ORIGIN] = origin
        else:
            if allow_origin is None:
                findings.append(_finding(catalog, CORS_MISSING_ALLOW_ORIGIN, origin=origin))
                missing.append(ALLOW_ORIGIN)
                recommended[ALLOW_ORIGIN] = origin
            elif allow_origin == "*":
                if credentials == "include":
                    findings.append(_finding(catalog, CORS_WILDCARD_WITH_CREDENTIALS))
                    notes["wildcard_with_credentials"] = True
                    recommended[ALLOW_ORIGIN] = origin
            elif allow_origin != origin:
                findings.append(
                    _finding(catalog, CORS_ORIGIN_MISMATCH, allow_origin=allow_origin, origin=origin)
                )
                recommended[ALLOW_ORIGIN] = origin

            declared_methods = [
                piece.upper() for piece in split_comma_list(response_headers.get(ALLOW_METHODS, []))
            ]
            if ALLOW_METHODS not in response_headers:
                findings.append(_finding(catalog, CORS_MISSING_ALLOW_METHODS, method=method))
                missing.append(ALLOW_METHODS)
                recommended[ALLOW_METHODS] = method
            elif not _method_is_allowed(declared_methods, method, credentials):
                findings.append(_finding(catalog, CORS_MISSING_ALLOW_METHODS, method=method))
                recommended[ALLOW_METHODS] = method

            unsafe = unsafe_request_headers(request_headers)
            declared_headers = split_comma_list(response_headers.get(ALLOW_HEADERS, []))
            if unsafe and ALLOW_HEADERS not in response_headers:
                findings.append(_finding(catalog, CORS_MISSING_ALLOW_HEADERS, header=unsafe[0]))
                missing.append(ALLOW_HEADERS)
                recommended[ALLOW_HEADERS] = ", ".join(sorted(unsafe))
            else:
                for name in unsafe:
                    if not _header_is_allowed(declared_headers, name, credentials):
                        findings.append(_finding(catalog, CORS_DISALLOWED_HEADER_NOT_EXPOSED, header=name))
                        recommended[ALLOW_HEADERS] = ", ".join(sorted(unsafe))

        if credentials == "include" and not credentials_true:
            findings.append(_finding(catalog, CORS_MISSING_ALLOW_CREDENTIALS))
            recommended[ALLOW_CREDENTIALS] = "true"

    findings = _sorted_findings(findings)
    decisive = any(
        catalog["codes"][finding["code"]]["severity"] == "decisive" for finding in findings
    )
    return {
        "decision": "block" if decisive else "allow",
        "violations": findings,
        "missing_headers": header_name_list(missing),
        "recommended_headers": recommended,
        "notes": notes,
    }
