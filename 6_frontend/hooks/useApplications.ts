"use client";

import { useState, useCallback } from "react";
import { applicationsApi, decisionsApi } from "@/lib/api";

interface Application {
  application_id: string;
  company_name: string;
  industry: string;
  requested_amount: number;
  requested_term_months: number;
  purpose: string;
  collateral_type: string;
  collateral_value: number;
  annual_revenue: number;
  net_income: number;
  total_assets: number;
  total_liabilities: number;
  status: string;
  submitted_at: string;
  updated_at: string;
}

interface Decision {
  application_id: string;
  final_decision: string;
  decision_type: string;
  decision_reason: string;
  approved_amount?: number;
  approved_rate?: number;
  pd_at_decision?: number;
  lgd_at_decision?: number;
  el_at_decision?: number;
}

interface ApplicationsState {
  applications: Application[];
  currentApplication: Application | null;
  decision: Decision | null;
  isLoading: boolean;
  error: string | null;
}

export function useApplications() {
  const [state, setState] = useState<ApplicationsState>({
    applications: [],
    currentApplication: null,
    decision: null,
    isLoading: false,
    error: null,
  });

  // List applications
  const listApplications = useCallback(async (params?: {
    status?: string;
    limit?: number;
    offset?: number;
  }) => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));

    try {
      const result = await applicationsApi.list(params);
      setState((prev) => ({
        ...prev,
        applications: result.applications as Application[],
        isLoading: false,
      }));
      return result.applications;
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to list applications";
      setState((prev) => ({ ...prev, error: message, isLoading: false }));
      throw error;
    }
  }, []);

  // Get single application
  const getApplication = useCallback(async (id: string) => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));

    try {
      const result = await applicationsApi.get(id);
      const application = result.application as Application;
      setState((prev) => ({
        ...prev,
        currentApplication: application,
        isLoading: false,
      }));
      return application;
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to get application";
      setState((prev) => ({ ...prev, error: message, isLoading: false }));
      throw error;
    }
  }, []);

  // Create application
  const createApplication = useCallback(async (data: Partial<Application>) => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));

    try {
      const result = await applicationsApi.create(data);
      setState((prev) => ({ ...prev, isLoading: false }));
      return result.application_id;
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to create application";
      setState((prev) => ({ ...prev, error: message, isLoading: false }));
      throw error;
    }
  }, []);

  // Update application status
  const updateStatus = useCallback(async (
    id: string,
    status: string,
    workflowId?: string
  ) => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));

    try {
      await applicationsApi.updateStatus(id, status, workflowId);
      setState((prev) => ({
        ...prev,
        currentApplication: prev.currentApplication
          ? { ...prev.currentApplication, status }
          : null,
        applications: prev.applications.map((app) =>
          app.application_id === id ? { ...app, status } : app
        ),
        isLoading: false,
      }));
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to update status";
      setState((prev) => ({ ...prev, error: message, isLoading: false }));
      throw error;
    }
  }, []);

  // Get decision for application
  const getDecision = useCallback(async (applicationId: string) => {
    try {
      const result = await decisionsApi.get(applicationId);
      const decision = result.decision as Decision | null;
      setState((prev) => ({ ...prev, decision }));
      return decision;
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to get decision";
      setState((prev) => ({ ...prev, error: message }));
      throw error;
    }
  }, []);

  // Get decision recommendation
  const getRecommendation = useCallback(async (applicationId: string) => {
    try {
      const result = await decisionsApi.getRecommendation(applicationId);
      return {
        recommendation: result.recommendation,
        riskMetrics: result.risk_metrics,
      };
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to get recommendation";
      setState((prev) => ({ ...prev, error: message }));
      throw error;
    }
  }, []);

  // Clear current application
  const clearCurrentApplication = useCallback(() => {
    setState((prev) => ({
      ...prev,
      currentApplication: null,
      decision: null,
    }));
  }, []);

  // Clear error
  const clearError = useCallback(() => {
    setState((prev) => ({ ...prev, error: null }));
  }, []);

  return {
    ...state,
    listApplications,
    getApplication,
    createApplication,
    updateStatus,
    getDecision,
    getRecommendation,
    clearCurrentApplication,
    clearError,
  };
}
