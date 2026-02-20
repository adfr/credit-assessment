# Credit Risk Platform - Deployment Guide

This guide provides step-by-step instructions for deploying the Credit Risk Assessment Platform on Cloudera Machine Learning (CML).

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Project Setup](#project-setup)
3. [Environment Configuration](#environment-configuration)
4. [Initial Setup Tasks](#initial-setup-tasks)
5. [Model Training](#model-training)
6. [Deploy Model Endpoints](#deploy-model-endpoints)
7. [Deploy Applications](#deploy-applications)
8. [Setup Scheduled Jobs](#setup-scheduled-jobs)
9. [CDE Integration](#cde-integration)
10. [Verification](#verification)
11. [Monitoring](#monitoring)
12. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Access
- Cloudera ML workspace with appropriate permissions
- Ability to create Projects, Models, Applications, and Jobs
- (Optional) Cloudera Data Engineering (CDE) access for Spark jobs

### Required API Keys
- **Anthropic API Key**: Required for RAG/AI analyst features
- Obtain from: https://console.anthropic.com/

### Recommended Resources
| Component | CPU | Memory | Storage |
|-----------|-----|--------|---------|
| Session (Setup) | 2 | 4 GB | 10 GB |
| Model Endpoints | 1-2 | 2-4 GB | - |
| Backend API | 2 | 4 GB | - |
| Frontend | 1 | 2 GB | - |
| Spark Jobs | 4 | 8 GB | - |

---

## Project Setup

### Option 1: Deploy as AMP (Recommended)

If your CML workspace supports Applied ML Prototypes (AMPs):

1. Navigate to **AMPs** in the CML sidebar
2. Click **Add AMP** → **From Git Repository**
3. Enter your repository URL
4. CML will automatically read `.project-metadata.yaml` and configure:
   - Environment variables
   - Setup tasks
   - Model endpoints
   - Applications
   - Scheduled jobs

### Option 2: Create Project from Git

1. Go to **Projects** → **New Project**
2. Select **Git** as the source
3. Enter repository details:
   ```
   Repository URL: https://github.com/your-org/credit-assessment.git
   Branch: main
   ```
4. Click **Create Project**

### Option 3: Manual Upload

1. Create a new blank project
2. Upload all project files via the CML file browser
3. Ensure directory structure is preserved

---

## Environment Configuration

### Set Environment Variables

Navigate to **Project Settings** → **Advanced** → **Environment Variables**

Add the following variables:

| Variable | Value | Required |
|----------|-------|----------|
| `ANTHROPIC_API_KEY` | `your-api-key-here` | Yes |
| `DATABASE_PATH` | `data/credit_risk.db` | No (has default) |
| `VECTOR_STORE_PATH` | `data/vector_store` | No (has default) |
| `LOG_LEVEL` | `INFO` | No |
| `PORT` | `8000` | No (for backend) |

### Configure Runtime

1. Go to **Project Settings** → **Runtime**
2. Select:
   - **Editor**: Workbench or JupyterLab
   - **Kernel**: Python 3.10
   - **Edition**: Standard or above

---

## Initial Setup Tasks

Run these tasks in order using a CML Session or as Jobs.

### Step 1: Install Dependencies

```bash
# Start a session with 2 CPU, 4GB RAM
python 0_setup/install_dependencies.py
```

This installs all required Python packages from `requirements.txt`.

### Step 2: Create Database Tables

```bash
python 0_setup/create_tables.py
```

Creates 11 SQLite tables:
- `companies`, `loan_history`, `payment_history`
- `bureau_data`, `model_features`
- `applications`, `predictions`, `decisions`
- `workflow_state`, `analyst_notes`, `monitoring`

### Step 3: Setup Vector Store

```bash
python 0_setup/setup_vector_store.py
```

Initializes ChromaDB collections for RAG:
- `credit_policies`
- `regulatory_documents`
- `internal_guidelines`

### Step 4: Load Policy Documents

```bash
python 0_setup/load_policy_docs.py
```

Loads 8 policy documents into the vector store for AI analyst queries.

### Step 5: Generate Synthetic Data

```bash
python 1_data/generate_synthetic.py
```

Generates:
- 5,000 synthetic companies
- 10,000 loan records
- Payment histories
- Bureau data

### Step 6: Load Data to Database

```bash
python 1_data/load_to_iceberg.py
```

Loads generated CSV/Parquet files into the SQLite database.

---

## Model Training

### Train PD Model

```bash
python 3_models/train_pd_model.py
```

Trains Probability of Default model using:
- Logistic Regression
- Gradient Boosting
- XGBoost

Outputs:
- Model artifacts in `models/`
- MLflow experiment tracking
- Validation metrics (AUC, Gini, KS)

### Train LGD Model

```bash
python 3_models/train_lgd_model.py
```

Trains Loss Given Default regression model.

### Validate Models

```bash
python 3_models/validate_models.py
```

Runs validation suite:
- Discrimination tests
- Calibration tests
- Stability tests

---

## Deploy Model Endpoints

### Using CML UI

For each model, go to **Models** → **New Model**:

#### PD Model
| Setting | Value |
|---------|-------|
| Name | `pd-model` |
| Description | Probability of Default prediction |
| Script | `4_endpoints/serve_pd.py` |
| Function | `predict` |
| CPU | 1 |
| Memory | 2 GB |
| Replicas | 2 |

#### LGD Model
| Setting | Value |
|---------|-------|
| Name | `lgd-model` |
| Script | `4_endpoints/serve_lgd.py` |
| Function | `predict` |
| CPU | 1 |
| Memory | 2 GB |

#### Risk Engine
| Setting | Value |
|---------|-------|
| Name | `risk-engine` |
| Script | `4_endpoints/serve_risk_engine.py` |
| Function | `score` |
| CPU | 2 |
| Memory | 4 GB |

#### Document Processor
| Setting | Value |
|---------|-------|
| Name | `document-processor` |
| Script | `4_endpoints/serve_documents.py` |
| Function | `process` |
| CPU | 2 |
| Memory | 4 GB |

#### RAG Query
| Setting | Value |
|---------|-------|
| Name | `rag-query` |
| Script | `4_endpoints/serve_rag.py` |
| Function | `query` |
| CPU | 2 |
| Memory | 4 GB |

### Using Deployment Script

```bash
python 9_deployment/deploy_all.py endpoints
```

### Verify Endpoints

After deployment, test each endpoint:

```bash
# Get endpoint URL from CML Model details
curl -X POST https://<model-url>/predict \
  -H "Content-Type: application/json" \
  -d '{"debt_to_equity": 1.5, "current_ratio": 1.8}'
```

---

## Deploy Applications

### Backend API

1. Go to **Applications** → **New Application**
2. Configure:

| Setting | Value |
|---------|-------|
| Name | `credit-risk-api` |
| Subdomain | `credit-api` |
| Script | `5_backend/start.sh` |
| CPU | 2 |
| Memory | 4 GB |

3. Set environment variables:
   - `PORT=8000`
   - `DATABASE_PATH=data/credit_risk.db`

4. Click **Create Application**

### Frontend Application

1. **New Application**
2. Configure:

| Setting | Value |
|---------|-------|
| Name | `credit-risk-frontend` |
| Subdomain | `credit-app` |
| Script | `6_frontend/start.sh` |
| CPU | 1 |
| Memory | 2 GB |

3. Set environment variables:
   - `NODE_ENV=production`
   - `NEXT_PUBLIC_API_URL=https://credit-api.<your-cml-domain>`

4. Click **Create Application**

### Access URLs

After deployment, applications will be available at:
- **API**: `https://credit-api.<workspace>.<cml-domain>`
- **Frontend**: `https://credit-app.<workspace>.<cml-domain>`

### Important: Update Frontend API URL After First Deployment

The frontend's backend API URL (`NEXT_PUBLIC_API_URL`) is **baked into the build at compile time**. During the initial AMP deployment, the backend application has not been created yet, so the frontend is built with an incorrect or missing API URL. This means **the frontend will not be able to reach the backend after the first deployment**.

To fix this, you must update the API URL and rebuild the frontend:

#### Option A: Re-run the AMP

1. Go to your CML project
2. Note the backend application URL (found under **Applications** → `credit-risk-api` → copy the full URL)
3. Set the environment variable `NEXT_PUBLIC_API_URL` to the backend URL (e.g. `https://credit-api-xxxxx.ml-xxxx.your-domain.cloudera.site/api`) in **Project Settings** → **Environment Variables**
4. Re-run the AMP — this will re-trigger `0_setup/configure_frontend.py` and rebuild the frontend with the correct URL

#### Option B: Rebuild Manually via CML Session Console

1. Open a **Session** in your CML project (Python 3.10, 2 CPU / 4 GB)
2. Note the backend URL from **Applications** → `credit-risk-api`
3. Run the following commands in the session terminal:

```bash
# Load nvm and node
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"

# Set the correct backend API URL
export NEXT_PUBLIC_API_URL="https://credit-api-xxxxx.ml-xxxx.your-domain.cloudera.site/api"

# Write it to .env.local so the build picks it up
echo "NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL" > 6_frontend/.env.local

# Rebuild the frontend
cd 6_frontend
npm install --include=dev
npm run build
```

4. Restart the frontend application from **Applications** → `credit-risk-frontend` → **Restart**

---

## Setup Scheduled Jobs

### Daily Drift Detection

1. Go to **Jobs** → **New Job**
2. Configure:

| Setting | Value |
|---------|-------|
| Name | `daily-drift-detection` |
| Script | `7_monitoring/drift_detection.py` |
| Schedule | `0 6 * * *` (6 AM daily) |
| CPU | 2 |
| Memory | 4 GB |

### Daily Performance Tracking

| Setting | Value |
|---------|-------|
| Name | `daily-performance-tracking` |
| Script | `7_monitoring/performance_tracker.py` |
| Schedule | `0 7 * * *` (7 AM daily) |

### Weekly Model Retraining (Optional)

| Setting | Value |
|---------|-------|
| Name | `weekly-model-retraining` |
| Script | `3_models/train_pd_model.py` |
| Schedule | `0 0 * * 0` (Sunday midnight) |
| CPU | 4 |
| Memory | 8 GB |
| Timeout | 4 hours |

---

## CDE Integration

Cloudera Data Engineering (CDE) is used for running Spark jobs for feature engineering and batch scoring.

### Prerequisites for CDE

- Access to a CDE Virtual Cluster
- CDE CLI installed (optional but recommended)
- S3/ADLS/HDFS storage configured for data

### Method 1: CDE CLI (Recommended)

#### Step 1: Install and Configure CDE CLI

```bash
# Download CLI from your CDE virtual cluster
# Go to CDE UI → Virtual Cluster → CLI Tool → Download

# Make executable (Linux/Mac)
chmod +x cde

# Add to PATH
export PATH=$PATH:/path/to/cde

# Configure CLI
cde configure
# Enter when prompted:
#   - CDE API URL: https://<your-cde-cluster>.cloudera.site/dex/api/v1
#   - CDP Access Key ID: your-access-key
#   - CDP Private Key: your-private-key
```

#### Step 2: Create Resource and Upload Files

```bash
# Create a resource to store job files
cde resource create --name credit-risk-jobs

# Upload Spark job files
cde resource upload \
  --name credit-risk-jobs \
  --local-path 8_cde_jobs/spark_jobs/feature_engineering.py

cde resource upload \
  --name credit-risk-jobs \
  --local-path 8_cde_jobs/spark_jobs/batch_scoring.py

# Upload any additional files
cde resource upload \
  --name credit-risk-jobs \
  --local-path requirements.txt
```

#### Step 3: Create Python Environment (for dependencies)

```bash
# Create Python environment resource
cde resource create --name credit-risk-python-env --type python-env

# Upload requirements file
cde resource upload \
  --name credit-risk-python-env \
  --local-path requirements.txt
```

#### Step 4: Create Feature Engineering Job

```bash
cde job create \
  --name feature-engineering \
  --type spark \
  --mount-1-resource credit-risk-jobs \
  --python-env-resource-name credit-risk-python-env \
  --application-file feature_engineering.py \
  --arg "--input-path" --arg "s3a://your-bucket/data/raw" \
  --arg "--output-path" --arg "s3a://your-bucket/data/features" \
  --arg "--date" --arg "{{ds}}" \
  --conf "spark.sql.adaptive.enabled=true" \
  --conf "spark.sql.shuffle.partitions=200" \
  --driver-cores 2 \
  --driver-memory "4g" \
  --executor-cores 2 \
  --executor-memory "4g" \
  --num-executors 4
```

#### Step 5: Create Batch Scoring Job

```bash
cde job create \
  --name batch-scoring \
  --type spark \
  --mount-1-resource credit-risk-jobs \
  --python-env-resource-name credit-risk-python-env \
  --application-file batch_scoring.py \
  --arg "--features-path" --arg "s3a://your-bucket/data/features" \
  --arg "--pd-model-path" --arg "s3a://your-bucket/models/pd_model.pkl" \
  --arg "--lgd-model-path" --arg "s3a://your-bucket/models/lgd_model.pkl" \
  --arg "--output-path" --arg "s3a://your-bucket/data/scores" \
  --arg "--date" --arg "{{ds}}" \
  --conf "spark.sql.adaptive.enabled=true" \
  --driver-cores 2 \
  --driver-memory "4g" \
  --executor-cores 2 \
  --executor-memory "4g" \
  --num-executors 4
```

#### Step 6: Schedule Jobs

```bash
# Schedule feature engineering (1 AM daily)
cde job update \
  --name feature-engineering \
  --schedule "0 1 * * *"

# Schedule batch scoring (2 AM daily, after features)
cde job update \
  --name batch-scoring \
  --schedule "0 2 * * *"
```

#### Step 7: Run Jobs Manually (Testing)

```bash
# Trigger immediate run
cde job run --name feature-engineering

# Run with custom arguments
cde job run --name batch-scoring \
  --arg "--date" --arg "2024-01-15"

# Check job status
cde job list-runs --name feature-engineering

# View logs
cde run logs --id <run-id>
```

### Method 2: CDE UI

#### Step 1: Access CDE

1. Go to **Cloudera Data Platform (CDP)** console
2. Navigate to **Data Engineering**
3. Select your **Virtual Cluster**
4. Click **View Jobs**

#### Step 2: Create Resource

1. Click **Resources** in the left sidebar
2. Click **Create Resource**
3. Configure:
   - Name: `credit-risk-jobs`
   - Type: `Files`
4. Click **Create**
5. Click **Upload Files** and select:
   - `8_cde_jobs/spark_jobs/feature_engineering.py`
   - `8_cde_jobs/spark_jobs/batch_scoring.py`

#### Step 3: Create Job

1. Click **Jobs** → **Create Job**
2. Configure:

| Field | Feature Engineering | Batch Scoring |
|-------|---------------------|---------------|
| Job Type | Spark | Spark |
| Name | `feature-engineering` | `batch-scoring` |
| Application File | `feature_engineering.py` | `batch_scoring.py` |
| Resource | `credit-risk-jobs` | `credit-risk-jobs` |
| Arguments | `--input-path`, `s3a://...` | `--features-path`, `s3a://...` |
| Executors | 4 | 4 |
| Executor Cores | 2 | 2 |
| Executor Memory | 4 GB | 4 GB |
| Driver Cores | 2 | 2 |
| Driver Memory | 4 GB | 4 GB |

3. Click **Schedule** tab:
   - Enable scheduling
   - Cron Expression: `0 1 * * *` (for feature engineering)
4. Click **Create**

### Method 3: CDE API

```python
"""
CDE API Deployment Script
"""
import requests
import json

# Configuration
CDE_API_URL = "https://<your-cde-cluster>.cloudera.site/dex/api/v1"
CDP_ACCESS_KEY = "your-access-key"
CDP_PRIVATE_KEY = "your-private-key"

def get_token():
    """Get CDE access token."""
    # Implementation depends on your auth method
    pass

headers = {
    "Authorization": f"Bearer {get_token()}",
    "Content-Type": "application/json"
}

# Create Resource
resource_payload = {"name": "credit-risk-jobs"}
requests.post(
    f"{CDE_API_URL}/resources",
    headers=headers,
    json=resource_payload
)

# Upload File
with open("8_cde_jobs/spark_jobs/feature_engineering.py", "rb") as f:
    requests.put(
        f"{CDE_API_URL}/resources/credit-risk-jobs/feature_engineering.py",
        headers={"Authorization": f"Bearer {get_token()}"},
        data=f
    )

# Create Job
job_payload = {
    "name": "feature-engineering",
    "type": "spark",
    "mounts": [{"resourceName": "credit-risk-jobs"}],
    "spark": {
        "file": "feature_engineering.py",
        "args": [
            "--input-path", "s3a://bucket/data/raw",
            "--output-path", "s3a://bucket/data/features"
        ],
        "numExecutors": 4,
        "executorCores": 2,
        "executorMemory": "4g",
        "driverCores": 2,
        "driverMemory": "4g",
        "conf": {
            "spark.sql.adaptive.enabled": "true"
        }
    },
    "schedule": {
        "enabled": True,
        "cronExpression": "0 1 * * *"
    }
}
requests.post(
    f"{CDE_API_URL}/jobs",
    headers=headers,
    json=job_payload
)
```

### Airflow DAGs in CDE

CDE supports Apache Airflow for complex workflow orchestration.

#### Upload DAGs via CLI

```bash
# Upload credit workflow DAG (daily pipeline)
cde airflow upload-dag \
  --dag-file 8_cde_jobs/airflow_dags/credit_workflow_dag.py

# Upload retraining DAG (weekly pipeline)
cde airflow upload-dag \
  --dag-file 8_cde_jobs/airflow_dags/retraining_dag.py

# List DAGs
cde airflow list-dags

# Trigger DAG run
cde airflow trigger-dag --dag-id credit_workflow_daily
```

#### Upload DAGs via UI

1. In CDE, go to **Jobs** → **Airflow**
2. Click **Upload DAG**
3. Select `credit_workflow_dag.py`
4. The DAG appears in the Airflow UI

#### Access Airflow UI

1. In CDE Virtual Cluster page
2. Click **Airflow UI** button
3. View DAGs, trigger runs, monitor progress

### DAG Descriptions

| DAG | Schedule | Description |
|-----|----------|-------------|
| `credit_workflow_daily` | `0 2 * * *` | Daily pipeline: extract → validate → features → scoring → decisions |
| `model_retraining_weekly` | `0 0 * * 0` | Weekly: drift check → training → validation → deployment |

### Monitoring CDE Jobs

#### CLI Commands

```bash
# List all jobs
cde job list

# List runs for a job
cde job list-runs --name feature-engineering

# Get run details
cde run describe --id <run-id>

# View logs (stdout)
cde run logs --id <run-id>

# View error logs (stderr)
cde run logs --id <run-id> --type stderr

# Kill a running job
cde run kill --id <run-id>
```

#### UI Monitoring

1. Go to **Job Runs** in CDE
2. View:
   - Run status (Running, Succeeded, Failed)
   - Duration
   - Spark UI link
   - Logs

### Spark Configuration Reference

| Config | Value | Description |
|--------|-------|-------------|
| `spark.sql.adaptive.enabled` | `true` | Adaptive query execution |
| `spark.sql.shuffle.partitions` | `200` | Number of shuffle partitions |
| `spark.executor.memoryOverhead` | `1g` | Off-heap memory |
| `spark.dynamicAllocation.enabled` | `true` | Dynamic executor allocation |
| `spark.sql.parquet.compression.codec` | `snappy` | Parquet compression |

### Troubleshooting CDE Jobs

#### Job Fails to Start
```bash
# Check resource exists
cde resource describe --name credit-risk-jobs

# Verify files uploaded
cde resource list-files --name credit-risk-jobs
```

#### Out of Memory Errors
```bash
# Increase executor memory
cde job update --name batch-scoring \
  --executor-memory "8g" \
  --conf "spark.executor.memoryOverhead=2g"
```

#### Slow Performance
```bash
# Increase parallelism
cde job update --name feature-engineering \
  --num-executors 8 \
  --conf "spark.sql.shuffle.partitions=400"
```

#### Check Logs
```bash
# Get recent failed runs
cde job list-runs --name feature-engineering --filter "status=failed"

# View driver logs
cde run logs --id <run-id> --type driver
```

---

## Verification

### Health Checks

```bash
# Check API health
curl https://credit-api.<your-domain>/health

# Expected response:
# {"status": "healthy", "version": "1.0.0"}
```

### Test Application Flow

1. **Create Application**
```bash
curl -X POST https://credit-api.<your-domain>/applications \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Test Corp",
    "industry": "technology",
    "requested_amount": 1000000,
    "requested_term_months": 24,
    "purpose": "working_capital"
  }'
```

2. **Start Workflow**
```bash
curl -X POST https://credit-api.<your-domain>/workflow/start \
  -H "Content-Type: application/json" \
  -d '{
    "application_id": "<application-id-from-step-1>",
    "auto_approve": true
  }'
```

3. **Check Frontend**
   - Navigate to `https://credit-app.<your-domain>`
   - Verify dashboard loads
   - Check applications list
   - Test workflow visualization

### Model Endpoint Tests

```bash
# Test PD Model
curl -X POST https://<pd-model-url> \
  -H "Content-Type: application/json" \
  -d '{
    "debt_to_equity": 1.5,
    "current_ratio": 1.8,
    "credit_score_normalized": 0.75
  }'

# Expected response:
# {"pd_score": 0.045, "risk_grade": "BB", "status": "success"}
```

---

## Monitoring

### CML Monitoring Dashboard

1. Go to **Models** → Select model → **Monitoring**
2. View:
   - Request counts
   - Latency metrics
   - Error rates

### Application Logs

1. Go to **Applications** → Select app
2. Click **Logs** tab
3. Filter by time range or search

### Custom Monitoring

Access the monitoring page in the frontend:
- `https://credit-app.<your-domain>/monitoring`

Features:
- Model performance metrics (AUC, Gini, KS)
- Feature drift detection (PSI)
- System health status
- Alert history

---

## Troubleshooting

### Common Issues

#### 1. Dependencies Installation Fails

```bash
# Try installing with pip directly in session
!pip install -r requirements.txt --quiet

# Or install packages individually
!pip install fastapi uvicorn langraph
```

#### 2. Database Connection Error

```bash
# Ensure data directory exists
mkdir -p data

# Check database file permissions
ls -la data/credit_risk.db

# Recreate tables if needed
python 0_setup/create_tables.py
```

#### 3. Model Endpoint Returns 500 Error

- Check model logs in CML
- Verify model file exists: `ls models/`
- Ensure all dependencies are installed
- Check input feature format

#### 4. Frontend Can't Connect to API

- Verify `NEXT_PUBLIC_API_URL` environment variable
- Check CORS settings in backend
- Ensure API application is running

#### 5. Vector Store Errors

```bash
# Reinitialize vector store
rm -rf data/vector_store
python 0_setup/setup_vector_store.py
python 0_setup/load_policy_docs.py
```

### Getting Help

- Check CML documentation: https://docs.cloudera.com/machine-learning/
- Review application logs in CML UI
- Contact your CML administrator for workspace-specific issues

---

## Architecture Reference

```
┌─────────────────────────────────────────────────────────────────┐
│                         Users                                    │
│                           │                                      │
│                           ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Frontend (Next.js/React)                     │   │
│  │         https://credit-app.<domain>                       │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           │                                      │
│                           ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Backend API (FastAPI)                        │   │
│  │         https://credit-api.<domain>                       │   │
│  │  ┌─────────────┬─────────────┬─────────────────────────┐ │   │
│  │  │ /applications│ /workflow   │ /analyst    │ /decisions│ │   │
│  │  └─────────────┴─────────────┴─────────────────────────┘ │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           │                                      │
│           ┌───────────────┼───────────────┐                     │
│           ▼               ▼               ▼                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  PD Model   │  │  LGD Model  │  │ Risk Engine │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│           │               │               │                     │
│           └───────────────┼───────────────┘                     │
│                           ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Data Layer                             │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │   │
│  │  │   SQLite    │  │  ChromaDB   │  │   MLflow    │       │   │
│  │  │  (Iceberg)  │  │(Vector Store)│  │ (Tracking)  │       │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘       │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    CDE (Optional)                         │   │
│  │  ┌─────────────────────┐  ┌─────────────────────┐        │   │
│  │  │ Feature Engineering │  │   Batch Scoring     │        │   │
│  │  │    (Spark Job)      │  │    (Spark Job)      │        │   │
│  │  └─────────────────────┘  └─────────────────────┘        │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Quick Reference

### Key URLs (replace `<domain>` with your CML domain)

| Component | URL |
|-----------|-----|
| Frontend | `https://credit-app.<domain>` |
| Backend API | `https://credit-api.<domain>` |
| API Docs | `https://credit-api.<domain>/docs` |
| Health Check | `https://credit-api.<domain>/health` |

### Key Commands

```bash
# Setup
python 0_setup/install_dependencies.py
python 0_setup/create_tables.py

# Data
python 1_data/generate_synthetic.py

# Training
python 3_models/train_pd_model.py

# Deployment
python 9_deployment/deploy_all.py all

# Monitoring
python 7_monitoring/drift_detection.py
```

---

**Last Updated**: January 2024
**Version**: 1.0.0
