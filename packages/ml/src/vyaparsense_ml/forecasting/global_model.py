"""Global LightGBM demand model (Phase 4; ``CLAUDE.md`` §4 rung 4).

The M5-winning pattern: one gradient-boosted model trained across *all*
SKUs/stores at once on the engineered feature frame (``features.build_features``),
rather than a separate model per series. A global model shares statistical
strength across series — a boon for short or sparse SKUs — and is cheap to serve
(one booster for the whole catalogue).

Forecasting is **recursive multi-step**: to predict ``h`` days ahead for a
series we predict day ``t+1``, append that prediction as if it were the realised
demand, rebuild the lag/rolling features with the same
:func:`~vyaparsense_ml.forecasting.features.build_features` code, predict
``t+2``, and so on — so multi-step lags stay consistent with training and there
is no leakage. Predictions are clamped to ``>= 0`` (demand is non-negative).

This is **not** a per-series :class:`~vyaparsense_ml.forecasting.models.Baseline`
— it fits across series — so it has its own fit/forecast API and a dedicated
backtest (:mod:`vyaparsense_ml.forecasting.global_backtest`). Everything is
seeded for reproducibility (``CLAUDE.md`` §7). Uses LightGBM + pandas.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import timedelta

import lightgbm as lgb
import pandas as pd

from vyaparsense_ml.forecasting.features import (
    DEFAULT_LAGS,
    DEFAULT_ROLL_WINDOWS,
    build_features,
    feature_columns,
)
from vyaparsense_ml.schema import COL_UNITS_SOLD, SalesRecord

# Conservative, fast defaults; tuned lightly for the small retail data shape.
DEFAULT_PARAMS: dict[str, object] = {
    "objective": "regression_l1",  # L1 ~ optimises toward the median; robust to spikes
    "num_leaves": 31,
    "learning_rate": 0.05,
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "bagging_freq": 1,
    "min_data_in_leaf": 20,
    "verbose": -1,
}


@dataclass
class GlobalLightGBM:
    """A single LightGBM booster trained across all series.

    Args:
        lags / roll_windows: feature config (must match across fit/forecast; the
            same values are passed to ``build_features``).
        num_boost_round: boosting iterations.
        params: LightGBM params (merged over :data:`DEFAULT_PARAMS`).
        seed: RNG seed for reproducible training.
    """

    lags: tuple[int, ...] = DEFAULT_LAGS
    roll_windows: tuple[int, ...] = DEFAULT_ROLL_WINDOWS
    num_boost_round: int = 200
    params: dict[str, object] = field(default_factory=dict)
    seed: int = 42
    _booster: lgb.Booster | None = field(default=None, init=False, repr=False, compare=False)

    @property
    def name(self) -> str:
        return "global_lightgbm"

    @property
    def feature_cols(self) -> list[str]:
        return feature_columns(self.lags, self.roll_windows)

    def resolved_params(self) -> dict[str, object]:
        merged = {**DEFAULT_PARAMS, **self.params}
        merged["seed"] = self.seed
        return merged

    def fit(self, records: Sequence[SalesRecord]) -> GlobalLightGBM:
        """Train the booster on the feature frame built from ``records``."""
        frame = build_features(records, lags=self.lags, roll_windows=self.roll_windows, dropna=True)
        if frame.empty:
            raise ValueError("no training rows after feature engineering (series too short)")
        x = frame[self.feature_cols]
        y = frame[COL_UNITS_SOLD]
        dataset = lgb.Dataset(x, label=y, free_raw_data=False)
        self._booster = lgb.train(
            self.resolved_params(),
            dataset,
            num_boost_round=self.num_boost_round,
        )
        return self

    def _predict_rows(self, frame: pd.DataFrame) -> list[float]:
        if self._booster is None:
            raise RuntimeError("model is not fitted; call fit() first")
        preds = self._booster.predict(frame[self.feature_cols])
        return [max(0.0, float(p)) for p in preds]

    def forecast_series(
        self,
        history: Sequence[SalesRecord],
        h: int,
        *,
        future_price: float | None = None,
        future_promo: bool = False,
    ) -> list[float]:
        """Recursively forecast the next ``h`` days for one series.

        ``history`` is that series' clean records (single store+sku). Future
        ``price``/``promo`` are unknown at inference, so we carry the last
        observed price forward (or ``future_price``) and assume no promo unless
        ``future_promo`` is set.
        """
        if self._booster is None:
            raise RuntimeError("model is not fitted; call fit() first")
        if h < 1:
            raise ValueError(f"horizon must be >= 1, got {h}")
        if not history:
            raise ValueError("cannot forecast from empty history")

        store_id = history[0].store_id
        sku_id = history[0].sku_id
        price = future_price if future_price is not None else history[-1].price
        working = list(history)
        out: list[float] = []
        next_date = history[-1].date + timedelta(days=1)

        for _ in range(h):
            # Append a placeholder row for the day to predict, build features,
            # read the last row's features, predict, then overwrite the
            # placeholder with the prediction so it feeds the next step's lags.
            placeholder = SalesRecord(
                date=next_date,
                store_id=store_id,
                sku_id=sku_id,
                units_sold=0,
                price=price,
                promo_flag=future_promo,
            )
            frame = build_features(
                [*working, placeholder],
                lags=self.lags,
                roll_windows=self.roll_windows,
                dropna=False,
            )
            yhat = self._predict_rows(frame.iloc[[-1]])[0]
            out.append(yhat)
            working.append(
                SalesRecord(
                    date=next_date,
                    store_id=store_id,
                    sku_id=sku_id,
                    units_sold=max(0, round(yhat)),
                    price=price,
                    promo_flag=future_promo,
                )
            )
            next_date = next_date + timedelta(days=1)
        return out

    def feature_importance(self) -> dict[str, int]:
        """Gain-free split-count importance per feature (fitted models only)."""
        if self._booster is None:
            raise RuntimeError("model is not fitted; call fit() first")
        importances = self._booster.feature_importance()
        return dict(zip(self.feature_cols, (int(i) for i in importances), strict=True))


__all__ = ["DEFAULT_PARAMS", "GlobalLightGBM"]
