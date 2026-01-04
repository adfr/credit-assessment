"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function MonitoringPage() {
  const [activeTab, setActiveTab] = useState("overview");

  // Mock data - in production, this would come from the API
  const modelMetrics = {
    pd_model: {
      name: "PD Model",
      version: "1.0",
      auc: 0.847,
      gini: 0.694,
      ks: 0.521,
      lastUpdated: "2024-01-15",
      status: "healthy",
    },
    lgd_model: {
      name: "LGD Model",
      version: "1.0",
      mse: 0.0234,
      r2: 0.782,
      lastUpdated: "2024-01-15",
      status: "healthy",
    },
  };

  const driftMetrics = [
    { feature: "debt_to_equity", psi: 0.023, status: "stable" },
    { feature: "current_ratio", psi: 0.018, status: "stable" },
    { feature: "credit_score", psi: 0.089, status: "warning" },
    { feature: "industry_default_rate", psi: 0.012, status: "stable" },
    { feature: "utilization_rate", psi: 0.045, status: "stable" },
  ];

  const recentAlerts = [
    {
      id: 1,
      type: "drift",
      message: "Credit score distribution showing moderate drift (PSI: 0.089)",
      severity: "warning",
      timestamp: "2024-01-15 14:32:00",
    },
    {
      id: 2,
      type: "performance",
      message: "PD model AUC dropped below threshold (0.83)",
      severity: "warning",
      timestamp: "2024-01-14 09:15:00",
    },
    {
      id: 3,
      type: "system",
      message: "Model endpoint latency increased to 450ms",
      severity: "info",
      timestamp: "2024-01-13 16:45:00",
    },
  ];

  const getStatusColor = (status: string) => {
    switch (status) {
      case "healthy":
      case "stable":
        return "bg-green-100 text-green-800";
      case "warning":
        return "bg-yellow-100 text-yellow-800";
      case "critical":
        return "bg-red-100 text-red-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Monitoring</h1>
          <p className="text-gray-500">Model performance and drift detection</p>
        </div>
        <Button variant="outline">
          <svg
            className="h-4 w-4 mr-2"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
          Refresh
        </Button>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="drift">Drift Detection</TabsTrigger>
          <TabsTrigger value="alerts">Alerts</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          {/* Model Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* PD Model */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>{modelMetrics.pd_model.name}</CardTitle>
                  <Badge className={getStatusColor(modelMetrics.pd_model.status)}>
                    {modelMetrics.pd_model.status}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <p className="text-sm text-gray-500">AUC-ROC</p>
                    <p className="text-2xl font-bold">
                      {modelMetrics.pd_model.auc.toFixed(3)}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Gini</p>
                    <p className="text-2xl font-bold">
                      {modelMetrics.pd_model.gini.toFixed(3)}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">KS Statistic</p>
                    <p className="text-2xl font-bold">
                      {modelMetrics.pd_model.ks.toFixed(3)}
                    </p>
                  </div>
                </div>
                <p className="text-xs text-gray-400 mt-4">
                  Version {modelMetrics.pd_model.version} · Last updated{" "}
                  {modelMetrics.pd_model.lastUpdated}
                </p>
              </CardContent>
            </Card>

            {/* LGD Model */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>{modelMetrics.lgd_model.name}</CardTitle>
                  <Badge className={getStatusColor(modelMetrics.lgd_model.status)}>
                    {modelMetrics.lgd_model.status}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-gray-500">MSE</p>
                    <p className="text-2xl font-bold">
                      {modelMetrics.lgd_model.mse.toFixed(4)}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">R² Score</p>
                    <p className="text-2xl font-bold">
                      {modelMetrics.lgd_model.r2.toFixed(3)}
                    </p>
                  </div>
                </div>
                <p className="text-xs text-gray-400 mt-4">
                  Version {modelMetrics.lgd_model.version} · Last updated{" "}
                  {modelMetrics.lgd_model.lastUpdated}
                </p>
              </CardContent>
            </Card>
          </div>

          {/* System Health */}
          <Card>
            <CardHeader>
              <CardTitle>System Health</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-4 gap-4">
                <div className="text-center p-4 bg-green-50 rounded-lg">
                  <p className="text-sm text-gray-500">API Uptime</p>
                  <p className="text-2xl font-bold text-green-600">99.9%</p>
                </div>
                <div className="text-center p-4 bg-green-50 rounded-lg">
                  <p className="text-sm text-gray-500">Avg Latency</p>
                  <p className="text-2xl font-bold text-green-600">120ms</p>
                </div>
                <div className="text-center p-4 bg-green-50 rounded-lg">
                  <p className="text-sm text-gray-500">Requests/day</p>
                  <p className="text-2xl font-bold text-green-600">2,450</p>
                </div>
                <div className="text-center p-4 bg-yellow-50 rounded-lg">
                  <p className="text-sm text-gray-500">Error Rate</p>
                  <p className="text-2xl font-bold text-yellow-600">0.5%</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="drift" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Feature Drift Analysis</CardTitle>
            </CardHeader>
            <CardContent>
              <table className="w-full">
                <thead>
                  <tr className="text-left text-sm text-gray-500 border-b">
                    <th className="pb-3">Feature</th>
                    <th className="pb-3">PSI Score</th>
                    <th className="pb-3">Status</th>
                    <th className="pb-3">Threshold</th>
                  </tr>
                </thead>
                <tbody>
                  {driftMetrics.map((metric) => (
                    <tr key={metric.feature} className="border-b last:border-0">
                      <td className="py-3 font-medium">
                        {metric.feature.replace(/_/g, " ")}
                      </td>
                      <td className="py-3">{metric.psi.toFixed(3)}</td>
                      <td className="py-3">
                        <Badge className={getStatusColor(metric.status)}>
                          {metric.status}
                        </Badge>
                      </td>
                      <td className="py-3 text-gray-500">
                        {metric.psi < 0.1 ? "< 0.1" : metric.psi < 0.2 ? "< 0.2" : "> 0.2"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              <div className="mt-6 p-4 bg-gray-50 rounded-lg">
                <h4 className="font-medium mb-2">PSI Thresholds</h4>
                <ul className="text-sm text-gray-600 space-y-1">
                  <li>• PSI &lt; 0.1: No significant drift (stable)</li>
                  <li>• 0.1 ≤ PSI &lt; 0.2: Moderate drift (warning)</li>
                  <li>• PSI ≥ 0.2: Significant drift (requires action)</li>
                </ul>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="alerts" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Recent Alerts</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {recentAlerts.map((alert) => (
                  <div
                    key={alert.id}
                    className={`p-4 rounded-lg border-l-4 ${
                      alert.severity === "warning"
                        ? "bg-yellow-50 border-yellow-500"
                        : alert.severity === "critical"
                        ? "bg-red-50 border-red-500"
                        : "bg-blue-50 border-blue-500"
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center space-x-2">
                          <Badge
                            variant={
                              alert.severity === "warning"
                                ? "warning"
                                : alert.severity === "critical"
                                ? "destructive"
                                : "default"
                            }
                          >
                            {alert.type}
                          </Badge>
                          <span className="text-xs text-gray-500">
                            {alert.timestamp}
                          </span>
                        </div>
                        <p className="mt-2 text-sm text-gray-700">
                          {alert.message}
                        </p>
                      </div>
                      <Button variant="ghost" size="sm">
                        Dismiss
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
