"""Shared input normalisation for the judgement layer (plan/03 section 0.1).

Deliberately pure string work: the judgement layer may not touch the disk, the
clock, the network, the process or the environment (gates: ``purity``). Only
``re`` and ``hashlib`` are imported, both of which are deterministic functions
of their arguments.

Normalisation rules, all from ``data/README.md`` section 4.3 / section 0.1 of
plan/03:

* header names are lowercased, trimmed, then checked against the RFC 9110 token
  character set;
* header values keep their internal whitespace and their case, with OWS removed
  at both ends only;
* an origin is reduced to ``scheme://host[:port]`` with a lowercase scheme/host
  and the default port dropped -- no path, no query, no trailing slash.
"""

import re
from hashlib import sha256

from .errors import JudgementError, invalid_header_name, invalid_input, unsupported_method

__all__ = [
    "METHODS",
    "OWS",
    "NULL_ORIGIN",
    "normalise_header_name",
    "normalise_headers",
    "normalise_method",
    "serialise_origin",
    "origin_key",
    "split_comma_list",
    "first_value",
    "header_name_list",
    "sha256_prefix",
]

# Optional whitespace, RFC 9110 section 5.6.3.
OWS = " \t"

NULL_ORIGIN = "null"

# The methods this server recognises. A method outside this set is rejected
# rather than passed through: silently accepting `TEST-METHOD` would make the
# safelisting branch below unreachable by accident (plan/03 section 0.1 item 4).
METHODS = (
    "GET",
    "HEAD",
    "POST",
    "PUT",
    "DELETE",
    "PATCH",
    "OPTIONS",
    "CONNECT",
    "TRACE",
)

DEFAULT_PORTS = {"http": 80, "https": 443}

# RFC 9110 section 5.6.2: tchar.
TOKEN = re.compile(r"^[a-z0-9!#$%&'*+.^_`|~-]+$")


def normalise_header_name(name, field):
    """Lowercase + trim + token check. Raises for anything that is not a name."""
    if not isinstance(name, str):
        raise invalid_header_name(field, name)
    lowered = name.strip(OWS).lower()
    if not lowered or TOKEN.fullmatch(lowered) is None:
        raise invalid_header_name(field, name)
    return lowered


def normalise_headers(headers, field):
    """Return ``{lowercase_name: [values...]}``, preserving value order.

    Input may be a string (single value) or an array (repeated header). Names
    are merged case-insensitively; the order of *names* is not observable
    because every consumer iterates a sorted view.
    """
    if headers is None:
        return {}
    if not isinstance(headers, dict):
        raise invalid_input(field, "expected an object of header name -> string or array")
    collected = {}
    for raw_name in sorted(headers):
        name = normalise_header_name(raw_name, field + "." + str(raw_name))
        raw_value = headers[raw_name]
        if isinstance(raw_value, str):
            values = [raw_value]
        elif isinstance(raw_value, list):
            values = []
            for item in raw_value:
                if not isinstance(item, str):
                    raise invalid_input(field + "." + name, "header values must be strings")
                values.append(item)
        else:
            raise invalid_input(field + "." + name, "header value must be a string or an array")
        collected.setdefault(name, []).extend(values)
    return collected


def normalise_method(method, field="method"):
    if not isinstance(method, str):
        raise invalid_input(field, "method must be a string")
    upper = method.strip(OWS).upper()
    if not upper:
        raise invalid_input(field, "method must not be empty")
    if upper not in METHODS:
        raise unsupported_method(field, method)
    return upper


def _split_url(url, field):
    """Return ``(scheme, host, port)`` from ``scheme://host[:port]``."""
    if not isinstance(url, str):
        raise invalid_input(field, "url must be a string")
    text = url.strip(OWS)
    marker = text.find("://")
    if marker <= 0:
        raise invalid_input(field, "url must be scheme://host[:port]")
    scheme = text[:marker].lower()
    if scheme not in DEFAULT_PORTS:
        raise invalid_input(field, "only http and https are supported")
    rest = text[marker + 3 :]
    for delimiter in ("/", "?", "#"):
        cut = rest.find(delimiter)
        if cut >= 0:
            rest = rest[:cut]
    if not rest:
        raise invalid_input(field, "url has no host")
    port = DEFAULT_PORTS[scheme]
    host = rest
    if ":" in rest:
        host, _, port_text = rest.rpartition(":")
        if not port_text.isdigit():
            raise invalid_input(field, "url port must be numeric")
        port = int(port_text)
        if not 0 < port < 65536:
            raise invalid_input(field, "url port is out of range")
        if not host:
            raise invalid_input(field, "url has no host")
    return scheme, host.lower(), port


def serialise_origin(url, field="url"):
    """Reduce a URL to its origin form, dropping the default port."""
    scheme, host, port = _split_url(url, field)
    if port == DEFAULT_PORTS[scheme]:
        return scheme + "://" + host
    return scheme + "://" + host + ":" + str(port)


def origin_key(value, field="origin"):
    """Normalise a request Origin.

    Returns ``None`` when the caller did not supply one (which is how a
    same-origin request is expressed), the literal ``"null"`` for the opaque
    origin, or the normalised ``scheme://host[:port]`` string.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        raise invalid_input(field, "origin must be a string or null")
    text = value.strip(OWS)
    if text.lower() == NULL_ORIGIN:
        return NULL_ORIGIN
    try:
        return serialise_origin(text, field)
    except JudgementError:
        raise invalid_input(field, "origin must be scheme://host[:port] or the literal null")


def split_comma_list(values):
    """Split repeated comma-separated header values, trimming OWS and empties."""
    pieces = []
    for value in values:
        for piece in value.split(","):
            trimmed = piece.strip(OWS)
            if trimmed:
                pieces.append(trimmed)
    return pieces


def first_value(headers, name):
    """First value of a header, OWS-trimmed, or ``None`` when absent."""
    values = headers.get(name)
    if not values:
        return None
    return values[0].strip(OWS)


def header_name_list(names):
    """Lowercase, de-duplicate, sort -- the single ordering rule for name lists."""
    cleaned = []
    for name in names:
        if not name:
            continue
        stripped = name.strip(OWS).lower()
        if stripped:
            cleaned.append(stripped)
    return sorted(set(cleaned))


def sha256_prefix(text, length):
    """First ``length`` hex characters of the SHA-256 of ``text`` (UTF-8)."""
    return sha256(text.encode("utf-8")).hexdigest()[:length]
