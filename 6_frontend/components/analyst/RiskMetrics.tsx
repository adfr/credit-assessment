"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface RiskMetricsProps {
  pdScore?: number;
  lgdScore?: number;
  expectedLoss?: number;
  economicCapital?: number;
  regulatoryCapital?: number;
  rorac?: number;
  riskGrade?: string;
}

export function RiskMetrics({
  pdScore,
  lgdScore,
  expectedLoss,
  economicCapital,
  regulatoryCapital,
  rorac,
  riskGrade,
}: RiskMetricsProps) {
  const formatPercent = (value?: number) => {
    if (value === undefined || value === null) return "—";
    return `${(value * 100).toFixed(2)}%`;
  };

  const formatCurrency = (value?: number) => {
    if (value === undefined || value === null) return "—";
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const getRiskGradeVariant = (grade?: string): "success" | "warning" | "destructive" | "secondary" => {
    if (!grade) return "secondary";
    if (["AAA", "AA", "A"].includes(grade)) return "success";
    if (["BBB", "BB"].includes(grade)) return "warning";
    return "destructive";
  };

  const getPDColor = (pd?: number) => {
    if (pd === undefined) return "text-gray-500";
    if (pd < 0.03) return "text-green-600";
    if (pd < 0.10) return "text-yellow-600";
    return "text-red-600";
  };

  const metrics = [
    {
      label: "PD Score",
      value: formatPercent(pdScore),
      color: getPDColor(pdScore),
      description: "Probability of Default",
    },
    {
      label: "LGD Score",
      value: formatPercent(lgdScore),
      description: "Loss Given Default",
    },
    {
      label: "Expected Loss",
      value: formatCurrency(expectedLoss),
      description: "EL = PD × LGD × EAD",
    },
    {
      label: "Economic Capital",
      value: formatCurrency(economicCapital),
      description: "Risk-adjusted capital",
    },
    {
      label: "Regulatory Capital",
      value: formatCurrency(regulatoryCapital),
      description: "Basel III requirement",
    },
    {
      label: "RORAC",
      value: formatPercent(rorac),
      color: rorac && rorac > 0.15 ? "text-green-600" : "text-yellow-600",
      description: "Return on Risk-Adjusted Capital",
    },
  ];

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Risk Metrics</CardTitle>
          {riskGrade && (
            <Badge variant={getRiskGradeVariant(riskGrade)} className="text-sm">
              Grade: {riskGrade}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4">
          {metrics.map((metric) => (
            <div key={metric.label} className="space-y-1">
              <p className="text-xs text-gray-500">{metric.label}</p>
              <p className={cn("text-lg font-semibold", metric.color)}>
                {metric.value}
              </p>
              <p className="text-xs text-gray-400">{metric.description}</p>
            </div>
          ))}
        </div>

        {/* Risk Gauge */}
        {pdScore !== undefined && (
          <div className="mt-6">
            <p className="text-xs font-medium text-gray-500 mb-2">Risk Level</p>
            <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className={cn(
                  "h-full rounded-full transition-all",
                  pdScore < 0.03
                    ? "bg-green-500"
                    : pdScore < 0.10
                    ? "bg-yellow-500"
                    : "bg-red-500"
                )}
                style={{ width: `${Math.min(pdScore * 200, 100)}%` }}
              />
            </div>
            <div className="flex justify-between mt-1 text-xs text-gray-400">
              <span>Low</span>
              <span>Medium</span>
              <span>High</span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
