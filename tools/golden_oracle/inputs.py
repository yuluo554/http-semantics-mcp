"""Shared input normalisation for the oracle (data/README.md §4.3, plan/03 §0.1).

Kept separate from the tool algorithms so that every tool normalises header
names, header values and URLs the same way -- and so that the production
implementation has a second, independent description to be compared against.
"""

import re

from .errors import invalid_header_name, invalid_input, unsupported_method

__all__ = [
    "HEADER_NAME",
    "normalise_header_name",
    "normalise_headers",
    "normalise_method",
    "parse_url",
    "serialise_origin",
    "split_list",
    "first_value",
    "canonical_header_name_list",
    "sha256_hex",
]

HEADER_NAME = re.compile(r"^[a-z0-9!#$%&'*+.^_`|~-]+$")

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


def normalise_header_name(name, field):
    if not isinstance(name, str):
        raise invalid_header_name(field, name)
    lowered = name.strip().lower()
    if not lowered or not HEADER_NAME.match(lowered):
        raise invalid_header_name(field, name)
    return lowered


def normalise_headers(headers, field):
    """Return ``{lowercase_name: [values...]}`` preserving value order."""
    if headers is None:
        return {}
    if not isinstance(headers, dict):
        raise invalid_input(field, "expected an object of header name -> string or array")
    result = {}
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
        result.setdefault(name, []).extend(values)
    return result


def normalise_method(method, field="method"):
    if not isinstance(method, str):
        raise invalid_input(field, "method must be a string")
    upper = method.strip().upper()
    if not upper:
        raise invalid_input(field, "method must not be empty")
    if upper not in METHODS:
        raise unsupported_method(field, method)
    return upper


def parse_url(url, field="url"):
    """Return ``(scheme, host, port)`` from ``scheme://host[:port]``.

    No DNS, no path handling beyond discarding it: the URL exists only to
    derive an origin (plan/02 D3).
    """
    if not isinstance(url, str):
        raise invalid_input(field, "url must be a string")
    text = url.strip()
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
    scheme, host, port = parse_url(url, field)
    if port == DEFAULT_PORTS[scheme]:
        return scheme + "://" + host
    return scheme + "://" + host + ":" + str(port)


def split_list(values):
    """Split comma-separated header values, trimming OWS and dropping empties."""
    items = []
    for value in values:
        for piece in value.split(","):
            trimmed = piece.strip(" \t")
            if trimmed:
                items.append(trimmed)
    return items


def first_value(headers, name):
    values = headers.get(name)
    if not values:
        return None
    return values[0].strip(" \t")


def canonical_header_name_list(names):
    """Lowercase, deduplicate, sort -- the one ordering rule for header lists."""
    return sorted({name.strip(" \t").lower() for name in names if name and name.strip(" \t")})


def sha256_hex(text, length):
    from hashlib import sha256

    return sha256(text.encode("utf-8")).hexdigest()[:length]
