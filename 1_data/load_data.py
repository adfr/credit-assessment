#!/usr/bin/env python3
"""
Load Data - Unified Data Loading Script
Loads synthetic data based on DATA_STORAGE_MODE:
- local: SQLite database (runs in CML)
- iceberg: Iceberg tables via Spark (CDE if configured, else CML Spark)

Environment Variables:
- DATA_STORAGE_MODE: "local" (SQLite) or "iceberg" (Spark/Iceberg)
- SPARK_WAREHOUSE_DIR: Required for Iceberg mode - S3/ADLS warehouse path
- CDE_API_URL: If set with iceberg mode, uses CDE for Spark jobs
- CDE_VIRTUAL_CLUSTER: CDE virtual cluster name
"""

import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Get configuration from environment
DATA_STORAGE_MODE = os.environ.get("DATA_STORAGE_MODE", "local").lower()
CDE_API_URL = os.environ.get("CDE_API_URL", "")
CDE_VIRTUAL_CLUSTER = os.environ.get("CDE_VIRTUAL_CLUSTER", "")


def is_cde_configured() -> bool:
    """Check if CDE is configured."""
    return bool(CDE_API_URL and CDE_VIRTUAL_CLUSTER)


def load_to_sqlite():
    """Load data to SQLite database (local mode)."""
    logger.info("Loading data to SQLite (local mode)...")

    # Add 1_data directory to path for relative imports
    project_root = os.environ.get("PROJECT_ROOT", "/home/cdsw")
    data_dir = os.path.join(project_root, "1_data")
    if data_dir not in sys.path:
        sys.path.insert(0, data_dir)

    # Import and run the SQLite loader
    from load_to_iceberg import main as sqlite_main
    return sqlite_main()


def load_to_iceberg_cde():
    """Load data to Iceberg via CDE Spark job."""
    logger.info("Loading data to Iceberg via CDE...")

    # Check required environment variable
    warehouse_dir = os.environ.get("SPARK_WAREHOUSE_DIR", "")
    if not warehouse_dir:
        logger.error("SPARK_WAREHOUSE_DIR is required for Iceberg mode")
        return 1

    # Import CDE client and submit job
    sys.path.insert(0, str(os.path.join(os.environ.get("PROJECT_ROOT", "/home/cdsw"), "8_cde_jobs")))
    from cde_client import CDEClient, CDEConfig, deploy_spark_jobs, run_spark_job

    # First deploy jobs if not already deployed
    logger.info("Ensuring CDE jobs are deployed...")
    deploy_result = deploy_spark_jobs()

    if deploy_result.get("status") == "error":
        logger.error(f"Failed to deploy CDE jobs: {deploy_result.get('error')}")
        return 1

    # Run the data load job
    logger.info("Submitting data load job to CDE...")
    run_result = run_spark_job("credit-risk-data-load")

    if run_result.get("status") == "error":
        logger.error(f"Failed to run CDE job: {run_result.get('error')}")
        return 1

    logger.info(f"CDE job submitted. Run ID: {run_result.get('run_id')}")
    logger.info("Check job status with: python 8_cde_jobs/cde_client.py status credit-risk-data-load")

    return 0


def load_to_iceberg_cml():
    """Load data to Iceberg via CML Spark session."""
    logger.info("Loading data to Iceberg via CML Spark session...")

    # Check required environment variable
    warehouse_dir = os.environ.get("SPARK_WAREHOUSE_DIR", "")
    if not warehouse_dir:
        logger.error("SPARK_WAREHOUSE_DIR is required for Iceberg mode")
        logger.error("Set it to your S3/ADLS path, e.g., s3a://bucket/warehouse/credit_risk")
        return 1

    # Add 1_data directory to path for relative imports
    project_root = os.environ.get("PROJECT_ROOT", "/home/cdsw")
    data_dir = os.path.join(project_root, "1_data")
    if data_dir not in sys.path:
        sys.path.insert(0, data_dir)

    # Import and run the Iceberg loader
    from load_to_iceberg_spark import main as iceberg_main
    return iceberg_main()


def main():
    """Main entry point - choose loader based on configuration."""
    print("\n" + "=" * 60)
    print("Credit Risk Platform - Data Loading")
    print("=" * 60)

    logger.info(f"Data storage mode: {DATA_STORAGE_MODE}")
    logger.info(f"CDE configured: {is_cde_configured()}")

    if DATA_STORAGE_MODE == "local":
        # Local mode - always use SQLite
        return load_to_sqlite()

    elif DATA_STORAGE_MODE == "iceberg":
        # Iceberg mode - use CDE if configured, else CML Spark
        if is_cde_configured():
            logger.info("Using CDE for Spark job execution")
            return load_to_iceberg_cde()
        else:
            logger.info("Using CML Spark session (CDE not configured)")
            return load_to_iceberg_cml()

    else:
        logger.error(f"Unknown DATA_STORAGE_MODE: {DATA_STORAGE_MODE}")
        logger.error("Valid options: 'local' (SQLite) or 'iceberg' (Spark/Iceberg)")
        return 1


if __name__ == "__main__":
    main()
