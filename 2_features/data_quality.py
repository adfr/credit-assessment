#!/usr/bin/env python3
"""
Data Quality Checks Script
Performs comprehensive data quality analysis on the feature matrix.
"""

import os
import sys
import sqlite3
from pathlib import Path
from datetime import datetime

try:
    import pandas as pd
    import numpy as np
    from scipy import stats
except ImportError as e:
    print(f"[ERROR] Missing required package: {e}")
    print("Run: pip install pandas numpy scipy")
    sys.exit(1)

# Get project root from environment or current working directory
PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", os.getcwd()))


def get_data_path() -> Path:
    """Get feature data path."""
    return PROJECT_ROOT / "data" / "features" / "feature_matrix.parquet"


def load_features() -> pd.DataFrame:
    """Load feature matrix."""
    data_path = get_data_path()

    if not data_path.exists():
        print(f"\n[ERROR] Feature matrix not found at {data_path}")
        print("Please run 2_features/feature_pipeline.py first")
        sys.exit(1)

    return pd.read_parquet(data_path)


def missing_value_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Analyze missing values in the dataset."""
    print("\n" + "=" * 60)
    print("Missing Value Analysis")
    print("=" * 60)

    missing = df.isnull().sum()
    missing_pct = (missing / len(df) * 100).round(2)
    total = len(df)

    missing_df = pd.DataFrame({
        "column": missing.index,
        "missing_count": missing.values,
        "missing_pct": missing_pct.values,
        "non_missing_count": total - missing.values
    })

    missing_df = missing_df.sort_values("missing_pct", ascending=False)

    # Print summary
    cols_with_missing = missing_df[missing_df["missing_count"] > 0]

    if len(cols_with_missing) == 0:
        print("\n  No missing values found!")
    else:
        print(f"\n  Columns with missing values: {len(cols_with_missing)}")
        print("\n  Top 15 columns by missing percentage:")
        for _, row in cols_with_missing.head(15).iterrows():
            bar = "█" * int(row["missing_pct"] / 5) + "░" * (20 - int(row["missing_pct"] / 5))
            print(f"    {row['column']:<35} {bar} {row['missing_pct']:>6.2f}%")

    return missing_df


def outlier_detection(df: pd.DataFrame, threshold: float = 3.0) -> pd.DataFrame:
    """Detect outliers using Z-score method."""
    print("\n" + "=" * 60)
    print("Outlier Detection (Z-score > 3)")
    print("=" * 60)

    numeric_cols = df.select_dtypes(include=[np.number]).columns
    exclude_cols = ["default_flag", "lgd", "loan_id"]
    numeric_cols = [c for c in numeric_cols if c not in exclude_cols and not c.startswith("purpose_") and not c.startswith("ind_")]

    outlier_info = []

    for col in numeric_cols:
        data = df[col].dropna()
        if len(data) == 0:
            continue

        # Calculate Z-scores
        z_scores = np.abs(stats.zscore(data))
        outliers = (z_scores > threshold).sum()
        outlier_pct = (outliers / len(data) * 100)

        if outliers > 0:
            outlier_info.append({
                "column": col,
                "outlier_count": outliers,
                "outlier_pct": round(outlier_pct, 2),
                "min": data.min(),
                "max": data.max(),
                "mean": data.mean(),
                "std": data.std()
            })

    outlier_df = pd.DataFrame(outlier_info)

    if len(outlier_df) > 0:
        outlier_df = outlier_df.sort_values("outlier_pct", ascending=False)
        print(f"\n  Columns with outliers: {len(outlier_df)}")
        print("\n  Top 10 columns by outlier percentage:")
        for _, row in outlier_df.head(10).iterrows():
            print(f"    {row['column']:<35} {row['outlier_count']:>6} outliers ({row['outlier_pct']:.2f}%)")
    else:
        print("\n  No significant outliers detected!")

    return outlier_df


def distribution_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Analyze distributions of key features."""
    print("\n" + "=" * 60)
    print("Distribution Analysis")
    print("=" * 60)

    # Key features to analyze
    key_features = [
        "debt_to_equity", "current_ratio", "interest_coverage_ratio",
        "credit_score_normalized", "avg_days_past_due", "loan_to_revenue_ratio",
        "payment_consistency_score", "utilization_rate", "profit_margin"
    ]

    dist_info = []

    for col in key_features:
        if col not in df.columns:
            continue

        data = df[col].dropna()
        if len(data) == 0:
            continue

        # Calculate statistics
        skewness = stats.skew(data)
        kurtosis = stats.kurtosis(data)
        shapiro_stat = None
        shapiro_p = None

        # Shapiro-Wilk test for normality (sample if too large)
        if len(data) > 5000:
            sample = data.sample(5000, random_state=42)
        else:
            sample = data

        try:
            shapiro_stat, shapiro_p = stats.shapiro(sample)
        except Exception:
            pass

        dist_info.append({
            "column": col,
            "mean": data.mean(),
            "median": data.median(),
            "std": data.std(),
            "skewness": skewness,
            "kurtosis": kurtosis,
            "shapiro_p": shapiro_p,
            "is_normal": shapiro_p > 0.05 if shapiro_p else False
        })

    dist_df = pd.DataFrame(dist_info)

    print("\n  Feature Distribution Summary:")
    for _, row in dist_df.iterrows():
        normality = "Normal" if row["is_normal"] else "Non-normal"
        skew_dir = "Right-skewed" if row["skewness"] > 0.5 else "Left-skewed" if row["skewness"] < -0.5 else "Symmetric"
        print(f"\n  {row['column']}:")
        print(f"    Mean: {row['mean']:.4f}, Median: {row['median']:.4f}, Std: {row['std']:.4f}")
        print(f"    Skewness: {row['skewness']:.2f} ({skew_dir}), Kurtosis: {row['kurtosis']:.2f}")
        print(f"    Distribution: {normality}")

    return dist_df


def correlation_analysis(df: pd.DataFrame, threshold: float = 0.8) -> pd.DataFrame:
    """Analyze feature correlations."""
    print("\n" + "=" * 60)
    print("Correlation Analysis")
    print("=" * 60)

    # Select numeric columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    exclude_cols = ["loan_id", "default_flag", "lgd"]
    numeric_cols = [c for c in numeric_cols if c not in exclude_cols and not c.startswith("purpose_") and not c.startswith("ind_")]

    # Calculate correlation matrix
    corr_matrix = df[numeric_cols].corr()

    # Find highly correlated pairs
    high_corr = []
    for i in range(len(corr_matrix.columns)):
        for j in range(i + 1, len(corr_matrix.columns)):
            corr_val = corr_matrix.iloc[i, j]
            if abs(corr_val) >= threshold:
                high_corr.append({
                    "feature_1": corr_matrix.columns[i],
                    "feature_2": corr_matrix.columns[j],
                    "correlation": round(corr_val, 4)
                })

    high_corr_df = pd.DataFrame(high_corr)

    if len(high_corr_df) > 0:
        high_corr_df = high_corr_df.sort_values("correlation", key=abs, ascending=False)
        print(f"\n  Highly correlated feature pairs (|r| >= {threshold}):")
        for _, row in high_corr_df.iterrows():
            sign = "+" if row["correlation"] > 0 else "-"
            print(f"    {row['feature_1']:<25} <-> {row['feature_2']:<25} r={sign}{abs(row['correlation']):.4f}")
    else:
        print(f"\n  No feature pairs with |correlation| >= {threshold}")

    # Correlation with target
    print("\n  Correlation with target (default_flag):")
    target_corr = df[numeric_cols + ["default_flag"]].corr()["default_flag"].drop("default_flag")
    target_corr = target_corr.sort_values(key=abs, ascending=False)

    for feat, corr in target_corr.head(15).items():
        sign = "+" if corr > 0 else "-"
        bar_len = int(abs(corr) * 20)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        print(f"    {feat:<35} {bar} {sign}{abs(corr):.4f}")

    return high_corr_df


def target_leakage_check(df: pd.DataFrame) -> list:
    """Check for potential target leakage."""
    print("\n" + "=" * 60)
    print("Target Leakage Check")
    print("=" * 60)

    leakage_suspects = []

    # Features that might leak target information
    suspicious_features = ["days_to_default", "loss_amount", "recovery_amount", "lgd"]

    for feat in suspicious_features:
        if feat in df.columns:
            # Check if feature is only available for defaulted loans
            non_default_count = df[df["default_flag"] == 0][feat].notna().sum()
            default_count = df[df["default_flag"] == 1][feat].notna().sum()

            if non_default_count == 0 and default_count > 0:
                leakage_suspects.append({
                    "feature": feat,
                    "reason": "Only available for defaulted loans",
                    "severity": "HIGH"
                })
            elif feat in df.columns:
                corr = df[[feat, "default_flag"]].corr().iloc[0, 1]
                if abs(corr) > 0.9:
                    leakage_suspects.append({
                        "feature": feat,
                        "reason": f"Very high correlation with target (r={corr:.4f})",
                        "severity": "HIGH"
                    })

    # Check for perfect predictors
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        if col in ["default_flag", "lgd", "loan_id"] or col.startswith("purpose_") or col.startswith("ind_"):
            continue

        # Check correlation
        try:
            corr = df[[col, "default_flag"]].corr().iloc[0, 1]
            if abs(corr) > 0.95:
                if col not in [s["feature"] for s in leakage_suspects]:
                    leakage_suspects.append({
                        "feature": col,
                        "reason": f"Near-perfect correlation with target (r={corr:.4f})",
                        "severity": "CRITICAL"
                    })
        except Exception:
            pass

    if leakage_suspects:
        print("\n  ⚠️  Potential leakage features detected:")
        for suspect in leakage_suspects:
            print(f"    [{suspect['severity']}] {suspect['feature']}: {suspect['reason']}")
        print("\n  Recommendation: Exclude these features from training or investigate further")
    else:
        print("\n  ✓ No obvious target leakage detected")

    return leakage_suspects


def class_balance_check(df: pd.DataFrame):
    """Check class balance of target variable."""
    print("\n" + "=" * 60)
    print("Class Balance Analysis")
    print("=" * 60)

    default_counts = df["default_flag"].value_counts()
    default_pct = df["default_flag"].value_counts(normalize=True) * 100

    print("\n  Target variable distribution:")
    print(f"    Non-default (0): {default_counts.get(0, 0):,} ({default_pct.get(0, 0):.2f}%)")
    print(f"    Default (1):     {default_counts.get(1, 0):,} ({default_pct.get(1, 0):.2f}%)")

    # Imbalance ratio
    majority = default_counts.max()
    minority = default_counts.min()
    imbalance_ratio = majority / minority if minority > 0 else float('inf')

    print(f"\n  Imbalance ratio: {imbalance_ratio:.1f}:1")

    if imbalance_ratio > 10:
        print("  ⚠️  Significant class imbalance detected")
        print("  Recommendation: Consider SMOTE, class weights, or stratified sampling")
    elif imbalance_ratio > 5:
        print("  ⚠️  Moderate class imbalance detected")
        print("  Recommendation: Use stratified cross-validation and class weights")
    else:
        print("  ✓ Class balance is acceptable")


def generate_report(
    df: pd.DataFrame,
    missing_df: pd.DataFrame,
    outlier_df: pd.DataFrame,
    dist_df: pd.DataFrame,
    corr_df: pd.DataFrame,
    leakage_suspects: list
):
    """Generate data quality report."""
    print("\n" + "=" * 60)
    print("Data Quality Report Summary")
    print("=" * 60)

    issues = []

    # Check missing values
    high_missing = missing_df[missing_df["missing_pct"] > 20]
    if len(high_missing) > 0:
        issues.append(f"⚠️  {len(high_missing)} features with >20% missing values")

    # Check outliers
    high_outliers = outlier_df[outlier_df["outlier_pct"] > 5] if len(outlier_df) > 0 else pd.DataFrame()
    if len(high_outliers) > 0:
        issues.append(f"⚠️  {len(high_outliers)} features with >5% outliers")

    # Check high correlations
    if len(corr_df) > 5:
        issues.append(f"⚠️  {len(corr_df)} highly correlated feature pairs")

    # Check leakage
    if leakage_suspects:
        issues.append(f"🚨 {len(leakage_suspects)} potential leakage features")

    print("\n  Dataset Overview:")
    print(f"    Total observations: {len(df):,}")
    print(f"    Total features: {len(df.columns)}")
    print(f"    Numeric features: {len(df.select_dtypes(include=[np.number]).columns)}")

    if issues:
        print("\n  Issues Found:")
        for issue in issues:
            print(f"    {issue}")
    else:
        print("\n  ✓ No major data quality issues found")

    print("\n  Recommendations:")
    print("    1. Handle missing values with imputation or feature removal")
    print("    2. Consider winsorizing or transforming outliers")
    print("    3. Remove or combine highly correlated features")
    print("    4. Exclude leakage features from model training")


def main():
    """Main function to run data quality checks."""
    print("\n" + "=" * 60)
    print("Credit Risk Platform - Data Quality Analysis")
    print("=" * 60)

    # Load data
    print("\n[INFO] Loading feature matrix...")
    df = load_features()
    print(f"  - Loaded {len(df)} observations with {len(df.columns)} features")

    # Run analyses
    missing_df = missing_value_analysis(df)
    outlier_df = outlier_detection(df)
    dist_df = distribution_analysis(df)
    corr_df = correlation_analysis(df)
    leakage_suspects = target_leakage_check(df)
    class_balance_check(df)

    # Generate report
    generate_report(df, missing_df, outlier_df, dist_df, corr_df, leakage_suspects)

    # Save report
    report_dir = PROJECT_ROOT / "data" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    # Save analysis results
    missing_df.to_csv(report_dir / "missing_values.csv", index=False)
    if len(outlier_df) > 0:
        outlier_df.to_csv(report_dir / "outliers.csv", index=False)
    dist_df.to_csv(report_dir / "distributions.csv", index=False)
    if len(corr_df) > 0:
        corr_df.to_csv(report_dir / "high_correlations.csv", index=False)

    print(f"\n[INFO] Reports saved to: {report_dir}")

    print("\n" + "=" * 60)
    print("[SUCCESS] Data quality analysis completed!")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Review the quality reports in data/reports/")
    print("  2. Run 3_models/train_pd_model.py to train PD model")

    return 0


if __name__ == "__main__":
    main()
