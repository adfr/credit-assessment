#!/usr/bin/env python3
"""
CDE Client
Handles deployment and execution of Spark jobs on Cloudera Data Engineering.
"""

import os
import sys
import json
import logging
import requests
from pathlib import Path
from typing import Optional, Dict, List, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", "/home/cdsw"))


class CDEConfig:
    """CDE configuration from environment variables."""

    def __init__(self):
        self.api_url = os.environ.get("CDE_API_URL", "").rstrip("/")
        self.virtual_cluster = os.environ.get("CDE_VIRTUAL_CLUSTER", "")
        self.resource_name = os.environ.get("CDE_RESOURCE_NAME", "credit-risk-jobs")

        # CDP credentials for authentication
        self.cdp_access_key_id = os.environ.get("CDP_ACCESS_KEY_ID", "")
        self.cdp_private_key = os.environ.get("CDP_PRIVATE_KEY", "")

        # Iceberg/Spark settings
        self.warehouse_dir = os.environ.get("SPARK_WAREHOUSE_DIR", "")
        self.iceberg_database = os.environ.get("SPARK_ICEBERG_DATABASE", "credit_risk")

    @property
    def is_configured(self) -> bool:
        """Check if CDE is properly configured."""
        has_api = bool(self.api_url and self.virtual_cluster)
        has_auth = bool(self.cdp_access_key_id and self.cdp_private_key)
        return has_api and has_auth

    def __repr__(self):
        return f"CDEConfig(api_url={self.api_url}, vc={self.virtual_cluster}, has_credentials={bool(self.cdp_access_key_id)}, configured={self.is_configured})"


class CDEClient:
    """Client for interacting with CDE API."""

    def __init__(self, config: Optional[CDEConfig] = None):
        self.config = config or CDEConfig()
        self._session: Optional[requests.Session] = None
        self._access_token: Optional[str] = None

    @property
    def session(self) -> requests.Session:
        """Get or create authenticated session."""
        if self._session is None:
            self._session = requests.Session()

            # Get token using CDP credentials
            token = self._get_cde_token()
            if token:
                self._session.headers.update({
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                })
            else:
                logger.warning("No authentication token available")

        return self._session

    def _get_cde_token(self) -> Optional[str]:
        """Get CDE access token using CDP credentials."""
        if self._access_token:
            return self._access_token

        # Use CDP credentials to get CDE token
        if self.config.cdp_access_key_id and self.config.cdp_private_key:
            token = self._exchange_cdp_credentials_for_token()
            if token:
                self._access_token = token
                return token

        # Fallback: check for credentials file
        creds = self._load_cdp_credentials_file()
        if creds:
            self.config.cdp_access_key_id = creds.get("access_key_id", "")
            self.config.cdp_private_key = creds.get("private_key", "")
            token = self._exchange_cdp_credentials_for_token()
            if token:
                self._access_token = token
                return token

        return None

    def _load_cdp_credentials_file(self) -> Optional[Dict]:
        """Load CDP credentials from ~/.cdp/credentials file."""
        creds_file = Path.home() / ".cdp" / "credentials"
        if not creds_file.exists():
            return None

        try:
            import configparser
            config = configparser.ConfigParser()
            config.read(creds_file)
            if "default" in config:
                return {
                    "access_key_id": config["default"].get("cdp_access_key_id", ""),
                    "private_key": config["default"].get("cdp_private_key", ""),
                }
        except Exception as e:
            logger.warning(f"Could not read CDP credentials file: {e}")

        return None

    def _exchange_cdp_credentials_for_token(self) -> Optional[str]:
        """Exchange CDP credentials for a CDE access token."""
        if not self.config.cdp_access_key_id or not self.config.cdp_private_key:
            return None

        try:
            import base64
            import hashlib
            import hmac
            from datetime import datetime, timezone

            # CDE token endpoint (derived from API URL)
            # Format: https://<service>.cde-<id>.<region>.cloudera.site/dex/api/v1
            # Token endpoint: https://<service>.cde-<id>.<region>.cloudera.site/gateway/authtkn/knoxtoken/api/v1/token
            base_url = self.config.api_url.replace("/dex/api/v1", "")
            token_url = f"{base_url}/gateway/authtkn/knoxtoken/api/v1/token"

            # Create timestamp
            timestamp = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

            # Create string to sign
            method = "GET"
            path = "/gateway/authtkn/knoxtoken/api/v1/token"
            string_to_sign = f"{method}\n\napplication/json\n{timestamp}\n{path}"

            # Sign with private key (ED25519 or RSA depending on key type)
            private_key = self.config.cdp_private_key

            # Handle multi-line private key (may be passed as single line with \n)
            if "\\n" in private_key:
                private_key = private_key.replace("\\n", "\n")

            # Try to sign using cryptography library
            try:
                from cryptography.hazmat.primitives import serialization, hashes
                from cryptography.hazmat.primitives.asymmetric import ed25519, padding
                from cryptography.hazmat.backends import default_backend

                # Load the private key
                key_bytes = private_key.encode('utf-8')
                try:
                    # Try ED25519 first (newer CDP keys)
                    private_key_obj = serialization.load_pem_private_key(
                        key_bytes, password=None, backend=default_backend()
                    )
                    if isinstance(private_key_obj, ed25519.Ed25519PrivateKey):
                        signature = private_key_obj.sign(string_to_sign.encode('utf-8'))
                    else:
                        # RSA key
                        signature = private_key_obj.sign(
                            string_to_sign.encode('utf-8'),
                            padding.PKCS1v15(),
                            hashes.SHA256()
                        )
                except Exception:
                    # Fallback for raw ED25519 keys without PEM header
                    logger.warning("Could not load private key, trying alternative format")
                    return None

                signature_b64 = base64.standard_b64encode(signature).decode('utf-8')

            except ImportError:
                logger.error("cryptography library not installed. Run: pip install cryptography")
                return None

            # Make request to get token
            headers = {
                "Content-Type": "application/json",
                "Date": timestamp,
                "Authorization": f"ed25519 {self.config.cdp_access_key_id}:{signature_b64}",
            }

            response = requests.get(token_url, headers=headers, timeout=30)
            response.raise_for_status()

            token_data = response.json()
            return token_data.get("access_token")

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get CDE token: {e}")
            return None
        except Exception as e:
            logger.error(f"Error exchanging CDP credentials: {e}")
            return None

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """Make API request."""
        url = f"{self.config.api_url}/{endpoint.lstrip('/')}"

        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json() if response.content else {}
        except requests.exceptions.RequestException as e:
            logger.error(f"CDE API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise

    # Resource Management
    def create_resource(self, name: str, resource_type: str = "files") -> Dict:
        """Create a CDE resource."""
        logger.info(f"Creating resource: {name}")
        return self._request("POST", "resources", json={
            "name": name,
            "type": resource_type,
        })

    def get_resource(self, name: str) -> Optional[Dict]:
        """Get resource by name."""
        try:
            return self._request("GET", f"resources/{name}")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise

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

        with open(file_path, "rb") as f:
            # Use multipart form data for file upload
            files = {"file": (dest_name, f)}
            url = f"{self.config.api_url}/resources/{resource_name}/{dest_name}"

            response = self.session.put(url, files=files)
            response.raise_for_status()

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

        job_def = {
            "name": name,
            "type": job_type,
            "mounts": [{"resourceName": resource_name}],
            "spark": {
                "file": script,
                "conf": spark_config or {
                    "spark.executor.memory": "4g",
                    "spark.executor.cores": "2",
                    "spark.executor.instances": "2",
                },
            },
        }

        if arguments:
            job_def["spark"]["args"] = arguments

        if schedule:
            job_def["schedule"] = {
                "enabled": True,
                "cronExpression": schedule,
            }

        return self._request("POST", "jobs", json=job_def)

    def get_job(self, name: str) -> Optional[Dict]:
        """Get job by name."""
        try:
            return self._request("GET", f"jobs/{name}")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise

    def delete_job(self, name: str) -> bool:
        """Delete a job."""
        try:
            self._request("DELETE", f"jobs/{name}")
            logger.info(f"Deleted job: {name}")
            return True
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"Job not found: {name}")
                return False
            raise

    def list_jobs(self) -> List[Dict]:
        """List all jobs."""
        response = self._request("GET", "jobs")
        return response.get("jobs", [])

    def run_job(self, name: str, arguments: Optional[List[str]] = None) -> Dict:
        """Run a job."""
        logger.info(f"Running job: {name}")
        body = {}
        if arguments:
            body["overrides"] = {"spark": {"args": arguments}}

        return self._request("POST", f"jobs/{name}/run", json=body)

    def get_job_runs(self, name: str, limit: int = 10) -> List[Dict]:
        """Get job run history."""
        response = self._request("GET", f"jobs/{name}/runs", params={"limit": limit})
        return response.get("runs", [])

    def get_run_status(self, run_id: str) -> Dict:
        """Get status of a specific run."""
        return self._request("GET", f"job-runs/{run_id}")


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
        print(f"CDE Configured: {config.is_configured}")
        print(f"  API URL: {config.api_url or '(not set)'}")
        print(f"  Virtual Cluster: {config.virtual_cluster or '(not set)'}")
        print(f"  CDP Access Key: {'***' + config.cdp_access_key_id[-4:] if config.cdp_access_key_id else '(not set)'}")
        print(f"  CDP Private Key: {'configured' if config.cdp_private_key else '(not set)'}")
        print(f"  Resource Name: {config.resource_name}")
        print(f"  Warehouse Dir: {config.warehouse_dir or '(not set)'")

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
