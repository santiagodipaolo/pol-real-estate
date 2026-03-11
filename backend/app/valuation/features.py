"""Feature engineering for the valuation model.

Transforms raw listing data into model-ready feature vectors.
"""

from __future__ import annotations

import pandas as pd
import numpy as np


# Property type encoding (ordinal — reflects typical price hierarchy)
PROPERTY_TYPE_MAP = {
    "Departamento": 0,
    "PH": 1,
    "Casa": 2,
    "Local": 3,
    "Oficina": 4,
    "Terreno": 5,
}

# Features used by the model
FEATURE_COLUMNS = [
    "surface_total_m2",
    "surface_covered_m2",
    "rooms",
    "bedrooms",
    "bathrooms",
    "garages",
    "age_years",
    "expenses_ars",
    "property_type_encoded",
    "barrio_median_usd_m2",
    "barrio_listing_count",
    "covered_ratio",
    "has_garage",
]

TARGET_COLUMN = "price_usd_m2"


def compute_barrio_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Compute per-barrio aggregate stats from the training data."""
    stats = df.groupby("barrio_id").agg(
        barrio_median_usd_m2=("price_usd_m2", "median"),
        barrio_listing_count=("price_usd_m2", "count"),
    ).reset_index()
    return stats


def engineer_features(df: pd.DataFrame, barrio_stats: pd.DataFrame | None = None) -> pd.DataFrame:
    """Transform raw listing DataFrame into model-ready features.

    Args:
        df: DataFrame with listing columns from the DB.
        barrio_stats: Pre-computed barrio stats (for inference). If None, computed from df.

    Returns:
        DataFrame with feature columns + target column.
    """
    df = df.copy()

    # Target: USD price per m2
    df["price_usd_m2"] = df["price_usd_blue"] / df["surface_total_m2"]

    # Property type encoding
    df["property_type_encoded"] = df["property_type"].map(PROPERTY_TYPE_MAP).fillna(0).astype(int)

    # Covered ratio
    df["covered_ratio"] = np.where(
        df["surface_total_m2"] > 0,
        df["surface_covered_m2"].fillna(df["surface_total_m2"]) / df["surface_total_m2"],
        1.0,
    )

    # Has garage
    df["has_garage"] = (df["garages"].fillna(0) > 0).astype(int)

    # Barrio stats
    if barrio_stats is None:
        barrio_stats = compute_barrio_stats(df)

    df = df.merge(barrio_stats, on="barrio_id", how="left")

    # Fill NaN barrio stats with global median
    global_median = df["price_usd_m2"].median() if "price_usd_m2" in df.columns else 2500
    df["barrio_median_usd_m2"] = df["barrio_median_usd_m2"].fillna(global_median)
    df["barrio_listing_count"] = df["barrio_listing_count"].fillna(1)

    # Fill missing numerical features
    df["surface_covered_m2"] = df["surface_covered_m2"].fillna(df["surface_total_m2"])
    df["rooms"] = df["rooms"].fillna(df["bedrooms"].fillna(1) + 1)
    df["bedrooms"] = df["bedrooms"].fillna(df["rooms"].fillna(2) - 1)
    df["bathrooms"] = df["bathrooms"].fillna(1)
    df["garages"] = df["garages"].fillna(0)
    df["age_years"] = df["age_years"].fillna(df["age_years"].median() if df["age_years"].notna().any() else 15)
    df["expenses_ars"] = df["expenses_ars"].fillna(0)

    return df
