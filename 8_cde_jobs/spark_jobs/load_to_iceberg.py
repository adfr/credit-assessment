#!/usr/bin/env python3
"""
Load Data to S3 as Parquet (CML Native Spark)
Loads synthetic data directly to S3 as parquet files using PySpark.

Prerequisites:
1. CML Session with Spark enabled (Runtime with Spark)
2. Access to S3 bucket
3. Environment variables configured (see below)

Environment Variables:
- SPARK_WAREHOUSE_DIR: Output S3 path (default: s3a://your-bucket/data)
"""

import os
import sys
from pathlib import Path

# Get project root
PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", "/home/cdsw"))
DATA_DIR = PROJECT_ROOT / "data" / "synthetic"

# Configuration
OUTPUT_PATH = os.environ.get("SPARK_WAREHOUSE_DIR", "s3a://your-bucket/data")


def get_spark_session():
    """Create or get SparkSession in local mode."""
    try:
        from pyspark.sql import SparkSession
    except ImportError:
        print("[ERROR] PySpark not available.")
        print("Please use a CML Runtime with Spark enabled.")
        sys.exit(1)

    spark = SparkSession.builder \
        .appName("CreditRisk-DataLoader") \
        .master("local[*]") \
        .config("spark.driver.memory", "4g") \
        .getOrCreate()

    return spark


def load_companies(spark):
    """Load companies data to S3."""
    print("\n[INFO] Loading companies...")

    from pyspark.sql.functions import current_timestamp

    df = spark.read.parquet(str(DATA_DIR / "companies.parquet"))
    print(f"  - Read {df.count()} companies from parquet")

    df = df.withColumn("_loaded_at", current_timestamp())

    output_path = f"{OUTPUT_PATH}/companies"

    df.write \
        .mode("overwrite") \
        .format("parquet") \
        .partitionBy("industry") \
        .save(output_path)

    print(f"  - Saved to: {output_path}")
    print(f"  - Partitioned by: industry")

    # Verify by reading back
    count = spark.read.parquet(output_path).count()
    print(f"  - Verified {count} records")

    return df


def load_loans(spark):
    """Load loans data to S3."""
    print("\n[INFO] Loading loans...")

    from pyspark.sql.functions import to_date, current_timestamp, year

    df = spark.read.parquet(str(DATA_DIR / "loans.parquet"))
    print(f"  - Read {df.count()} loans from parquet")

    df = df.withColumn("origination_date", to_date("origination_date"))
    df = df.withColumn("origination_year", year("origination_date"))
    df = df.withColumn("_loaded_at", current_timestamp())

    output_path = f"{OUTPUT_PATH}/loans"

    df.write \
        .mode("overwrite") \
        .format("parquet") \
        .partitionBy("origination_year", "loan_status") \
        .save(output_path)

    print(f"  - Saved to: {output_path}")
    print(f"  - Partitioned by: origination_year, loan_status")

    count = spark.read.parquet(output_path).count()
    print(f"  - Verified {count} records")

    return df


def load_bureau_data(spark):
    """Load bureau data to S3."""
    print("\n[INFO] Loading bureau data...")

    from pyspark.sql.functions import to_date, current_timestamp

    df = spark.read.parquet(str(DATA_DIR / "bureau_data.parquet"))
    print(f"  - Read {df.count()} bureau records from parquet")

    df = df.withColumn("report_date", to_date("report_date"))
    df = df.withColumn("_loaded_at", current_timestamp())

    output_path = f"{OUTPUT_PATH}/bureau_data"

    df.write \
        .mode("overwrite") \
        .format("parquet") \
        .save(output_path)

    print(f"  - Saved to: {output_path}")

    count = spark.read.parquet(output_path).count()
    print(f"  - Verified {count} records")

    return df


def load_payments(spark):
    """Load payment history to S3."""
    print("\n[INFO] Loading payment history...")

    from pyspark.sql.functions import to_date, current_timestamp, year, month

    df = spark.read.parquet(str(DATA_DIR / "payments.parquet"))
    print(f"  - Read {df.count()} payment records from parquet")

    df = df.withColumn("payment_date", to_date("payment_date"))
    df = df.withColumn("payment_year", year("payment_date"))
    df = df.withColumn("payment_month", month("payment_date"))
    df = df.withColumn("_loaded_at", current_timestamp())

    output_path = f"{OUTPUT_PATH}/payment_history"

    df.write \
        .mode("overwrite") \
        .format("parquet") \
        .partitionBy("payment_year", "payment_status") \
        .save(output_path)

    print(f"  - Saved to: {output_path}")
    print(f"  - Partitioned by: payment_year, payment_status")

    count = spark.read.parquet(output_path).count()
    print(f"  - Verified {count} records")

    return df


def show_summary(spark):
    """Show summary of loaded data."""
    print("\n" + "=" * 60)
    print("Data Summary")
    print("=" * 60)

    tables = ["companies", "loans", "bureau_data", "payment_history"]

    for table in tables:
        path = f"{OUTPUT_PATH}/{table}"
        try:
            df = spark.read.parquet(path)
            count = df.count()
            print(f"\n{table}:")
            print(f"  Path: {path}")
            print(f"  Records: {count:,}")
            print(f"  Columns: {len(df.columns)}")
        except Exception as e:
            print(f"\n{table}: Error - {e}")


def main():
    """Main function to load all data."""
    print("\n" + "=" * 60)
    print("Credit Risk Platform - Data Loading to S3")
    print("=" * 60)

    # Check for data files
    if not DATA_DIR.exists():
        print(f"\n[ERROR] Data directory not found: {DATA_DIR}")
        print("Please run 1_data/generate_synthetic.py first")
        return 1

    print(f"\nConfiguration:")
    print(f"  Output Path: {OUTPUT_PATH}")
    print(f"  Data Source: {DATA_DIR}")

    # Get Spark session
    spark = get_spark_session()
    print(f"\nSpark Version: {spark.version}")

    try:
        # Load all tables
        load_companies(spark)
        load_loans(spark)
        load_bureau_data(spark)
        load_payments(spark)

        # Show summary
        show_summary(spark)

        print("\n" + "=" * 60)
        print("[SUCCESS] Data loaded to S3!")
        print("=" * 60)

        print(f"\nData available at: {OUTPUT_PATH}/")
        print("\nQuery examples:")
        print(f"  spark.read.parquet('{OUTPUT_PATH}/companies')")
        print(f"  spark.read.parquet('{OUTPUT_PATH}/loans')")

    except Exception as e:
        print(f"\n[ERROR] Failed to load data: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        spark.stop()

    return 0


if __name__ == "__main__":
    main()
