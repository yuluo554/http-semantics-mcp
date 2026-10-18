"""Pure judgement functions (T1-T5).

M0 ships this package empty on purpose: no judgement logic exists yet, and
``tools/list`` reports zero tools. M2 adds ``cors`` / ``fetch_sim``, M3 adds
``cache``, M4 adds ``conditional`` / ``vary``.

Discipline enforced by ``tools/gates.py`` (purity gate):

* no ``time`` / ``datetime`` / ``random`` / ``secrets``
* no ``socket`` / ``ssl`` / ``http`` / ``urllib``
* no ``os`` / ``sys`` / ``subprocess`` / ``pathlib`` / ``shutil``
* no ``open`` / ``read_text`` / ``write_text``

Everything here is a pure function of its arguments. Time is an input
(``cache_evaluate`` takes ``now``), never a clock read.
"""

__all__ = []
