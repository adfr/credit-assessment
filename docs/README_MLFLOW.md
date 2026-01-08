# MLflow Environment-Aware Configuration - Documentation Index

Welcome to the MLflow configuration documentation for the Credit Risk Platform. This guide will help you set up and use MLflow in both local development and production (Cloudera ML) environments.

## Quick Links

### For Developers (Get Started Fast)
- **[Quick Start Guide](MLFLOW_QUICKSTART.md)** - Start here! Get up and running in 5 minutes
- **[Code Examples](MLFLOW_CODE_EXAMPLES.md)** - Copy-paste examples for common tasks
- **[Test Script](../scripts/test_mlflow_config.py)** - Verify your configuration

### For Understanding the System
- **[Complete Configuration Guide](MLFLOW_CONFIGURATION.md)** - Detailed explanation of all features
- **[Implementation Summary](MLFLOW_IMPLEMENTATION_SUMMARY.md)** - Architecture and design decisions

### For Deployment
- **[Deployment Checklist](MLFLOW_DEPLOYMENT_CHECKLIST.md)** - Step-by-step deployment guide

## What's New

The Credit Risk Platform now features **environment-aware MLflow configuration** that automatically adapts to your environment:

- **Local Development**: Works out of the box with local `./mlruns` directory
- **Production (Cloudera ML)**: Automatically connects to Cloudera MLflow server with authentication
- **Zero Configuration**: Default settings work for local development
- **Flexible**: Override any setting via environment variables

## Getting Started

### 1. Install Dependencies

```bash
pip install mlflow python-dotenv
```

### 2. Local Development (Zero Config!)

```python
from config import settings
import mlflow

# Configure MLflow
settings.configure_mlflow()

# Use MLflow normally
with mlflow.start_run():
    mlflow.log_metric("accuracy", 0.95)
```

### 3. Production (Cloudera ML)

Set environment variables in Cloudera ML project settings:

```bash
APP_ENV=production
MLFLOW_TRACKING_URI=https://your-workspace.ml.cloudera.site/mlflow
MLFLOW_TRACKING_USERNAME=your_username
MLFLOW_TRACKING_PASSWORD=your_password
```

That's it! The same code works in both environments.

## Documentation Structure

### Quick References

| Document | Purpose | When to Use |
|----------|---------|-------------|
| [Quick Start](MLFLOW_QUICKSTART.md) | Fast setup guide | Starting a new project |
| [Code Examples](MLFLOW_CODE_EXAMPLES.md) | Copy-paste code | Writing MLflow code |
| [Deployment Checklist](MLFLOW_DEPLOYMENT_CHECKLIST.md) | Step-by-step deployment | Deploying to production |

### Detailed Guides

| Document | Purpose | When to Use |
|----------|---------|-------------|
| [Configuration Guide](MLFLOW_CONFIGURATION.md) | Complete reference | Understanding all options |
| [Implementation Summary](MLFLOW_IMPLEMENTATION_SUMMARY.md) | Architecture details | Understanding how it works |

### Tools and Scripts

| Tool | Purpose | Usage |
|------|---------|-------|
| [Test Script](../scripts/test_mlflow_config.py) | Verify configuration | `python scripts/test_mlflow_config.py` |
| [Usage Examples](../examples/mlflow_usage_example.py) | Interactive examples | `python examples/mlflow_usage_example.py` |
| [Register Models](../3_models/register_models.py) | Register ML models | `python 3_models/register_models.py` |

## Key Features

### 1. Environment-Aware Configuration

The system automatically detects your environment and configures MLflow accordingly:

```python
# Automatic detection based on APP_ENV
from config import is_production, is_local

if is_production():
    # Uses Cloudera MLflow server
    # Applies authentication
    # Uses production experiment names
    pass
else:
    # Uses local ./mlruns directory
    # No authentication needed
    # Uses local experiment names
    pass
```

### 2. Configuration Hierarchy

Settings are applied in priority order:

```
Environment Variables (highest priority)
    ↓
YAML Config Files (environment-specific)
    ↓
Code Defaults (fallback)
```

This allows you to override any setting at any level.

### 3. Secure Credential Management

- No credentials in code
- Environment variables for sensitive values
- Supports both username/password and token authentication
- GitHub Secrets integration for CI/CD

### 4. Graceful Fallbacks

If MLflow is unavailable, the system:
- Logs a warning
- Falls back to local file storage
- Continues operation without crashing
- Provides clear error messages

## Configuration Files

### Project Structure

```
credit-assessment/
├── config/
│   ├── local.yaml           # Local development settings
│   ├── production.yaml      # Production settings
│   └── config_loader.py     # Configuration loading logic
├── 5_backend/
│   └── config.py           # Backend settings (includes configure_mlflow())
├── 3_models/
│   └── register_models.py  # Model registration (environment-aware)
├── docs/
│   ├── README_MLFLOW.md    # This file
│   ├── MLFLOW_QUICKSTART.md
│   ├── MLFLOW_CONFIGURATION.md
│   ├── MLFLOW_CODE_EXAMPLES.md
│   ├── MLFLOW_IMPLEMENTATION_SUMMARY.md
│   └── MLFLOW_DEPLOYMENT_CHECKLIST.md
├── scripts/
│   └── test_mlflow_config.py
├── examples/
│   └── mlflow_usage_example.py
└── .env.template           # Environment variable template
```

### Key Configuration Files

1. **`.env.template`** - Template for local `.env` file
2. **`config/local.yaml`** - Local development configuration
3. **`config/production.yaml`** - Production (Cloudera ML) configuration
4. **`5_backend/config.py`** - Backend settings with `configure_mlflow()` method

## Common Tasks

### Task 1: Test Your Configuration

```bash
python scripts/test_mlflow_config.py
```

This will verify:
- Configuration loads correctly
- Environment is detected
- MLflow can connect
- All required files exist

### Task 2: View MLflow UI Locally

```bash
mlflow ui --backend-store-uri ./mlruns
# Open http://localhost:5000
```

### Task 3: Register a Model

```bash
# Local
python 3_models/register_models.py

# Production
APP_ENV=production python 3_models/register_models.py
```

### Task 4: Run Examples

```bash
python examples/mlflow_usage_example.py
```

This shows:
- Basic configuration
- Model training
- Model loading
- Production usage

### Task 5: Override Configuration

```bash
# Use custom MLflow server
MLFLOW_TRACKING_URI=http://custom-server/mlflow python your_script.py

# Use custom experiment name
MLFLOW_EXPERIMENT_NAME=my_experiment python your_script.py
```

## Environment Variables

### Required

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `local` | Environment: `local` or `production` |

### Optional (Override Defaults)

| Variable | Local Default | Production Default |
|----------|--------------|-------------------|
| `MLFLOW_TRACKING_URI` | `./mlruns` | `/home/cdsw/mlruns` |
| `MLFLOW_EXPERIMENT_NAME` | `credit_risk_local` | `credit_risk_production` |
| `MLFLOW_TRACKING_USERNAME` | - | - |
| `MLFLOW_TRACKING_PASSWORD` | - | - |
| `MLFLOW_TRACKING_TOKEN` | - | - |
| `MLFLOW_REGISTRY_URI` | - | - |

## Troubleshooting

### Issue: "MLflow not installed"

```bash
pip install mlflow
```

### Issue: "Configuration failed"

1. Check environment: `echo $APP_ENV`
2. Run test: `python scripts/test_mlflow_config.py`
3. Verify config files exist: `ls config/*.yaml`

### Issue: "Cannot connect to MLflow server"

1. Verify tracking URI: `echo $MLFLOW_TRACKING_URI`
2. Test connectivity: `curl $MLFLOW_TRACKING_URI`
3. Check credentials are set
4. Verify network access

### Issue: "Authentication failed"

1. Verify credentials: `echo $MLFLOW_TRACKING_USERNAME`
2. Check password/token is correct
3. Ensure user has necessary permissions
4. Try token authentication instead of username/password

### More Help

- See [Configuration Guide](MLFLOW_CONFIGURATION.md#troubleshooting) for detailed troubleshooting
- Run test script with verbose output
- Check application logs for errors

## Examples

### Example 1: Basic Usage

```python
from config import settings
import mlflow

# Configure (call once)
settings.configure_mlflow()

# Use MLflow
with mlflow.start_run():
    mlflow.log_metric("accuracy", 0.95)
```

### Example 2: Train and Register Model

```python
from config import settings
import mlflow
import mlflow.sklearn

settings.configure_mlflow()

with mlflow.start_run(run_name="pd_model_v1"):
    # Train model
    model = train_model(X_train, y_train)

    # Log metrics
    mlflow.log_metric("accuracy", accuracy)
    mlflow.log_metric("auc", auc)

    # Register model
    mlflow.sklearn.log_model(
        model,
        "model",
        registered_model_name="pd_model"
    )
```

### Example 3: Load Production Model

```python
from config import settings
import mlflow

settings.configure_mlflow()

# Load production model
model = mlflow.sklearn.load_model("models:/pd_model/Production")
predictions = model.predict(X_test)
```

For more examples, see [Code Examples](MLFLOW_CODE_EXAMPLES.md).

## Best Practices

### Local Development

1. Use default settings (no `.env` needed)
2. View experiments in MLflow UI
3. Test model registration locally first
4. Keep `./mlruns` in `.gitignore`

### Production Deployment

1. Set `APP_ENV=production` in Cloudera ML
2. Use Cloudera MLflow server (not filesystem)
3. Store credentials in secrets management
4. Use separate experiment names per environment
5. Monitor MLflow server health

### Code Integration

1. Call `settings.configure_mlflow()` once at startup
2. Use standard MLflow functions after configuration
3. Handle MLflow errors gracefully
4. Log meaningful metrics and parameters
5. Use model registry for production models

## Support

### Documentation

- **Questions about setup**: See [Quick Start](MLFLOW_QUICKSTART.md)
- **Questions about code**: See [Code Examples](MLFLOW_CODE_EXAMPLES.md)
- **Questions about deployment**: See [Deployment Checklist](MLFLOW_DEPLOYMENT_CHECKLIST.md)
- **Questions about internals**: See [Implementation Summary](MLFLOW_IMPLEMENTATION_SUMMARY.md)

### Tools

- **Test configuration**: `python scripts/test_mlflow_config.py`
- **See examples**: `python examples/mlflow_usage_example.py`
- **Register models**: `python 3_models/register_models.py`

### External Resources

- [MLflow Documentation](https://mlflow.org/docs/latest/)
- [Cloudera ML Documentation](https://docs.cloudera.com/machine-learning/)
- [MLflow Authentication](https://mlflow.org/docs/latest/auth/index.html)

## Contributing

When adding new MLflow functionality:

1. Follow the environment-aware pattern
2. Use `settings.configure_mlflow()` for configuration
3. Add examples to `examples/mlflow_usage_example.py`
4. Update relevant documentation
5. Test in both local and production environments

## Version History

- **v1.0** (2026-01-07): Initial environment-aware MLflow configuration
  - Environment detection (local/production)
  - Automatic Cloudera ML support
  - Configuration via YAML and environment variables
  - Comprehensive documentation and examples

---

## Quick Command Reference

```bash
# Test configuration
python scripts/test_mlflow_config.py

# Test with production config
APP_ENV=production python scripts/test_mlflow_config.py

# View MLflow UI
mlflow ui --backend-store-uri ./mlruns

# Register models
python 3_models/register_models.py

# Run examples
python examples/mlflow_usage_example.py

# Custom tracking URI
MLFLOW_TRACKING_URI=http://custom/mlflow python your_script.py
```

---

**Last Updated**: 2026-01-07
**Maintainer**: Credit Risk Platform Team
**Version**: 1.0

For the latest documentation, see the `docs/` directory in the project repository.
