"""Tests for model-card generation (reproducibility artifacts)."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from vyaparsense_ml.forecasting.metrics import ForecastMetrics
from vyaparsense_ml.forecasting.model_card import (
    ModelCard,
    data_hash,
    write_card,
)
from vyaparsense_ml.schema import SalesRecord

_METRICS = ForecastMetrics(wape=0.41, mae=5.0, rmse=7.0, bias=-0.2, mape=0.33, mase=1.1)


def _recs(units: list[int], store: str = "A") -> list[SalesRecord]:
    start = date(2024, 1, 1)
    return [
        SalesRecord(
            date=start + timedelta(days=i),
            store_id=store,
            sku_id="X",
            units_sold=u,
            price=10.0,
            promo_flag=False,
        )
        for i, u in enumerate(units)
    ]


def test_data_hash_is_stable_and_order_independent() -> None:
    a = _recs([1, 2, 3])
    b = list(reversed(_recs([1, 2, 3])))
    assert data_hash(a) == data_hash(b)  # order independent
    assert len(data_hash(a)) == 64  # full sha-256 hex


def test_data_hash_changes_with_data() -> None:
    assert data_hash(_recs([1, 2, 3])) != data_hash(_recs([1, 2, 4]))
    # a different store is different data
    assert data_hash(_recs([1, 2, 3])) != data_hash(_recs([1, 2, 3], store="B"))


def test_card_to_markdown_contains_key_sections() -> None:
    card = ModelCard(
        model="global_lightgbm",
        data_hash="abc123" + "0" * 58,
        n_rows=1000,
        n_series=16,
        metrics=_METRICS,
        features=["lag_1", "lag_7", "price"],
        params={"learning_rate": 0.05, "num_leaves": 31},
        backtest={"horizon": 7, "n_folds_run": 4},
        library_versions={"lightgbm": "4.6.0"},
        created_at="2026-06-02T12:00:00Z",
        notes="beats per-series champions",
    )
    md = card.to_markdown()
    assert "# Model card — global_lightgbm" in md
    assert "abc123" in md
    assert "WAPE" in md and "0.4100" in md
    assert "lag_1" in md
    assert "learning_rate" in md
    assert "lightgbm" in md and "4.6.0" in md
    assert "beats per-series champions" in md
    assert "2026-06-02T12:00:00Z" in md


def test_mase_none_renders_na() -> None:
    metrics = ForecastMetrics(wape=0.4, mae=5.0, rmse=7.0, bias=0.0, mape=0.3, mase=None)
    card = ModelCard(model="m", data_hash="d" * 64, n_rows=1, n_series=1, metrics=metrics)
    md = card.to_markdown()
    assert "| MASE | n/a |" in md


def test_slug_is_filename_safe() -> None:
    card = ModelCard(
        model="global lightgbm/v2",
        data_hash="deadbeef" + "0" * 56,
        n_rows=1,
        n_series=1,
        metrics=_METRICS,
        created_at="2026-06-02T12:00:00Z",
    )
    slug = card.slug()
    assert "/" not in slug and " " not in slug and ":" not in slug
    assert slug.endswith("deadbeef")


def test_write_card_creates_file(tmp_path: Path) -> None:
    card = ModelCard(
        model="global_lightgbm",
        data_hash="abc" + "0" * 61,
        n_rows=10,
        n_series=2,
        metrics=_METRICS,
        created_at="2026-06-02T12:00:00Z",
    )
    path = write_card(card, tmp_path)
    assert path.exists()
    assert path.suffix == ".md"
    assert path.parent == tmp_path
    assert "# Model card" in path.read_text(encoding="utf-8")


def test_write_card_creates_missing_directory(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "cards"
    card = ModelCard(model="m", data_hash="f" * 64, n_rows=1, n_series=1, metrics=_METRICS)
    path = write_card(card, target)
    assert path.exists()
    assert path.parent == target


def test_empty_features_and_params_render_placeholder() -> None:
    card = ModelCard(model="m", data_hash="a" * 64, n_rows=1, n_series=1, metrics=_METRICS)
    md = card.to_markdown()
    assert "_none recorded_" in md
