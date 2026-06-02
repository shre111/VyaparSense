"""Model cards for reproducible training runs (``CLAUDE.md`` §7).

Every model run should be reconstructable: which data, which features, which
params, what accuracy. This module turns those into a versioned markdown card
saved under ``docs/model-cards/`` so each run leaves an auditable trail (the
honesty backbone of the project's accuracy story).

* :func:`data_hash` — a stable SHA-256 over the canonical sales records, so the
  exact training set is identifiable without storing it.
* :class:`ModelCard` — the captured run: data hash + row/series counts, feature
  config, model name + params, metrics, backtest setup, UTC timestamp, and the
  versions of the libraries that produced it. ``to_markdown()`` renders it.
* :func:`write_card` — render and write to ``docs/model-cards/``.
* :func:`card_from_global_backtest` — convenience builder from a
  :class:`~vyaparsense_ml.forecasting.global_backtest.GlobalBacktestResult`.

Pure stdlib (``hashlib``); no heavy imports at module top.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from vyaparsense_ml.forecasting.metrics import ForecastMetrics
from vyaparsense_ml.schema import SalesRecord

# Repo-root-relative default location for cards.
DEFAULT_CARD_DIR = Path("docs/model-cards")


def data_hash(records: Sequence[SalesRecord]) -> str:
    """Stable SHA-256 over canonical records (order-independent).

    Each record is serialised to its canonical column tuple; the per-record
    hashes are sorted before combining, so the digest depends on the *set* of
    rows, not their order. Returns the full hex digest.
    """
    h = hashlib.sha256()
    rows = sorted(
        f"{r.date.isoformat()}|{r.store_id}|{r.sku_id}|{r.units_sold}|{r.price}|{int(r.promo_flag)}"
        for r in records
    )
    for row in rows:
        h.update(row.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def _metrics_rows(metrics: ForecastMetrics) -> list[tuple[str, str]]:
    def fmt(v: float | None) -> str:
        return "n/a" if v is None else f"{v:.4f}"

    return [
        ("WAPE", fmt(metrics.wape)),
        ("MAE", fmt(metrics.mae)),
        ("RMSE", fmt(metrics.rmse)),
        ("bias", fmt(metrics.bias)),
        ("MAPE", fmt(metrics.mape)),
        ("MASE", fmt(metrics.mase)),
    ]


@dataclass(frozen=True)
class ModelCard:
    """A reproducible record of one model training/backtest run."""

    model: str
    data_hash: str
    n_rows: int
    n_series: int
    metrics: ForecastMetrics
    features: Sequence[str] = ()
    params: Mapping[str, object] = field(default_factory=dict)
    backtest: Mapping[str, object] = field(default_factory=dict)
    library_versions: Mapping[str, str] = field(default_factory=dict)
    created_at: str = ""
    notes: str = ""

    def _resolved_timestamp(self) -> str:
        return self.created_at or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    def slug(self) -> str:
        """Filename-safe identifier: ``<timestamp>__<model>__<hash8>``."""
        ts = self._resolved_timestamp().replace(":", "").replace("-", "")
        safe_model = "".join(c if c.isalnum() else "_" for c in self.model)
        return f"{ts}__{safe_model}__{self.data_hash[:8]}"

    def to_markdown(self) -> str:
        ts = self._resolved_timestamp()
        lines: list[str] = [
            f"# Model card — {self.model}",
            "",
            f"- **Created (UTC):** {ts}",
            f"- **Data hash (SHA-256):** `{self.data_hash}`",
            f"- **Training rows:** {self.n_rows}",
            f"- **Series:** {self.n_series}",
            "",
            "## Metrics",
            "",
            "| metric | value |",
            "|---|---|",
        ]
        lines += [f"| {name} | {val} |" for name, val in _metrics_rows(self.metrics)]

        lines += ["", "## Features", ""]
        lines.append(", ".join(self.features) if self.features else "_none recorded_")

        lines += ["", "## Model params", ""]
        if self.params:
            lines += ["| param | value |", "|---|---|"]
            lines += [f"| {k} | {self.params[k]} |" for k in sorted(self.params)]
        else:
            lines.append("_none recorded_")

        if self.backtest:
            lines += ["", "## Backtest setup", "", "| key | value |", "|---|---|"]
            lines += [f"| {k} | {self.backtest[k]} |" for k in sorted(self.backtest)]

        if self.library_versions:
            lines += ["", "## Library versions", "", "| library | version |", "|---|---|"]
            lines += [
                f"| {k} | {self.library_versions[k]} |" for k in sorted(self.library_versions)
            ]

        if self.notes:
            lines += ["", "## Notes", "", self.notes]

        lines.append("")
        return "\n".join(lines)

    def write(self, directory: str | Path = DEFAULT_CARD_DIR) -> Path:
        """Render and write the card; returns the path written."""
        return write_card(self, directory)


def write_card(card: ModelCard, directory: str | Path = DEFAULT_CARD_DIR) -> Path:
    """Write ``card`` as ``<slug>.md`` under ``directory`` (created if needed)."""
    out_dir = Path(directory)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{card.slug()}.md"
    path.write_text(card.to_markdown(), encoding="utf-8")
    return path
