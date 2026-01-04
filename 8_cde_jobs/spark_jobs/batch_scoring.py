"""
Batch Scoring Spark Job
Runs batch predictions for credit risk models.
"""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, StringType, StructType, StructField
from pyspark.ml.feature import VectorAssembler
import argparse
from datetime import datetime
import pickle
import numpy as np
from typing import List


def create_spark_session(app_name: str = "BatchScoring") -> SparkSession:
    """Create Spark session."""
    return SparkSession.builder \
        .appName(app_name) \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.shuffle.partitions", "200") \
        .getOrCreate()


def load_model(model_path: str):
    """Load pickled model."""
    with open(model_path, "rb") as f:
        return pickle.load(f)


def get_feature_columns() -> List[str]:
    """Get list of feature columns for model input."""
    return [
        "debt_to_equity",
        "debt_to_assets",
        "current_ratio",
        "quick_ratio",
        "return_on_assets",
        "return_on_equity",
        "profit_margin",
        "credit_score_normalized",
        "utilization_rate",
        "derogatory_ratio",
        "industry_default_rate",
        "industry_risk_tier",
        "loan_to_value",
        "late_payment_ratio",
        "has_previous_default",
    ]


def score_partition(iterator, model_broadcast, feature_cols):
    """Score a partition using broadcast model."""
    import pandas as pd

    model = model_broadcast.value
    rows = list(iterator)

    if not rows:
        return iter([])

    # Convert to pandas
    df = pd.DataFrame([row.asDict() for row in rows])

    # Prepare features
    X = df[feature_cols].fillna(0).values

    # Score
    pd_scores = model.predict_proba(X)[:, 1]

    # Add scores to dataframe
    df["pd_score"] = pd_scores

    # Assign risk grades
    def get_risk_grade(pd):
        grades = [
            (0.005, "AAA"), (0.01, "AA"), (0.02, "A"),
            (0.03, "BBB"), (0.05, "BB"), (0.10, "B"),
            (0.15, "CCC"), (0.25, "CC"), (0.50, "C"), (1.0, "D")
        ]
        for threshold, grade in grades:
            if pd <= threshold:
                return grade
        return "D"

    df["risk_grade"] = df["pd_score"].apply(get_risk_grade)

    # Convert back to rows
    from pyspark.sql import Row
    for _, row in df.iterrows():
        yield Row(**row.to_dict())


def calculate_risk_metrics(df):
    """Calculate additional risk metrics."""
    # Expected loss = PD * LGD * EAD
    df = df.withColumn(
        "expected_loss",
        F.col("pd_score") * F.col("lgd_score") * F.col("loan_amount")
    )

    # Unexpected loss (simplified)
    df = df.withColumn(
        "unexpected_loss",
        F.sqrt(F.col("pd_score") * (1 - F.col("pd_score"))) *
        F.col("lgd_score") * F.col("loan_amount") * 2.33  # 99% confidence
    )

    # Economic capital
    df = df.withColumn(
        "economic_capital",
        F.col("unexpected_loss") - F.col("expected_loss")
    )

    # Risk-weighted assets (simplified Basel approach)
    df = df.withColumn(
        "risk_weighted_assets",
        F.col("loan_amount") * F.col("pd_score") * 12.5
    )

    return df


def score_pd_model(spark: SparkSession, df, model_path: str):
    """Score using PD model."""
    feature_cols = get_feature_columns()

    # Load and broadcast model
    model = load_model(model_path)
    model_broadcast = spark.sparkContext.broadcast(model)

    # Define output schema
    output_schema = df.schema \
        .add(StructField("pd_score", DoubleType(), True)) \
        .add(StructField("risk_grade", StringType(), True))

    # Score using mapPartitions
    scored_rdd = df.rdd.mapPartitions(
        lambda it: score_partition(it, model_broadcast, feature_cols)
    )

    scored_df = spark.createDataFrame(scored_rdd, output_schema)

    return scored_df


def score_lgd_model(spark: SparkSession, df, model_path: str):
    """Score using LGD model."""
    # For LGD, we use a simpler approach based on collateral
    # In production, this would use the actual LGD model

    df = df.withColumn(
        "lgd_score",
        F.when(F.col("collateral_type") == "real_estate", 0.25)
        .when(F.col("collateral_type") == "equipment", 0.35)
        .when(F.col("collateral_type") == "inventory", 0.50)
        .when(F.col("collateral_type") == "accounts_receivable", 0.45)
        .when(F.col("collateral_type") == "securities", 0.20)
        .otherwise(0.60)
    )

    # Adjust for loan-to-value
    df = df.withColumn(
        "lgd_score",
        F.when(
            F.col("loan_to_value") > 0.8,
            F.least(F.col("lgd_score") * 1.2, F.lit(0.9))
        ).otherwise(F.col("lgd_score"))
    )

    return df


def validate_scores(df):
    """Validate scoring results."""
    # Check for nulls
    null_counts = df.select([
        F.sum(F.when(F.col(c).isNull(), 1).otherwise(0)).alias(c)
        for c in ["pd_score", "lgd_score", "expected_loss"]
    ]).collect()[0]

    print("Null counts in scores:")
    print(f"  PD Score: {null_counts['pd_score']}")
    print(f"  LGD Score: {null_counts['lgd_score']}")
    print(f"  Expected Loss: {null_counts['expected_loss']}")

    # Score distribution
    print("\nPD Score Distribution:")
    df.select(
        F.min("pd_score").alias("min"),
        F.avg("pd_score").alias("avg"),
        F.max("pd_score").alias("max"),
        F.stddev("pd_score").alias("std")
    ).show()

    # Risk grade distribution
    print("\nRisk Grade Distribution:")
    df.groupBy("risk_grade").count().orderBy("risk_grade").show()


def save_scores(df, output_path: str, partition_date: str):
    """Save scoring results."""
    # Add scoring metadata
    df = df.withColumn("scoring_date", F.lit(partition_date))
    df = df.withColumn("scoring_timestamp", F.current_timestamp())

    # Save
    df.write \
        .mode("overwrite") \
        .partitionBy("scoring_date") \
        .parquet(output_path)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Batch Scoring Job")
    parser.add_argument("--features-path", required=True, help="Features input path")
    parser.add_argument("--pd-model-path", required=True, help="PD model path")
    parser.add_argument("--lgd-model-path", required=True, help="LGD model path")
    parser.add_argument("--output-path", required=True, help="Output scores path")
    parser.add_argument("--date", default=None, help="Scoring date (YYYY-MM-DD)")

    args = parser.parse_args()

    # Create Spark session
    spark = create_spark_session()

    scoring_date = args.date or datetime.now().strftime("%Y-%m-%d")

    print(f"Starting batch scoring job")
    print(f"Features path: {args.features_path}")
    print(f"Scoring date: {scoring_date}")

    try:
        # Load features
        print("Loading features...")
        features_df = spark.read.parquet(args.features_path)
        record_count = features_df.count()
        print(f"Loaded {record_count} records")

        # Score PD model
        print("Scoring PD model...")
        scored_df = score_pd_model(spark, features_df, args.pd_model_path)

        # Score LGD model
        print("Scoring LGD model...")
        scored_df = score_lgd_model(spark, scored_df, args.lgd_model_path)

        # Calculate risk metrics
        print("Calculating risk metrics...")
        scored_df = calculate_risk_metrics(scored_df)

        # Validate scores
        print("Validating scores...")
        validate_scores(scored_df)

        # Save results
        print("Saving scores...")
        save_scores(scored_df, args.output_path, scoring_date)

        print(f"Batch scoring complete. Scored {record_count} records")

        # Summary stats
        print("\nScoring Summary:")
        scored_df.select(
            F.sum("expected_loss").alias("total_expected_loss"),
            F.sum("economic_capital").alias("total_economic_capital"),
            F.avg("pd_score").alias("avg_pd"),
            F.sum(F.when(F.col("risk_grade").isin(["CCC", "CC", "C", "D"]), 1).otherwise(0)).alias("high_risk_count")
        ).show()

    except Exception as e:
        print(f"Error in batch scoring: {e}")
        raise
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
