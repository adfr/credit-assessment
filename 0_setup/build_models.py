#!/usr/bin/env python3
"""
Build and Deploy CML Model Endpoints

This script builds and deploys the model endpoints that were created by the AMP.
Run this after the AMP creates the model definitions.

Usage:
    python 0_setup/build_models.py
"""

import os
import sys
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Model configurations matching .project-metadata.yaml
MODEL_CONFIGS = [
    {
        "entity_label": "pd_model",
        "name": "PD Model Endpoint",
        "script": "4_endpoints/cml_serve_pd.py",
        "function": "predict",
        "cpu": 2,
        "memory": 4,
    },
    {
        "entity_label": "lgd_model",
        "name": "LGD Model Endpoint",
        "script": "4_endpoints/cml_serve_lgd.py",
        "function": "predict",
        "cpu": 2,
        "memory": 4,
    },
    {
        "entity_label": "rag_query",
        "name": "RAG Query Endpoint",
        "script": "4_endpoints/serve_rag.py",
        "function": "query",
        "cpu": 2,
        "memory": 4,
    },
    {
        "entity_label": "regulatory_capital_model",
        "name": "Regulatory Capital Model Endpoint",
        "script": "4_endpoints/cml_serve_regulatory_capital.py",
        "function": "predict",
        "cpu": 2,
        "memory": 4,
    },
    {
        "entity_label": "var_model",
        "name": "VaR Model Endpoint",
        "script": "4_endpoints/cml_serve_var.py",
        "function": "predict",
        "cpu": 2,
        "memory": 4,
    },
]


def get_cml_client():
    """Get CML API client."""
    try:
        import cmlapi
        return cmlapi.default_client()
    except ImportError:
        logger.error("cmlapi not available. This script must run inside CML.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to initialize CML client: {e}")
        sys.exit(1)


def find_model_by_name(client, project_id: str, name: str):
    """Find a model by name in the project (supports partial matching, prefers latest version)."""
    try:
        models = client.list_models(project_id=project_id)
        matches = []
        for model in models.models:
            # Exact match or starts with (for versioned names like "PD Model Endpoint v2.1")
            if model.name == name or model.name.startswith(name):
                matches.append(model)

        if matches:
            # Sort by name descending to get highest version first (v3.1 > v2.1)
            matches.sort(key=lambda m: m.name, reverse=True)
            return matches[0]
    except Exception as e:
        logger.error(f"Error listing models: {e}")
    return None


def list_all_models(client, project_id: str):
    """List all models in the project."""
    try:
        models = client.list_models(project_id=project_id)
        logger.info(f"Available models in project:")
        for model in models.models:
            logger.info(f"  - {model.name} (ID: {model.id})")
        return models.models
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        return []


def get_available_runtime(client):
    """Get an available Python 3.10 runtime from CML."""
    try:
        runtimes = client.list_runtimes(search_filter='{"kernel": "Python 3.10"}')
        if runtimes.runtimes:
            # Prefer standard workbench runtime
            for rt in runtimes.runtimes:
                if 'workbench' in rt.image_identifier.lower() and 'standard' in rt.image_identifier.lower():
                    logger.info(f"Using runtime: {rt.image_identifier}")
                    return rt.image_identifier
            # Fall back to first available Python 3.10 runtime
            runtime = runtimes.runtimes[0].image_identifier
            logger.info(f"Using runtime: {runtime}")
            return runtime
    except Exception as e:
        logger.warning(f"Could not list runtimes: {e}")

    # Try without filter
    try:
        runtimes = client.list_runtimes()
        if runtimes.runtimes:
            for rt in runtimes.runtimes:
                if 'python3.10' in rt.image_identifier.lower() or 'python3.9' in rt.image_identifier.lower():
                    logger.info(f"Using runtime: {rt.image_identifier}")
                    return rt.image_identifier
            # Just use first available
            runtime = runtimes.runtimes[0].image_identifier
            logger.info(f"Using runtime: {runtime}")
            return runtime
    except Exception as e:
        logger.error(f"Could not list runtimes: {e}")

    return None


def create_model(client, project_id: str, model_config: dict):
    """Create a model with proper file path and function."""
    import cmlapi

    model_name = model_config["name"]
    logger.info(f"Creating model: {model_name}")

    try:
        model_request = cmlapi.CreateModelRequest(
            name=model_name,
            description=model_config.get("description", f"{model_name} endpoint"),
            disable_authentication=False,
        )

        model = client.create_model(
            project_id=project_id,
            body=model_request
        )

        logger.info(f"Model created: {model.id}")
        return model

    except Exception as e:
        logger.error(f"Failed to create model: {e}")
        return None


def delete_model(client, project_id: str, model_id: str):
    """Delete a model."""
    try:
        client.delete_model(project_id=project_id, model_id=model_id)
        logger.info(f"Deleted model: {model_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete model: {e}")
        return False


def build_and_deploy_model(client, project_id: str, model_config: dict):
    """Build and deploy a single model."""
    import cmlapi

    model_name = model_config["name"]
    logger.info(f"\n{'='*60}")
    logger.info(f"Processing: {model_name}")
    logger.info(f"{'='*60}")

    # Find the model
    model = find_model_by_name(client, project_id, model_name)

    if not model:
        logger.warning(f"Model '{model_name}' not found. It may not have been created by AMP yet.")
        return None

    logger.info(f"Found model: {model.name} (ID: {model.id})")

    # Check if model has builds - if it shows "N/A" source, existing builds may be incomplete
    # We'll create a new build with proper file_path and function_name

    # Check for existing builds
    try:
        builds = client.list_model_builds(project_id=project_id, model_id=model.id)
        active_build = None

        for build in builds.model_builds:
            if build.status in ["built", "building"]:
                # Check if this build has proper file_path
                has_file_path = hasattr(build, 'file_path') and build.file_path
                logger.info(f"Found existing build: {build.id} (status: {build.status}, file_path: {getattr(build, 'file_path', 'N/A')})")
                if has_file_path:
                    active_build = build
                    break

        if active_build and active_build.status == "built":
            logger.info("Using existing successful build with valid file path")
            build = active_build
        else:
            if builds.model_builds:
                logger.info("Existing builds have no file_path configured - creating new build")
            # Create new build with file path and function
            logger.info("Creating new model build...")
            logger.info(f"  Script: {model_config['script']}")
            logger.info(f"  Function: {model_config['function']}")

            # Get runtime from environment or discover available one
            runtime = os.environ.get("ML_RUNTIME_IDENTIFIER")
            if not runtime:
                runtime = get_available_runtime(client)

            if not runtime:
                logger.error("No runtime available. Set ML_RUNTIME_IDENTIFIER environment variable.")
                return None

            build_request = cmlapi.CreateModelBuildRequest(
                comment=f"Auto-build for {model_name}",
                file_path=model_config["script"],
                function_name=model_config["function"],
                runtime_identifier=runtime,
            )

            build = client.create_model_build(
                project_id=project_id,
                model_id=model.id,
                body=build_request
            )
            logger.info(f"Build created: {build.id}")

            # Wait for build to complete
            logger.info("Waiting for build to complete...")
            max_wait = 600  # 10 minutes
            wait_interval = 10
            elapsed = 0

            while elapsed < max_wait:
                build = client.get_model_build(
                    project_id=project_id,
                    model_id=model.id,
                    build_id=build.id
                )

                if build.status == "built":
                    logger.info(f"Build completed successfully!")
                    break
                elif build.status == "build failed":
                    logger.error(f"Build failed!")
                    return None
                else:
                    logger.info(f"Build status: {build.status} (waiting...)")
                    time.sleep(wait_interval)
                    elapsed += wait_interval

            if build.status != "built":
                logger.error(f"Build timed out after {max_wait} seconds")
                return None

    except Exception as e:
        logger.error(f"Error during build: {e}")
        return None

    # Check for existing deployments
    try:
        deployments = client.list_model_deployments(
            project_id=project_id,
            model_id=model.id,
            build_id=build.id
        )

        for deployment in deployments.model_deployments:
            if deployment.status in ["deployed", "deploying"]:
                logger.info(f"Found existing deployment: {deployment.id} (status: {deployment.status})")
                return {
                    "model_name": model_name,
                    "model_id": model.id,
                    "build_id": build.id,
                    "deployment_id": deployment.id,
                    "status": deployment.status,
                }

        # Create new deployment
        logger.info("Creating new deployment...")

        deployment_request = cmlapi.CreateModelDeploymentRequest(
            cpu=model_config.get("cpu", 2),
            memory=model_config.get("memory", 4),
        )

        deployment = client.create_model_deployment(
            project_id=project_id,
            model_id=model.id,
            build_id=build.id,
            body=deployment_request
        )

        logger.info(f"Deployment created: {deployment.id}")

        # Wait for deployment
        logger.info("Waiting for deployment...")
        max_wait = 300  # 5 minutes
        wait_interval = 10
        elapsed = 0

        while elapsed < max_wait:
            deployment = client.get_model_deployment(
                project_id=project_id,
                model_id=model.id,
                build_id=build.id,
                deployment_id=deployment.id
            )

            if deployment.status == "deployed":
                logger.info("Deployment successful!")
                break
            elif deployment.status in ["failed", "stopped"]:
                logger.error(f"Deployment failed with status: {deployment.status}")
                return None
            else:
                logger.info(f"Deployment status: {deployment.status} (waiting...)")
                time.sleep(wait_interval)
                elapsed += wait_interval

        return {
            "model_name": model_name,
            "model_id": model.id,
            "build_id": build.id,
            "deployment_id": deployment.id,
            "status": deployment.status,
        }

    except Exception as e:
        logger.error(f"Error during deployment: {e}")
        return None


def main():
    """Main function to build and deploy all models."""
    print("\n" + "=" * 60)
    print("CML Model Build and Deploy")
    print("=" * 60)

    # Get project ID
    project_id = os.environ.get("CDSW_PROJECT_ID")
    if not project_id:
        logger.error("CDSW_PROJECT_ID not set. This script must run inside a CML project.")
        sys.exit(1)

    logger.info(f"Project ID: {project_id}")

    # Get CML client
    client = get_cml_client()

    # List all available models first
    list_all_models(client, project_id)

    # Process each model
    results = []
    for config in MODEL_CONFIGS:
        result = build_and_deploy_model(client, project_id, config)
        if result:
            results.append(result)

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    if results:
        logger.info(f"Successfully deployed {len(results)} model(s):")
        for r in results:
            logger.info(f"  - {r['model_name']}: {r['status']}")
    else:
        logger.warning("No models were deployed. Check if models exist and try again.")

    return 0 if results else 1


def _is_interactive():
    """Check if running in an interactive environment (IPython/Jupyter)."""
    try:
        get_ipython()  # noqa: F821
        return True
    except NameError:
        return False


if __name__ == "__main__":
    result = main()
    if not _is_interactive():
        sys.exit(result)
