"use client";

import { useEffect, useState } from "react";
import { analyticsApi, ConcentrationData, LargeExposures, VintageData, MigrationMatrix } from "@/lib/api";

function formatCurrency(value: number): string {
  if (value >= 1000000000) {
    return `$${(value / 1000000000).toFixed(1)}B`;
  }
  if (value >= 1000000) {
    return `$${(value / 1000000).toFixed(1)}M`;
  }
  if (value >= 1000) {
    return `$${(value / 1000).toFixed(0)}K`;
  }
  return `$${value.toFixed(0)}`;
}

type Dimension = "industry" | "region" | "risk_grade" | "collateral" | "purpose";

export default function AnalyticsPage() {
  const [concentration, setConcentration] = useState<ConcentrationData | null>(null);
  const [largeExposures, setLargeExposures] = useState<LargeExposures | null>(null);
  const [vintageData, setVintageData] = useState<VintageData | null>(null);
  const [migrationMatrix, setMigrationMatrix] = useState<MigrationMatrix | null>(null);
  const [selectedDimension, setSelectedDimension] = useState<Dimension>("industry");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"concentration" | "exposures" | "vintage" | "migration">("concentration");

  useEffect(() => {
    async function fetchData() {
      setIsLoading(true);
      try {
        const [concData, expData, vintData, migData] = await Promise.all([
          analyticsApi.getConcentration(selectedDimension),
          analyticsApi.getLargeExposures(5),
          analyticsApi.getVintageAnalysis(),
          analyticsApi.getMigrationMatrix(12),
        ]);
        setConcentration(concData);
        setLargeExposures(expData);
        setVintageData(vintData);
        setMigrationMatrix(migData);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load analytics");
      } finally {
        setIsLoading(false);
      }
    }
    fetchData();
  }, [selectedDimension]);

  const dimensions: { value: Dimension; label: string }[] = [
    { value: "industry", label: "Industry" },
    { value: "region", label: "Region" },
    { value: "risk_grade", label: "Risk Grade" },
    { value: "collateral", label: "Collateral Type" },
    { value: "purpose", label: "Loan Purpose" },
  ];

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-gray-200 rounded w-1/4"></div>
          <div className="grid grid-cols-2 gap-6">
            <div className="h-64 bg-gray-200 rounded"></div>
            <div className="h-64 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Portfolio Analytics</h1>
        <p className="text-gray-500">Concentration analysis, risk metrics, and portfolio insights</p>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {[
            { id: "concentration", label: "Concentration" },
            { id: "exposures", label: "Large Exposures" },
            { id: "vintage", label: "Vintage Analysis" },
            { id: "migration", label: "Migration Matrix" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === tab.id
                  ? "border-blue-500 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Concentration Tab */}
      {activeTab === "concentration" && concentration && (
        <div className="space-y-6">
          {/* Dimension Selector */}
          <div className="bg-white rounded-lg border p-4">
            <div className="flex items-center gap-4">
              <label className="text-sm font-medium text-gray-700">Analyze by:</label>
              <div className="flex gap-2">
                {dimensions.map((dim) => (
                  <button
                    key={dim.value}
                    onClick={() => setSelectedDimension(dim.value)}
                    className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                      selectedDimension === dim.value
                        ? "bg-blue-600 text-white"
                        : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                    }`}
                  >
                    {dim.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* HHI Summary */}
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-white rounded-lg border p-5">
              <p className="text-sm text-gray-500">Herfindahl-Hirschman Index</p>
              <p className="text-3xl font-bold text-gray-900">{concentration.hhi.toFixed(0)}</p>
              <span className={`inline-block mt-2 px-2 py-1 text-xs rounded ${
                concentration.concentration_level === "Low"
                  ? "bg-green-100 text-green-800"
                  : concentration.concentration_level === "Moderate"
                  ? "bg-yellow-100 text-yellow-800"
                  : "bg-red-100 text-red-800"
              }`}>
                {concentration.concentration_level} Concentration
              </span>
            </div>
            <div className="bg-white rounded-lg border p-5">
              <p className="text-sm text-gray-500">Total Exposure</p>
              <p className="text-3xl font-bold text-gray-900">{formatCurrency(concentration.total_exposure)}</p>
              <p className="text-sm text-gray-400 mt-2">{concentration.breakdown.length} categories</p>
            </div>
            <div className="bg-white rounded-lg border p-5">
              <p className="text-sm text-gray-500">Top Category Share</p>
              <p className="text-3xl font-bold text-gray-900">
                {concentration.breakdown[0]?.percentage.toFixed(1)}%
              </p>
              <p className="text-sm text-gray-400 mt-2 capitalize">{concentration.breakdown[0]?.category}</p>
            </div>
          </div>

          {/* Breakdown Table */}
          <div className="bg-white rounded-lg border overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Category</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Loans</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Exposure</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Share</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Avg PD</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Avg LGD</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Distribution</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {concentration.breakdown.map((item) => (
                  <tr key={item.category} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm font-medium text-gray-900 capitalize">{item.category}</td>
                    <td className="px-4 py-3 text-sm text-right text-gray-600">{item.count}</td>
                    <td className="px-4 py-3 text-sm text-right font-medium">{formatCurrency(item.exposure)}</td>
                    <td className="px-4 py-3 text-sm text-right text-gray-600">{item.percentage.toFixed(1)}%</td>
                    <td className="px-4 py-3 text-sm text-right text-gray-600">{item.avg_pd.toFixed(2)}%</td>
                    <td className="px-4 py-3 text-sm text-right text-gray-600">{item.avg_lgd.toFixed(2)}%</td>
                    <td className="px-4 py-3">
                      <div className="w-full bg-gray-100 rounded-full h-2">
                        <div
                          className="bg-blue-500 h-2 rounded-full"
                          style={{ width: `${Math.min(item.percentage, 100)}%` }}
                        />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Large Exposures Tab */}
      {activeTab === "exposures" && largeExposures && (
        <div className="space-y-6">
          {/* Summary */}
          <div className="grid grid-cols-4 gap-4">
            <div className="bg-white rounded-lg border p-5">
              <p className="text-sm text-gray-500">Large Exposures Count</p>
              <p className="text-3xl font-bold text-gray-900">{largeExposures.count}</p>
              <p className="text-sm text-gray-400 mt-2">{`>${largeExposures.threshold_pct}% threshold`}</p>
            </div>
            <div className="bg-white rounded-lg border p-5">
              <p className="text-sm text-gray-500">Threshold Amount</p>
              <p className="text-3xl font-bold text-gray-900">{formatCurrency(largeExposures.threshold_amount)}</p>
            </div>
            <div className="bg-white rounded-lg border p-5">
              <p className="text-sm text-gray-500">Total Large Exposure</p>
              <p className="text-3xl font-bold text-orange-600">{formatCurrency(largeExposures.total_large_exposure)}</p>
            </div>
            <div className="bg-white rounded-lg border p-5">
              <p className="text-sm text-gray-500">Share of Portfolio</p>
              <p className="text-3xl font-bold text-gray-900">{largeExposures.large_exposure_pct.toFixed(1)}%</p>
            </div>
          </div>

          {/* Large Exposures Table */}
          <div className="bg-white rounded-lg border overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Company</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Industry</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Exposure</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">% of Portfolio</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Risk Grade</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">PD</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {largeExposures.exposures.map((exp) => (
                  <tr key={exp.loan_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <div className="font-medium text-gray-900">{exp.company_name}</div>
                      <div className="text-xs text-gray-500">{exp.loan_id}</div>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600 capitalize">{exp.industry}</td>
                    <td className="px-4 py-3 text-sm text-right font-medium">{formatCurrency(exp.outstanding_balance)}</td>
                    <td className="px-4 py-3 text-sm text-right text-gray-600">{exp.percentage.toFixed(2)}%</td>
                    <td className="px-4 py-3 text-center">
                      <span className={`px-2 py-1 text-xs font-medium rounded ${
                        ["AAA", "AA", "A"].includes(exp.risk_grade)
                          ? "bg-green-100 text-green-800"
                          : ["BBB", "BB"].includes(exp.risk_grade)
                          ? "bg-yellow-100 text-yellow-800"
                          : "bg-red-100 text-red-800"
                      }`}>
                        {exp.risk_grade}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-right">{exp.pd_score.toFixed(2)}%</td>
                  </tr>
                ))}
                {largeExposures.exposures.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                      No large exposures above {largeExposures.threshold_pct}% threshold
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Vintage Analysis Tab */}
      {activeTab === "vintage" && vintageData && (
        <div className="space-y-6">
          <div className="bg-white rounded-lg border overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Vintage</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Loans</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Original Volume</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Current Exposure</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Defaults</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Default Rate</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Loss Rate</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Avg PD</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {vintageData.vintages.map((vintage) => (
                  <tr key={vintage.vintage} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">{vintage.vintage}</td>
                    <td className="px-4 py-3 text-sm text-right text-gray-600">{vintage.loan_count}</td>
                    <td className="px-4 py-3 text-sm text-right">{formatCurrency(vintage.original_volume)}</td>
                    <td className="px-4 py-3 text-sm text-right">{formatCurrency(vintage.current_exposure)}</td>
                    <td className="px-4 py-3 text-sm text-right text-gray-600">{vintage.default_count}</td>
                    <td className="px-4 py-3 text-sm text-right">
                      <span className={vintage.default_rate > 5 ? "text-red-600" : "text-gray-600"}>
                        {vintage.default_rate.toFixed(2)}%
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-right">
                      <span className={vintage.loss_rate > 3 ? "text-red-600" : "text-gray-600"}>
                        {vintage.loss_rate.toFixed(2)}%
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-right text-gray-600">{vintage.avg_pd.toFixed(2)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Migration Matrix Tab */}
      {activeTab === "migration" && migrationMatrix && (
        <div className="space-y-6">
          <div className="bg-white rounded-lg border p-5">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              {migrationMatrix.period_months}-Month Transition Matrix
            </h3>
            <p className="text-sm text-gray-500 mb-4">
              Probability (%) of migrating from row grade to column grade
            </p>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">From / To</th>
                    {migrationMatrix.grades.map((grade) => (
                      <th key={grade} className="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase">
                        {grade}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {Object.entries(migrationMatrix.matrix).map(([fromGrade, transitions]) => (
                    <tr key={fromGrade}>
                      <td className="px-3 py-2 text-sm font-medium text-gray-900">{fromGrade}</td>
                      {migrationMatrix.grades.map((toGrade) => {
                        const value = transitions[toGrade] || 0;
                        const isStable = fromGrade === toGrade;
                        const isUpgrade = migrationMatrix.grades.indexOf(toGrade) < migrationMatrix.grades.indexOf(fromGrade);
                        const isDefault = toGrade === "Default";

                        return (
                          <td
                            key={toGrade}
                            className={`px-3 py-2 text-center text-sm ${
                              isStable
                                ? "bg-blue-50 font-medium"
                                : isDefault && value > 1
                                ? "bg-red-50 text-red-700"
                                : isUpgrade && value > 0
                                ? "bg-green-50 text-green-700"
                                : ""
                            }`}
                          >
                            {value.toFixed(1)}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-xs text-gray-400 mt-4 italic">{migrationMatrix.note}</p>
          </div>
        </div>
      )}
    </div>
  );
}
