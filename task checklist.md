# Credit Risk Platform - Task Checklist

## Quick Reference

**Project**: Credit Risk Approval Platform on Cloudera ML
**Stack**: Python/FastAPI + LangGraph + React/Next.js + React Flow
**Data**: Synthetic corporate loans

---

## Phase 0: Setup
- [ ] 0.1 Create directory structure
- [ ] 0.2 Create requirements.txt
- [ ] 0.3 Create install_dependencies.py
- [ ] 0.4 Create create_tables.py (SQLite/Iceberg)
- [ ] 0.5 Create setup_vector_store.py (Chroma)
- [ ] 0.6 Create load_policy_docs.py

## Phase 1: Data Generation
- [ ] 1.1 Create generate_synthetic.py (5000 companies, 10000 loans)
- [ ] 1.2 Create load_to_iceberg.py
- [ ] 1.3 Create sample documents folder

## Phase 2: Features
- [ ] 2.1 Create feature_pipeline.py
- [ ] 2.2 Create data_quality.py

## Phase 3: Models
- [ ] 3.1 Create pd_config.yaml
- [ ] 3.2 Create lgd_config.yaml
- [ ] 3.3 Create train_pd_model.py (XGBoost)
- [ ] 3.4 Create train_lgd_model.py (GBRegressor)
- [ ] 3.5 Create validate_models.py (discrimination, calibration, stability)
- [ ] 3.6 Create register_models.py (MLflow)

## Phase 4: Endpoints
- [ ] 4.1 Create serve_pd.py
- [ ] 4.2 Create serve_lgd.py
- [ ] 4.3 Create serve_documents.py (OCR + LLM)
- [ ] 4.4 Create serve_rag.py
- [ ] 4.5 Create serve_risk_engine.py (PD+LGD+RORAC+Capital)

## Phase 5: Backend
- [ ] 5.1 Create Pydantic models (application, workflow, risk, decision)
- [ ] 5.2 Create config.py
- [ ] 5.3 Create services (document, model, rag, iceberg)
- [ ] 5.4 Create agents/state.py (CreditWorkflowState)
- [ ] 5.5 Create agent nodes (document, validation, enrichment, compliance, scoring, review, decision)
- [ ] 5.6 Create agent tools (model, data, rag, notification)
- [ ] 5.7 Create agents/graph.py (LangGraph workflow)
- [ ] 5.8 Create api/applications.py
- [ ] 5.9 Create api/workflow.py
- [ ] 5.10 Create api/analyst.py
- [ ] 5.11 Create api/decisions.py
- [ ] 5.12 Create api/websocket.py
- [ ] 5.13 Create main.py (FastAPI app)
- [ ] 5.14 Create start.sh

## Phase 6: Frontend
- [ ] 6.1 Create package.json
- [ ] 6.2 Create config files (tailwind, next, tsconfig)
- [ ] 6.3 Create UI components (shadcn/ui)
- [ ] 6.4 Create layout components (Sidebar, Header)
- [ ] 6.5 Create workflow components (WorkflowCanvas, nodes, edges)
- [ ] 6.6 Create analyst components (ChatInterface, RiskMetrics)
- [ ] 6.7 Create application components (Form, Table, Upload)
- [ ] 6.8 Create monitoring components (DriftChart, Alerts)
- [ ] 6.9 Create lib (api, websocket, utils)
- [ ] 6.10 Create hooks (useWorkflow, useChat, useApplications)
- [ ] 6.11 Create types/index.ts
- [ ] 6.12 Create app/layout.tsx
- [ ] 6.13 Create app/page.tsx (Dashboard)
- [ ] 6.14 Create applications list page
- [ ] 6.15 Create new application page
- [ ] 6.16 Create application detail page
- [ ] 6.17 Create workflow visualization page
- [ ] 6.18 Create analyst workbench page
- [ ] 6.19 Create monitoring page
- [ ] 6.20 Create start.sh
- [ ] 6.21 Create build.sh

## Phase 7: Monitoring
- [ ] 7.1 Create drift_detection.py
- [ ] 7.2 Create performance_tracker.py
- [ ] 7.3 Create alert_handler.py

## Phase 8: CDE Jobs (Optional)
- [ ] 8.1 Create Spark feature_engineering.py
- [ ] 8.2 Create Spark batch_scoring.py
- [ ] 8.3 Create credit_workflow_dag.py
- [ ] 8.4 Create retraining_dag.py

## Phase 9: Deployment
- [ ] 9.1 Create deploy_all.py
- [ ] 9.2 Create config files
- [ ] 9.3 Create tests
- [ ] 9.4 Create documentation

## Phase 10: Integration
- [ ] 10.1 Complete .project-metadata.yaml
- [ ] 10.2 Create README.md
- [ ] 10.3 End-to-end testing

---

## MVP Priority (Do First)

1. **Data**: 1.1 generate_synthetic.py
2. **Models**: 3.3 train_pd_model.py, 3.4 train_lgd_model.py
3. **Endpoints**: 4.1-4.5 all serve_*.py
4. **Backend Core**: 5.4-5.7 LangGraph agents
5. **Backend API**: 5.8-5.13 FastAPI routes
6. **Frontend Core**: 6.5-6.6 workflow + analyst UI
7. **Frontend Pages**: 6.17-6.18 workflow + analyst pages

---

## Key Files Quick Reference

| Component | Main File | Purpose |
|-----------|-----------|---------|
| Data Gen | 1_data/generate_synthetic.py | Create synthetic corporate loans |
| PD Model | 3_models/train_pd_model.py | Train probability of default model |
| LGD Model | 3_models/train_lgd_model.py | Train loss given default model |
| Risk Engine | 4_endpoints/serve_risk_engine.py | Combined scoring endpoint |
| Workflow | 5_backend/agents/graph.py | LangGraph state machine |
| API | 5_backend/main.py | FastAPI application |
| UI | 6_frontend/app/applications/[id]/workflow/page.tsx | Workflow visualization |
| Analyst | 6_frontend/app/applications/[id]/analyst/page.tsx | AI workbench |

---

## Environment Variables Needed

```bash
CLAUDE_API_KEY=           # Anthropic API key
REDIS_URL=redis://localhost:6379
DATABASE_URL=sqlite:///./credit_risk.db  # or Iceberg connection
```

---

## Test Commands

```bash
# Start backend
cd 5_backend && uvicorn main:app --reload --port 8000

# Start frontend
cd 6_frontend && npm run dev

# Run tests
pytest tests/ -v
```