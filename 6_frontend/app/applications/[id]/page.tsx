"use client";

import { useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { RiskMetrics } from "@/components/analyst/RiskMetrics";
import { useApplications } from "@/hooks/useApplications";
import { formatCurrency, formatDate } from "@/lib/utils";

export default function ApplicationDetailPage() {
  const params = useParams();
  const applicationId = params.id as string;

  const {
    currentApplication,
    decision,
    isLoading,
    error,
    getApplication,
    getDecision,
  } = useApplications();

  useEffect(() => {
    if (applicationId) {
      getApplication(applicationId);
      getDecision(applicationId).catch(() => {
        // Decision might not exist yet
      });
    }
  }, [applicationId, getApplication, getDecision]);

  const getStatusVariant = (status: string): "success" | "warning" | "destructive" | "secondary" | "default" => {
    switch (status?.toLowerCase()) {
      case "approved":
        return "success";
      case "declined":
        return "destructive";
      case "processing":
      case "under_review":
        return "warning";
      case "pending":
        return "default";
      default:
        return "secondary";
    }
  };

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-gray-200 rounded w-1/4" />
          <div className="h-48 bg-gray-200 rounded" />
          <div className="h-48 bg-gray-200 rounded" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-700">{error}</p>
        </div>
      </div>
    );
  }

  if (!currentApplication) {
    return (
      <div className="p-6">
        <p className="text-gray-500">Application not found</p>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center space-x-3">
            <h1 className="text-2xl font-bold text-gray-900">
              {currentApplication.company_name}
            </h1>
            <Badge variant={getStatusVariant(currentApplication.status)}>
              {currentApplication.status}
            </Badge>
          </div>
          <p className="text-gray-500">
            Application ID: {currentApplication.application_id}
          </p>
        </div>
        <div className="flex space-x-3">
          <Link href={`/applications/${applicationId}/workflow`}>
            <Button variant="outline">View Workflow</Button>
          </Link>
          <Link href={`/applications/${applicationId}/analyst`}>
            <Button>AI Analyst</Button>
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Loan Details */}
          <Card>
            <CardHeader>
              <CardTitle>Loan Details</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="grid grid-cols-2 gap-4">
                <div>
                  <dt className="text-sm text-gray-500">Requested Amount</dt>
                  <dd className="text-lg font-semibold">
                    {formatCurrency(currentApplication.requested_amount)}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm text-gray-500">Term</dt>
                  <dd className="text-lg font-semibold">
                    {currentApplication.requested_term_months} months
                  </dd>
                </div>
                <div>
                  <dt className="text-sm text-gray-500">Purpose</dt>
                  <dd className="text-lg font-semibold capitalize">
                    {currentApplication.purpose?.replace(/_/g, " ")}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm text-gray-500">Industry</dt>
                  <dd className="text-lg font-semibold capitalize">
                    {currentApplication.industry}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm text-gray-500">Collateral Type</dt>
                  <dd className="text-lg font-semibold capitalize">
                    {currentApplication.collateral_type?.replace(/_/g, " ") || "None"}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm text-gray-500">Collateral Value</dt>
                  <dd className="text-lg font-semibold">
                    {currentApplication.collateral_value
                      ? formatCurrency(currentApplication.collateral_value)
                      : "N/A"}
                  </dd>
                </div>
              </dl>
            </CardContent>
          </Card>

          {/* Financial Information */}
          <Card>
            <CardHeader>
              <CardTitle>Financial Information</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="grid grid-cols-2 gap-4">
                <div>
                  <dt className="text-sm text-gray-500">Annual Revenue</dt>
                  <dd className="text-lg font-semibold">
                    {formatCurrency(currentApplication.annual_revenue || 0)}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm text-gray-500">Net Income</dt>
                  <dd className="text-lg font-semibold">
                    {formatCurrency(currentApplication.net_income || 0)}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm text-gray-500">Total Assets</dt>
                  <dd className="text-lg font-semibold">
                    {formatCurrency(currentApplication.total_assets || 0)}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm text-gray-500">Total Liabilities</dt>
                  <dd className="text-lg font-semibold">
                    {formatCurrency(currentApplication.total_liabilities || 0)}
                  </dd>
                </div>
              </dl>
            </CardContent>
          </Card>

          {/* Decision */}
          {decision && (
            <Card>
              <CardHeader>
                <CardTitle>Decision</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center space-x-3">
                    <Badge
                      variant={
                        decision.final_decision === "APPROVE"
                          ? "success"
                          : decision.final_decision === "DECLINE"
                          ? "destructive"
                          : "warning"
                      }
                      className="text-lg px-4 py-1"
                    >
                      {decision.final_decision}
                    </Badge>
                    <span className="text-sm text-gray-500">
                      ({decision.decision_type})
                    </span>
                  </div>
                  {decision.decision_reason && (
                    <p className="text-gray-700">{decision.decision_reason}</p>
                  )}
                  {decision.approved_amount && (
                    <p className="text-sm text-gray-500">
                      Approved Amount: {formatCurrency(decision.approved_amount)}
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Risk Metrics */}
          {decision && (
            <RiskMetrics
              pdScore={decision.pd_at_decision}
              lgdScore={decision.lgd_at_decision}
              expectedLoss={decision.el_at_decision}
            />
          )}

          {/* Timeline */}
          <Card>
            <CardHeader>
              <CardTitle>Timeline</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-start space-x-3">
                  <div className="h-2 w-2 mt-2 rounded-full bg-blue-600" />
                  <div>
                    <p className="text-sm font-medium">Submitted</p>
                    <p className="text-xs text-gray-500">
                      {formatDate(currentApplication.submitted_at)}
                    </p>
                  </div>
                </div>
                <div className="flex items-start space-x-3">
                  <div className="h-2 w-2 mt-2 rounded-full bg-gray-300" />
                  <div>
                    <p className="text-sm font-medium">Last Updated</p>
                    <p className="text-xs text-gray-500">
                      {formatDate(currentApplication.updated_at)}
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
