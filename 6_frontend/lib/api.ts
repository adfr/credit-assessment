const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

interface ApiOptions {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  body?: unknown;
  headers?: Record<string, string>;
}

async function fetchApi<T>(endpoint: string, options: ApiOptions = {}): Promise<T> {
  const { method = "GET", body, headers = {} } = options;

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `API Error: ${response.status}`);
  }

  return response.json();
}

// Types
export interface Loan {
  loan_id: string;
  company_name: string;
  industry: string;
  region: string;
  country: string;
  original_balance: number;
  outstanding_balance: number;
  interest_rate: number;
  term_months: number;
  purpose: string;
  collateral_type: string;
  collateral_value: number;
  disbursement_date: string;
  maturity_date: string;
  last_payment_date: string;
  last_payment_amount: number;
  days_past_due: number;
  payment_status: string;
  status: string;
  pd_score: number;
  lgd_score: number;
  risk_grade: string;
  annual_revenue: number;
  net_income: number;
  total_assets: number;
  total_liabilities: number;
  regulatory_capital?: number;
  expected_loss?: number;
  risk_weighted_assets?: number;
}

export interface PortfolioSummary {
  loan_count: number;
  total_exposure: number;
  total_original: number;
  avg_pd: number;
  avg_lgd: number;
  avg_rate: number;
  active_count: number;
  defaulted_count: number;
  current_count: number;
  delinquent_count: number;
  default_count: number;
  regulatory_capital: number;
  economic_capital: number;
  expected_loss: number;
  var_999: number;
  risk_weighted_assets: number;
  reg_capital_ratio: number;
  econ_capital_ratio: number;
}

export interface CapitalMetrics {
  regulatory_capital: number;
  economic_capital: number;
  risk_weighted_assets: number;
  expected_loss: number;
  var_999: number;
  reg_capital_ratio: number;
  econ_capital_ratio: number;
  total_exposure: number;
}

export interface RiskDistribution {
  distribution: Array<{
    risk_grade: string;
    count: number;
    exposure: number;
    percentage: number;
    avg_pd: number;
  }>;
  total_exposure: number;
}

export interface ConcentrationData {
  dimension: string;
  hhi: number;
  concentration_level: string;
  breakdown: Array<{
    category: string;
    count: number;
    exposure: number;
    percentage: number;
    avg_pd: number;
    avg_lgd: number;
  }>;
  total_exposure: number;
}

export interface LargeExposures {
  threshold_pct: number;
  threshold_amount: number;
  total_exposure: number;
  count: number;
  exposures: Array<{
    loan_id: string;
    company_name: string;
    industry: string;
    outstanding_balance: number;
    percentage: number;
    risk_grade: string;
    pd_score: number;
  }>;
  total_large_exposure: number;
  large_exposure_pct: number;
}

export interface MigrationMatrix {
  period_months: number;
  grades: string[];
  matrix: Record<string, Record<string, number>>;
}

export interface VintageData {
  vintages: Array<{
    vintage: string;
    loan_count: number;
    original_volume: number;
    current_exposure: number;
    default_count: number;
    default_rate: number;
    default_exposure: number;
    loss_rate: number;
    avg_pd: number;
  }>;
  total_vintages: number;
}

export interface Repayment {
  repayment_id: number;
  loan_id: string;
  payment_date: string;
  payment_amount: number;
  principal_amount: number;
  interest_amount: number;
  balance_after: number;
  status: string;
}

export interface ChatResponse {
  message: string;
  sources: Array<{ title: string; category: string }>;
  portfolio_context: PortfolioSummary | null;
}

// Portfolio API
export const portfolioApi = {
  getSummary: () => fetchApi<PortfolioSummary>("/portfolio/summary"),

  getRiskDistribution: () => fetchApi<RiskDistribution>("/portfolio/risk-distribution"),

  getCapital: () => fetchApi<CapitalMetrics>("/portfolio/capital"),
};

// Loans API
export const loansApi = {
  list: (params?: {
    status?: string;
    risk_grade?: string;
    industry?: string;
    region?: string;
    payment_status?: string;
    limit?: number;
    offset?: number;
  }) => {
    const query = new URLSearchParams();
    if (params?.status) query.set("status", params.status);
    if (params?.risk_grade) query.set("risk_grade", params.risk_grade);
    if (params?.industry) query.set("industry", params.industry);
    if (params?.region) query.set("region", params.region);
    if (params?.payment_status) query.set("payment_status", params.payment_status);
    if (params?.limit) query.set("limit", params.limit.toString());
    if (params?.offset) query.set("offset", params.offset.toString());
    const queryStr = query.toString();
    return fetchApi<{ loans: Loan[]; total: number; limit: number; offset: number }>(
      `/loans${queryStr ? `?${queryStr}` : ""}`
    );
  },

  get: (id: string) => fetchApi<Loan>(`/loans/${id}`),

  getRepayments: (id: string) =>
    fetchApi<{ loan_id: string; repayments: Repayment[]; count: number }>(`/loans/${id}/repayments`),

  create: (data: {
    company_name: string;
    industry: string;
    region: string;
    country: string;
    loan_amount: number;
    interest_rate?: number;
    term_months?: number;
    purpose?: string;
    collateral_type?: string;
    collateral_value?: number;
    pd_score?: number;
    lgd_score?: number;
    risk_grade?: string;
  }) =>
    fetchApi<{ loan_id: string; message: string }>("/loans", {
      method: "POST",
      body: data,
    }),
};

// Analytics API
export const analyticsApi = {
  getConcentration: (dimension: string) =>
    fetchApi<ConcentrationData>(`/analytics/concentration/${dimension}`),

  getLargeExposures: (threshold?: number) => {
    const query = threshold ? `?threshold=${threshold}` : "";
    return fetchApi<LargeExposures>(`/analytics/large-exposures${query}`);
  },

  getMigrationMatrix: (period?: number) => {
    const query = period ? `?period=${period}` : "";
    return fetchApi<MigrationMatrix>(`/analytics/migration-matrix${query}`);
  },

  getVintageAnalysis: () => fetchApi<VintageData>("/analytics/vintage"),
};

// AI Assistant API
export const assistantApi = {
  chat: (message: string, includeContext: boolean = true) =>
    fetchApi<ChatResponse>("/assistant/chat", {
      method: "POST",
      body: { message, include_portfolio_context: includeContext },
    }),
};

// Monitoring API
export const monitoringApi = {
  getMetrics: () =>
    fetchApi<{
      pd_model: Record<string, unknown>;
      lgd_model: Record<string, unknown>;
      system: Record<string, unknown>;
    }>("/monitoring/metrics"),
};
