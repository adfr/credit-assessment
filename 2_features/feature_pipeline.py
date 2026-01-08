#!/usr/bin/env python3
"""
Feature Engineering Pipeline
Creates engineered features for PD and LGD models.
"""

import os
import sys
import sqlite3
from pathlib import Path
from datetime import datetime

try:
    import pandas as pd
    import numpy as np
except ImportError as e:
    print(f"[ERROR] Missing required package: {e}")
    print("Run: pip install pandas numpy")
    sys.exit(1)

# Industry risk tiers and default rates
INDUSTRY_RISK = {
    "technology": {"default_rate": 0.03, "risk_tier": 2},
    "healthcare": {"default_rate": 0.025, "risk_tier": 1},
    "manufacturing": {"default_rate": 0.04, "risk_tier": 3},
    "retail": {"default_rate": 0.06, "risk_tier": 4},
    "financial_services": {"default_rate": 0.02, "risk_tier": 1},
    "energy": {"default_rate": 0.05, "risk_tier": 4},
    "construction": {"default_rate": 0.07, "risk_tier": 5},
    "transportation": {"default_rate": 0.045, "risk_tier": 3},
    "hospitality": {"default_rate": 0.08, "risk_tier": 5},
    "professional_services": {"default_rate": 0.025, "risk_tier": 2},
}


def get_db_path() -> Path:
    """Get database path."""
    project_root = Path(__file__).parent.parent
    return project_root / "data" / "credit_risk.db"


def load_data(conn: sqlite3.Connection) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load all required data from database."""
    print("\n[INFO] Loading data from database...")

    companies = pd.read_sql("SELECT * FROM companies", conn)
    print(f"  - Companies: {len(companies)} records")

    loans = pd.read_sql("SELECT * FROM loan_history", conn)
    print(f"  - Loans: {len(loans)} records")

    bureau = pd.read_sql("SELECT * FROM bureau_data", conn)
    print(f"  - Bureau data: {len(bureau)} records")

    payments = pd.read_sql("SELECT * FROM payment_history", conn)
    print(f"  - Payments: {len(payments)} records")

    return companies, loans, bureau, payments


def calculate_financial_ratios(companies: pd.DataFrame) -> pd.DataFrame:
    """Calculate financial ratio features."""
    print("\n[INFO] Calculating financial ratios...")

    df = companies.copy()

    # Debt ratios
    df["equity"] = df["total_assets"] - df["total_liabilities"]
    df["debt_to_assets"] = df["total_liabilities"] / df["total_assets"].replace(0, np.nan)

    # Profitability ratios
    df["return_on_assets"] = df["net_income"] / df["total_assets"].replace(0, np.nan)
    df["return_on_equity"] = df["net_income"] / df["equity"].replace(0, np.nan)
    df["profit_margin"] = df["net_income"] / df["annual_revenue"].replace(0, np.nan)

    # Size features
    df["log_revenue"] = np.log1p(df["annual_revenue"])
    df["log_assets"] = np.log1p(df["total_assets"])
    df["log_employees"] = np.log1p(df["employee_count"])

    # Revenue per employee
    df["revenue_per_employee"] = df["annual_revenue"] / df["employee_count"].replace(0, np.nan)

    print(f"  - Calculated {8} financial ratio features")

    return df


def calculate_bureau_features(bureau: pd.DataFrame, companies: pd.DataFrame) -> pd.DataFrame:
    """Calculate bureau-derived features."""
    print("\n[INFO] Calculating bureau features...")

    # Get most recent bureau data per company
    bureau_sorted = bureau.sort_values("report_date", ascending=False)
    bureau_latest = bureau_sorted.groupby("company_id").first().reset_index()

    # Normalize credit score (0-100 to 0-1)
    bureau_latest["credit_score_normalized"] = bureau_latest["credit_score"] / 100

    # Payment index trend (if multiple reports, calculate trend)
    bureau_trend = (
        bureau_sorted.groupby("company_id")["payment_index"]
        .apply(lambda x: x.iloc[0] - x.iloc[-1] if len(x) > 1 else 0)
        .reset_index(name="payment_index_trend")
    )

    bureau_latest = bureau_latest.merge(bureau_trend, on="company_id", how="left")

    # Derogatory ratio
    bureau_latest["derogatory_ratio"] = bureau_latest["derogatory_count"] / (
        bureau_latest["years_on_file"].replace(0, 1) * 12
    )

    # Trade line density
    bureau_latest["trade_line_density"] = bureau_latest["trade_lines_count"] / (
        bureau_latest["years_on_file"].replace(0, 1)
    )

    # Rename columns for clarity
    bureau_features = bureau_latest[[
        "company_id",
        "credit_score",
        "credit_score_normalized",
        "payment_index",
        "payment_index_trend",
        "derogatory_count",
        "derogatory_ratio",
        "years_on_file",
        "trade_lines_count",
        "trade_line_density",
        "utilization_rate",
    ]]

    print(f"  - Calculated {8} bureau features")

    return bureau_features


def calculate_behavioral_features(payments: pd.DataFrame, loans: pd.DataFrame) -> pd.DataFrame:
    """Calculate behavioral features from payment history."""
    print("\n[INFO] Calculating behavioral features...")

    # Aggregate payment behavior by loan
    payment_agg = payments.groupby("loan_id").agg({
        "days_past_due": ["mean", "max", "std"],
        "payment_status": lambda x: (x == "on_time").mean(),
        "actual_amount": "sum",
        "scheduled_amount": "sum",
    }).reset_index()

    # Flatten column names
    payment_agg.columns = [
        "loan_id",
        "avg_days_past_due",
        "max_days_past_due",
        "dpd_volatility",
        "on_time_rate",
        "total_paid",
        "total_scheduled",
    ]

    # Calculate payment consistency score
    payment_agg["payment_consistency_score"] = (
        payment_agg["total_paid"] / payment_agg["total_scheduled"].replace(0, np.nan)
    ).clip(0, 1)

    # Count DPD buckets
    dpd_counts = payments.groupby("loan_id").apply(
        lambda x: pd.Series({
            "count_30dpd": (x["days_past_due"] >= 30).sum(),
            "count_60dpd": (x["days_past_due"] >= 60).sum(),
            "count_90dpd": (x["days_past_due"] >= 90).sum(),
        }),
        include_groups=False
    ).reset_index()

    payment_agg = payment_agg.merge(dpd_counts, on="loan_id", how="left")

    # Fill NaN in volatility with 0
    payment_agg["dpd_volatility"] = payment_agg["dpd_volatility"].fillna(0)

    print(f"  - Calculated {9} behavioral features")

    return payment_agg


def calculate_loan_features(loans: pd.DataFrame, companies: pd.DataFrame) -> pd.DataFrame:
    """Calculate loan-specific features."""
    print("\n[INFO] Calculating loan features...")

    # Merge loan with company data
    loan_company = loans.merge(
        companies[["company_id", "annual_revenue", "total_assets", "industry"]],
        on="company_id",
        how="left"
    )

    # Loan to financial ratios
    loan_company["loan_to_revenue_ratio"] = (
        loan_company["loan_amount"] / loan_company["annual_revenue"].replace(0, np.nan)
    )
    loan_company["loan_to_assets_ratio"] = (
        loan_company["loan_amount"] / loan_company["total_assets"].replace(0, np.nan)
    )

    # Collateral coverage
    loan_company["collateral_coverage_ratio"] = (
        loan_company["collateral_value"] / loan_company["loan_amount"].replace(0, np.nan)
    ).fillna(0)

    # Is secured flag
    loan_company["is_secured"] = (loan_company["collateral_type"] != "unsecured").astype(int)

    # Term buckets
    loan_company["is_short_term"] = (loan_company["term_months"] <= 12).astype(int)
    loan_company["is_long_term"] = (loan_company["term_months"] >= 48).astype(int)

    # Purpose encoding
    purpose_dummies = pd.get_dummies(loan_company["purpose"], prefix="purpose")
    loan_company = pd.concat([loan_company, purpose_dummies], axis=1)

    # Log loan amount
    loan_company["log_loan_amount"] = np.log1p(loan_company["loan_amount"])

    print(f"  - Calculated loan features")

    return loan_company


def add_industry_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add industry-level features."""
    print("\n[INFO] Adding industry features...")

    df["industry_default_rate"] = df["industry"].map(
        lambda x: INDUSTRY_RISK.get(x, {}).get("default_rate", 0.05)
    )
    df["industry_risk_tier"] = df["industry"].map(
        lambda x: INDUSTRY_RISK.get(x, {}).get("risk_tier", 3)
    )

    # Industry one-hot encoding
    industry_dummies = pd.get_dummies(df["industry"], prefix="ind")
    df = pd.concat([df, industry_dummies], axis=1)

    print(f"  - Added industry features")

    return df


def calculate_lgd(loans: pd.DataFrame) -> pd.DataFrame:
    """Calculate LGD for defaulted loans."""
    print("\n[INFO] Calculating LGD...")

    defaulted = loans[loans["default_flag"] == 1].copy()

    # LGD = Loss / EAD (using loan amount as EAD proxy)
    defaulted["lgd"] = (
        defaulted["loss_amount"] / defaulted["loan_amount"].replace(0, np.nan)
    ).clip(0, 1)

    print(f"  - Calculated LGD for {len(defaulted)} defaulted loans")
    print(f"  - Mean LGD: {defaulted['lgd'].mean():.2%}")

    return defaulted[["loan_id", "lgd"]]


def create_feature_matrix(
    companies: pd.DataFrame,
    loans: pd.DataFrame,
    bureau_features: pd.DataFrame,
    behavioral_features: pd.DataFrame,
) -> pd.DataFrame:
    """Create final feature matrix for modeling."""
    print("\n[INFO] Creating feature matrix...")

    # Start with loans
    features = loans[[
        "loan_id", "company_id", "loan_amount", "interest_rate",
        "term_months", "ltv_ratio", "default_flag", "origination_date"
    ]].copy()

    # Calculate financial ratios for companies
    company_features = calculate_financial_ratios(companies)

    # Merge company features
    features = features.merge(
        company_features[[
            "company_id", "industry", "years_in_business",
            "debt_to_equity", "debt_to_assets", "current_ratio", "quick_ratio",
            "interest_coverage_ratio", "return_on_assets", "return_on_equity",
            "profit_margin", "log_revenue", "log_assets", "log_employees",
            "revenue_per_employee", "annual_revenue", "total_assets"
        ]],
        on="company_id",
        how="left"
    )

    # Merge bureau features
    features = features.merge(bureau_features, on="company_id", how="left")

    # Merge behavioral features
    features = features.merge(behavioral_features, on="loan_id", how="left")

    # Calculate loan-specific ratios
    features["loan_to_revenue_ratio"] = (
        features["loan_amount"] / features["annual_revenue"].replace(0, np.nan)
    )
    features["loan_to_assets_ratio"] = (
        features["loan_amount"] / features["total_assets"].replace(0, np.nan)
    )

    # Add industry features
    features = add_industry_features(features)

    # Calculate LGD for defaulted loans
    lgd_data = calculate_lgd(loans)
    features = features.merge(lgd_data, on="loan_id", how="left")

    # Add feature date
    features["feature_date"] = datetime.now().strftime("%Y-%m-%d")

    print(f"  - Final feature matrix: {features.shape[0]} rows, {features.shape[1]} columns")

    return features


def save_features(features: pd.DataFrame, conn: sqlite3.Connection):
    """Save features to database and file."""
    print("\n[INFO] Saving features...")

    # Select columns for model_features table
    feature_columns = [
        "company_id", "loan_id", "feature_date",
        # Financial Ratios
        "debt_to_equity", "debt_to_assets", "current_ratio", "quick_ratio",
        "interest_coverage_ratio", "return_on_assets", "return_on_equity",
        "profit_margin",
        # Bureau Features
        "credit_score_normalized", "payment_index_trend", "utilization_rate",
        "derogatory_ratio",
        # Behavioral Features
        "avg_days_past_due", "max_days_past_due", "dpd_volatility",
        "count_30dpd", "count_60dpd", "count_90dpd", "payment_consistency_score",
        # Loan Features
        "loan_to_revenue_ratio", "loan_to_assets_ratio",
        # Industry Features
        "industry_default_rate", "industry_risk_tier",
        # Target
        "default_flag", "lgd"
    ]

    # Filter to available columns
    available_columns = [c for c in feature_columns if c in features.columns]
    feature_subset = features[available_columns].copy()

    # Handle NaN for max_days_past_due (convert to int)
    if "max_days_past_due" in feature_subset.columns:
        feature_subset["max_days_past_due"] = feature_subset["max_days_past_due"].fillna(0).astype(int)

    # Save to database
    feature_subset.to_sql("model_features", conn, if_exists="replace", index=False)
    print(f"  - Saved {len(feature_subset)} rows to model_features table")

    # Also save full feature matrix to parquet
    project_root = Path(__file__).parent.parent
    output_path = project_root / "data" / "features"
    output_path.mkdir(parents=True, exist_ok=True)

    features.to_parquet(output_path / "feature_matrix.parquet", index=False)
    print(f"  - Saved full feature matrix to {output_path / 'feature_matrix.parquet'}")


def print_feature_summary(features: pd.DataFrame):
    """Print feature summary statistics."""
    print("\n" + "=" * 60)
    print("Feature Engineering Summary")
    print("=" * 60)

    print(f"\nTotal observations: {len(features)}")
    print(f"Total features: {len(features.columns)}")
    print(f"Default rate: {features['default_flag'].mean():.2%}")

    # Missing value summary
    missing = features.isnull().sum()
    missing_pct = (missing / len(features) * 100).round(2)
    missing_df = pd.DataFrame({
        "missing_count": missing,
        "missing_pct": missing_pct
    })
    missing_df = missing_df[missing_df["missing_count"] > 0].sort_values(
        "missing_pct", ascending=False
    )

    if len(missing_df) > 0:
        print("\nFeatures with missing values:")
        for col, row in missing_df.head(10).iterrows():
            print(f"  - {col}: {row['missing_count']} ({row['missing_pct']:.1f}%)")

    # Key feature statistics
    key_features = [
        "debt_to_equity", "current_ratio", "interest_coverage_ratio",
        "credit_score_normalized", "avg_days_past_due", "loan_to_revenue_ratio"
    ]

    print("\nKey Feature Statistics:")
    for feat in key_features:
        if feat in features.columns:
            stats = features[feat].describe()
            print(f"  {feat}:")
            print(f"    Mean: {stats['mean']:.4f}, Std: {stats['std']:.4f}")
            print(f"    Min: {stats['min']:.4f}, Max: {stats['max']:.4f}")


def main():
    """Main function to run feature engineering pipeline."""
    print("\n" + "=" * 60)
    print("Credit Risk Platform - Feature Engineering")
    print("=" * 60)

    db_path = get_db_path()
    if not db_path.exists():
        print(f"\n[ERROR] Database not found at {db_path}")
        print("Please run 1_data/load_to_iceberg.py first")
        return 1

    conn = sqlite3.connect(str(db_path))

    try:
        # Load data
        companies, loans, bureau, payments = load_data(conn)

        # Calculate features
        bureau_features = calculate_bureau_features(bureau, companies)
        behavioral_features = calculate_behavioral_features(payments, loans)

        # Create feature matrix
        features = create_feature_matrix(
            companies, loans, bureau_features, behavioral_features
        )

        # Save features
        save_features(features, conn)

        # Print summary
        print_feature_summary(features)

        conn.commit()

        print("\n" + "=" * 60)
        print("[SUCCESS] Feature engineering completed!")
        print("=" * 60)
        print("\nNext steps:")
        print("  1. Run 2_features/data_quality.py for quality checks")
        print("  2. Run 3_models/train_pd_model.py to train PD model")

    except Exception as e:
        print(f"\n[ERROR] Feature engineering failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
