const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

// Applications API
export const applicationsApi = {
  list: (params?: { status?: string; limit?: number; offset?: number }) => {
    const query = new URLSearchParams();
    if (params?.status) query.set("status", params.status);
    if (params?.limit) query.set("limit", params.limit.toString());
    if (params?.offset) query.set("offset", params.offset.toString());
    const queryStr = query.toString();
    return fetchApi<{ applications: unknown[]; count: number }>(
      `/applications${queryStr ? `?${queryStr}` : ""}`
    );
  },

  get: (id: string) => fetchApi<{ application: unknown }>(`/applications/${id}`),

  create: (data: unknown) =>
    fetchApi<{ application_id: string }>("/applications", {
      method: "POST",
      body: data,
    }),

  updateStatus: (id: string, status: string, workflowId?: string) =>
    fetchApi<{ message: string }>(`/applications/${id}/status`, {
      method: "PUT",
      body: { status, workflow_id: workflowId },
    }),
};

// Workflow API
export const workflowApi = {
  start: (applicationId: string, autoApprove: boolean = true) =>
    fetchApi<{ workflow_id: string }>("/workflow/start", {
      method: "POST",
      body: { application_id: applicationId, auto_approve: autoApprove },
    }),

  getStatus: (workflowId: string) =>
    fetchApi<{ workflow: unknown }>(`/workflow/${workflowId}`),

  getSteps: (workflowId: string) =>
    fetchApi<{ steps: unknown[]; current_step: string }>(`/workflow/${workflowId}/steps`),

  resume: (workflowId: string, decision: string, notes?: string) =>
    fetchApi<{ message: string }>(`/workflow/${workflowId}/resume`, {
      method: "POST",
      body: { workflow_id: workflowId, decision, notes },
    }),

  cancel: (workflowId: string) =>
    fetchApi<{ message: string }>(`/workflow/${workflowId}/cancel`, {
      method: "POST",
    }),

  list: (status?: string) => {
    const query = status ? `?status=${status}` : "";
    return fetchApi<{ workflows: unknown[] }>(`/workflow${query}`);
  },
};

// Analyst API
export const analystApi = {
  chat: (message: string, applicationId?: string, includeRiskContext: boolean = true) =>
    fetchApi<{ message: unknown; sources: unknown[] }>("/analyst/chat", {
      method: "POST",
      body: {
        message,
        application_id: applicationId,
        include_risk_context: includeRiskContext,
      },
    }),

  queryPolicies: (question: string, nResults: number = 5) =>
    fetchApi<{ answer: string; sources: unknown[] }>("/analyst/query-policies", {
      method: "POST",
      body: { question, n_results: nResults },
    }),

  getSuggestions: (applicationId: string) =>
    fetchApi<{ suggestions: string[] }>("/analyst/suggestions", {
      method: "POST",
      body: { application_id: applicationId },
    }),

  getRiskSummary: (applicationId: string) =>
    fetchApi<{ summary: unknown }>(`/analyst/${applicationId}/risk-summary`),
};

// Decisions API
export const decisionsApi = {
  get: (applicationId: string) =>
    fetchApi<{ decision: unknown }>(`/decisions/${applicationId}`),

  create: (data: unknown) =>
    fetchApi<{ message: string }>("/decisions", {
      method: "POST",
      body: data,
    }),

  override: (applicationId: string, data: unknown) =>
    fetchApi<{ message: string; override: unknown }>(`/decisions/${applicationId}/override`, {
      method: "PUT",
      body: data,
    }),

  getRecommendation: (applicationId: string) =>
    fetchApi<{ recommendation: unknown; risk_metrics: unknown }>(
      `/decisions/${applicationId}/recommendation`
    ),

  getStats: () => fetchApi<{ stats: unknown }>("/decisions/stats/summary"),
};

// WebSocket helper
export function createWebSocket(
  endpoint: string,
  onMessage: (data: unknown) => void,
  onError?: (error: Event) => void,
  onClose?: () => void
): WebSocket {
  const wsUrl = API_BASE_URL.replace(/^http/, "ws");
  const ws = new WebSocket(`${wsUrl}${endpoint}`);

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    onMessage(data);
  };

  ws.onerror = (error) => {
    console.error("WebSocket error:", error);
    onError?.(error);
  };

  ws.onclose = () => {
    console.log("WebSocket closed");
    onClose?.();
  };

  return ws;
}
