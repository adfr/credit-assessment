#!/usr/bin/env python3
"""
Deploy CDE Jobs
Deploys Spark jobs to CDE when Iceberg mode is configured.
This script is called during AMP setup but only takes action if CDE is configured.
"""

import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
DATA_STORAGE_MODE = os.environ.get("DATA_STORAGE_MODE", "local").lower()
CDE_API_URL = os.environ.get("CDE_API_URL", "")
CDE_VIRTUAL_CLUSTER = os.environ.get("CDE_VIRTUAL_CLUSTER", "")


def is_cde_enabled() -> bool:
    """Check if CDE should be used (Iceberg mode + CDE configured)."""
    cde_configured = bool(CDE_API_URL and CDE_VIRTUAL_CLUSTER)
    iceberg_mode = DATA_STORAGE_MODE == "iceberg"
    return cde_configured and iceberg_mode


def main():
    """Deploy CDE jobs if configured."""
    print("\n" + "=" * 60)
    print("Credit Risk Platform - CDE Deployment")
    print("=" * 60)

    logger.info(f"Data storage mode: {DATA_STORAGE_MODE}")
    logger.info(f"CDE API URL: {CDE_API_URL or '(not set)'}")
    logger.info(f"CDE Virtual Cluster: {CDE_VIRTUAL_CLUSTER or '(not set)'}")

    if not is_cde_enabled():
        if DATA_STORAGE_MODE != "iceberg":
            logger.info("Skipping CDE deployment - DATA_STORAGE_MODE is not 'iceberg'")
        else:
            logger.info("Skipping CDE deployment - CDE_API_URL or CDE_VIRTUAL_CLUSTER not configured")
        logger.info("CDE deployment not required for current configuration")
        return 0

    logger.info("CDE is enabled - deploying Spark jobs...")

    # Add CDE jobs directory to path
    project_root = os.environ.get("PROJECT_ROOT", "/home/cdsw")
    sys.path.insert(0, os.path.join(project_root, "8_cde_jobs"))

    try:
        from cde_client import deploy_spark_jobs

        result = deploy_spark_jobs()

        if result.get("status") == "success":
            logger.info("CDE deployment successful!")
            logger.info(f"  Resource: {result.get('resource')}")
            logger.info(f"  Files uploaded: {len(result.get('files_uploaded', []))}")
            logger.info(f"  Jobs created: {result.get('jobs_created')}")
            return 0
        else:
            logger.error(f"CDE deployment failed: {result.get('error')}")
            return 1

    except ImportError as e:
        logger.error(f"Failed to import CDE client: {e}")
        return 1
    except Exception as e:
        logger.error(f"CDE deployment error: {e}")
        return 1


if __name__ == "__main__":
    main()
