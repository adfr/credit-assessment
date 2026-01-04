"""
Feature Engineering Spark Job
Processes raw data and generates features for model training and scoring.
"""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window
from pyspark.sql.types import DoubleType
import argparse
from datetime import datetime


def create_spark_session(app_name: str = "FeatureEngineering") -> SparkSession:
    """Create Spark session."""
    return SparkSession.builder \
        .appName(app_name) \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
        .getOrCreate()


def load_raw_data(spark: SparkSession, data_path: str) -> dict:
    """Load raw data tables."""
    tables = {}

    tables["companies"] = spark.read.parquet(f"{data_path}/companies")
    tables["loans"] = spark.read.parquet(f"{data_path}/loan_history")
    tables["payments"] = spark.read.parquet(f"{data_path}/payment_history")
    tables["bureau"] = spark.read.parquet(f"{data_path}/bureau_data")

    return tables


def create_financial_features(companies_df):
    """Create financial ratio features."""
    df = companies_df

    # Leverage ratios
    df = df.withColumn(
        "debt_to_equity",
        F.col("total_liabilities") / F.greatest(
            F.col("total_assets") - F.col("total_liabilities"),
            F.lit(1)
        )
    )

    df = df.withColumn(
        "debt_to_assets",
        F.col("total_liabilities") / F.greatest(F.col("total_assets"), F.lit(1))
    )

    # Profitability ratios
    df = df.withColumn(
        "return_on_assets",
        F.col("net_income") / F.greatest(F.col("total_assets"), F.lit(1))
    )

    df = df.withColumn(
        "return_on_equity",
        F.col("net_income") / F.greatest(
            F.col("total_assets") - F.col("total_liabilities"),
            F.lit(1)
        )
    )

    df = df.withColumn(
        "profit_margin",
        F.col("net_income") / F.greatest(F.col("annual_revenue"), F.lit(1))
    )

    # Liquidity ratios
    df = df.withColumn(
        "current_ratio",
        F.coalesce(F.col("current_ratio"), F.lit(1.5))
    )

    df = df.withColumn(
        "quick_ratio",
        F.coalesce(F.col("quick_ratio"), F.lit(1.0))
    )

    return df


def create_loan_features(loans_df):
    """Create loan-level features."""
    df = loans_df

    # Loan to value
    df = df.withColumn(
        "loan_to_value",
        F.col("loan_amount") / F.greatest(F.col("collateral_value"), F.lit(1))
    )

    # Term features
    df = df.withColumn(
        "term_years",
        F.col("term_months") / 12
    )

    # Calculate loan age
    df = df.withColumn(
        "loan_age_months",
        F.months_between(F.current_date(), F.col("origination_date"))
    )

    # Remaining term
    df = df.withColumn(
        "remaining_term_months",
        F.greatest(F.col("term_months") - F.col("loan_age_months"), F.lit(0))
    )

    return df


def create_payment_features(payments_df, loans_df):
    """Create payment behavior features."""
    # Aggregate payment history per loan
    payment_agg = payments_df.groupBy("loan_id").agg(
        F.count("*").alias("total_payments"),
        F.sum(F.when(F.col("days_past_due") > 0, 1).otherwise(0)).alias("late_payments"),
        F.avg("days_past_due").alias("avg_days_past_due"),
        F.max("days_past_due").alias("max_days_past_due"),
        F.sum(F.when(F.col("days_past_due") > 30, 1).otherwise(0)).alias("dpd_30_count"),
        F.sum(F.when(F.col("days_past_due") > 60, 1).otherwise(0)).alias("dpd_60_count"),
        F.sum(F.when(F.col("days_past_due") > 90, 1).otherwise(0)).alias("dpd_90_count"),
    )

    # Calculate late payment ratio
    payment_agg = payment_agg.withColumn(
        "late_payment_ratio",
        F.col("late_payments") / F.greatest(F.col("total_payments"), F.lit(1))
    )

    # Join with loans
    df = loans_df.join(payment_agg, "loan_id", "left")

    # Fill nulls for loans without payment history
    df = df.fillna({
        "total_payments": 0,
        "late_payments": 0,
        "avg_days_past_due": 0,
        "max_days_past_due": 0,
        "late_payment_ratio": 0,
        "dpd_30_count": 0,
        "dpd_60_count": 0,
        "dpd_90_count": 0,
    })

    return df


def create_bureau_features(bureau_df):
    """Create bureau/credit features."""
    df = bureau_df

    # Normalize credit score
    df = df.withColumn(
        "credit_score_normalized",
        F.col("credit_score") / 100
    )

    # Derogatory ratio
    df = df.withColumn(
        "derogatory_ratio",
        F.col("derogatory_count") / 12  # Normalize by max expected
    )

    # Utilization features
    df = df.withColumn(
        "high_utilization_flag",
        F.when(F.col("utilization_rate") > 0.7, 1).otherwise(0)
    )

    return df


def create_industry_features(spark: SparkSession, companies_df, loans_df):
    """Create industry-level features."""
    # Calculate industry default rates
    industry_stats = loans_df.join(
        companies_df.select("company_id", "industry"),
        "company_id"
    ).groupBy("industry").agg(
        F.avg("default_flag").alias("industry_default_rate"),
        F.count("*").alias("industry_loan_count"),
        F.avg("loan_amount").alias("industry_avg_loan"),
    )

    # Assign risk tiers
    industry_stats = industry_stats.withColumn(
        "industry_risk_tier",
        F.when(F.col("industry_default_rate") < 0.03, 1)
        .when(F.col("industry_default_rate") < 0.05, 2)
        .when(F.col("industry_default_rate") < 0.08, 3)
        .when(F.col("industry_default_rate") < 0.12, 4)
        .otherwise(5)
    )

    return industry_stats


def create_company_history_features(loans_df):
    """Create company loan history features."""
    # Window for company history
    company_window = Window.partitionBy("company_id").orderBy("origination_date")

    df = loans_df

    # Number of previous loans
    df = df.withColumn(
        "previous_loan_count",
        F.count("*").over(company_window) - 1
    )

    # Previous default flag
    df = df.withColumn(
        "previous_defaults",
        F.sum("default_flag").over(
            company_window.rowsBetween(Window.unboundedPreceding, -1)
        )
    )

    df = df.fillna({"previous_loan_count": 0, "previous_defaults": 0})

    # Previous default flag binary
    df = df.withColumn(
        "has_previous_default",
        F.when(F.col("previous_defaults") > 0, 1).otherwise(0)
    )

    return df


def assemble_features(
    companies_df,
    loans_df,
    bureau_df,
    industry_df
):
    """Assemble all features into final dataset."""
    # Start with loans as base
    df = loans_df

    # Join company features
    company_cols = [
        "company_id", "company_name", "industry",
        "debt_to_equity", "debt_to_assets",
        "return_on_assets", "return_on_equity", "profit_margin",
        "current_ratio", "quick_ratio"
    ]
    df = df.join(
        companies_df.select(company_cols),
        "company_id",
        "left"
    )

    # Join bureau features
    bureau_cols = [
        "company_id",
        "credit_score_normalized", "utilization_rate",
        "derogatory_ratio", "high_utilization_flag"
    ]
    df = df.join(
        bureau_df.select(bureau_cols),
        "company_id",
        "left"
    )

    # Join industry features
    df = df.join(industry_df, "industry", "left")

    return df


def save_features(df, output_path: str, partition_cols: list = None):
    """Save feature dataset."""
    writer = df.write.mode("overwrite")

    if partition_cols:
        writer = writer.partitionBy(partition_cols)

    writer.parquet(output_path)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Feature Engineering Job")
    parser.add_argument("--input-path", required=True, help="Input data path")
    parser.add_argument("--output-path", required=True, help="Output features path")
    parser.add_argument("--date", default=None, help="Processing date (YYYY-MM-DD)")

    args = parser.parse_args()

    # Create Spark session
    spark = create_spark_session()

    print(f"Starting feature engineering job")
    print(f"Input path: {args.input_path}")
    print(f"Output path: {args.output_path}")

    try:
        # Load raw data
        print("Loading raw data...")
        tables = load_raw_data(spark, args.input_path)

        # Create features
        print("Creating financial features...")
        companies_df = create_financial_features(tables["companies"])

        print("Creating loan features...")
        loans_df = create_loan_features(tables["loans"])

        print("Creating payment features...")
        loans_df = create_payment_features(tables["payments"], loans_df)

        print("Creating bureau features...")
        bureau_df = create_bureau_features(tables["bureau"])

        print("Creating industry features...")
        industry_df = create_industry_features(spark, tables["companies"], tables["loans"])

        print("Creating company history features...")
        loans_df = create_company_history_features(loans_df)

        # Assemble final feature set
        print("Assembling features...")
        features_df = assemble_features(
            companies_df, loans_df, bureau_df, industry_df
        )

        # Add metadata
        features_df = features_df.withColumn(
            "feature_generation_date",
            F.lit(args.date or datetime.now().strftime("%Y-%m-%d"))
        )

        # Save
        print("Saving features...")
        save_features(features_df, args.output_path)

        record_count = features_df.count()
        print(f"Feature engineering complete. Records: {record_count}")

    except Exception as e:
        print(f"Error in feature engineering: {e}")
        raise
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
