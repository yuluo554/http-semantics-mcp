"""Pure judgement functions (T1-T5).

M2 lands ``cors`` (T1) and ``fetch_sim`` (T2) plus the shared ``normalise`` and
``errors`` helpers; M3 adds ``cache``, M4 adds ``conditional`` / ``vary``.

Discipline enforced by ``tools/gates.py`` (purity gate):

* no ``time`` / ``datetime`` / ``random`` / ``secrets``
* no ``socket`` / ``ssl`` / ``http`` / ``urllib``
* no ``os`` / ``sys`` / ``subprocess`` / ``pathlib`` / ``shutil``
* no ``open`` / ``read_text`` / ``write_text``

Rule codes are imported from the generated ``http_semantics_mcp.rules`` module
rather than spelled here: ``tools/gates.py:code_literals`` fails any hand-written
package source containing a code literal (decisions D41/D42).

Everything here is a pure function of its arguments. Time is an input
(``cache_evaluate`` takes ``now``), never a clock read.
"""

__all__ = []
