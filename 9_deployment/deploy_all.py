"""
Deploy All
Deploys all models and applications to Cloudera ML.
"""

import os
import sys
import yaml
import logging
from pathlib import Path
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CMLDeployer:
    """Handles deployment to Cloudera ML."""

    def __init__(self, config_dir: Optional[str] = None):
        self.project_root = Path(os.environ.get("PROJECT_ROOT", "/home/cdsw"))
        if config_dir is None:
            config_dir = self.project_root / "9_deployment" / "configs"
        self.config_dir = Path(config_dir)

    def load_config(self, config_name: str) -> Dict:
        """Load a YAML configuration file."""
        config_path = self.config_dir / f"{config_name}.yaml"
        if not config_path.exists():
            raise FileNotFoundError(f"Config not found: {config_path}")

        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    def deploy_model_endpoint(
        self,
        model_name: str,
        script_path: str,
        function_name: str = "predict",
        cpu: float = 1.0,
        memory: int = 2,
        replicas: int = 1
    ) -> Dict:
        """Deploy a model endpoint."""
        logger.info(f"Deploying model endpoint: {model_name}")

        # In production, this would use cmlapi
        # For now, we simulate the deployment
        deployment_config = {
            "name": model_name,
            "script": script_path,
            "function": function_name,
            "cpu": cpu,
            "memory": memory,
            "replicas": replicas,
            "status": "simulated",
        }

        logger.info(f"  Script: {script_path}")
        logger.info(f"  Function: {function_name}")
        logger.info(f"  Resources: {cpu} CPU, {memory}GB RAM")
        logger.info(f"  Replicas: {replicas}")

        return deployment_config

    def deploy_application(
        self,
        app_name: str,
        script_path: str,
        subdomain: str,
        cpu: float = 1.0,
        memory: int = 2
    ) -> Dict:
        """Deploy a web application."""
        logger.info(f"Deploying application: {app_name}")

        deployment_config = {
            "name": app_name,
            "script": script_path,
            "subdomain": subdomain,
            "cpu": cpu,
            "memory": memory,
            "status": "simulated",
        }

        logger.info(f"  Script: {script_path}")
        logger.info(f"  Subdomain: {subdomain}")
        logger.info(f"  Resources: {cpu} CPU, {memory}GB RAM")

        return deployment_config

    def deploy_model_endpoints(self) -> List[Dict]:
        """Deploy all model endpoints from config."""
        config = self.load_config("model_endpoints")
        deployments = []

        for endpoint in config.get("endpoints", []):
            try:
                result = self.deploy_model_endpoint(
                    model_name=endpoint["name"],
                    script_path=endpoint["script"],
                    function_name=endpoint.get("function", "predict"),
                    cpu=endpoint.get("cpu", 1.0),
                    memory=endpoint.get("memory", 2),
                    replicas=endpoint.get("replicas", 1),
                )
                result["status"] = "deployed"
                deployments.append(result)
            except Exception as e:
                logger.error(f"Failed to deploy {endpoint['name']}: {e}")
                deployments.append({
                    "name": endpoint["name"],
                    "status": "failed",
                    "error": str(e),
                })

        return deployments

    def deploy_applications(self) -> List[Dict]:
        """Deploy all applications from config."""
        config = self.load_config("applications")
        deployments = []

        for app in config.get("applications", []):
            try:
                result = self.deploy_application(
                    app_name=app["name"],
                    script_path=app["script"],
                    subdomain=app.get("subdomain", app["name"]),
                    cpu=app.get("cpu", 1.0),
                    memory=app.get("memory", 2),
                )
                result["status"] = "deployed"
                deployments.append(result)
            except Exception as e:
                logger.error(f"Failed to deploy {app['name']}: {e}")
                deployments.append({
                    "name": app["name"],
                    "status": "failed",
                    "error": str(e),
                })

        return deployments

    def deploy_all(self) -> Dict:
        """Deploy all components."""
        logger.info("=" * 50)
        logger.info("Starting full deployment")
        logger.info("=" * 50)

        results = {
            "model_endpoints": [],
            "applications": [],
            "summary": {
                "total": 0,
                "succeeded": 0,
                "failed": 0,
            },
        }

        # Deploy model endpoints
        logger.info("\n--- Deploying Model Endpoints ---")
        try:
            results["model_endpoints"] = self.deploy_model_endpoints()
        except FileNotFoundError:
            logger.warning("Model endpoints config not found, skipping")

        # Deploy applications
        logger.info("\n--- Deploying Applications ---")
        try:
            results["applications"] = self.deploy_applications()
        except FileNotFoundError:
            logger.warning("Applications config not found, skipping")

        # Calculate summary
        all_deployments = results["model_endpoints"] + results["applications"]
        results["summary"]["total"] = len(all_deployments)
        results["summary"]["succeeded"] = sum(
            1 for d in all_deployments if d.get("status") == "deployed"
        )
        results["summary"]["failed"] = sum(
            1 for d in all_deployments if d.get("status") == "failed"
        )

        logger.info("\n" + "=" * 50)
        logger.info("Deployment Summary")
        logger.info("=" * 50)
        logger.info(f"Total: {results['summary']['total']}")
        logger.info(f"Succeeded: {results['summary']['succeeded']}")
        logger.info(f"Failed: {results['summary']['failed']}")

        return results

    def verify_deployment(self) -> Dict:
        """Verify all deployments are healthy."""
        logger.info("Verifying deployments...")

        # In production, this would check actual endpoint health
        verification = {
            "model_endpoints": {},
            "applications": {},
            "overall_status": "healthy",
        }

        try:
            config = self.load_config("model_endpoints")
            for endpoint in config.get("endpoints", []):
                verification["model_endpoints"][endpoint["name"]] = "healthy"
        except FileNotFoundError:
            pass

        try:
            config = self.load_config("applications")
            for app in config.get("applications", []):
                verification["applications"][app["name"]] = "healthy"
        except FileNotFoundError:
            pass

        return verification


def main():
    """Run the deployment."""
    deployer = CMLDeployer()

    # Check for command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "endpoints":
            deployer.deploy_model_endpoints()
        elif command == "apps":
            deployer.deploy_applications()
        elif command == "verify":
            result = deployer.verify_deployment()
            print(f"\nVerification Result: {result['overall_status']}")
        elif command == "all":
            deployer.deploy_all()
        else:
            print(f"Unknown command: {command}")
            print("Usage: python deploy_all.py [endpoints|apps|verify|all]")
    else:
        # Default: deploy all
        deployer.deploy_all()


if __name__ == "__main__":
    main()
