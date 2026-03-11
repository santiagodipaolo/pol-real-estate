"""Train the valuation model from scraped listings in the database.

Usage:
    cd backend
    python -m scripts.train_model                        # Train on sale data
    python -m scripts.train_model --operation rent       # Train on rental data
    python -m scripts.train_model --model-name v2        # Custom model name
"""

from __future__ import annotations

import argparse
import logging
import sys

import pandas as pd
from sqlalchemy import create_engine, text

sys.path.insert(0, ".")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("train")


def load_listings(operation: str) -> pd.DataFrame:
    """Load listings from the database into a DataFrame."""
    from app.core.config import settings

    engine = create_engine(settings.sync_database_url)

    query = text("""
        SELECT
            l.id,
            l.external_id,
            l.operation_type,
            l.property_type,
            l.price_usd_blue,
            l.price_ars,
            l.expenses_ars,
            l.surface_total_m2,
            l.surface_covered_m2,
            l.rooms,
            l.bedrooms,
            l.bathrooms,
            l.garages,
            l.age_years,
            l.barrio_id,
            l.latitude,
            l.longitude,
            l.days_on_market,
            b.name as barrio_name
        FROM listings l
        LEFT JOIN barrios b ON l.barrio_id = b.id
        WHERE l.operation_type = :operation
          AND l.is_active = true
          AND l.price_usd_blue > 0
          AND l.surface_total_m2 > 0
    """)

    df = pd.read_sql(query, engine, params={"operation": operation})
    engine.dispose()

    logger.info("Loaded %d %s listings from DB", len(df), operation)
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the valuation model")
    parser.add_argument(
        "--operation",
        choices=["sale", "rent"],
        default="sale",
        help="Operation type to train on (default: sale)",
    )
    parser.add_argument(
        "--model-name",
        default=None,
        help="Model name for saving (default: valuation_{operation}_v1)",
    )
    args = parser.parse_args()

    model_name = args.model_name or f"valuation_{args.operation}_v1"

    # Load data
    df = load_listings(args.operation)

    if len(df) < 20:
        logger.error("Not enough listings (%d). Scrape more data first.", len(df))
        sys.exit(1)

    # Train
    from app.valuation.model import ValuationModel

    model = ValuationModel()
    metrics = model.train(df)

    logger.info("=" * 60)
    logger.info("TRAINING RESULTS")
    logger.info("=" * 60)
    logger.info("  Samples:    %d", metrics["samples"])
    logger.info("  MAE (CV):   %.0f USD/m² (±%.0f)", metrics["mae_cv"], metrics["mae_cv_std"])
    logger.info("  MAE %%:      %.1f%%", metrics["mae_pct"])
    logger.info("  Median:     %.0f USD/m²", metrics["median_price_usd_m2"])
    logger.info("")
    logger.info("  Feature importance:")
    for feat, imp in metrics["feature_importance"].items():
        logger.info("    %-25s %.3f", feat, imp)

    # Save
    path = model.save(model_name)
    logger.info("")
    logger.info("Model saved to: %s", path)

    # Quick test prediction
    logger.info("")
    logger.info("TEST PREDICTION (75m² depto, 3 amb, Palermo):")
    # Find Palermo barrio_id
    palermo_id = df[df["barrio_name"] == "Palermo"]["barrio_id"].iloc[0] if "Palermo" in df["barrio_name"].values else None
    pred = model.predict(
        surface_total_m2=75,
        rooms=3,
        bedrooms=2,
        bathrooms=1,
        property_type="Departamento",
        barrio_id=palermo_id,
    )
    logger.info("  Estimated: USD %s (range: %s - %s)",
                f"{pred['price_usd']:,.0f}",
                f"{pred['price_usd_low']:,.0f}",
                f"{pred['price_usd_high']:,.0f}")
    logger.info("  USD/m²:    %s (range: %s - %s)",
                f"{pred['price_usd_m2']:,.0f}",
                f"{pred['price_usd_m2_low']:,.0f}",
                f"{pred['price_usd_m2_high']:,.0f}")


if __name__ == "__main__":
    main()
