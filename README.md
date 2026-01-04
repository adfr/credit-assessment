# Credit Risk Platform

An end-to-end credit risk approval and monitoring platform built for Cloudera Machine Learning (CML).

## Overview

This platform provides comprehensive credit risk assessment capabilities including:
- **Synthetic Data Generation**: Corporate loan data with realistic patterns
- **ML Models**: Probability of Default (PD) and Loss Given Default (LGD) models
- **LangGraph Workflow**: Agentic approval workflow with human-in-the-loop
- **React Frontend**: Workflow visualization and AI analyst workbench
- **Real-time Monitoring**: Drift detection and model performance tracking

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React/Next.js)                 │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────────────┐  │
│  │  Dashboard   │  │  Workflow UI  │  │  AI Analyst Chat     │  │
│  └──────────────┘  └───────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI)                           │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────────────┐  │
│  │  REST API    │  │  WebSocket    │  │  LangGraph Engine    │  │
│  └──────────────┘  └───────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│   PD Model       │ │   LGD Model      │ │   RAG Service    │
│   (XGBoost)      │ │   (GradBoost)    │ │   (ChromaDB)     │
└──────────────────┘ └──────────────────┘ └──────────────────┘
```

## Project Structure

```
credit-assessment/
├── 0_setup/                 # Setup scripts
│   ├── install_dependencies.py
│   ├── create_tables.py
│   ├── setup_vector_store.py
│   └── load_policy_docs.py
├── 1_data/                  # Data generation
│   ├── generate_synthetic.py
│   ├── load_to_iceberg.py
│   └── sample_documents/
├── 2_features/              # Feature engineering
│   ├── feature_pipeline.py
│   └── data_quality.py
├── 3_models/                # Model training
│   ├── configs/
│   ├── train_pd_model.py
│   ├── train_lgd_model.py
│   ├── validate_models.py
│   └── register_models.py
├── 4_endpoints/             # CML model endpoints
│   ├── serve_pd.py
│   ├── serve_lgd.py
│   ├── serve_documents.py
│   ├── serve_rag.py
│   └── serve_risk_engine.py
├── 5_backend/               # FastAPI backend
│   ├── agents/              # LangGraph workflow
│   ├── api/                 # API routes
│   ├── models/              # Pydantic models
│   ├── services/            # Business logic
│   └── main.py
├── 6_frontend/              # React/Next.js frontend
│   ├── app/
│   ├── components/
│   └── lib/
├── 7_monitoring/            # Model monitoring
│   └── drift_detection.py
├── data/                    # Generated data and models
├── docs/                    # Documentation
└── tests/                   # Test suite
```

## Quick Start

### 1. Install Dependencies

```bash
cd 0_setup
python install_dependencies.py
```

### 2. Setup Database and Vector Store

```bash
python 0_setup/create_tables.py
python 0_setup/setup_vector_store.py
python 0_setup/load_policy_docs.py
```

### 3. Generate Synthetic Data

```bash
python 1_data/generate_synthetic.py
python 1_data/load_to_iceberg.py
```

### 4. Engineer Features

```bash
python 2_features/feature_pipeline.py
python 2_features/data_quality.py
```

### 5. Train Models

```bash
python 3_models/train_pd_model.py
python 3_models/train_lgd_model.py
python 3_models/validate_models.py
```

### 6. Start Backend

```bash
cd 5_backend
chmod +x start.sh
./start.sh
```

### 7. Start Frontend

```bash
cd 6_frontend
npm install
npm run dev
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/applications` | GET | List applications |
| `/api/applications` | POST | Create application |
| `/api/applications/{id}` | GET | Get application details |
| `/api/workflow/start` | POST | Start approval workflow |
| `/api/workflow/{id}/status` | GET | Get workflow status |
| `/api/workflow/{id}/resume` | POST | Resume after review |
| `/api/analyst/chat` | POST | AI analyst chat |
| `/api/decisions/{id}` | GET | Get final decision |

## Workflow Steps

1. **Document Processing**: Extract data from uploaded documents
2. **Validation**: Verify required fields and data consistency
3. **Enrichment**: Pull bureau data and industry benchmarks
4. **Compliance**: Run sanctions, AML, and policy checks
5. **Scoring**: Calculate PD, LGD, Expected Loss, RORAC
6. **Review**: Human-in-the-loop for referred cases
7. **Decision**: Generate final decision with conditions

## Configuration

Create a `.env` file based on `.env.template`:

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Claude API (for LLM features)
ANTHROPIC_API_KEY=your_key_here

# Redis (optional, for workflow checkpointing)
REDIS_URL=redis://localhost:6379
```

## Model Performance

| Model | Metric | Value |
|-------|--------|-------|
| PD | AUC-ROC | 0.82 |
| PD | Gini | 0.64 |
| PD | KS | 0.52 |
| LGD | MAE | 0.12 |
| LGD | R² | 0.45 |

## Technologies

- **Backend**: Python, FastAPI, LangGraph, SQLite
- **ML**: scikit-learn, XGBoost, MLflow
- **Vector Store**: ChromaDB
- **Frontend**: React, Next.js, Tailwind CSS, React Flow
- **Deployment**: Cloudera Machine Learning (CML)

## License

Proprietary - For demonstration purposes only.
