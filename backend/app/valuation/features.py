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

# Condition encoding (ordinal — reflects typical price hierarchy)
CONDITION_MAP = {
    "Nuevo": 5,
    "Excelente": 4,
    "Muy bueno": 3,
    "Bueno": 2,
    "Regular": 1,
    "A reciclar": 0,
    "En construccion": 3,
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
    # Detail-enriched features
    "floor",
    "has_pool",
    "has_gym",
    "has_security",
    "has_balcony",
    "is_front",
    "condition_encoded",
    "amenity_count",
    # Geo features
    "latitude",
    "longitude",
    # Derived features
    "surface_per_room",
    "log_barrio_median",
]

TARGET_COLUMN = "price_usd_m2"
LOG_TARGET_COLUMN = "log_price_usd_m2"


def filter_outliers(df: pd.DataFrame, column: str = TARGET_COLUMN, iqr_factor: float = 2.0) -> pd.DataFrame:
    """Remove outliers using IQR method. More robust than fixed thresholds."""
    q1 = df[column].quantile(0.05)
    q3 = df[column].quantile(0.95)
    iqr = q3 - q1
    lower = q1 - iqr_factor * iqr
    upper = q3 + iqr_factor * iqr
    mask = (df[column] >= lower) & (df[column] <= upper)
    return df[mask]


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

    # Detail-enriched features
    df["floor"] = df["floor"].fillna(0).astype(int)

    # Amenity flags — extract from JSONB amenities column
    def _amenity_bool(col_name: str, amenity_key: str) -> None:
        if "amenities" in df.columns:
            df[col_name] = df["amenities"].apply(
                lambda a: int(isinstance(a, dict) and a.get(amenity_key, False))
            )
        else:
            df[col_name] = 0

    _amenity_bool("has_pool", "pool")
    _amenity_bool("has_gym", "gym")
    _amenity_bool("has_security", "security")
    _amenity_bool("has_balcony", "balcony")

    # Is front (orientation)
    if "orientation" in df.columns:
        df["is_front"] = df["orientation"].apply(
            lambda o: 1 if isinstance(o, str) and o.lower() in ("frente", "n", "ne", "no") else 0
        )
    else:
        df["is_front"] = 0

    # Condition encoded
    if "condition" in df.columns:
        df["condition_encoded"] = df["condition"].map(CONDITION_MAP).fillna(2).astype(int)
    else:
        df["condition_encoded"] = 2  # default "Bueno"

    # Amenity count
    if "amenities" in df.columns:
        df["amenity_count"] = df["amenities"].apply(
            lambda a: sum(1 for v in a.values() if v) if isinstance(a, dict) else 0
        )
    else:
        df["amenity_count"] = 0

    # Geo features — fill missing with CABA centroid
    CABA_LAT, CABA_LNG = -34.6037, -58.3816
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce").fillna(CABA_LAT)
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce").fillna(CABA_LNG)

    # Derived: surface per room (efficiency metric)
    df["surface_per_room"] = np.where(
        df["rooms"].fillna(1) > 0,
        df["surface_total_m2"] / df["rooms"].fillna(1).clip(lower=1),
        df["surface_total_m2"],
    )

    # Barrio stats
    if barrio_stats is None:
        barrio_stats = compute_barrio_stats(df)

    df = df.merge(barrio_stats, on="barrio_id", how="left")

    # Fill NaN barrio stats with global median
    global_median = df["price_usd_m2"].median() if "price_usd_m2" in df.columns else 2500
    df["barrio_median_usd_m2"] = df["barrio_median_usd_m2"].fillna(global_median)
    df["barrio_listing_count"] = df["barrio_listing_count"].fillna(1)

    # Log-transformed barrio median (reduces skew)
    df["log_barrio_median"] = np.log1p(df["barrio_median_usd_m2"])

    # Log-transformed target for training
    if "price_usd_m2" in df.columns:
        df["log_price_usd_m2"] = np.log1p(df["price_usd_m2"])

    # Fill missing numerical features
    df["surface_covered_m2"] = df["surface_covered_m2"].fillna(df["surface_total_m2"])
    df["rooms"] = df["rooms"].fillna(df["bedrooms"].fillna(1) + 1)
    df["bedrooms"] = df["bedrooms"].fillna(df["rooms"].fillna(2) - 1)
    df["bathrooms"] = df["bathrooms"].fillna(1)
    df["garages"] = df["garages"].fillna(0)
    df["age_years"] = df["age_years"].fillna(df["age_years"].median() if df["age_years"].notna().any() else 15)
    df["expenses_ars"] = df["expenses_ars"].fillna(0)

    return df
