# MLflow Configuration Guide

This document explains how MLflow is configured to work seamlessly across local development and production (Cloudera ML) environments.

## Overview

The Credit Risk Platform uses environment-aware MLflow configuration that automatically adapts based on the `APP_ENV` environment variable:

- **Local Mode** (`APP_ENV=local`): Uses local filesystem (`./mlruns`)
- **Production Mode** (`APP_ENV=production`): Uses Cloudera MLflow server or CML filesystem

## Configuration Architecture

### 1. Configuration Files

MLflow settings are defined in YAML configuration files:

**`config/local.yaml`** (Local Development):
```yaml
mlflow:
  tracking_uri: "${MLFLOW_TRACKING_URI:-./mlruns}"
  experiment_name: "${MLFLOW_EXPERIMENT_NAME:-credit_risk_local}"
  registry_uri: null
```

**`config/production.yaml`** (Cloudera ML):
```yaml
mlflow:
  tracking_uri: "${MLFLOW_TRACKING_URI:-/home/cdsw/mlruns}"
  experiment_name: "${MLFLOW_EXPERIMENT_NAME:-credit_risk_production}"
  registry_uri: "${MLFLOW_REGISTRY_URI}"
  tracking_username: "${MLFLOW_TRACKING_USERNAME}"
  tracking_password: "${MLFLOW_TRACKING_PASSWORD}"
  tracking_token: "${MLFLOW_TRACKING_TOKEN}"
```

### 2. Environment Variables

All configuration values support environment variable override using the `${VAR_NAME:-default}` syntax.

## Local Development Setup

### Step 1: Copy Environment Template

```bash
cp .env.template .env
```

### Step 2: Configure for Local Development

The default settings in `config/local.yaml` work out of the box. No changes needed to `.env` unless you want to override defaults:

```bash
# .env file (optional overrides)
APP_ENV=local
# MLFLOW_TRACKING_URI=./mlruns  # Optional: override default
```

### Step 3: Install Dependencies

```bash
pip install mlflow python-dotenv
```

### Step 4: Use MLflow

```python
from config import settings

# Automatically configures MLflow based on APP_ENV
mlflow_info = settings.configure_mlflow()
print(f"MLflow configured: {mlflow_info}")

# Now use mlflow normally
import mlflow
mlflow.start_run()
# ... your code ...
mlflow.end_run()
```

## Production Setup (Cloudera ML)

### Option 1: Cloudera MLflow Server (Recommended)

When using Cloudera's managed MLflow service:

**Step 1: Set Environment Variables in Cloudera ML**

In your Cloudera ML project settings, set these environment variables:

```bash
APP_ENV=production
MLFLOW_TRACKING_URI=https://your-workspace.ml.cloudera.site/mlflow
MLFLOW_TRACKING_USERNAME=your_username
MLFLOW_TRACKING_PASSWORD=your_password
# OR use token authentication:
# MLFLOW_TRACKING_TOKEN=your_token
```

**Step 2: Deploy Application**

The application will automatically:
- Detect production environment
- Connect to Cloudera MLflow server
- Use authentication credentials
- Create experiments and register models remotely

### Option 2: CML Filesystem (Fallback)

If Cloudera MLflow server is not available:

```bash
APP_ENV=production
MLFLOW_TRACKING_URI=/home/cdsw/mlruns
```

This stores MLflow data on the CML filesystem instead of a remote server.

## Model Registration Script

The `3_models/register_models.py` script is environment-aware:

### Local Usage

```bash
# Uses local ./mlruns
python 3_models/register_models.py

# View MLflow UI
mlflow ui --backend-store-uri ./mlruns
# Open http://localhost:5000
```

### Production Usage

```bash
# Uses Cloudera MLflow (configured via environment variables)
APP_ENV=production python 3_models/register_models.py
```

The script will:
1. Detect the environment (local or production)
2. Load configuration from backend settings
3. Set up MLflow with appropriate tracking URI and authentication
4. Register models in the configured MLflow instance
5. Provide clear logging of configuration used

## Configuration Priority

Settings are applied in this order (highest priority first):

1. **Environment Variables** - Direct overrides (e.g., `MLFLOW_TRACKING_URI`)
2. **YAML Config Files** - Environment-specific files (`local.yaml`, `production.yaml`)
3. **Code Defaults** - Fallback defaults in `config.py`

## Backend Configuration API

The `5_backend/config.py` provides a helper method:

```python
from config import settings

# Configure MLflow (call once at startup)
mlflow_info = settings.configure_mlflow()
# Returns:
# {
#     "status": "configured",
#     "tracking_uri": "./mlruns",
#     "registry_uri": "./mlruns",
#     "experiment_name": "credit_risk_local",
#     "environment": "local"
# }
```

This method:
- Sets MLflow tracking URI
- Sets registry URI (if different)
- Configures authentication for remote servers
- Sets default experiment name
- Returns configuration info for logging

## Troubleshooting

### Issue: "MLflow not installed"

```bash
pip install mlflow
```

### Issue: "python-dotenv not installed"

For local development:
```bash
pip install python-dotenv
```

### Issue: "Authentication failed" (Production)

Verify Cloudera MLflow credentials:
1. Check `MLFLOW_TRACKING_USERNAME` and `MLFLOW_TRACKING_PASSWORD` are set
2. Or ensure `MLFLOW_TRACKING_TOKEN` is configured
3. Verify the tracking URI is correct

### Issue: "Cannot connect to MLflow server"

Production checklist:
1. Verify `MLFLOW_TRACKING_URI` is the correct Cloudera MLflow URL
2. Check network connectivity from CML to MLflow server
3. Verify SSL certificates if using HTTPS
4. Test with MLflow CLI: `mlflow experiments list`

### Issue: "Permission denied writing to /home/cdsw/mlruns"

Ensure the CML user has write permissions to the directory:
```bash
mkdir -p /home/cdsw/mlruns
chmod 755 /home/cdsw/mlruns
```

## Environment Detection

The system automatically detects Cloudera ML environment by checking for:
- `CDSW_PROJECT_URL`
- `CML_DOMAIN`
- `HADOOP_CONF_DIR`

If detected but `APP_ENV=local`, you'll see a warning suggesting to set `APP_ENV=production`.

## Best Practices

### Local Development

1. Use default settings (no changes to `.env` needed)
2. Use MLflow UI to view experiments: `mlflow ui`
3. Keep models in `./mlruns` (gitignored)
4. Test model registration locally before production deployment

### Production Deployment

1. Always set `APP_ENV=production` in Cloudera ML environment
2. Use Cloudera MLflow server (not filesystem) for better collaboration
3. Store credentials in GitHub Secrets (for CI/CD) or Cloudera ML secrets
4. Use separate experiment names per environment
5. Tag models with environment and version information

### Model Registry Workflow

1. **Development**: Train and register models locally
2. **Staging**: Promote models to "Staging" stage
3. **Testing**: Validate model performance
4. **Production**: Promote to "Production" stage via:
   ```bash
   python register_models.py --promote pd
   ```

## Integration Examples

### FastAPI Application

```python
from fastapi import FastAPI
from config import settings

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    # Configure MLflow on application startup
    mlflow_info = settings.configure_mlflow()
    print(f"MLflow configured: {mlflow_info}")

@app.get("/models/info")
async def get_mlflow_info():
    return {
        "tracking_uri": settings.mlflow_tracking_uri,
        "experiment": settings.mlflow_experiment_name,
        "environment": settings.app_env
    }
```

### Training Script

```python
from config import settings
import mlflow

# Configure MLflow
settings.configure_mlflow()

# Start run
with mlflow.start_run(run_name="pd_model_training"):
    # Training code
    model = train_model(X_train, y_train)

    # Log metrics
    mlflow.log_metric("accuracy", accuracy)
    mlflow.log_metric("auc", auc)

    # Log model
    mlflow.sklearn.log_model(model, "model")
```

## Security Considerations

### Credentials Management

1. **Never commit credentials** to version control
2. **Use environment variables** for all sensitive values
3. **GitHub Secrets**: Store production credentials in GitHub repository secrets
4. **Cloudera Secrets**: Use CML's secret management for production deployments

### Network Security

1. **Use HTTPS** for Cloudera MLflow server URLs
2. **Verify SSL certificates** in production
3. **Use VPN/private network** for MLflow server access if required
4. **Rotate credentials** regularly

## References

- [MLflow Documentation](https://mlflow.org/docs/latest/index.html)
- [Cloudera ML Documentation](https://docs.cloudera.com/machine-learning/)
- [MLflow Authentication](https://mlflow.org/docs/latest/auth/index.html)
- Project Configuration: `config/README.md`
