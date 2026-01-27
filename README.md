# Credit Risk Approval Platform

End-to-end credit risk assessment platform on Cloudera ML with visual agentic workflow.

## 🎯 Features

- **Synthetic Corporate Loan Data**: Realistic corporate loan portfolios with default outcomes
- **ML Models**: PD (Probability of Default) and LGD (Loss Given Default) models
- **Agentic Workflow**: LangGraph-powered credit approval process
- **Visual UI**: React Flow workflow visualization
- **AI Analyst**: RAG-based Q&A on documents and policies
- **Risk Calculations**: RORAC, Economic Capital, Regulatory Capital (Basel IRB)
- **Real-time Monitoring**: Drift detection and model performance tracking

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     CML PROJECT                                  │
├─────────────────────────────────────────────────────────────────┤
│  Applications:                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ React UI     │  │ FastAPI      │  │ Monitoring   │          │
│  │ (Next.js)    │  │ + LangGraph  │  │ Dashboard    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│  Model Endpoints:                                                │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐       │
│  │   PD   │ │  LGD   │ │  Doc   │ │  RAG   │ │  Risk  │       │
│  │ Model  │ │ Model  │ │ Proc   │ │Service │ │ Engine │       │
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
credit-risk-platform/
├── 0_setup/          # Bootstrap and initialization
├── 1_data/           # Synthetic data generation
├── 2_features/       # Feature engineering
├── 3_models/         # Model training and validation
├── 4_endpoints/      # CML model endpoints
├── 5_backend/        # FastAPI + LangGraph
├── 6_frontend/       # React/Next.js UI
├── 7_monitoring/     # Drift detection
├── 8_cde_jobs/       # Optional Spark jobs
└── 9_deployment/     # Deployment scripts
```

## 🚀 Quick Start

### 1. Deploy as CML AMP

Upload this project to CML and it will auto-deploy via `.project-metadata.yaml`.

### 2. Manual Setup

```bash
# Install CDE CLI (for Spark job deployment)
mkdir -p ~/.local/bin
mv cde ~/.local/bin/cde-cli
chmod +x ~/.local/bin/cde-cli

# Install dependencies
python 0_setup/install_dependencies.py

# Create tables
python 0_setup/create_tables.py

# Generate synthetic data
python 1_data/generate_synthetic.py

# Build features
python 2_features/feature_pipeline.py

# Train models
python 3_models/train_pd_model.py
python 3_models/train_lgd_model.py

# Start backend
cd 5_backend && uvicorn main:app --port 8000

# Start frontend
cd 6_frontend && npm install && npm run dev
```

## 📋 Task Plan

See `CLAUDE_CODE_TASKS.md` for detailed implementation tasks.
See `TASKS_CHECKLIST.md` for a quick checklist.
See `tasks.json` for machine-readable task definitions.

## 🔧 Configuration

Environment variables:
```bash
CLAUDE_API_KEY=         # Anthropic API key
REDIS_URL=redis://localhost:6379
DATABASE_URL=sqlite:///./credit_risk.db
```

## 📊 Workflow

```
Document Upload → OCR/Extract → Validate → Bureau Pull → 
Compliance Check → Risk Scoring → Human Review (if needed) → Decision
```

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14, React Flow, TailwindCSS, shadcn/ui |
| Backend | FastAPI, LangGraph, WebSocket |
| ML | XGBoost, scikit-learn, MLflow |
| Vector Store | Chroma |
| State | Redis |
| Data | SQLite (demo) / Iceberg (production) |

## 📄 License

Apache 2.0