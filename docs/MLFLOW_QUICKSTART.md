# MLflow Quick Start Guide

Quick reference for using environment-aware MLflow configuration in the Credit Risk Platform.

## TL;DR

### Local Development

```bash
# 1. Install dependencies
pip install mlflow python-dotenv

# 2. Use in your code
from config import settings
settings.configure_mlflow()  # Done! MLflow is configured

# 3. Register models
python 3_models/register_models.py

# 4. View in UI
mlflow ui --backend-store-uri ./mlruns
```

### Production (Cloudera ML)

```bash
# 1. Set environment variables in Cloudera ML project settings
APP_ENV=production
MLFLOW_TRACKING_URI=https://your-workspace.ml.cloudera.site/mlflow
MLFLOW_TRACKING_USERNAME=your_username
MLFLOW_TRACKING_PASSWORD=your_password

# 2. Deploy and run - configuration is automatic
```

## Configuration Files

The system uses these configuration files:

| File | Purpose |
|------|---------|
| `.env.template` | Template for local `.env` file |
| `config/local.yaml` | Local development settings |
| `config/production.yaml` | Production (Cloudera ML) settings |
| `5_backend/config.py` | Backend configuration class |

## Environment Variable Reference

### Required

| Variable | Local Default | Production Default |
|----------|---------------|-------------------|
| `APP_ENV` | `local` | `production` |

### Optional (Override defaults)

| Variable | Description | Example |
|----------|-------------|---------|
| `MLFLOW_TRACKING_URI` | MLflow server URL | `https://mlflow.example.com/mlflow` |
| `MLFLOW_EXPERIMENT_NAME` | Experiment name | `credit_risk_custom` |
| `MLFLOW_TRACKING_USERNAME` | Username for auth | `your_username` |
| `MLFLOW_TRACKING_PASSWORD` | Password for auth | `your_password` |
| `MLFLOW_TRACKING_TOKEN` | Token for auth | `your_token` |
| `MLFLOW_REGISTRY_URI` | Separate registry URL | (optional) |

## Usage Examples

### Basic Configuration

```python
from config import settings

# Configure MLflow (call once at startup)
mlflow_info = settings.configure_mlflow()
print(f"MLflow configured: {mlflow_info}")

# Now use MLflow normally
import mlflow

with mlflow.start_run():
    mlflow.log_metric("accuracy", 0.95)
    mlflow.log_param("model_type", "random_forest")
```

### Training with MLflow

```python
from config import settings
import mlflow
import mlflow.sklearn

# Configure
settings.configure_mlflow()

# Train
with mlflow.start_run(run_name="pd_model_v1"):
    model = train_model(X_train, y_train)

    # Log metrics
    mlflow.log_metric("accuracy", accuracy)
    mlflow.log_metric("auc", auc)

    # Log model
    mlflow.sklearn.log_model(model, "model")
```

### Checking Environment

```python
from config import settings, is_production, is_local

if is_production():
    print(f"Running in production")
    print(f"MLflow URI: {settings.mlflow_tracking_uri}")
else:
    print(f"Running locally")
    print(f"MLflow URI: {settings.mlflow_tracking_uri}")
```

## Testing Configuration

Run the test script to verify your setup:

```bash
# Test local configuration
python scripts/test_mlflow_config.py

# Test production configuration
APP_ENV=production python scripts/test_mlflow_config.py

# Test with custom URI
MLFLOW_TRACKING_URI=http://custom-server/mlflow python scripts/test_mlflow_config.py
```

## Common Scenarios

### Scenario 1: Local Development (Default)

No configuration needed! Just use the defaults:

```bash
python 3_models/register_models.py
```

Models are saved to `./mlruns`.

### Scenario 2: Custom Local MLflow Server

Create `.env`:
```bash
MLFLOW_TRACKING_URI=http://localhost:5000
```

### Scenario 3: Cloudera MLflow Server

Set environment variables in Cloudera ML:
```bash
APP_ENV=production
MLFLOW_TRACKING_URI=https://workspace.ml.cloudera.site/mlflow
MLFLOW_TRACKING_USERNAME=username
MLFLOW_TRACKING_PASSWORD=password
```

### Scenario 4: CML Filesystem (No MLflow Server)

Set environment variables in Cloudera ML:
```bash
APP_ENV=production
MLFLOW_TRACKING_URI=/home/cdsw/mlruns
```

### Scenario 5: GitHub Actions / CI Pipeline

Use GitHub Secrets:

```yaml
# .github/workflows/deploy.yml
env:
  APP_ENV: production
  MLFLOW_TRACKING_URI: ${{ secrets.MLFLOW_TRACKING_URI }}
  MLFLOW_TRACKING_TOKEN: ${{ secrets.MLFLOW_TRACKING_TOKEN }}
```

## Troubleshooting

### Issue: MLflow not found

```bash
pip install mlflow
```

### Issue: Authentication failed

Check credentials are set correctly:
```bash
echo $MLFLOW_TRACKING_USERNAME
echo $MLFLOW_TRACKING_URI
```

### Issue: Cannot connect to server

Test connectivity:
```bash
mlflow experiments list
```

### Issue: Wrong environment detected

Force environment:
```bash
APP_ENV=production python your_script.py
```

## File Structure

```
credit-assessment/
├── .env.template          # Environment variable template
├── config/
│   ├── local.yaml         # Local configuration
│   ├── production.yaml    # Production configuration
│   └── config_loader.py   # Config loading logic
├── 5_backend/
│   └── config.py          # Backend settings (includes configure_mlflow())
├── 3_models/
│   └── register_models.py # Model registration (environment-aware)
├── docs/
│   ├── MLFLOW_CONFIGURATION.md  # Detailed documentation
│   └── MLFLOW_QUICKSTART.md     # This file
├── scripts/
│   └── test_mlflow_config.py    # Configuration test
└── examples/
    └── mlflow_usage_example.py  # Usage examples
```

## Next Steps

1. **Read Full Documentation**: See `docs/MLFLOW_CONFIGURATION.md`
2. **Run Tests**: `python scripts/test_mlflow_config.py`
3. **Try Examples**: `python examples/mlflow_usage_example.py`
4. **Register Models**: `python 3_models/register_models.py`

## Support

For issues or questions:
1. Check `docs/MLFLOW_CONFIGURATION.md` for detailed documentation
2. Run test script to diagnose issues
3. Check MLflow logs for errors

## Key Benefits

1. **Zero Configuration**: Works out of the box locally
2. **Environment Aware**: Automatically adapts to local/production
3. **Secure**: Supports authentication for production servers
4. **Flexible**: Override any setting via environment variables
5. **Testable**: Includes test scripts to verify configuration

## Architecture

```
Environment Variable (highest priority)
          ↓
YAML Config File (environment-specific)
          ↓
Code Defaults (fallback)
```

Each layer can override the previous one, giving you full control over configuration.
