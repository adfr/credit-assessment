# Credit Risk Platform Architecture

This document describes the data architecture, Spark jobs, and Iceberg integration for the Credit Risk Assessment Platform.

## Overview

The platform supports two operational modes:

| Mode | Storage | Processing | Use Case |
|------|---------|------------|----------|
| **Local** | SQLite + local Parquet | Pandas | Development, testing |
| **Iceberg/Spark** | S3 + Parquet | CDE Spark | Production |

Switch modes via environment variable:
```bash
export DATA_STORAGE_MODE=iceberg  # or "local"
```

---

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           DATA SOURCES                                   │
├─────────────────┬─────────────────┬─────────────────┬───────────────────┤
│   Companies     │   Loan History  │ Payment History │   Bureau Data     │
│   (5,000)       │   (10,000)      │   (~50,000)     │   (credit scores) │
└────────┬────────┴────────┬────────┴────────┬────────┴─────────┬─────────┘
         │                 │                 │                  │
         └─────────────────┼─────────────────┼──────────────────┘
                           ▼
              ┌────────────────────────┐
              │  Data Loading (Spark)  │
              │  load_to_iceberg.py    │
              └───────────┬────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        S3 DATA WAREHOUSE                                 │
│  s3a://<bucket>/data/                                                   │
├─────────────────┬─────────────────┬─────────────────┬───────────────────┤
│   /companies/   │  /loan_history/ │/payment_history/│   /bureau_data/   │
│  (by industry)  │ (by year/status)│ (by year/status)│   (unpartitioned) │
└────────┬────────┴────────┬────────┴────────┬────────┴─────────┬─────────┘
         │                 │                 │                  │
         └─────────────────┼─────────────────┼──────────────────┘
                           ▼
              ┌────────────────────────┐
              │ Feature Engineering    │
              │ (CDE Spark Job)        │
              │ Daily @ 1:00 AM        │
              └───────────┬────────────┘
                          ▼
              ┌────────────────────────┐
              │   s3a://.../features/  │
              │   (Parquet)            │
              └───────────┬────────────┘
                          │
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────────┐
│ PD Training │  │ LGD Training│  │ Batch Scoring   │
│ (CML)       │  │ (CML)       │  │ (CDE Spark)     │
└──────┬──────┘  └──────┬──────┘  │ Daily @ 2:00 AM │
       │                │         └────────┬────────┘
       ▼                ▼                  ▼
┌─────────────────────────┐    ┌────────────────────┐
│   s3a://.../models/     │    │  s3a://.../scores/ │
│   pd_model_latest.pkl   │    │  (by scoring_date) │
│   lgd_model_latest.pkl  │    └────────────────────┘
└─────────────────────────┘
```

---

## S3 Storage Layout

```
s3a://<bucket>/
├── data/
│   ├── companies/
│   │   ├── industry=technology/
│   │   ├── industry=healthcare/
│   │   ├── industry=manufacturing/
│   │   └── industry=retail/
│   │
│   ├── loan_history/
│   │   ├── origination_year=2024/loan_status=active/
│   │   ├── origination_year=2024/loan_status=defaulted/
│   │   └── origination_year=2023/...
│   │
│   ├── payment_history/
│   │   ├── payment_year=2024/payment_status=on_time/
│   │   ├── payment_year=2024/payment_status=late/
│   │   └── ...
│   │
│   ├── bureau_data/
│   │   └── *.parquet (unpartitioned)
│   │
│   ├── features/
│   │   └── part-*.snappy.parquet
│   │
│   └── scores/
│       ├── scoring_date=2024-01-27/
│       ├── scoring_date=2024-01-26/
│       └── ...
│
└── models/
    ├── pd/
    │   ├── pd_model_xgboost.pkl
    │   └── pd_model_latest.pkl
    └── lgd/
        └── lgd_model_latest.pkl
```

---

## Spark Jobs

### Job 1: Data Loading (`load_to_iceberg_spark.py`)

Loads raw data from synthetic sources to S3 with partitioning.

**Location:** `8_cde_jobs/spark_jobs/load_to_iceberg.py`

**Arguments:**
| Argument | Description | Example |
|----------|-------------|---------|
| `--output-path` | S3 warehouse path | `s3a://bucket/data/` |

**Partitioning Strategy:**
- `companies`: by `industry`
- `loan_history`: by `origination_year`, `loan_status`
- `payment_history`: by `payment_year`, `payment_status`
- `bureau_data`: none

---

### Job 2: Feature Engineering (`feature_engineering.py`)

Creates 23+ features from raw data tables.

**Location:** `8_cde_jobs/spark_jobs/feature_engineering.py`

**Arguments:**
| Argument | Description | Example |
|----------|-------------|---------|
| `--input-path` | Source data path | `s3a://bucket/data/` |
| `--output-path` | Feature output path | `s3a://bucket/data/features/` |
| `--date` | Processing date | `2024-01-27` |

**Spark Configuration:**
```python
spark.sql.adaptive.enabled = true
spark.sql.adaptive.coalescePartitions.enabled = true
spark.executor.memory = 4g
spark.executor.cores = 2
spark.executor.instances = 4
```

**Features Created:**

| Category | Features |
|----------|----------|
| **Financial Ratios** | debt_to_equity, debt_to_assets, ROA, ROE, profit_margin, current_ratio, quick_ratio |
| **Bureau** | credit_score_normalized, utilization_rate, derogatory_ratio, high_utilization_flag |
| **Behavioral** | avg_days_past_due, max_days_past_due, on_time_rate, count_30dpd, count_60dpd, count_90dpd |
| **Loan** | loan_to_value, term_years, remaining_term, loan_age_months |
| **Industry** | industry_default_rate, industry_risk_tier |

---

### Job 3: Batch Scoring (`batch_scoring.py`)

Scores all records with PD/LGD models and calculates risk metrics.

**Location:** `8_cde_jobs/spark_jobs/batch_scoring.py`

**Arguments:**
| Argument | Description | Example |
|----------|-------------|---------|
| `--features-path` | Feature matrix location | `s3a://bucket/data/features/` |
| `--pd-model-path` | PD model pickle | `s3a://bucket/models/pd/pd_model_latest.pkl` |
| `--lgd-model-path` | LGD model pickle | `s3a://bucket/models/lgd/lgd_model_latest.pkl` |
| `--output-path` | Scores output | `s3a://bucket/data/scores/` |
| `--date` | Scoring date | `2024-01-27` |

**Scoring Pipeline:**
```
Load Features → Broadcast Models → Score PD → Score LGD → Calculate Risk Metrics → Validate → Write
```

**Risk Metrics Calculated:**
- **Expected Loss** = PD × LGD × EAD
- **Unexpected Loss** = √(PD × (1-PD)) × LGD × EAD × 2.33
- **Economic Capital** = Unexpected Loss - Expected Loss
- **Risk-Weighted Assets** = EAD × PD × 12.5

**Risk Grade Mapping:**
| Grade | PD Range |
|-------|----------|
| AAA | 0.0% - 0.5% |
| AA | 0.5% - 1.0% |
| A | 1.0% - 2.0% |
| BBB | 2.0% - 5.0% |
| BB | 5.0% - 10.0% |
| B | 10.0% - 20.0% |
| CCC | 20.0% - 50.0% |
| D | 50.0% - 100.0% |

---

## CDE Deployment

### Environment Variables

```bash
# Required for Iceberg/Spark mode
export SPARK_WAREHOUSE_DIR=s3a://your-bucket/data/user/username
export DATA_STORAGE_MODE=iceberg

# Optional
export SPARK_ICEBERG_DATABASE=credit_risk
export KRB5_KEYTAB=/home/cdsw/.keytab
export KRB5_PRINCIPAL=username@REALM
```

### CDE Client Usage

```python
from cde_client import CDEClient, CDEConfig

config = CDEConfig()
client = CDEClient(config)

# Upload job files
client.upload_directory("spark_jobs/", "*.py")

# Create job
client.create_job(
    name="credit-risk-feature-engineering",
    script="feature_engineering.py",
    arguments=["--input-path", config.spark_warehouse_dir, ...],
    spark_config={
        "spark.executor.memory": "4g",
        "spark.executor.cores": "2"
    }
)

# Run job
run_id = client.run_job("credit-risk-feature-engineering")
```

### Job Schedule (Airflow)

| Job | Schedule | Dependency |
|-----|----------|------------|
| Feature Engineering | Daily 1:00 AM | Data extraction complete |
| Batch Scoring | Daily 2:00 AM | Feature engineering complete |
| Model Retraining | Weekly Sunday | Drift detection trigger |

---

## Model Training

### PD Model (Probability of Default)

**Script:** `3_models/train_pd_model.py`

**Algorithms:**
1. XGBoost (default)
2. Gradient Boosting
3. Logistic Regression

**Selection:** Best AUC-ROC on test set

**Metrics:**
- AUC-ROC, Gini, KS Statistic, Brier Score, Log Loss

### LGD Model (Loss Given Default)

**Script:** `3_models/train_lgd_model.py`

**Type:** Regression

**Target:** `lgd = loss_amount / loan_amount`

**Metrics:**
- MAE, RMSE, R², MAPE

---

## Authentication (RAZ-enabled S3)

The platform uses Kerberos authentication for RAZ-protected S3 buckets.

**Flow:**
1. Training scripts call `kinit` to refresh credentials
2. Spark runs in `local[*]` mode (driver-only) to use local Kerberos ticket
3. For distributed mode, CDE handles credential distribution via delegation tokens

**Configuration in training scripts:**
```python
# Runs kinit before Spark operations
refresh_kerberos_credentials()

# Local mode keeps processing on driver where ticket is valid
spark = SparkSession.builder \
    .master("local[*]") \
    .appName("Training") \
    .getOrCreate()
```

---

## Component Connections

```
┌──────────────────────────────────────────────────────────────┐
│                     CML Application                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  Frontend   │  │   Backend   │  │   Model Training    │  │
│  │  (React)    │──│  (FastAPI)  │──│   (Python/Spark)    │  │
│  └─────────────┘  └──────┬──────┘  └──────────┬──────────┘  │
└──────────────────────────┼─────────────────────┼─────────────┘
                           │                     │
              ┌────────────┴────────────┐        │
              ▼                         ▼        ▼
       ┌─────────────┐          ┌─────────────────────┐
       │   SQLite    │          │    S3 Storage       │
       │  (Audit DB) │          │  (Data + Models)    │
       └─────────────┘          └──────────┬──────────┘
                                           │
                                           ▼
                                ┌─────────────────────┐
                                │   CDE Spark Jobs    │
                                │  - Feature Eng      │
                                │  - Batch Scoring    │
                                └─────────────────────┘
```

---

## Quick Reference

### Run PD Training (Iceberg mode)
```bash
export DATA_STORAGE_MODE=iceberg
export SPARK_WAREHOUSE_DIR=s3a://bucket/data/user/username
python 3_models/train_pd_model.py
```

### Run LGD Training (Iceberg mode)
```bash
export DATA_STORAGE_MODE=iceberg
export SPARK_WAREHOUSE_DIR=s3a://bucket/data/user/username
python 3_models/train_lgd_model.py
```

### Deploy CDE Jobs
```bash
python 8_cde_jobs/deploy_jobs.py
```

### Check Job Status
```bash
python 8_cde_jobs/cde_client.py --status credit-risk-feature-engineering
```
