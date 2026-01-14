#!/usr/bin/env python3
"""
Create CML Jobs
Creates scheduled jobs in Cloudera Machine Learning using the cmlapi.
Run this script after the project is set up to create monitoring and retraining jobs.
"""

import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_jobs():
    """Create scheduled jobs in CML."""
    try:
        import cmlapi
    except ImportError:
        logger.error("cmlapi not available. This script must run inside CML.")
        sys.exit(1)

    # Initialize CML client
    client = cmlapi.default_client()

    # Get project ID from environment
    project_id = os.environ.get("CDSW_PROJECT_ID")
    if not project_id:
        logger.error("CDSW_PROJECT_ID not set. This script must run inside a CML project.")
        sys.exit(1)

    logger.info(f"Creating jobs for project: {project_id}")

    # Job definitions
    jobs_to_create = [
        # Monitoring jobs
        {
            "name": "Daily Model Monitoring",
            "script": "7_monitoring/drift_detection.py",
            "schedule": "0 6 * * *",  # Daily at 6 AM
            "cpu": 2,
            "memory": 4,
            "timeout": 3600,
        },
        # Training jobs
        {
            "name": "Train PD Model",
            "script": "3_models/train_pd_model.py",
            "schedule": None,  # Manual trigger
            "cpu": 4,
            "memory": 8,
            "timeout": 7200,
        },
        {
            "name": "Train LGD Model",
            "script": "3_models/train_lgd_model.py",
            "schedule": None,  # Manual trigger
            "cpu": 4,
            "memory": 8,
            "timeout": 7200,
        },
        {
            "name": "Validate Models",
            "script": "3_models/validate_models.py",
            "schedule": None,  # Manual trigger
            "cpu": 2,
            "memory": 4,
            "timeout": 3600,
        },
        # Scheduled retraining
        {
            "name": "Weekly PD Model Retraining",
            "script": "3_models/train_pd_model.py",
            "schedule": "0 0 * * 0",  # Weekly on Sunday at midnight
            "cpu": 4,
            "memory": 8,
            "timeout": 7200,
        },
        {
            "name": "Weekly LGD Model Retraining",
            "script": "3_models/train_lgd_model.py",
            "schedule": "0 2 * * 0",  # Weekly on Sunday at 2 AM
            "cpu": 4,
            "memory": 8,
            "timeout": 7200,
        },
    ]

    created_jobs = []

    for job_def in jobs_to_create:
        try:
            # Check if job already exists
            existing_jobs = client.list_jobs(project_id=project_id)
            job_exists = any(j.name == job_def["name"] for j in existing_jobs.jobs)

            if job_exists:
                logger.info(f"Job '{job_def['name']}' already exists, skipping...")
                continue

            # Build job request parameters
            job_params = {
                "name": job_def["name"],
                "script": job_def["script"],
                "kernel": "python3",
                "cpu": job_def["cpu"],
                "memory": job_def["memory"],
                "timeout": job_def.get("timeout", 3600),
            }

            # Only add schedule for scheduled jobs (not manual)
            if job_def.get("schedule"):
                job_params["schedule"] = job_def["schedule"]

            job_body = cmlapi.CreateJobRequest(**job_params)

            # Create the job
            job = client.create_job(
                project_id=project_id,
                body=job_body,
            )

            job_type = "scheduled" if job_def.get("schedule") else "manual"
            logger.info(f"Created {job_type} job: {job.name} (ID: {job.id})")
            created_jobs.append({
                "name": job.name,
                "id": job.id,
                "schedule": job_def.get("schedule"),
                "type": job_type,
            })

        except cmlapi.rest.ApiException as e:
            logger.error(f"Failed to create job '{job_def['name']}': {e}")
        except Exception as e:
            logger.error(f"Unexpected error creating job '{job_def['name']}': {e}")

    return created_jobs


def list_jobs():
    """List all jobs in the project."""
    try:
        import cmlapi
    except ImportError:
        logger.error("cmlapi not available.")
        return []

    client = cmlapi.default_client()
    project_id = os.environ.get("CDSW_PROJECT_ID")

    if not project_id:
        logger.error("CDSW_PROJECT_ID not set.")
        return []

    jobs = client.list_jobs(project_id=project_id)

    logger.info(f"\nExisting jobs in project {project_id}:")
    for job in jobs.jobs:
        schedule = getattr(job, 'schedule', 'manual')
        logger.info(f"  - {job.name} (ID: {job.id}, Schedule: {schedule})")

    return jobs.jobs


def delete_job(job_name: str):
    """Delete a job by name."""
    try:
        import cmlapi
    except ImportError:
        logger.error("cmlapi not available.")
        return False

    client = cmlapi.default_client()
    project_id = os.environ.get("CDSW_PROJECT_ID")

    if not project_id:
        logger.error("CDSW_PROJECT_ID not set.")
        return False

    jobs = client.list_jobs(project_id=project_id)

    for job in jobs.jobs:
        if job.name == job_name:
            client.delete_job(project_id=project_id, job_id=job.id)
            logger.info(f"Deleted job: {job_name}")
            return True

    logger.warning(f"Job not found: {job_name}")
    return False


def run_job(job_name: str):
    """Run a job by name (trigger manual execution)."""
    try:
        import cmlapi
    except ImportError:
        logger.error("cmlapi not available.")
        return None

    client = cmlapi.default_client()
    project_id = os.environ.get("CDSW_PROJECT_ID")

    if not project_id:
        logger.error("CDSW_PROJECT_ID not set.")
        return None

    jobs = client.list_jobs(project_id=project_id)

    for job in jobs.jobs:
        if job.name == job_name:
            # Create a job run
            job_run = client.create_job_run(
                project_id=project_id,
                job_id=job.id,
                body=cmlapi.CreateJobRunRequest()
            )
            logger.info(f"Started job run: {job_name} (Run ID: {job_run.id})")
            return {
                "job_name": job_name,
                "job_id": job.id,
                "run_id": job_run.id,
                "status": job_run.status,
            }

    logger.warning(f"Job not found: {job_name}")
    return None


def get_job_run_status(job_name: str, run_id: str = None):
    """Get status of job runs."""
    try:
        import cmlapi
    except ImportError:
        logger.error("cmlapi not available.")
        return None

    client = cmlapi.default_client()
    project_id = os.environ.get("CDSW_PROJECT_ID")

    if not project_id:
        logger.error("CDSW_PROJECT_ID not set.")
        return None

    jobs = client.list_jobs(project_id=project_id)

    for job in jobs.jobs:
        if job.name == job_name:
            runs = client.list_job_runs(project_id=project_id, job_id=job.id)

            if run_id:
                # Get specific run
                for run in runs.job_runs:
                    if run.id == run_id:
                        return {
                            "job_name": job_name,
                            "run_id": run.id,
                            "status": run.status,
                            "started_at": run.started_at,
                            "finished_at": run.finished_at,
                        }
            else:
                # Get latest run
                if runs.job_runs:
                    latest = runs.job_runs[0]
                    return {
                        "job_name": job_name,
                        "run_id": latest.id,
                        "status": latest.status,
                        "started_at": latest.started_at,
                        "finished_at": latest.finished_at,
                    }

            return {"job_name": job_name, "message": "No runs found"}

    logger.warning(f"Job not found: {job_name}")
    return None


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "create":
            create_jobs()
        elif command == "list":
            list_jobs()
        elif command == "delete" and len(sys.argv) > 2:
            delete_job(sys.argv[2])
        elif command == "run" and len(sys.argv) > 2:
            job_name = " ".join(sys.argv[2:])
            result = run_job(job_name)
            if result:
                print(f"Job started: {result}")
        elif command == "status" and len(sys.argv) > 2:
            job_name = " ".join(sys.argv[2:])
            result = get_job_run_status(job_name)
            if result:
                print(f"Job status: {result}")
        else:
            print("Usage: python create_jobs.py <command> [args]")
            print("")
            print("Commands:")
            print("  create              Create all defined jobs")
            print("  list                List all jobs in project")
            print("  delete <job_name>   Delete a job by name")
            print("  run <job_name>      Run a job manually")
            print("  status <job_name>   Get status of latest job run")
            print("")
            print("Examples:")
            print("  python create_jobs.py create")
            print("  python create_jobs.py run \"Train PD Model\"")
            print("  python create_jobs.py status \"Train PD Model\"")
    else:
        # Default: create jobs
        logger.info("Creating CML jobs...")
        created = create_jobs()

        if created:
            logger.info(f"\nSuccessfully created {len(created)} job(s)")
        else:
            logger.info("\nNo new jobs created")

        # List all jobs
        list_jobs()
