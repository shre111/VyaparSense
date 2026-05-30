"""Smoke test: the package imports and exposes a version."""

from __future__ import annotations

import vyaparsense_ml


def test_has_version() -> None:
    assert isinstance(vyaparsense_ml.__version__, str)
    assert vyaparsense_ml.__version__.count(".") == 2
