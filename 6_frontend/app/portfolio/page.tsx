"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { loansApi, Loan } from "@/lib/api";

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

function getStatusColor(status: string): string {
  switch (status) {
    case "active":
      return "bg-green-100 text-green-800";
    case "paid_off":
      return "bg-blue-100 text-blue-800";
    case "defaulted":
      return "bg-red-100 text-red-800";
    default:
      return "bg-gray-100 text-gray-800";
  }
}

function getPaymentStatusColor(status: string): string {
  switch (status) {
    case "current":
      return "text-green-600";
    case "delinquent":
      return "text-yellow-600";
    case "default":
      return "text-red-600";
    default:
      return "text-gray-600";
  }
}

function getRiskGradeColor(grade: string): string {
  if (["AAA", "AA", "A"].includes(grade)) return "bg-green-100 text-green-800";
  if (["BBB", "BB"].includes(grade)) return "bg-yellow-100 text-yellow-800";
  return "bg-red-100 text-red-800";
}

export default function PortfolioPage() {
  const [loans, setLoans] = useState<Loan[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [industryFilter, setIndustryFilter] = useState<string>("");
  const [paymentFilter, setPaymentFilter] = useState<string>("");

  useEffect(() => {
    async function fetchLoans() {
      setIsLoading(true);
      try {
        const params: Record<string, string | number> = { limit: 1000 };
        if (statusFilter) params.status = statusFilter;
        if (industryFilter) params.industry = industryFilter;
        if (paymentFilter) params.payment_status = paymentFilter;

        const result = await loansApi.list(params);
        setLoans(result.loans);
        setTotal(result.total);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load loans");
      } finally {
        setIsLoading(false);
      }
    }
    fetchLoans();
  }, [statusFilter, industryFilter, paymentFilter]);

  const industries = Array.from(new Set(loans.map((l) => l.industry))).sort();

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Portfolio</h1>
          <p className="text-gray-500">{total} loans in portfolio</p>
        </div>
        <Link
          href="/portfolio/new"
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          Add Loan
        </Link>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg border p-4">
        <div className="flex gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="border rounded-md px-3 py-2 text-sm"
            >
              <option value="">All Statuses</option>
              <option value="active">Active</option>
              <option value="paid_off">Paid Off</option>
              <option value="defaulted">Defaulted</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Industry</label>
            <select
              value={industryFilter}
              onChange={(e) => setIndustryFilter(e.target.value)}
              className="border rounded-md px-3 py-2 text-sm"
            >
              <option value="">All Industries</option>
              {industries.map((ind) => (
                <option key={ind} value={ind}>
                  {ind.charAt(0).toUpperCase() + ind.slice(1)}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Payment Status</label>
            <select
              value={paymentFilter}
              onChange={(e) => setPaymentFilter(e.target.value)}
              className="border rounded-md px-3 py-2 text-sm"
            >
              <option value="">All</option>
              <option value="current">Current</option>
              <option value="delinquent">Delinquent</option>
              <option value="default">Default</option>
            </select>
          </div>

          {(statusFilter || industryFilter || paymentFilter) && (
            <div className="flex items-end">
              <button
                onClick={() => {
                  setStatusFilter("");
                  setIndustryFilter("");
                  setPaymentFilter("");
                }}
                className="text-sm text-blue-600 hover:text-blue-800"
              >
                Clear filters
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          {error}
        </div>
      )}

      {/* Loans Table */}
      <div className="bg-white rounded-lg border overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Company</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Industry</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Outstanding</th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Risk Grade</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">PD</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Last Payment</th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">DPD</th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {isLoading ? (
              [...Array(5)].map((_, i) => (
                <tr key={i}>
                  {[...Array(9)].map((_, j) => (
                    <td key={j} className="px-4 py-4">
                      <div className="h-4 bg-gray-200 rounded animate-pulse"></div>
                    </td>
                  ))}
                </tr>
              ))
            ) : loans.length === 0 ? (
              <tr>
                <td colSpan={9} className="px-4 py-12 text-center text-gray-500">
                  No loans found matching your filters.
                </td>
              </tr>
            ) : (
              loans.map((loan) => (
                <tr key={loan.loan_id} className="hover:bg-gray-50">
                  <td className="px-4 py-4">
                    <div className="font-medium text-gray-900">{loan.company_name}</div>
                    <div className="text-xs text-gray-500">{loan.loan_id}</div>
                  </td>
                  <td className="px-4 py-4 text-sm text-gray-600 capitalize">{loan.industry}</td>
                  <td className="px-4 py-4 text-sm text-right font-medium">
                    {formatCurrency(loan.outstanding_balance)}
                  </td>
                  <td className="px-4 py-4 text-center">
                    <span className={`px-2 py-1 text-xs font-medium rounded ${getRiskGradeColor(loan.risk_grade)}`}>
                      {loan.risk_grade}
                    </span>
                  </td>
                  <td className="px-4 py-4 text-sm text-right">
                    {(loan.pd_score * 100).toFixed(2)}%
                  </td>
                  <td className="px-4 py-4 text-sm text-gray-600">
                    {loan.last_payment_date ? new Date(loan.last_payment_date).toLocaleDateString() : "-"}
                  </td>
                  <td className="px-4 py-4 text-center">
                    <span className={`text-sm font-medium ${loan.days_past_due > 0 ? "text-red-600" : "text-gray-600"}`}>
                      {loan.days_past_due}
                    </span>
                  </td>
                  <td className="px-4 py-4 text-center">
                    <span className={`px-2 py-1 text-xs rounded ${getStatusColor(loan.status)}`}>
                      {loan.status}
                    </span>
                  </td>
                  <td className="px-4 py-4 text-center">
                    <Link
                      href={`/portfolio/${loan.loan_id}`}
                      className="text-blue-600 hover:text-blue-800 text-sm"
                    >
                      View
                    </Link>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
