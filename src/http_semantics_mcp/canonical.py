"""Single serialisation point for every outbound message.

Every byte this server writes to stdout goes through :func:`dumps` /
:func:`encode_message`. Keeping one implementation is what makes
"same input -> byte-identical output" a property of the code rather than a
convention.

Frozen parameters (see plan/02 section 6 and data/README.md section 4.5):

* ``sort_keys=True``       -- object keys are ordered by ASCII
* ``ensure_ascii=False``   -- Chinese text stays readable, no ``\\uXXXX``
* ``separators=(",", ":")`` -- no whitespace, no trailing spaces
* ``allow_nan=False``      -- NaN / Infinity are not valid JSON
"""

import json

__all__ = ["dumps", "encode_message", "loads", "NonFiniteNumber"]

_SEPARATORS = (",", ":")


class NonFiniteNumber(ValueError):
    """Raised when a value cannot be represented as strict JSON."""


def _reject_constant(token):
    raise NonFiniteNumber("non-finite number is not allowed: " + token)


def dumps(value):
    """Serialise ``value`` to the canonical JSON text form."""
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=_SEPARATORS,
        allow_nan=False,
    )


def encode_message(value):
    """Serialise and frame one message: UTF-8 bytes plus a single ``\\n``."""
    return dumps(value).encode("utf-8") + b"\n"


def loads(text):
    """Parse JSON text, rejecting NaN / Infinity as strict JSON does."""
    return json.loads(text, parse_constant=_reject_constant)
