#!/usr/bin/env python3
"""
CDE Client
Handles deployment and execution of Spark jobs on Cloudera Data Engineering.
Uses the official CDE CLI for authentication and API calls.
"""

import os
import sys
import json
import logging
import subprocess
import shutil
import time
import requests
from pathlib import Path
from typing import Optional, Dict, List, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", "/home/cdsw"))

# Find CDE CLI binary
CDE_CLI_PATH = shutil.which("cde-cli") or os.path.expanduser("~/.local/bin/cde-cli")

# Token cache
_token_cache = {"token": None, "expires_at": 0}


class CDEConfig:
    """CDE configuration from environment variables."""

    def __init__(self):
        self.api_url = os.environ.get("CDE_API_URL", "").rstrip("/")
        self.virtual_cluster = os.environ.get("CDE_VIRTUAL_CLUSTER", "")
        self.resource_name = os.environ.get("CDE_RESOURCE_NAME", "credit-risk-jobs")

        # Iceberg/Spark settings
        self.warehouse_dir = os.environ.get("SPARK_WAREHOUSE_DIR", "")
        self.iceberg_database = os.environ.get("SPARK_ICEBERG_DATABASE", "credit_risk")

    @property
    def has_cdp_credentials(self) -> bool:
        """Check if CDP credentials are available in environment."""
        return bool(
            os.environ.get("CDP_ACCESS_KEY_ID") and
            os.environ.get("CDP_PRIVATE_KEY")
        )

    @property
    def is_configured(self) -> bool:
        """Check if CDE is properly configured."""
        has_api = bool(self.api_url and self.virtual_cluster)
        has_cli = os.path.exists(CDE_CLI_PATH)
        return has_api and self.has_cdp_credentials and has_cli

    def __repr__(self):
        return f"CDEConfig(api_url={self.api_url}, vc={self.virtual_cluster}, has_credentials={self.has_cdp_credentials}, configured={self.is_configured})"


class CDEClient:
    """Client for interacting with CDE using token-based authentication."""

    def __init__(self, config: Optional[CDEConfig] = None):
        self.config = config or CDEConfig()
        self._token = None
        self._token_expires_at = 0

    def _get_cde_token(self) -> str:
        """Retrieve CDE access token using CDP credentials from environment variables."""
        global _token_cache

        # Check if we have a valid cached token
        current_time = time.time()
        if _token_cache["token"] and _token_cache["expires_at"] > current_time + 60:
            return _token_cache["token"]

        # Get CDP credentials from environment
        access_key = os.environ.get("CDP_ACCESS_KEY_ID")
        private_key = os.environ.get("CDP_PRIVATE_KEY")

        if not access_key or not private_key:
            raise RuntimeError(
                "CDP credentials not found in environment. "
                "Set CDP_ACCESS_KEY_ID and CDP_PRIVATE_KEY environment variables."
            )

        # Request token from CDE API
        token_url = f"{self.config.api_url}/gateway/authtkn/knoxtoken/api/v1/token"
        try:
            response = requests.get(
                token_url,
                auth=(access_key, private_key),
                timeout=30
            )
            response.raise_for_status()
            token_data = response.json()
            token = token_data.get("access_token")

            if not token:
                raise RuntimeError(f"No access_token in response: {token_data}")

            # Cache the token (default 1 hour expiry)
            expires_in = token_data.get("expires_in", 3600)
            _token_cache["token"] = token
            _token_cache["expires_at"] = current_time + expires_in

            logger.debug("Successfully retrieved CDE access token")
            return token

        except requests.RequestException as e:
            raise RuntimeError(f"Failed to retrieve CDE token: {e}")

    def _run_cde_cli(self, args: List[str], check: bool = True) -> subprocess.CompletedProcess:
        """Run a CDE CLI command with token-based authentication."""
        token = self._get_cde_token()

        cmd = [
            CDE_CLI_PATH,
            "--vcluster-endpoint", self.config.api_url,
            "--access-token", token,
        ] + args

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if check and result.returncode != 0:
            logger.error(f"CDE CLI error: {result.stderr}")
            raise RuntimeError(f"CDE CLI failed: {result.stderr}")

        return result

    def _parse_json_output(self, output: str) -> Any:
        """Parse JSON output from CDE CLI."""
        if not output.strip():
            return []
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return output

    # Resource Management
    def create_resource(self, name: str, resource_type: str = "files") -> Dict:
        """Create a CDE resource."""
        logger.info(f"Creating resource: {name}")
        result = self._run_cde_cli(["resource", "create", "--name", name, "--type", resource_type], check=False)
        if result.returncode != 0:
            if "already exists" in result.stderr.lower():
                logger.info(f"Resource {name} already exists")
                return {"name": name, "status": "exists"}
            raise RuntimeError(f"Failed to create resource: {result.stderr}")
        return {"name": name, "status": "created"}

    def get_resource(self, name: str) -> Optional[Dict]:
        """Get resource by name."""
        result = self._run_cde_cli(["resource", "describe", "--name", name], check=False)
        if result.returncode != 0:
            return None
        return self._parse_json_output(result.stdout)

    def ensure_resource(self, name: str) -> Dict:
        """Ensure resource exists, create if not."""
        resource = self.get_resource(name)
        if resource is None:
            resource = self.create_resource(name)
        return resource

    def upload_file(self, resource_name: str, file_path: Path, dest_name: str = None) -> Dict:
        """Upload a file to a CDE resource."""
        dest_name = dest_name or file_path.name
        logger.info(f"Uploading {file_path.name} to resource {resource_name}")

        result = self._run_cde_cli([
            "resource", "upload",
            "--name", resource_name,
            "--local-path", str(file_path),
            "--resource-path", dest_name
        ])
        return {"status": "uploaded", "file": dest_name}

    def upload_directory(self, resource_name: str, dir_path: Path, pattern: str = "*.py") -> List[Dict]:
        """Upload all matching files from a directory."""
        results = []
        for file_path in dir_path.glob(pattern):
            if file_path.is_file():
                result = self.upload_file(resource_name, file_path)
                results.append(result)
        return results

    # Job Management
    def create_job(
        self,
        name: str,
        script: str,
        resource_name: str,
        job_type: str = "spark",
        spark_config: Optional[Dict] = None,
        arguments: Optional[List[str]] = None,
        schedule: Optional[str] = None,
    ) -> Dict:
        """Create a CDE job."""
        logger.info(f"Creating job: {name}")

        # Build the CLI command
        cmd = [
            "job", "create",
            "--name", name,
            "--type", job_type,
            "--mount-1-resource", resource_name,
            "--application-file", script,
        ]

        # Add Spark config
        conf = spark_config or {
            "spark.executor.memory": "4g",
            "spark.executor.cores": "2",
            "spark.executor.instances": "2",
        }
        for key, value in conf.items():
            cmd.extend(["--conf", f"{key}={value}"])

        # Add arguments
        if arguments:
            cmd.extend(["--arg", " ".join(arguments)])

        result = self._run_cde_cli(cmd, check=False)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to create job: {result.stderr}")
        return {"name": name, "status": "created"}

    def get_job(self, name: str) -> Optional[Dict]:
        """Get job by name."""
        result = self._run_cde_cli(["job", "describe", "--name", name], check=False)
        if result.returncode != 0:
            return None
        return self._parse_json_output(result.stdout)

    def delete_job(self, name: str) -> bool:
        """Delete a job."""
        result = self._run_cde_cli(["job", "delete", "--name", name], check=False)
        if result.returncode != 0:
            if "not found" in result.stderr.lower():
                logger.warning(f"Job not found: {name}")
                return False
            raise RuntimeError(f"Failed to delete job: {result.stderr}")
        logger.info(f"Deleted job: {name}")
        return True

    def list_jobs(self) -> List[Dict]:
        """List all jobs."""
        result = self._run_cde_cli(["job", "list"])
        return self._parse_json_output(result.stdout)

    def run_job(self, name: str, arguments: Optional[List[str]] = None) -> Dict:
        """Run a job."""
        logger.info(f"Running job: {name}")
        cmd = ["job", "run", "--name", name]
        if arguments:
            cmd.extend(["--arg", " ".join(arguments)])

        result = self._run_cde_cli(cmd)
        return self._parse_json_output(result.stdout) if result.stdout.strip() else {"status": "submitted"}

    def get_job_runs(self, name: str, limit: int = 10) -> List[Dict]:
        """Get job run history."""
        result = self._run_cde_cli(["run", "list", "--filter", f"job[eq]{name}"])
        runs = self._parse_json_output(result.stdout)
        return runs[:limit] if isinstance(runs, list) else []

    def get_run_status(self, run_id: str) -> Dict:
        """Get status of a specific run."""
        result = self._run_cde_cli(["run", "describe", "--id", str(run_id)])
        return self._parse_json_output(result.stdout)


def is_cde_configured() -> bool:
    """Check if CDE is configured."""
    config = CDEConfig()
    return config.is_configured


def deploy_spark_jobs() -> Dict:
    """Deploy all Spark jobs to CDE."""
    config = CDEConfig()

    if not config.is_configured:
        logger.error("CDE is not configured. Set CDE_API_URL and CDE_VIRTUAL_CLUSTER.")
        return {"status": "error", "message": "CDE not configured"}

    client = CDEClient(config)

    results = {
        "resource": None,
        "files_uploaded": [],
        "jobs_created": [],
    }

    try:
        # Ensure resource exists
        resource = client.ensure_resource(config.resource_name)
        results["resource"] = config.resource_name

        # Upload Spark job files
        spark_jobs_dir = PROJECT_ROOT / "8_cde_jobs" / "spark_jobs"
        if spark_jobs_dir.exists():
            uploaded = client.upload_directory(config.resource_name, spark_jobs_dir)
            results["files_uploaded"].extend(uploaded)

        # Define jobs to create
        jobs_to_create = [
            {
                "name": "credit-risk-feature-engineering",
                "script": "feature_engineering.py",
                "arguments": [
                    "--input-path", f"{config.warehouse_dir}/raw",
                    "--output-path", f"{config.warehouse_dir}/features",
                ],
                "spark_config": {
                    "spark.executor.memory": "4g",
                    "spark.executor.cores": "2",
                    "spark.executor.instances": "4",
                },
            },
            {
                "name": "credit-risk-batch-scoring",
                "script": "batch_scoring.py",
                "arguments": [
                    "--features-path", f"{config.warehouse_dir}/features",
                    "--output-path", f"{config.warehouse_dir}/scores",
                ],
                "spark_config": {
                    "spark.executor.memory": "4g",
                    "spark.executor.cores": "2",
                    "spark.executor.instances": "4",
                },
            },
            {
                "name": "credit-risk-data-load",
                "script": "load_to_iceberg.py",
                "arguments": [
                    "--warehouse-dir", config.warehouse_dir,
                    "--database", config.iceberg_database,
                ],
                "spark_config": {
                    "spark.executor.memory": "2g",
                    "spark.executor.cores": "2",
                    "spark.executor.instances": "2",
                },
            },
        ]

        # Create jobs
        for job_def in jobs_to_create:
            # Delete existing job if present
            existing = client.get_job(job_def["name"])
            if existing:
                client.delete_job(job_def["name"])

            job = client.create_job(
                name=job_def["name"],
                script=job_def["script"],
                resource_name=config.resource_name,
                arguments=job_def.get("arguments"),
                spark_config=job_def.get("spark_config"),
            )
            results["jobs_created"].append(job_def["name"])

        logger.info(f"Deployed {len(results['jobs_created'])} jobs to CDE")
        results["status"] = "success"

    except Exception as e:
        logger.error(f"Failed to deploy to CDE: {e}")
        results["status"] = "error"
        results["error"] = str(e)

    return results


def run_spark_job(job_name: str, arguments: Optional[List[str]] = None) -> Dict:
    """Run a Spark job on CDE."""
    config = CDEConfig()

    if not config.is_configured:
        return {"status": "error", "message": "CDE not configured"}

    client = CDEClient(config)

    try:
        result = client.run_job(job_name, arguments)
        return {
            "status": "submitted",
            "job_name": job_name,
            "run_id": result.get("id"),
        }
    except Exception as e:
        return {
            "status": "error",
            "job_name": job_name,
            "error": str(e),
        }


def list_cde_jobs() -> List[Dict]:
    """List all CDE jobs."""
    config = CDEConfig()

    if not config.is_configured:
        logger.error("CDE is not configured")
        return []

    client = CDEClient(config)
    return client.list_jobs()


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python cde_client.py <command> [args]")
        print("")
        print("Commands:")
        print("  check          Check if CDE is configured")
        print("  deploy         Deploy all Spark jobs to CDE")
        print("  list           List all CDE jobs")
        print("  run <job>      Run a specific job")
        print("  status <job>   Get status of a job's recent runs")
        print("")
        print("Examples:")
        print("  python cde_client.py deploy")
        print("  python cde_client.py run credit-risk-feature-engineering")
        sys.exit(1)

    command = sys.argv[1]

    if command == "check":
        config = CDEConfig()
        access_key = os.environ.get("CDP_ACCESS_KEY_ID", "")
        private_key = os.environ.get("CDP_PRIVATE_KEY", "")
        print(f"CDE Configured: {config.is_configured}")
        print(f"  API URL: {config.api_url or '(not set)'}")
        print(f"  Virtual Cluster: {config.virtual_cluster or '(not set)'}")
        print(f"  CDP Access Key: {'***' + access_key[-4:] if access_key else '(not set)'}")
        print(f"  CDP Private Key: {'configured' if private_key else '(not set)'}")
        print(f"  Resource Name: {config.resource_name}")
        print(f"  Warehouse Dir: {config.warehouse_dir or '(not set)'}")

    elif command == "deploy":
        result = deploy_spark_jobs()
        print(json.dumps(result, indent=2))

    elif command == "list":
        jobs = list_cde_jobs()
        if jobs:
            print(f"Found {len(jobs)} jobs:")
            for job in jobs:
                print(f"  - {job.get('name')}: {job.get('type')}")
        else:
            print("No jobs found (or CDE not configured)")

    elif command == "run" and len(sys.argv) > 2:
        job_name = sys.argv[2]
        args = sys.argv[3:] if len(sys.argv) > 3 else None
        result = run_spark_job(job_name, args)
        print(json.dumps(result, indent=2))

    elif command == "status" and len(sys.argv) > 2:
        job_name = sys.argv[2]
        config = CDEConfig()
        if config.is_configured:
            client = CDEClient(config)
            runs = client.get_job_runs(job_name)
            print(f"Recent runs for {job_name}:")
            for run in runs[:5]:
                print(f"  - {run.get('id')}: {run.get('status')}")
        else:
            print("CDE not configured")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
