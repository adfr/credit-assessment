#!/usr/bin/env python3
"""
Load Data to Iceberg Tables
Loads synthetic data into Apache Iceberg tables using PySpark.

Prerequisites:
1. CML Session with Spark enabled (Runtime with Spark)
2. Access to CDP Data Lake with Iceberg support
3. Environment variables configured (see below)

Environment Variables:
- SPARK_ICEBERG_CATALOG: Catalog name (default: spark_catalog)
- SPARK_ICEBERG_DATABASE: Database name (default: credit_risk)
- SPARK_WAREHOUSE_DIR: Warehouse directory (S3 or HDFS path)
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Get project root
PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", "/home/cdsw"))
DATA_DIR = PROJECT_ROOT / "data" / "synthetic"

# Iceberg configuration
ICEBERG_CATALOG = os.environ.get("SPARK_ICEBERG_CATALOG", "spark_catalog")
ICEBERG_DATABASE = os.environ.get("SPARK_ICEBERG_DATABASE", "credit_risk")
WAREHOUSE_DIR = os.environ.get("SPARK_WAREHOUSE_DIR", "s3a://your-bucket/warehouse")


def get_spark_session():
    """Create or get SparkSession with Iceberg support."""
    try:
        from pyspark.sql import SparkSession
    except ImportError:
        print("[ERROR] PySpark not available.")
        print("Please use a CML Runtime with Spark enabled.")
        sys.exit(1)

    # Check if we're in an existing Spark context (CML provides this)
    spark = SparkSession.builder \
        .appName("CreditRisk-IcebergLoader") \
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
        .config(f"spark.sql.catalog.{ICEBERG_CATALOG}", "org.apache.iceberg.spark.SparkCatalog") \
        .config(f"spark.sql.catalog.{ICEBERG_CATALOG}.type", "hive") \
        .config(f"spark.sql.catalog.{ICEBERG_CATALOG}.warehouse", WAREHOUSE_DIR) \
        .config("spark.sql.defaultCatalog", ICEBERG_CATALOG) \
        .enableHiveSupport() \
        .getOrCreate()

    return spark


def create_database(spark):
    """Create the Iceberg database if it doesn't exist."""
    print(f"\n[INFO] Creating database: {ICEBERG_DATABASE}")
    spark.sql(f"CREATE DATABASE IF NOT EXISTS {ICEBERG_DATABASE}")
    spark.sql(f"USE {ICEBERG_DATABASE}")
    print(f"  - Using database: {ICEBERG_DATABASE}")


def load_companies(spark):
    """Load companies data to Iceberg table."""
    print("\n[INFO] Loading companies to Iceberg...")

    # Read parquet file
    df = spark.read.parquet(str(DATA_DIR / "companies.parquet"))
    print(f"  - Read {df.count()} companies from parquet")

    # Add metadata columns
    df = df.withColumn("_loaded_at", spark.sql("SELECT current_timestamp()").first()[0])

    # Create Iceberg table
    table_name = f"{ICEBERG_DATABASE}.companies"

    # Drop if exists and create new
    spark.sql(f"DROP TABLE IF EXISTS {table_name}")

    df.writeTo(table_name) \
        .using("iceberg") \
        .tableProperty("format-version", "2") \
        .tableProperty("write.format.default", "parquet") \
        .partitionedBy("industry") \
        .create()

    print(f"  - Created Iceberg table: {table_name}")
    print(f"  - Partitioned by: industry")

    # Verify
    count = spark.sql(f"SELECT COUNT(*) FROM {table_name}").first()[0]
    print(f"  - Verified {count} records in table")

    return df


def load_loans(spark):
    """Load loans data to Iceberg table."""
    print("\n[INFO] Loading loans to Iceberg...")

    df = spark.read.parquet(str(DATA_DIR / "loans.parquet"))
    print(f"  - Read {df.count()} loans from parquet")

    # Convert date strings to date type
    from pyspark.sql.functions import to_date, current_timestamp, year

    df = df.withColumn("origination_date", to_date("origination_date"))
    df = df.withColumn("origination_year", year("origination_date"))
    df = df.withColumn("_loaded_at", current_timestamp())

    table_name = f"{ICEBERG_DATABASE}.loans"
    spark.sql(f"DROP TABLE IF EXISTS {table_name}")

    df.writeTo(table_name) \
        .using("iceberg") \
        .tableProperty("format-version", "2") \
        .tableProperty("write.format.default", "parquet") \
        .partitionedBy("origination_year", "loan_status") \
        .create()

    print(f"  - Created Iceberg table: {table_name}")
    print(f"  - Partitioned by: origination_year, loan_status")

    count = spark.sql(f"SELECT COUNT(*) FROM {table_name}").first()[0]
    print(f"  - Verified {count} records in table")

    return df


def load_bureau_data(spark):
    """Load bureau data to Iceberg table."""
    print("\n[INFO] Loading bureau data to Iceberg...")

    df = spark.read.parquet(str(DATA_DIR / "bureau_data.parquet"))
    print(f"  - Read {df.count()} bureau records from parquet")

    from pyspark.sql.functions import to_date, current_timestamp

    df = df.withColumn("report_date", to_date("report_date"))
    df = df.withColumn("_loaded_at", current_timestamp())

    table_name = f"{ICEBERG_DATABASE}.bureau_data"
    spark.sql(f"DROP TABLE IF EXISTS {table_name}")

    df.writeTo(table_name) \
        .using("iceberg") \
        .tableProperty("format-version", "2") \
        .create()

    print(f"  - Created Iceberg table: {table_name}")

    count = spark.sql(f"SELECT COUNT(*) FROM {table_name}").first()[0]
    print(f"  - Verified {count} records in table")

    return df


def load_payments(spark):
    """Load payment history to Iceberg table."""
    print("\n[INFO] Loading payment history to Iceberg...")

    df = spark.read.parquet(str(DATA_DIR / "payments.parquet"))
    print(f"  - Read {df.count()} payment records from parquet")

    from pyspark.sql.functions import to_date, current_timestamp, year, month

    df = df.withColumn("payment_date", to_date("payment_date"))
    df = df.withColumn("payment_year", year("payment_date"))
    df = df.withColumn("payment_month", month("payment_date"))
    df = df.withColumn("_loaded_at", current_timestamp())

    table_name = f"{ICEBERG_DATABASE}.payment_history"
    spark.sql(f"DROP TABLE IF EXISTS {table_name}")

    df.writeTo(table_name) \
        .using("iceberg") \
        .tableProperty("format-version", "2") \
        .tableProperty("write.format.default", "parquet") \
        .partitionedBy("payment_year", "payment_status") \
        .create()

    print(f"  - Created Iceberg table: {table_name}")
    print(f"  - Partitioned by: payment_year, payment_status")

    count = spark.sql(f"SELECT COUNT(*) FROM {table_name}").first()[0]
    print(f"  - Verified {count} records in table")

    return df


def show_table_info(spark):
    """Show information about created tables."""
    print("\n" + "=" * 60)
    print("Iceberg Tables Summary")
    print("=" * 60)

    tables = ["companies", "loans", "bureau_data", "payment_history"]

    for table in tables:
        table_name = f"{ICEBERG_DATABASE}.{table}"
        try:
            # Get record count
            count = spark.sql(f"SELECT COUNT(*) FROM {table_name}").first()[0]
            print(f"\n{table_name}:")
            print(f"  Records: {count:,}")

            # Show table history (Iceberg feature)
            print("  Snapshots:")
            history = spark.sql(f"SELECT * FROM {table_name}.history LIMIT 3")
            for row in history.collect():
                print(f"    - {row.made_current_at}: snapshot {row.snapshot_id}")

            # Show partitions
            print("  Partitions:")
            partitions = spark.sql(f"SELECT * FROM {table_name}.partitions LIMIT 5")
            for row in partitions.collect():
                print(f"    - {row.partition}: {row.record_count} records")

        except Exception as e:
            print(f"  Error reading table info: {e}")


def main():
    """Main function to load all data to Iceberg."""
    print("\n" + "=" * 60)
    print("Credit Risk Platform - Iceberg Data Loading")
    print("=" * 60)

    # Check for data files
    if not DATA_DIR.exists():
        print(f"\n[ERROR] Data directory not found: {DATA_DIR}")
        print("Please run 1_data/generate_synthetic.py first")
        return 1

    print(f"\nConfiguration:")
    print(f"  Catalog: {ICEBERG_CATALOG}")
    print(f"  Database: {ICEBERG_DATABASE}")
    print(f"  Warehouse: {WAREHOUSE_DIR}")
    print(f"  Data Source: {DATA_DIR}")

    # Get Spark session
    spark = get_spark_session()
    print(f"\nSpark Version: {spark.version}")

    try:
        # Create database
        create_database(spark)

        # Load all tables
        load_companies(spark)
        load_loans(spark)
        load_bureau_data(spark)
        load_payments(spark)

        # Show summary
        show_table_info(spark)

        print("\n" + "=" * 60)
        print("[SUCCESS] Data loaded to Iceberg tables!")
        print("=" * 60)

        print("\nIceberg Features Available:")
        print("  - Time travel: SELECT * FROM table FOR VERSION AS OF <snapshot_id>")
        print("  - History: SELECT * FROM table.history")
        print("  - Snapshots: SELECT * FROM table.snapshots")
        print("  - Schema evolution supported")

    except Exception as e:
        print(f"\n[ERROR] Failed to load data: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        spark.stop()

    return 0


if __name__ == "__main__":
    sys.exit(main())
