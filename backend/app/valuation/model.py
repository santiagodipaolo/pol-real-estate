"""Valuation model — XGBoost-based price predictor with confidence intervals.

The model predicts USD/m² for a property, then multiplies by surface to get
the total estimated price.  Confidence intervals are computed using quantile
regression (two additional models for the 10th and 90th percentiles).
"""

from __future__ import annotations

import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import cross_val_score

from app.valuation.features import (
    FEATURE_COLUMNS,
    LOG_TARGET_COLUMN,
    TARGET_COLUMN,
    compute_barrio_stats,
    engineer_features,
    filter_outliers,
)

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "models"


class ValuationModel:
    """XGBoost ensemble for real estate valuation."""

    def __init__(self) -> None:
        self.model_median: xgb.XGBRegressor | None = None
        self.model_low: xgb.XGBRegressor | None = None
        self.model_high: xgb.XGBRegressor | None = None
        self.barrio_stats: pd.DataFrame | None = None
        self.metrics: dict = {}

    def train(self, df: pd.DataFrame) -> dict:
        """Train the valuation model on listing data.

        Args:
            df: DataFrame with raw listing data (from DB query).

        Returns:
            Dict with training metrics.
        """
        # Compute barrio stats from training data
        df_feat = engineer_features(df)
        self.barrio_stats = compute_barrio_stats(df_feat)

        # Filter valid rows
        mask = (
            df_feat[TARGET_COLUMN].notna()
            & (df_feat[TARGET_COLUMN] > 0)
            & df_feat["surface_total_m2"].notna()
            & (df_feat["surface_total_m2"] > 10)
        )
        df_clean = df_feat[mask].copy()

        # IQR-based outlier removal (replaces fixed 15000 threshold)
        before = len(df_clean)
        df_clean = filter_outliers(df_clean, TARGET_COLUMN)
        logger.info("Outlier filter: %d → %d samples (removed %d)", before, len(df_clean), before - len(df_clean))

        if len(df_clean) < 20:
            raise ValueError(f"Not enough data to train: {len(df_clean)} rows (need >= 20)")

        X = df_clean[FEATURE_COLUMNS].values
        # Train on log-transformed target (reduces skew, improves predictions on expensive properties)
        y_log = df_clean[LOG_TARGET_COLUMN].values
        y_raw = df_clean[TARGET_COLUMN].values

        logger.info("Training on %d samples with %d features (log-target)", len(X), len(FEATURE_COLUMNS))

        # Common params — tuned for regularization with sparse enrichment data
        base_params = {
            "n_estimators": 300,
            "max_depth": 4,
            "learning_rate": 0.05,
            "subsample": 0.7,
            "colsample_bytree": 0.7,
            "min_child_weight": 5,
            "reg_alpha": 0.1,
            "reg_lambda": 1.0,
            "random_state": 42,
        }

        # Median model (main predictor) — trained on log-target
        self.model_median = xgb.XGBRegressor(
            objective="reg:squarederror",
            **base_params,
        )
        self.model_median.fit(X, y_log)

        # Low bound (10th percentile)
        self.model_low = xgb.XGBRegressor(
            objective="reg:quantileerror",
            quantile_alpha=0.10,
            **base_params,
        )
        self.model_low.fit(X, y_log)

        # High bound (90th percentile)
        self.model_high = xgb.XGBRegressor(
            objective="reg:quantileerror",
            quantile_alpha=0.90,
            **base_params,
        )
        self.model_high.fit(X, y_log)

        # Cross-validation on log-target, then convert MAE back to real scale
        from sklearn.metrics import make_scorer

        def mae_real_scale(y_true_log, y_pred_log):
            """MAE in real USD/m² from log-space predictions."""
            return -np.mean(np.abs(np.expm1(y_true_log) - np.expm1(y_pred_log)))

        cv_scorer = make_scorer(mae_real_scale, greater_is_better=True)
        cv_scores = cross_val_score(
            xgb.XGBRegressor(objective="reg:squarederror", **base_params),
            X, y_log, cv=min(5, len(X) // 5), scoring=cv_scorer,
        )

        mae_real = float(-cv_scores.mean())
        median_price = float(np.median(y_raw))

        self.metrics = {
            "samples": len(X),
            "features": len(FEATURE_COLUMNS),
            "mae_cv": round(mae_real, 1),
            "mae_cv_std": float(cv_scores.std()),
            "median_price_usd_m2": median_price,
            "mae_pct": round(mae_real / median_price * 100, 1),
        }

        logger.info(
            "Model trained: MAE=%.0f USD/m² (%.1f%%), median=%.0f USD/m²",
            self.metrics["mae_cv"],
            self.metrics["mae_pct"],
            self.metrics["median_price_usd_m2"],
        )

        # Feature importance
        importances = self.model_median.feature_importances_
        feat_imp = sorted(
            zip(FEATURE_COLUMNS, importances), key=lambda x: x[1], reverse=True
        )
        self.metrics["feature_importance"] = {f: float(v) for f, v in feat_imp}

        return self.metrics

    def predict(
        self,
        surface_total_m2: float,
        rooms: int | None = None,
        bedrooms: int | None = None,
        bathrooms: int | None = None,
        garages: int | None = None,
        age_years: int | None = None,
        expenses_ars: float | None = None,
        property_type: str = "Departamento",
        barrio_id: int | None = None,
        surface_covered_m2: float | None = None,
        floor: int | None = None,
        orientation: str | None = None,
        condition: str | None = None,
        amenities: dict | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> dict:
        """Predict the valuation for a single property.

        Returns:
            Dict with estimated price, range, and price per m².
        """
        if self.model_median is None:
            raise RuntimeError("Model not trained. Call train() or load() first.")

        # Build a single-row DataFrame
        row = pd.DataFrame([{
            "surface_total_m2": surface_total_m2,
            "surface_covered_m2": surface_covered_m2 or surface_total_m2,
            "rooms": rooms or (bedrooms + 1 if bedrooms else 2),
            "bedrooms": bedrooms or (rooms - 1 if rooms else 1),
            "bathrooms": bathrooms or 1,
            "garages": garages or 0,
            "age_years": age_years or 15,
            "expenses_ars": expenses_ars or 0,
            "property_type": property_type,
            "barrio_id": barrio_id,
            "price_usd_blue": 0,  # Placeholder, not used for prediction
            "floor": floor,
            "orientation": orientation,
            "condition": condition,
            "amenities": amenities or {},
            "latitude": latitude,
            "longitude": longitude,
        }])

        row_feat = engineer_features(row, barrio_stats=self.barrio_stats)

        X = row_feat[FEATURE_COLUMNS].values

        # Predictions are in log space — convert back with expm1
        pred_median = float(np.expm1(self.model_median.predict(X)[0]))
        pred_low = float(np.expm1(self.model_low.predict(X)[0]))
        pred_high = float(np.expm1(self.model_high.predict(X)[0]))

        # Ensure bounds are ordered
        pred_low, pred_high = min(pred_low, pred_median), max(pred_high, pred_median)

        return {
            "price_usd_m2": round(pred_median, 0),
            "price_usd_m2_low": round(pred_low, 0),
            "price_usd_m2_high": round(pred_high, 0),
            "price_usd": round(pred_median * surface_total_m2, 0),
            "price_usd_low": round(pred_low * surface_total_m2, 0),
            "price_usd_high": round(pred_high * surface_total_m2, 0),
            "surface_total_m2": surface_total_m2,
        }

    def save(self, name: str = "valuation_v1") -> Path:
        """Save the trained model to disk."""
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        path = MODEL_DIR / f"{name}.joblib"
        joblib.dump(
            {
                "model_median": self.model_median,
                "model_low": self.model_low,
                "model_high": self.model_high,
                "barrio_stats": self.barrio_stats,
                "metrics": self.metrics,
            },
            path,
        )
        logger.info("Model saved to %s", path)
        return path

    def load(self, name: str = "valuation_v1") -> None:
        """Load a trained model from disk."""
        path = MODEL_DIR / f"{name}.joblib"
        data = joblib.load(path)
        self.model_median = data["model_median"]
        self.model_low = data["model_low"]
        self.model_high = data["model_high"]
        self.barrio_stats = data["barrio_stats"]
        self.metrics = data["metrics"]
        logger.info("Model loaded from %s (%d samples)", path, self.metrics.get("samples", 0))
