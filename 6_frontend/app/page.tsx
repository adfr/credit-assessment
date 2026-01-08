"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { portfolioApi, analyticsApi, PortfolioSummary, ConcentrationData } from "@/lib/api";

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

function formatPercent(value: number): string {
  return `${value.toFixed(2)}%`;
}

export default function DashboardPage() {
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [concentration, setConcentration] = useState<ConcentrationData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const [summaryData, concentrationData] = await Promise.all([
          portfolioApi.getSummary(),
          analyticsApi.getConcentration("industry"),
        ]);
        setSummary(summaryData);
        setConcentration(concentrationData);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load data");
      } finally {
        setIsLoading(false);
      }
    }
    fetchData();
  }, []);

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-gray-200 rounded w-1/4"></div>
          <div className="grid grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-24 bg-gray-200 rounded"></div>
            ))}
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
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Portfolio Overview</h1>
          <p className="text-gray-500">Risk metrics, capital requirements, and concentration analysis</p>
        </div>
        <Link
          href="/portfolio/new"
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          + Add Loan
        </Link>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border p-4">
          <p className="text-sm text-gray-500">Total Exposure</p>
          <p className="text-2xl font-bold text-gray-900">
            {formatCurrency(summary?.total_exposure || 0)}
          </p>
          <p className="text-sm text-gray-400">{summary?.loan_count || 0} loans</p>
        </div>

        <div className="bg-white rounded-lg border p-4">
          <p className="text-sm text-gray-500">Average PD</p>
          <p className="text-2xl font-bold text-gray-900">
            {formatPercent(summary?.avg_pd || 0)}
          </p>
          <p className="text-sm text-gray-400">Probability of Default</p>
        </div>

        <div className="bg-white rounded-lg border p-4">
          <p className="text-sm text-gray-500">Expected Loss</p>
          <p className="text-2xl font-bold text-orange-600">
            {formatCurrency(summary?.expected_loss || 0)}
          </p>
          <p className="text-sm text-gray-400">
            {((summary?.expected_loss || 0) / (summary?.total_exposure || 1) * 100).toFixed(2)}% of exposure
          </p>
        </div>

        <div className="bg-white rounded-lg border p-4">
          <p className="text-sm text-gray-500">Portfolio Health</p>
          <div className="flex items-baseline gap-2">
            <p className="text-2xl font-bold text-green-600">{summary?.current_count || 0}</p>
            <span className="text-sm text-gray-400">current</span>
          </div>
          <div className="flex gap-4 text-sm">
            <span className="text-yellow-600">{summary?.delinquent_count || 0} delinquent</span>
            <span className="text-red-600">{summary?.default_count || 0} default</span>
          </div>
        </div>
      </div>

      {/* Capital Section */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg border border-blue-200 p-5">
          <div className="flex items-center gap-2 mb-2">
            <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
            <p className="text-sm font-medium text-blue-800">Regulatory Capital (Basel IRB)</p>
          </div>
          <p className="text-3xl font-bold text-blue-900">
            {formatCurrency(summary?.regulatory_capital || 0)}
          </p>
          <p className="text-sm text-blue-600 mt-1">
            {formatPercent(summary?.reg_capital_ratio || 0)} of exposure
          </p>
        </div>

        <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg border border-purple-200 p-5">
          <div className="flex items-center gap-2 mb-2">
            <svg className="w-5 h-5 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
            </svg>
            <p className="text-sm font-medium text-purple-800">Economic Capital (VaR 99.9%)</p>
          </div>
          <p className="text-3xl font-bold text-purple-900">
            {formatCurrency(summary?.economic_capital || 0)}
          </p>
          <p className="text-sm text-purple-600 mt-1">
            {formatPercent(summary?.econ_capital_ratio || 0)} of exposure
          </p>
        </div>

        <div className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-lg border border-gray-200 p-5">
          <div className="flex items-center gap-2 mb-2">
            <svg className="w-5 h-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" />
            </svg>
            <p className="text-sm font-medium text-gray-700">Risk Weighted Assets</p>
          </div>
          <p className="text-3xl font-bold text-gray-900">
            {formatCurrency(summary?.risk_weighted_assets || 0)}
          </p>
          <p className="text-sm text-gray-500 mt-1">
            {((summary?.risk_weighted_assets || 0) / (summary?.total_exposure || 1) * 100).toFixed(0)}% avg risk weight
          </p>
        </div>
      </div>

      {/* Concentration Analysis */}
      <div className="grid grid-cols-2 gap-6">
        {/* Industry Concentration */}
        <div className="bg-white rounded-lg border p-5">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Industry Concentration</h2>
            <div className="flex items-center gap-2">
              <span className={`px-2 py-1 rounded text-xs font-medium ${
                concentration?.concentration_level === "Low"
                  ? "bg-green-100 text-green-800"
                  : concentration?.concentration_level === "Moderate"
                  ? "bg-yellow-100 text-yellow-800"
                  : "bg-red-100 text-red-800"
              }`}>
                HHI: {concentration?.hhi?.toFixed(0) || 0}
              </span>
            </div>
          </div>
          <div className="space-y-3">
            {concentration?.breakdown?.slice(0, 6).map((item) => (
              <div key={item.category}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-700 capitalize">{item.category}</span>
                  <span className="text-gray-500">{formatCurrency(item.exposure)} ({item.percentage.toFixed(1)}%)</span>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full"
                    style={{ width: `${Math.min(item.percentage, 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
          <Link href="/analytics" className="block mt-4 text-sm text-blue-600 hover:text-blue-800">
            View full analysis →
          </Link>
        </div>

        {/* Quick Stats */}
        <div className="bg-white rounded-lg border p-5">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Risk Metrics</h2>
          <div className="space-y-4">
            <div className="flex justify-between items-center py-2 border-b">
              <span className="text-gray-600">Average LGD</span>
              <span className="font-semibold">{formatPercent(summary?.avg_lgd || 0)}</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b">
              <span className="text-gray-600">Average Interest Rate</span>
              <span className="font-semibold">{formatPercent(summary?.avg_rate || 0)}</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b">
              <span className="text-gray-600">VaR (99.9%)</span>
              <span className="font-semibold">{formatCurrency(summary?.var_999 || 0)}</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b">
              <span className="text-gray-600">Active Loans</span>
              <span className="font-semibold">{summary?.active_count || 0}</span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-gray-600">Defaulted Loans</span>
              <span className="font-semibold text-red-600">{summary?.defaulted_count || 0}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-3 gap-4">
        <Link
          href="/portfolio"
          className="bg-white rounded-lg border p-4 hover:border-blue-300 hover:shadow-md transition-all group"
        >
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 rounded-lg group-hover:bg-blue-200">
              <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
              </svg>
            </div>
            <div>
              <p className="font-medium text-gray-900">Loan List</p>
              <p className="text-sm text-gray-500">Browse all loans</p>
            </div>
          </div>
        </Link>

        <Link
          href="/assistant"
          className="bg-white rounded-lg border p-4 hover:border-purple-300 hover:shadow-md transition-all group"
        >
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-100 rounded-lg group-hover:bg-purple-200">
              <svg className="w-5 h-5 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
            </div>
            <div>
              <p className="font-medium text-gray-900">AI Assistant</p>
              <p className="text-sm text-gray-500">Ask about your portfolio</p>
            </div>
          </div>
        </Link>

        <Link
          href="/analytics"
          className="bg-white rounded-lg border p-4 hover:border-green-300 hover:shadow-md transition-all group"
        >
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-100 rounded-lg group-hover:bg-green-200">
              <svg className="w-5 h-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <div>
              <p className="font-medium text-gray-900">Analytics</p>
              <p className="text-sm text-gray-500">Deep dive into risk</p>
            </div>
          </div>
        </Link>
      </div>
    </div>
  );
}
