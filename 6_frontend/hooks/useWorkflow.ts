"use client";

import { useState, useCallback, useEffect } from "react";
import { workflowApi, createWebSocket } from "@/lib/api";

interface WorkflowStep {
  name: string;
  label: string;
  status: "pending" | "in_progress" | "completed" | "failed";
}

interface WorkflowState {
  workflowId: string | null;
  status: string;
  currentStep: string | null;
  steps: WorkflowStep[];
  error: string | null;
}

export function useWorkflow(applicationId: string) {
  const [state, setState] = useState<WorkflowState>({
    workflowId: null,
    status: "idle",
    currentStep: null,
    steps: [],
    error: null,
  });

  const [isLoading, setIsLoading] = useState(false);

  // Start a new workflow
  const startWorkflow = useCallback(async (autoApprove: boolean = true) => {
    setIsLoading(true);
    setState((prev) => ({ ...prev, error: null }));

    try {
      const result = await workflowApi.start(applicationId, autoApprove);

      setState((prev) => ({
        ...prev,
        workflowId: result.workflow_id,
        status: "started",
      }));

      return result.workflow_id;
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to start workflow";
      setState((prev) => ({ ...prev, error: message }));
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, [applicationId]);

  // Get workflow status
  const getStatus = useCallback(async (workflowId: string) => {
    try {
      const result = await workflowApi.getStatus(workflowId);
      setState((prev) => ({
        ...prev,
        status: (result.workflow as { status?: string })?.status || "unknown",
      }));
      return result.workflow;
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to get workflow status";
      setState((prev) => ({ ...prev, error: message }));
      throw error;
    }
  }, []);

  // Get workflow steps
  const getSteps = useCallback(async (workflowId: string) => {
    try {
      const result = await workflowApi.getSteps(workflowId);
      setState((prev) => ({
        ...prev,
        steps: result.steps as WorkflowStep[],
        currentStep: result.current_step,
      }));
      return result.steps;
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to get workflow steps";
      setState((prev) => ({ ...prev, error: message }));
      throw error;
    }
  }, []);

  // Resume workflow with human decision
  const resumeWorkflow = useCallback(async (
    workflowId: string,
    decision: string,
    notes?: string
  ) => {
    setIsLoading(true);

    try {
      await workflowApi.resume(workflowId, decision, notes);
      setState((prev) => ({ ...prev, status: "resuming" }));
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to resume workflow";
      setState((prev) => ({ ...prev, error: message }));
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Cancel workflow
  const cancelWorkflow = useCallback(async (workflowId: string) => {
    setIsLoading(true);

    try {
      await workflowApi.cancel(workflowId);
      setState((prev) => ({ ...prev, status: "cancelled" }));
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to cancel workflow";
      setState((prev) => ({ ...prev, error: message }));
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Subscribe to workflow updates via WebSocket
  const subscribeToUpdates = useCallback((workflowId: string) => {
    const ws = createWebSocket(
      `/ws/workflow/${applicationId}`,
      (data: unknown) => {
        const message = data as { type?: string; step_name?: string; step_status?: string; status?: string };

        if (message.type === "workflow_update") {
          setState((prev) => ({
            ...prev,
            currentStep: message.step_name || prev.currentStep,
            steps: prev.steps.map((step) =>
              step.name === message.step_name
                ? { ...step, status: (message.step_status as WorkflowStep["status"]) || step.status }
                : step
            ),
          }));
        }

        if (message.type === "decision") {
          setState((prev) => ({
            ...prev,
            status: "completed",
          }));
        }
      },
      (error) => {
        console.error("WebSocket error:", error);
      }
    );

    return () => ws.close();
  }, [applicationId]);

  // Load workflow state on mount if workflowId exists
  useEffect(() => {
    if (state.workflowId) {
      getStatus(state.workflowId);
      getSteps(state.workflowId);
    }
  }, [state.workflowId, getStatus, getSteps]);

  return {
    ...state,
    isLoading,
    startWorkflow,
    getStatus,
    getSteps,
    resumeWorkflow,
    cancelWorkflow,
    subscribeToUpdates,
  };
}
