"""anti-slop: opinionated AST rules that reject low-evidence Python patterns.

This is the Python counterpart to `dmmulroy/anti-slop <https://github.com/dmmulroy/anti-slop>`_
(TypeScript/JavaScript on Oxlint). Like the original, it is meant to be *vendored*:
copy the :mod:`anti_slop` package into a repository, read the rules, and change them
to match your team's standards.

The whole tool runs on the Python standard library (the :mod:`ast` module).
There are no runtime dependencies.
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
