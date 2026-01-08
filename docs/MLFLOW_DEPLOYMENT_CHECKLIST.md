# MLflow Configuration Deployment Checklist

Use this checklist to ensure MLflow is properly configured for your environment.

## Local Development Setup

### Prerequisites
- [ ] Python 3.8+ installed
- [ ] Project cloned and virtual environment set up
- [ ] Dependencies installed: `pip install -r requirements.txt`

### Configuration
- [ ] MLflow installed: `pip install mlflow`
- [ ] python-dotenv installed: `pip install python-dotenv` (optional)
- [ ] `.env` file created (optional - default config works without it)
- [ ] `APP_ENV` set to `local` or left unset (defaults to `local`)

### Testing
- [ ] Run configuration test: `python scripts/test_mlflow_config.py`
- [ ] Verify output shows:
  - `Environment: local`
  - `Tracking URI: ./mlruns`
  - `Status: configured`
- [ ] Run example: `python examples/mlflow_usage_example.py`

### Usage
- [ ] Register models: `python 3_models/register_models.py`
- [ ] Verify `./mlruns` directory created
- [ ] Start MLflow UI: `mlflow ui --backend-store-uri ./mlruns`
- [ ] Open browser to `http://localhost:5000`
- [ ] Verify experiments and models appear in UI

### Verification
- [ ] Can create MLflow runs
- [ ] Can log metrics and parameters
- [ ] Can register models
- [ ] Can view runs in MLflow UI

---

## Production Deployment (Cloudera ML)

### Option A: Cloudera MLflow Server (Recommended)

#### Prerequisites
- [ ] Cloudera ML workspace provisioned
- [ ] MLflow server URL obtained from Cloudera admin
- [ ] Authentication credentials obtained (username/password or token)
- [ ] Network access from CML to MLflow server verified

#### Configuration in Cloudera ML
- [ ] Navigate to Project Settings → Environment Variables
- [ ] Set required variables:
  - [ ] `APP_ENV` = `production`
  - [ ] `MLFLOW_TRACKING_URI` = `https://your-workspace.ml.cloudera.site/mlflow`
  - [ ] `MLFLOW_TRACKING_USERNAME` = `your_username`
  - [ ] `MLFLOW_TRACKING_PASSWORD` = `your_password` (or use token)
- [ ] Optional variables:
  - [ ] `MLFLOW_TRACKING_TOKEN` (alternative to username/password)
  - [ ] `MLFLOW_EXPERIMENT_NAME` (custom experiment name)

#### Testing in CML
- [ ] Start a CML session
- [ ] Run configuration test: `python scripts/test_mlflow_config.py`
- [ ] Verify output shows:
  - `Environment: production`
  - `Tracking URI: https://...` (your MLflow server)
  - `Authentication: basic` (or token)
  - `Status: configured`
- [ ] Test connectivity: `mlflow experiments list`

#### Deployment
- [ ] Deploy backend application
- [ ] Verify application starts without errors
- [ ] Check logs for MLflow configuration messages
- [ ] Register a test model: `python 3_models/register_models.py`
- [ ] Access Cloudera MLflow UI
- [ ] Verify experiment and model appear

#### Verification
- [ ] Application can connect to MLflow server
- [ ] Authentication succeeds
- [ ] Can create runs and log metrics
- [ ] Can register models
- [ ] Models visible in Cloudera MLflow UI

---

### Option B: CML Filesystem Storage (Fallback)

#### Prerequisites
- [ ] Cloudera ML workspace provisioned
- [ ] File storage permissions configured

#### Configuration in Cloudera ML
- [ ] Navigate to Project Settings → Environment Variables
- [ ] Set required variables:
  - [ ] `APP_ENV` = `production`
  - [ ] `MLFLOW_TRACKING_URI` = `/home/cdsw/mlruns`
- [ ] Verify directory permissions:
  ```bash
  mkdir -p /home/cdsw/mlruns
  chmod 755 /home/cdsw/mlruns
  ```

#### Testing
- [ ] Start a CML session
- [ ] Run configuration test: `python scripts/test_mlflow_config.py`
- [ ] Verify output shows:
  - `Environment: production`
  - `Tracking URI: /home/cdsw/mlruns`
  - `Using CML filesystem for MLflow`
  - `Status: configured`

#### Deployment
- [ ] Deploy backend application
- [ ] Register a test model
- [ ] Verify `/home/cdsw/mlruns` directory populated
- [ ] Check file permissions

#### Verification
- [ ] Can create runs and log metrics
- [ ] Can register models
- [ ] Files stored in `/home/cdsw/mlruns`

---

## CI/CD Pipeline Setup (GitHub Actions)

### GitHub Secrets Configuration
- [ ] Navigate to repository Settings → Secrets and variables → Actions
- [ ] Add production secrets:
  - [ ] `MLFLOW_TRACKING_URI` - Cloudera MLflow server URL
  - [ ] `MLFLOW_TRACKING_TOKEN` - Authentication token (recommended for CI/CD)
  - [ ] Or: `MLFLOW_TRACKING_USERNAME` and `MLFLOW_TRACKING_PASSWORD`

### Workflow Configuration
- [ ] Update `.github/workflows/deploy.yml` with environment variables:
  ```yaml
  env:
    APP_ENV: production
    MLFLOW_TRACKING_URI: ${{ secrets.MLFLOW_TRACKING_URI }}
    MLFLOW_TRACKING_TOKEN: ${{ secrets.MLFLOW_TRACKING_TOKEN }}
  ```

### Testing
- [ ] Trigger workflow manually or via push
- [ ] Check workflow logs for MLflow configuration
- [ ] Verify deployment succeeds
- [ ] Check models are registered in MLflow

### Verification
- [ ] CI/CD pipeline runs successfully
- [ ] Models registered automatically
- [ ] No authentication errors in logs

---

## Security Checklist

### Credentials Management
- [ ] No credentials hardcoded in code
- [ ] No credentials in version control (check `.gitignore`)
- [ ] `.env` file not committed (in `.gitignore`)
- [ ] `.env.template` provides guidance without secrets
- [ ] Cloudera ML environment variables use secrets/vault
- [ ] GitHub Secrets used for CI/CD credentials

### Network Security
- [ ] HTTPS used for Cloudera MLflow server URLs
- [ ] SSL certificate verification enabled (default)
- [ ] VPN/private network used if required
- [ ] Firewall rules allow CML → MLflow connectivity

### Access Control
- [ ] MLflow credentials have minimum required permissions
- [ ] Separate credentials for dev/staging/production
- [ ] Regular credential rotation policy in place
- [ ] Audit logging enabled on MLflow server

---

## Troubleshooting Checklist

### Configuration Issues
- [ ] Verify `APP_ENV` is set correctly
- [ ] Check all environment variables are set
- [ ] Run test script: `python scripts/test_mlflow_config.py`
- [ ] Check for typos in environment variable names
- [ ] Verify YAML config files exist and are valid

### Connection Issues
- [ ] Test network connectivity: `curl <mlflow_url>`
- [ ] Verify SSL certificates if using HTTPS
- [ ] Check firewall rules
- [ ] Test with MLflow CLI: `mlflow experiments list`
- [ ] Review application logs for errors

### Authentication Issues
- [ ] Verify credentials are correct
- [ ] Check credential format (username/password vs token)
- [ ] Ensure credentials are not expired
- [ ] Verify user has necessary permissions
- [ ] Check for special characters in credentials (may need escaping)

### Permission Issues
- [ ] Verify write permissions to MLflow storage
- [ ] Check file/directory ownership
- [ ] Verify user has permissions to create experiments
- [ ] Check user has permissions to register models

---

## Rollback Plan

If issues occur in production:

1. **Immediate Actions**
   - [ ] Switch back to filesystem storage:
     ```bash
     MLFLOW_TRACKING_URI=/home/cdsw/mlruns
     ```
   - [ ] Restart application
   - [ ] Verify application functions normally

2. **Investigation**
   - [ ] Review error logs
   - [ ] Run test script with debug logging
   - [ ] Contact Cloudera support if MLflow server issue
   - [ ] Check recent configuration changes

3. **Recovery**
   - [ ] Fix identified issues
   - [ ] Test in staging environment first
   - [ ] Re-deploy to production
   - [ ] Monitor for 24 hours

---

## Monitoring and Maintenance

### Regular Checks
- [ ] Weekly: Review MLflow storage usage
- [ ] Weekly: Check for failed runs or errors
- [ ] Monthly: Review and clean up old experiments
- [ ] Monthly: Verify credentials still valid
- [ ] Quarterly: Review and update documentation

### Alerts to Configure
- [ ] MLflow server downtime
- [ ] Authentication failures
- [ ] Storage quota exceeded
- [ ] Failed model registrations

### Metrics to Track
- [ ] Number of experiments created
- [ ] Number of models registered
- [ ] Storage usage trend
- [ ] API response times
- [ ] Error rates

---

## Documentation Review

- [ ] Read `docs/MLFLOW_QUICKSTART.md` for quick reference
- [ ] Read `docs/MLFLOW_CONFIGURATION.md` for detailed guide
- [ ] Review `docs/MLFLOW_IMPLEMENTATION_SUMMARY.md` for architecture
- [ ] Bookmark documentation for team reference

---

## Sign-off

### Local Development
- **Tested by**: ___________________
- **Date**: ___________________
- **Status**: Pass / Fail
- **Notes**: ___________________

### Production Deployment
- **Deployed by**: ___________________
- **Reviewed by**: ___________________
- **Date**: ___________________
- **Status**: Pass / Fail
- **Notes**: ___________________

---

## Additional Resources

- MLflow Documentation: https://mlflow.org/docs/latest/
- Cloudera ML Documentation: https://docs.cloudera.com/machine-learning/
- Project Documentation: `docs/MLFLOW_CONFIGURATION.md`
- Test Script: `python scripts/test_mlflow_config.py`
- Usage Examples: `python examples/mlflow_usage_example.py`

---

**Last Updated**: 2026-01-07
**Version**: 1.0
