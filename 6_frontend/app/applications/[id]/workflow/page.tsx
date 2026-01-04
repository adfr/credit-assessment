"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { WorkflowCanvas } from "@/components/workflow/WorkflowCanvas";
import { useWorkflow } from "@/hooks/useWorkflow";
import { useApplications } from "@/hooks/useApplications";

export default function WorkflowPage() {
  const params = useParams();
  const applicationId = params.id as string;

  const {
    workflowId,
    status: workflowStatus,
    currentStep,
    steps,
    isLoading: workflowLoading,
    error: workflowError,
    startWorkflow,
    getSteps,
    subscribeToUpdates,
  } = useWorkflow(applicationId);

  const { currentApplication, getApplication } = useApplications();

  const [isStarting, setIsStarting] = useState(false);

  useEffect(() => {
    getApplication(applicationId);
  }, [applicationId, getApplication]);

  useEffect(() => {
    // If application has a workflow_id, load its steps
    if (currentApplication?.workflow_id) {
      getSteps(currentApplication.workflow_id);
    }
  }, [currentApplication, getSteps]);

  useEffect(() => {
    // Subscribe to real-time updates when workflow is running
    if (workflowId && workflowStatus === "started") {
      const unsubscribe = subscribeToUpdates(workflowId);
      return unsubscribe;
    }
  }, [workflowId, workflowStatus, subscribeToUpdates]);

  const handleStartWorkflow = async () => {
    setIsStarting(true);
    try {
      await startWorkflow(true);
    } catch (err) {
      console.error(err);
    } finally {
      setIsStarting(false);
    }
  };

  const defaultSteps = [
    { name: "document_processing", label: "Documents", status: "pending" as const },
    { name: "validation", label: "Validation", status: "pending" as const },
    { name: "enrichment", label: "Enrichment", status: "pending" as const },
    { name: "compliance", label: "Compliance", status: "pending" as const },
    { name: "scoring", label: "Scoring", status: "pending" as const },
    { name: "review", label: "Review", status: "pending" as const },
    { name: "decision", label: "Decision", status: "pending" as const },
  ];

  const displaySteps = steps.length > 0 ? steps : defaultSteps;
  const hasWorkflow = currentApplication?.workflow_id || workflowId;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Workflow</h1>
          <p className="text-gray-500">
            {currentApplication?.company_name || "Loading..."}
          </p>
        </div>
        <div className="flex items-center space-x-3">
          {workflowStatus && (
            <Badge
              variant={
                workflowStatus === "completed"
                  ? "success"
                  : workflowStatus === "failed"
                  ? "destructive"
                  : "default"
              }
            >
              {workflowStatus}
            </Badge>
          )}
          {!hasWorkflow && (
            <Button
              onClick={handleStartWorkflow}
              loading={isStarting || workflowLoading}
            >
              Start Workflow
            </Button>
          )}
        </div>
      </div>

      {/* Error */}
      {workflowError && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-700">{workflowError}</p>
        </div>
      )}

      {/* Workflow Canvas */}
      <Card>
        <CardHeader>
          <CardTitle>Workflow Progress</CardTitle>
        </CardHeader>
        <CardContent>
          <WorkflowCanvas
            steps={displaySteps}
            currentStep={currentStep || undefined}
          />
        </CardContent>
      </Card>

      {/* Step Details */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {displaySteps.map((step) => (
          <Card key={step.name}>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-medium">{step.label}</h3>
                  <p className="text-sm text-gray-500 capitalize">
                    {step.status.replace("_", " ")}
                  </p>
                </div>
                <div
                  className={`h-3 w-3 rounded-full ${
                    step.status === "completed"
                      ? "bg-green-500"
                      : step.status === "in_progress"
                      ? "bg-blue-500 animate-pulse"
                      : step.status === "failed"
                      ? "bg-red-500"
                      : "bg-gray-300"
                  }`}
                />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Human Review Panel */}
      {currentStep === "review" && (
        <Card className="border-yellow-200 bg-yellow-50">
          <CardHeader>
            <CardTitle className="text-yellow-800">
              Human Review Required
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-yellow-700 mb-4">
              This application requires manual review before a decision can be made.
            </p>
            <div className="flex space-x-3">
              <Button variant="default">Approve</Button>
              <Button variant="destructive">Decline</Button>
              <Button variant="outline">Request More Info</Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
