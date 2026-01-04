 Credit Risk Platform - Claude Code Task Plan

## Project Overview

Build an end-to-end credit risk approval and monitoring platform on Cloudera ML with:
- Synthetic corporate loan data generation
- ML models (PD, LGD) for risk scoring
- LangGraph agentic workflow with visual UI
- React frontend with React Flow workflow visualization
- AI analyst workbench with RAG
- Real-time monitoring and drift detection

**All components deployed in CML (Cloudera Machine Learning)**

---

## Task Execution Order

Execute tasks in phases. Each phase should be completed before moving to the next.

---

## PHASE 0: PROJECT SETUP

### Task 0.1: Create Project Structure
```
Create the complete directory structure for the project:
- 0_setup/
- 1_data/
- 2_features/
- 3_models/configs/
- 4_endpoints/
- 5_backend/api/, agents/nodes/, agents/tools/, services/, models/, utils/
- 6_frontend/app/, components/, lib/, hooks/, types/
- 7_monitoring/
- 8_cde_jobs/spark_jobs/, airflow_dags/
- 9_deployment/configs/
- tests/, docs/, notebooks/
```

### Task 0.2: Create requirements.txt
```
Create Python requirements file with:
- fastapi, uvicorn, websockets
- langgraph, langchain, langchain-anthropic
- scikit-learn, xgboost, pandas, numpy
- mlflow
- chromadb (vector store)
- redis
- pydantic
- python-multipart (file uploads)
- PyMuPDF, pytesseract (document processing)
- faker (synthetic data)
- pyarrow (Iceberg/Parquet)
```

### Task 0.3: Create 0_setup/install_dependencies.py
```
Script to:
- Install Python packages from requirements.txt
- Install Node.js and npm for frontend
- Verify installations
```

### Task 0.4: Create 0_setup/create_tables.py
```
Script to create database tables (SQLite for demo, Iceberg for production):
- loan_history (historical corporate loans)
- payment_history (payment records)
- bureau_data (credit bureau information)
- model_features (engineered features)
- applications (new credit applications)
- predictions (model prediction audit trail)
- workflow_state (LangGraph checkpoints)
```

### Task 0.5: Create 0_setup/setup_vector_store.py
```
Script to:
- Initialize Chroma vector store
- Create collections for policy documents and customer documents
```

### Task 0.6: Create 0_setup/load_policy_docs.py
```
Script to:
- Create sample credit policy documents (markdown/text)
- Embed and load into vector store
- Policy docs should cover: approval criteria, risk thresholds, RORAC hurdles, documentation requirements
```

---

## PHASE 1: SYNTHETIC DATA GENERATION

### Task 1.1: Create 1_data/generate_synthetic.py
```
Generate synthetic corporate loan data using Faker:

Companies (5000+):
- company_id, company_name
- industry (manufacturing, retail, technology, healthcare, etc.)
- years_in_business
- employee_count
- annual_revenue, net_income, total_assets, total_liabilities
- current_ratio, quick_ratio, debt_to_equity
- interest_coverage_ratio
- geography (region, country)

Loans (10000+):
- loan_id, company_id
- loan_amount ($100K - $50M range)
- interest_rate
- term_months (12, 24, 36, 48, 60)
- purpose (working_capital, expansion, equipment, acquisition, refinancing)
- collateral_type, collateral_value, ltv_ratio
- origination_date
- loan_status (current, paid_off, default, restructured)
- default_flag (0/1)
- days_to_default (if defaulted)
- loss_amount, recovery_amount (if defaulted)

Bureau Data:
- company_id, report_date
- credit_score (business credit score 0-100)
- payment_index
- derogatory_count
- years_on_file
- trade_lines_count
- utilization_rate

Payment History:
- loan_id, payment_date
- scheduled_amount, actual_amount
- days_past_due
- payment_status

Create realistic correlations:
- Higher default rates for high leverage, low coverage
- Industry-specific default patterns
- Economic cycle effects (simulate recession period)
- Default rate ~3-8% overall
```

### Task 1.2: Create 1_data/load_to_iceberg.py
```
Script to:
- Load generated CSV/Parquet files into database tables
- Create indices for common queries
- Validate data integrity
```

### Task 1.3: Create sample documents
```
Create 1_data/sample_documents/ with:
- Sample financial statements (text/markdown format)
- Sample loan application forms
- Sample supporting documents
These will be used for document processing demos
```

---

## PHASE 2: FEATURE ENGINEERING

### Task 2.1: Create 2_features/feature_pipeline.py
```
Feature engineering pipeline:

Financial Ratios:
- debt_to_equity, debt_to_assets
- current_ratio, quick_ratio
- interest_coverage_ratio
- return_on_assets, return_on_equity
- revenue_growth_yoy
- profit_margin

Bureau Features:
- credit_score_normalized
- payment_index_trend
- utilization_rate
- derogatory_ratio

Behavioral Features (from payment history):
- avg_days_past_due
- max_days_past_due
- payment_volatility
- count_30dpd, count_60dpd, count_90dpd
- payment_consistency_score

Loan Features:
- loan_to_revenue_ratio
- loan_to_assets_ratio
- collateral_coverage_ratio

Industry Features:
- industry_default_rate (historical)
- industry_risk_tier

Output: model_features table with all engineered features
```

### Task 2.2: Create 2_features/data_quality.py
```
Data quality checks:
- Missing value analysis
- Outlier detection
- Distribution analysis
- Feature correlation matrix
- Target leakage checks
```

---

## PHASE 3: MODEL TRAINING

### Task 3.1: Create 3_models/configs/pd_config.yaml
```
PD model configuration:
- features list
- hyperparameters for XGBoost
- cross-validation settings
- threshold settings
```

### Task 3.2: Create 3_models/configs/lgd_config.yaml
```
LGD model configuration:
- features list
- hyperparameters for Gradient Boosting Regressor
- validation settings
```

### Task 3.3: Create 3_models/train_pd_model.py
```
PD Model Training:
- Load features from model_features table
- Train/test split with stratification
- Train multiple models: Logistic Regression, XGBoost, GradientBoosting
- Track experiments with MLflow
- Log metrics: AUC, Gini, KS statistic, Brier score
- Plot calibration curves
- Select best model
- Save model artifact
```

### Task 3.4: Create 3_models/train_lgd_model.py
```
LGD Model Training:
- Filter to defaulted loans only
- Calculate LGD = loss_amount / loan_amount
- Train Gradient Boosting Regressor
- Track with MLflow
- Log metrics: MAE, RMSE, R²
- Save model artifact
```

### Task 3.5: Create 3_models/validate_models.py
```
Model Validation Suite:

Discrimination Tests:
- AUC-ROC, Gini coefficient
- KS statistic
- Somers' D

Calibration Tests:
- Hosmer-Lemeshow test
- Binomial test per decile
- Calibration plot

Stability Tests:
- PSI (Population Stability Index)
- CSI (Characteristic Stability Index) per feature

Generate validation report (PDF or HTML)
```

### Task 3.6: Create 3_models/register_models.py
```
MLflow Model Registry:
- Register PD model with version
- Register LGD model with version
- Set model stage (Staging -> Production)
- Add model metadata and tags
```

---

## PHASE 4: MODEL ENDPOINTS

### Task 4.1: Create 4_endpoints/serve_pd.py
```
CML Model Endpoint for PD:
- Load model from MLflow or local artifact
- predict(args) function
- Input: customer features dict
- Output: probability of default (0-1)
- Include feature preprocessing
```

### Task 4.2: Create 4_endpoints/serve_lgd.py
```
CML Model Endpoint for LGD:
- Load model from artifact
- predict(args) function
- Input: customer features dict
- Output: loss given default (0-1)
```

### Task 4.3: Create 4_endpoints/serve_documents.py
```
Document Processing Endpoint:
- process(args) function
- Input: document base64 or file path
- Use OCR (pytesseract) for images/scanned PDFs
- Use Claude API for structured extraction
- Output: extracted fields as JSON
  - company_name, financial_figures, dates, etc.
```

### Task 4.4: Create 4_endpoints/serve_rag.py
```
RAG Service Endpoint:
- query(args) function
- Input: question, optional context (customer_id, document_ids)
- Search vector store for relevant policy docs
- Search customer documents if provided
- Call Claude API with context
- Output: answer with sources
```

### Task 4.5: Create 4_endpoints/serve_risk_engine.py
```
Combined Risk Engine Endpoint:
- score(args) function
- Input: customer features, loan parameters
- Call PD model
- Call LGD model
- Calculate:
  - Expected Loss = PD × LGD × EAD
  - Economic Capital (99.9% VaR)
  - Regulatory Capital (Basel IRB formula)
  - RORAC = Net Income / Economic Capital
- Output: complete risk assessment with decision recommendation
```

---

## PHASE 5: BACKEND (FastAPI + LangGraph)

### Task 5.1: Create 5_backend/models/ (Pydantic schemas)
```
Create Pydantic models:

5_backend/models/application.py:
- ApplicationCreate, ApplicationResponse
- ApplicationStatus enum
- CustomerData, LoanRequest

5_backend/models/workflow.py:
- WorkflowState
- WorkflowStep, WorkflowStatus
- StepResult

5_backend/models/risk.py:
- RiskScores (pd, lgd, el, ec, rorac)
- RiskDecision enum (APPROVE, REFER, DECLINE)

5_backend/models/decision.py:
- DecisionResponse
- DecisionConditions
```

### Task 5.2: Create 5_backend/config.py
```
Configuration:
- Model endpoint URLs
- Redis connection
- Claude API key
- Database connection
- Vector store settings
```

### Task 5.3: Create 5_backend/services/
```
5_backend/services/document_service.py:
- Call document processor endpoint
- Handle file uploads
- Parse extraction results

5_backend/services/model_service.py:
- Call PD, LGD, Risk Engine endpoints
- Handle model errors

5_backend/services/rag_service.py:
- Call RAG endpoint
- Format context for chat

5_backend/services/iceberg_service.py:
- Query database tables
- Save applications, predictions
- Get historical data
```

### Task 5.4: Create 5_backend/agents/state.py
```
LangGraph State Definition:

class CreditWorkflowState(TypedDict):
    application_id: str
    customer_data: dict
    loan_request: dict
    documents: list[dict]
    extracted_data: dict
    validation_results: dict
    bureau_data: dict
    risk_scores: dict
    compliance_flags: list[str]
    analyst_notes: list[str]
    human_decision: str | None
    final_decision: str
    decision_conditions: list[str]
    current_step: str
    error: str | None
    messages: list  # For chat history in review step
```

### Task 5.5: Create 5_backend/agents/nodes/
```
LangGraph Node Functions:

document_node.py:
- Process uploaded documents
- Call document processor endpoint
- Extract structured data
- Update state with extracted_data

validation_node.py:
- Validate extracted data
- Check required fields
- Cross-reference with bureau data
- Flag inconsistencies

enrichment_node.py:
- Simulate bureau data pull
- Add industry benchmarks
- Calculate derived metrics

compliance_node.py:
- Check against policy rules
- Sanction screening (simulated)
- Return pass/fail with flags

scoring_node.py:
- Call risk engine endpoint
- Get PD, LGD, RORAC, Capital
- Determine initial decision (approve/refer/decline)

review_node.py:
- Interrupt point for human review
- Handle analyst chat (RAG)
- Collect human decision

decision_node.py:
- Generate final decision
- Set conditions
- Create audit record
```

### Task 5.6: Create 5_backend/agents/tools/
```
LangGraph Tools:

model_tools.py:
- call_pd_model(features) -> float
- call_lgd_model(features) -> float
- call_risk_engine(features, loan) -> RiskScores

data_tools.py:
- get_customer_history(customer_id) -> dict
- get_industry_benchmarks(industry) -> dict
- save_application(data) -> str

rag_tools.py:
- query_policies(question) -> str
- query_documents(question, doc_ids) -> str

notification_tools.py:
- send_alert(message, channel) -> bool
```

### Task 5.7: Create 5_backend/agents/graph.py
```
Main LangGraph Workflow:

Build StateGraph with:
- All nodes from nodes/
- Conditional edges for decision routing
- Interrupt at review_node for human-in-the-loop
- Redis checkpointer for state persistence

Routing logic:
- After compliance: pass -> scoring, fail -> decision (auto-decline)
- After scoring: approve -> decision, refer -> review, decline -> decision
- After review: approve/decline -> decision, request_info -> document_node

Compile graph with checkpointer
```

### Task 5.8: Create 5_backend/api/applications.py
```
FastAPI Routes for Applications:

POST /api/applications
- Create new credit application
- Upload documents
- Return application_id

GET /api/applications
- List applications with filters (status, date range)
- Pagination

GET /api/applications/{id}
- Get application details
- Include current workflow state

DELETE /api/applications/{id}
- Cancel/delete application
```

### Task 5.9: Create 5_backend/api/workflow.py
```
FastAPI Routes for Workflow:

POST /api/workflow/start
- Start workflow for application_id
- Initialize LangGraph
- Return workflow_id

GET /api/workflow/{id}/status
- Get current workflow state
- Step history with timestamps

POST /api/workflow/{id}/resume
- Resume after human review
- Pass human decision and notes

GET /api/workflow/{id}/history
- Full step-by-step history
```

### Task 5.10: Create 5_backend/api/analyst.py
```
FastAPI Routes for AI Analyst:

POST /api/analyst/chat
- Input: application_id, message
- Get relevant context (documents, risk data)
- Call RAG service
- Return AI response

GET /api/analyst/{application_id}/suggestions
- Get suggested questions based on risk flags

POST /api/analyst/{application_id}/note
- Add analyst note to application
```

### Task 5.11: Create 5_backend/api/decisions.py
```
FastAPI Routes for Decisions:

GET /api/decisions/{application_id}
- Get final decision with all details

POST /api/decisions/{application_id}/override
- Manual decision override (with authorization)

GET /api/decisions/report
- Decision report for date range
- Summary statistics
```

### Task 5.12: Create 5_backend/api/websocket.py
```
WebSocket Handler:

/ws/workflow/{application_id}
- Real-time workflow updates
- Send step completion events
- Send status changes
- Handle connection lifecycle
```

### Task 5.13: Create 5_backend/main.py
```
FastAPI Application:
- Include all routers
- CORS middleware
- WebSocket endpoint
- Health check endpoint
- Startup/shutdown events (initialize services)
```

### Task 5.14: Create 5_backend/start.sh
```
Startup script for CML Application:
- Set environment variables
- Start uvicorn with FastAPI app
- Configure port and host
```

---

## PHASE 6: FRONTEND (React + Next.js)

### Task 6.1: Create 6_frontend/package.json
```
Dependencies:
- next, react, react-dom
- reactflow (workflow visualization)
- @tanstack/react-query (data fetching)
- zustand (state management)
- tailwindcss, postcss, autoprefixer
- @radix-ui/* (shadcn/ui primitives)
- lucide-react (icons)
- socket.io-client (websocket)
- date-fns
- zod (validation)
```

### Task 6.2: Create 6_frontend/tailwind.config.js and related configs
```
Tailwind configuration with shadcn/ui theme
next.config.js
tsconfig.json
postcss.config.js
```

### Task 6.3: Create 6_frontend/components/ui/
```
shadcn/ui components (can use CLI or create manually):
- button.tsx
- card.tsx
- input.tsx
- label.tsx
- select.tsx
- table.tsx
- dialog.tsx
- alert.tsx
- badge.tsx
- tabs.tsx
- textarea.tsx
- toast.tsx
- progress.tsx
- skeleton.tsx
```

### Task 6.4: Create 6_frontend/components/layout/
```
Layout components:

Sidebar.tsx:
- Navigation menu
- Links: Dashboard, Applications, Monitoring
- Collapse/expand

Header.tsx:
- Page title
- User menu
- Notifications

PageContainer.tsx:
- Main content wrapper
- Breadcrumbs
```

### Task 6.5: Create 6_frontend/components/workflow/
```
Workflow visualization components:

WorkflowCanvas.tsx:
- React Flow canvas
- Handle node/edge rendering
- Zoom/pan controls
- Auto-layout

nodes/ProcessNode.tsx:
- Custom node for processing steps
- Status indicator (pending, running, complete, error)
- Step name and duration

nodes/DecisionNode.tsx:
- Diamond shape for decision points
- Show routing paths

nodes/StatusNode.tsx:
- Final status display

edges/AnimatedEdge.tsx:
- Animated edge for active transitions

WorkflowLegend.tsx:
- Legend for node statuses
```

### Task 6.6: Create 6_frontend/components/analyst/
```
AI Analyst components:

ChatInterface.tsx:
- Chat message list
- Input field with send button
- Suggested questions
- Loading states

ChatMessage.tsx:
- Message bubble (user/assistant)
- Timestamp
- Source citations (for RAG responses)

DocumentViewer.tsx:
- Display uploaded documents
- PDF preview if possible
- Extracted data view

RiskMetrics.tsx:
- Risk score cards (PD, LGD, RORAC, Capital)
- Visual indicators (gauges, progress bars)
- Decision recommendation
```

### Task 6.7: Create 6_frontend/components/applications/
```
Application management components:

ApplicationForm.tsx:
- Multi-step form for new application
- Customer details
- Loan request
- Document upload
- Validation

ApplicationCard.tsx:
- Summary card for list view
- Status badge
- Key metrics

ApplicationTable.tsx:
- Sortable, filterable table
- Pagination
- Actions column

DocumentUpload.tsx:
- Drag-and-drop upload
- File type validation
- Upload progress
```

### Task 6.8: Create 6_frontend/components/monitoring/
```
Monitoring components:

DriftChart.tsx:
- PSI over time chart
- Threshold lines

PerformanceMetrics.tsx:
- Model performance metrics
- AUC trend
- Approval rate trend

AlertsList.tsx:
- Recent alerts
- Severity indicators
- Acknowledge action
```

### Task 6.9: Create 6_frontend/lib/
```
Utility libraries:

api.ts:
- Axios/fetch client
- Base URL configuration
- Request/response interceptors
- Type-safe API functions

websocket.ts:
- Socket.io client setup
- Connection management
- Event handlers

utils.ts:
- Formatting functions
- Date utilities
- Number formatting

constants.ts:
- Status enums
- Color mappings
- Configuration constants
```

### Task 6.10: Create 6_frontend/hooks/
```
Custom React hooks:

useWorkflow.ts:
- Fetch workflow state
- WebSocket subscription
- State management

useChat.ts:
- Chat message state
- Send message function
- Loading state

useApplications.ts:
- List applications
- CRUD operations
- Filtering/sorting

useWebSocket.ts:
- Generic WebSocket hook
- Auto-reconnect
- Event subscription
```

### Task 6.11: Create 6_frontend/types/index.ts
```
TypeScript definitions:
- Application types
- Workflow types
- Risk types
- API response types
- WebSocket event types
```

### Task 6.12: Create 6_frontend/app/layout.tsx
```
Root layout:
- HTML structure
- Providers (React Query, etc.)
- Sidebar + Header
- Toast container
```

### Task 6.13: Create 6_frontend/app/page.tsx
```
Dashboard page:
- Summary statistics cards
- Recent applications list
- Pending reviews count
- Model health status
```

### Task 6.14: Create 6_frontend/app/applications/page.tsx
```
Applications list page:
- Filter controls
- ApplicationTable component
- New application button
```

### Task 6.15: Create 6_frontend/app/applications/new/page.tsx
```
New application page:
- ApplicationForm component
- Submit and start workflow
- Redirect to workflow view on success
```

### Task 6.16: Create 6_frontend/app/applications/[id]/page.tsx
```
Application detail page:
- Application summary
- Current status
- Links to workflow and analyst views
- Decision history
```

### Task 6.17: Create 6_frontend/app/applications/[id]/workflow/page.tsx
```
Workflow visualization page:
- WorkflowCanvas (full screen)
- Step details panel
- Real-time updates via WebSocket
- Step history timeline
```

### Task 6.18: Create 6_frontend/app/applications/[id]/analyst/page.tsx
```
AI Analyst workbench page:
- Split view: documents + chat
- Risk metrics sidebar
- Action buttons (Approve, Decline, Request Docs)
- Note adding
```

### Task 6.19: Create 6_frontend/app/monitoring/page.tsx
```
Monitoring dashboard:
- Model performance charts
- Drift detection charts
- Alert list
- Quick actions
```

### Task 6.20: Create 6_frontend/start.sh
```
Frontend startup script:
- Build Next.js (if not pre-built)
- Start Next.js server
- Configure port for CML Application
```

### Task 6.21: Create 6_frontend/build.sh
```
Build script:
- npm install
- npm run build
- Output to .next/
```

---

## PHASE 7: MONITORING

### Task 7.1: Create 7_monitoring/drift_detection.py
```
Scheduled drift detection job:
- Load recent predictions
- Calculate PSI vs baseline
- Calculate feature drift (CSI)
- Generate alerts if thresholds exceeded
- Save results to monitoring table
```

### Task 7.2: Create 7_monitoring/performance_tracker.py
```
Model performance tracking:
- Join predictions with actual outcomes (where available)
- Calculate realized AUC, Gini
- Track approval rates
- Generate performance report
```

### Task 7.3: Create 7_monitoring/alert_handler.py
```
Alert handling:
- Check for new alerts
- Send notifications (log, email placeholder)
- Update alert status
```

---

## PHASE 8: CDE JOBS (Optional - for production)

### Task 8.1: Create 8_cde_jobs/spark_jobs/feature_engineering.py
```
Spark version of feature pipeline:
- Read from Iceberg tables
- Distributed feature computation
- Write to feature table
```

### Task 8.2: Create 8_cde_jobs/spark_jobs/batch_scoring.py
```
Batch scoring job:
- Score all active loans
- Update risk metrics
- Flag deteriorating credits
```

### Task 8.3: Create 8_cde_jobs/airflow_dags/credit_workflow_dag.py
```
Airflow DAG for credit workflow:
- Trigger on new application
- Orchestrate CML model calls
- Update status
```

### Task 8.4: Create 8_cde_jobs/airflow_dags/retraining_dag.py
```
Airflow DAG for model retraining:
- Trigger on drift alert or schedule
- Run training pipeline
- Validate new model
- Deploy if passes validation
```

---

## PHASE 9: DEPLOYMENT & TESTING

### Task 9.1: Create 9_deployment/deploy_all.py
```
Master deployment script:
- Deploy models to CML endpoints
- Deploy applications
- Configure environment variables
- Verify deployments
```

### Task 9.2: Create 9_deployment/configs/
```
Configuration files:
- model_endpoints.yaml
- applications.yaml
- environment variables template
```

### Task 9.3: Create tests/
```
Test suite:
- test_models/ - Model prediction tests
- test_agents/ - LangGraph node tests
- test_api/ - API endpoint tests
- test_e2e/ - End-to-end workflow tests
```

### Task 9.4: Create docs/
```
Documentation:
- architecture.md - System architecture
- api_reference.md - API documentation
- deployment_guide.md - Deployment instructions
- user_guide.md - User manual
```

---

## PHASE 10: FINAL INTEGRATION

### Task 10.1: Update .project-metadata.yaml
```
Complete the CML AMP configuration:
- All tasks in order
- All model endpoints
- All applications
- Environment variables
```

### Task 10.2: Create README.md
```
Project README:
- Overview
- Quick start
- Architecture diagram
- Configuration
- Development setup
```

### Task 10.3: End-to-end testing
```
Test complete flow:
1. Generate synthetic data
2. Train models
3. Deploy endpoints
4. Start applications
5. Create new application via UI
6. Watch workflow execute
7. Complete analyst review
8. Verify decision logged
```

---

## Execution Notes for Claude Code

1. **Execute phases in order** - Each phase depends on the previous
2. **Test incrementally** - Test each component before moving on
3. **Use placeholder LLM calls** - If Claude API not available, mock responses
4. **Database flexibility** - Use SQLite for local dev, can swap to Iceberg
5. **Frontend can be simplified** - Start with core pages, add polish later
6. **Skip CDE jobs initially** - Phase 8 is optional for demo

## Priority Order (MVP)

If time is limited, prioritize:
1. Phase 1 (Data) - Need data for everything
2. Phase 3 (Models) - Core ML functionality
3. Phase 4 (Endpoints) - Enable model serving
4. Phase 5.1-5.7 (Backend core) - LangGraph workflow
5. Phase 6.5-6.6 (Workflow UI) - Visual workflow
6. Phase 5.8-5.13 (Backend API) - Complete API
7. Phase 6 remaining (Full UI)

---

## File Dependencies

```
generate_synthetic.py → load_to_iceberg.py → feature_pipeline.py
                                                      ↓
                                            train_pd_model.py
                                            train_lgd_model.py
                                                      ↓
                                            serve_pd.py
                                            serve_lgd.py
                                            serve_risk_engine.py
                                                      ↓
                                            agents/graph.py
                                                      ↓
                                            main.py (FastAPI)
                                                      ↓
                                            Frontend (React)