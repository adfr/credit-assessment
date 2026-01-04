// Application Types
export interface Application {
  application_id: string;
  company_name: string;
  industry: string;
  requested_amount: number;
  requested_term_months: number;
  purpose: string;
  collateral_type?: string;
  collateral_value?: number;
  annual_revenue?: number;
  net_income?: number;
  total_assets?: number;
  total_liabilities?: number;
  status: ApplicationStatus;
  workflow_id?: string;
  documents_json?: string;
  submitted_at: string;
  updated_at: string;
}

export type ApplicationStatus =
  | "pending"
  | "processing"
  | "under_review"
  | "approved"
  | "declined"
  | "cancelled";

export interface ApplicationCreate {
  company_name: string;
  industry: string;
  requested_amount: number;
  requested_term_months: number;
  purpose: string;
  collateral_type?: string;
  collateral_value?: number;
  annual_revenue?: number;
  net_income?: number;
  total_assets?: number;
  total_liabilities?: number;
  documents?: string[];
}

// Workflow Types
export interface WorkflowStep {
  name: string;
  label: string;
  status: WorkflowStepStatus;
  started_at?: string;
  completed_at?: string;
  data?: Record<string, unknown>;
}

export type WorkflowStepStatus = "pending" | "in_progress" | "completed" | "failed";

export interface Workflow {
  workflow_id: string;
  application_id: string;
  status: string;
  current_step: string;
  steps_completed: string[];
  started_at: string;
  completed_at?: string;
  human_decision?: HumanDecision;
  final_state?: Record<string, unknown>;
}

export interface HumanDecision {
  decision: string;
  notes?: string;
  timestamp: string;
}

// Risk Types
export interface RiskScores {
  pd_score: number;
  lgd_score: number;
  ead: number;
  expected_loss: number;
  unexpected_loss?: number;
  economic_capital?: number;
  regulatory_capital?: number;
  rorac?: number;
}

export interface RiskMetrics extends RiskScores {
  risk_grade: RiskGrade;
}

export type RiskGrade =
  | "AAA"
  | "AA"
  | "A"
  | "BBB"
  | "BB"
  | "B"
  | "CCC"
  | "CC"
  | "C"
  | "D";

// Decision Types
export interface Decision {
  application_id: string;
  final_decision: DecisionOutcome;
  decision_type: DecisionType;
  decision_reason?: string;
  conditions_json?: string;
  approved_by: string;
  approved_amount?: number;
  approved_rate?: number;
  approved_term_months?: number;
  pd_at_decision?: number;
  lgd_at_decision?: number;
  el_at_decision?: number;
  decided_at: string;
}

export type DecisionOutcome = "APPROVE" | "DECLINE" | "REFER";
export type DecisionType = "auto" | "manual" | "manual_override";

export interface DecisionOverride {
  decision: "approve" | "decline";
  reason: string;
  approved_by: string;
  approved_amount?: number;
  approved_rate?: number;
  approved_term_months?: number;
  conditions?: string[];
}

// Chat/Analyst Types
export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
  sources?: PolicySource[];
}

export interface PolicySource {
  title: string;
  category: string;
  relevance_score?: number;
}

export interface AnalystQuery {
  question: string;
  application_id?: string;
  risk_context?: RiskScores;
  n_results?: number;
}

// API Response Types
export interface ApiResponse<T> {
  status: "success" | "error";
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

// WebSocket Types
export interface WebSocketMessage {
  type: string;
  application_id?: string;
  data?: Record<string, unknown>;
  timestamp: string;
}

export interface WorkflowUpdate extends WebSocketMessage {
  type: "workflow_update";
  step_name: string;
  step_status: WorkflowStepStatus;
}

export interface DecisionNotification extends WebSocketMessage {
  type: "decision";
  decision: DecisionOutcome;
  decision_type: DecisionType;
  reason?: string;
}

// Dashboard Types
export interface DashboardStats {
  total_applications: number;
  pending_applications: number;
  approved_applications: number;
  declined_applications: number;
  average_processing_time: number;
  approval_rate: number;
}

export interface RecentActivity {
  id: string;
  type: "application" | "decision" | "workflow";
  description: string;
  timestamp: string;
  application_id?: string;
}
