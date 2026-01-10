"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { modelsApi, monitoringApi, ModelInfo } from "@/lib/api";

interface MonitoringData {
  pd_model: {
    status: string;
    model_id?: string;
    model_name?: string;
    version?: string;
    framework?: string;
    trained_at?: string;
    auc_roc?: number;
    gini?: number;
    ks_statistic?: number;
    brier_score?: number;
    log_loss?: number;
  };
  lgd_model: {
    status: string;
    model_id?: string;
    model_name?: string;
    version?: string;
    framework?: string;
    trained_at?: string;
    mse?: number;
    rmse?: number;
    mae?: number;
    r2?: number;
  };
  models_summary: {
    total_pd_models: number;
    total_lgd_models: number;
    active_pd: string | null;
    active_lgd: string | null;
  };
  system: {
    uptime_seconds: number;
    total_requests: number;
    total_errors: number;
    error_rate_percent: number;
    avg_latency_ms: number;
    loans_count: number;
    total_exposure: number;
  };
}

export default function MonitoringPage() {
  const [activeTab, setActiveTab] = useState("overview");
  const [metrics, setMetrics] = useState<MonitoringData | null>(null);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activating, setActivating] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [metricsData, modelsData] = await Promise.all([
        monitoringApi.getMetrics(),
        modelsApi.list(),
      ]);
      setMetrics(metricsData);
      setModels(modelsData.models);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleActivateModel = async (modelId: string) => {
    try {
      setActivating(modelId);
      await modelsApi.activate(modelId);
      await fetchData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to activate model");
    } finally {
      setActivating(null);
    }
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
      case "active":
        return "bg-green-100 text-green-800";
      case "warning":
      case "candidate":
        return "bg-yellow-100 text-yellow-800";
      case "critical":
      case "deprecated":
        return "bg-red-100 text-red-800";
      case "inactive":
        return "bg-gray-100 text-gray-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  const pdModels = models.filter((m) => m.model_type === "pd");
  const lgdModels = models.filter((m) => m.model_type === "lgd");

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Model Management</h1>
          <p className="text-gray-500">Monitor models, performance, and drift detection</p>
        </div>
        <Button variant="outline" onClick={fetchData}>
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
          <TabsTrigger value="models">Models ({models.length})</TabsTrigger>
          <TabsTrigger value="drift">Drift Detection</TabsTrigger>
          <TabsTrigger value="alerts">Alerts</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          {loading && !metrics && (
            <div className="text-center py-8 text-gray-500">Loading metrics...</div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
              {error}
            </div>
          )}

          {metrics && (
            <>
              {/* Models Summary */}
              <div className="grid grid-cols-4 gap-4">
                <Card className="bg-blue-50">
                  <CardContent className="pt-6">
                    <p className="text-sm text-blue-600">Total PD Models</p>
                    <p className="text-3xl font-bold text-blue-900">{metrics.models_summary?.total_pd_models || 0}</p>
                    <p className="text-xs text-blue-600 mt-1">Active: {metrics.models_summary?.active_pd || "None"}</p>
                  </CardContent>
                </Card>
                <Card className="bg-purple-50">
                  <CardContent className="pt-6">
                    <p className="text-sm text-purple-600">Total LGD Models</p>
                    <p className="text-3xl font-bold text-purple-900">{metrics.models_summary?.total_lgd_models || 0}</p>
                    <p className="text-xs text-purple-600 mt-1">Active: {metrics.models_summary?.active_lgd || "None"}</p>
                  </CardContent>
                </Card>
                <Card className="bg-green-50">
                  <CardContent className="pt-6">
                    <p className="text-sm text-green-600">Loans Scored</p>
                    <p className="text-3xl font-bold text-green-900">{metrics.system.loans_count}</p>
                    <p className="text-xs text-green-600 mt-1">Total in portfolio</p>
                  </CardContent>
                </Card>
                <Card className="bg-gray-50">
                  <CardContent className="pt-6">
                    <p className="text-sm text-gray-600">API Requests</p>
                    <p className="text-3xl font-bold text-gray-900">{metrics.system.total_requests}</p>
                    <p className="text-xs text-gray-600 mt-1">Error rate: {metrics.system.error_rate_percent}%</p>
                  </CardContent>
                </Card>
              </div>

              {/* Active Model Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* PD Model */}
                <Card>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle>Active PD Model</CardTitle>
                      <Badge className={getStatusColor(metrics.pd_model.status)}>
                        {metrics.pd_model.status}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent>
                    {metrics.pd_model.model_name ? (
                      <>
                        <div className="mb-4">
                          <p className="text-lg font-semibold">{metrics.pd_model.model_name}</p>
                          <p className="text-sm text-gray-500">
                            Version {metrics.pd_model.version} | {metrics.pd_model.framework}
                          </p>
                        </div>
                        <div className="grid grid-cols-3 gap-4">
                          <div>
                            <p className="text-sm text-gray-500">AUC-ROC</p>
                            <p className="text-2xl font-bold">
                              {metrics.pd_model.auc_roc?.toFixed(3) || "N/A"}
                            </p>
                          </div>
                          <div>
                            <p className="text-sm text-gray-500">Gini</p>
                            <p className="text-2xl font-bold">
                              {metrics.pd_model.gini?.toFixed(3) || "N/A"}
                            </p>
                          </div>
                          <div>
                            <p className="text-sm text-gray-500">KS Statistic</p>
                            <p className="text-2xl font-bold">
                              {metrics.pd_model.ks_statistic?.toFixed(3) || "N/A"}
                            </p>
                          </div>
                        </div>
                        <p className="text-xs text-gray-400 mt-4">
                          Trained:{" "}
                          {metrics.pd_model.trained_at
                            ? new Date(metrics.pd_model.trained_at).toLocaleDateString()
                            : "N/A"}
                        </p>
                      </>
                    ) : (
                      <p className="text-gray-500">No active PD model. Select one from the Models tab.</p>
                    )}
                  </CardContent>
                </Card>

                {/* LGD Model */}
                <Card>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle>Active LGD Model</CardTitle>
                      <Badge className={getStatusColor(metrics.lgd_model.status)}>
                        {metrics.lgd_model.status}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent>
                    {metrics.lgd_model.model_name ? (
                      <>
                        <div className="mb-4">
                          <p className="text-lg font-semibold">{metrics.lgd_model.model_name}</p>
                          <p className="text-sm text-gray-500">
                            Version {metrics.lgd_model.version} | {metrics.lgd_model.framework}
                          </p>
                        </div>
                        <div className="grid grid-cols-3 gap-4">
                          <div>
                            <p className="text-sm text-gray-500">R2 Score</p>
                            <p className="text-2xl font-bold">
                              {metrics.lgd_model.r2?.toFixed(3) || "N/A"}
                            </p>
                          </div>
                          <div>
                            <p className="text-sm text-gray-500">RMSE</p>
                            <p className="text-2xl font-bold">
                              {metrics.lgd_model.rmse?.toFixed(4) || "N/A"}
                            </p>
                          </div>
                          <div>
                            <p className="text-sm text-gray-500">MAE</p>
                            <p className="text-2xl font-bold">
                              {metrics.lgd_model.mae?.toFixed(4) || "N/A"}
                            </p>
                          </div>
                        </div>
                        <p className="text-xs text-gray-400 mt-4">
                          Trained:{" "}
                          {metrics.lgd_model.trained_at
                            ? new Date(metrics.lgd_model.trained_at).toLocaleDateString()
                            : "N/A"}
                        </p>
                      </>
                    ) : (
                      <p className="text-gray-500">No active LGD model. Select one from the Models tab.</p>
                    )}
                  </CardContent>
                </Card>
              </div>

              {/* System Health */}
              <Card>
                <CardHeader>
                  <CardTitle>System Health</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="text-center p-4 bg-green-50 rounded-lg">
                      <p className="text-sm text-gray-500">Uptime</p>
                      <p className="text-2xl font-bold text-green-600">
                        {Math.floor(metrics.system.uptime_seconds / 60)}m
                      </p>
                    </div>
                    <div className="text-center p-4 bg-green-50 rounded-lg">
                      <p className="text-sm text-gray-500">Avg Latency</p>
                      <p className="text-2xl font-bold text-green-600">
                        {metrics.system.avg_latency_ms.toFixed(0)}ms
                      </p>
                    </div>
                    <div className="text-center p-4 bg-blue-50 rounded-lg">
                      <p className="text-sm text-gray-500">Total Requests</p>
                      <p className="text-2xl font-bold text-blue-600">
                        {metrics.system.total_requests.toLocaleString()}
                      </p>
                    </div>
                    <div
                      className={`text-center p-4 rounded-lg ${
                        metrics.system.error_rate_percent > 1 ? "bg-red-50" : "bg-green-50"
                      }`}
                    >
                      <p className="text-sm text-gray-500">Error Rate</p>
                      <p
                        className={`text-2xl font-bold ${
                          metrics.system.error_rate_percent > 1 ? "text-red-600" : "text-green-600"
                        }`}
                      >
                        {metrics.system.error_rate_percent}%
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </>
          )}
        </TabsContent>

        <TabsContent value="models" className="space-y-6">
          {/* PD Models */}
          <Card>
            <CardHeader>
              <CardTitle>PD Models (Probability of Default)</CardTitle>
            </CardHeader>
            <CardContent>
              {pdModels.length === 0 ? (
                <p className="text-gray-500">No PD models registered.</p>
              ) : (
                <table className="w-full">
                  <thead>
                    <tr className="text-left text-sm text-gray-500 border-b">
                      <th className="pb-3">Model Name</th>
                      <th className="pb-3">Version</th>
                      <th className="pb-3">Framework</th>
                      <th className="pb-3">Status</th>
                      <th className="pb-3">Trained</th>
                      <th className="pb-3">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pdModels.map((model) => (
                      <tr key={model.model_id} className="border-b last:border-0">
                        <td className="py-3 font-medium">{model.model_name}</td>
                        <td className="py-3">{model.version}</td>
                        <td className="py-3">{model.framework}</td>
                        <td className="py-3">
                          <Badge className={getStatusColor(model.status)}>{model.status}</Badge>
                        </td>
                        <td className="py-3 text-sm text-gray-500">
                          {model.training_date
                            ? new Date(model.training_date).toLocaleDateString()
                            : "N/A"}
                        </td>
                        <td className="py-3">
                          {model.status !== "active" && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleActivateModel(model.model_id)}
                              disabled={activating === model.model_id}
                            >
                              {activating === model.model_id ? "Activating..." : "Activate"}
                            </Button>
                          )}
                          {model.status === "active" && (
                            <span className="text-green-600 text-sm font-medium">Currently Active</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </CardContent>
          </Card>

          {/* LGD Models */}
          <Card>
            <CardHeader>
              <CardTitle>LGD Models (Loss Given Default)</CardTitle>
            </CardHeader>
            <CardContent>
              {lgdModels.length === 0 ? (
                <p className="text-gray-500">No LGD models registered.</p>
              ) : (
                <table className="w-full">
                  <thead>
                    <tr className="text-left text-sm text-gray-500 border-b">
                      <th className="pb-3">Model Name</th>
                      <th className="pb-3">Version</th>
                      <th className="pb-3">Framework</th>
                      <th className="pb-3">Status</th>
                      <th className="pb-3">Trained</th>
                      <th className="pb-3">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {lgdModels.map((model) => (
                      <tr key={model.model_id} className="border-b last:border-0">
                        <td className="py-3 font-medium">{model.model_name}</td>
                        <td className="py-3">{model.version}</td>
                        <td className="py-3">{model.framework}</td>
                        <td className="py-3">
                          <Badge className={getStatusColor(model.status)}>{model.status}</Badge>
                        </td>
                        <td className="py-3 text-sm text-gray-500">
                          {model.training_date
                            ? new Date(model.training_date).toLocaleDateString()
                            : "N/A"}
                        </td>
                        <td className="py-3">
                          {model.status !== "active" && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleActivateModel(model.model_id)}
                              disabled={activating === model.model_id}
                            >
                              {activating === model.model_id ? "Activating..." : "Activate"}
                            </Button>
                          )}
                          {model.status === "active" && (
                            <span className="text-green-600 text-sm font-medium">Currently Active</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
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
                      <td className="py-3 font-medium">{metric.feature.replace(/_/g, " ")}</td>
                      <td className="py-3">{metric.psi.toFixed(3)}</td>
                      <td className="py-3">
                        <Badge className={getStatusColor(metric.status)}>{metric.status}</Badge>
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
                  <li>PSI &lt; 0.1: No significant drift (stable)</li>
                  <li>0.1 &le; PSI &lt; 0.2: Moderate drift (warning)</li>
                  <li>PSI &ge; 0.2: Significant drift (requires action)</li>
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
                          <span className="text-xs text-gray-500">{alert.timestamp}</span>
                        </div>
                        <p className="mt-2 text-sm text-gray-700">{alert.message}</p>
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
