"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { loansApi, Loan, Repayment } from "@/lib/api";

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

function getRiskGradeColor(grade: string): string {
  if (["AAA", "AA", "A"].includes(grade)) return "bg-green-100 text-green-800";
  if (["BBB", "BB"].includes(grade)) return "bg-yellow-100 text-yellow-800";
  return "bg-red-100 text-red-800";
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

export default function LoanDetailPage() {
  const params = useParams();
  const loanId = params.id as string;

  const [loan, setLoan] = useState<Loan | null>(null);
  const [repayments, setRepayments] = useState<Repayment[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const [loanData, repaymentData] = await Promise.all([
          loansApi.get(loanId),
          loansApi.getRepayments(loanId),
        ]);
        setLoan(loanData);
        setRepayments(repaymentData.repayments);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load loan");
      } finally {
        setIsLoading(false);
      }
    }
    fetchData();
  }, [loanId]);

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-gray-200 rounded w-1/4"></div>
          <div className="grid grid-cols-3 gap-4">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-24 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error || !loan) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          {error || "Loan not found"}
        </div>
        <Link href="/portfolio" className="mt-4 inline-block text-blue-600 hover:text-blue-800">
          Back to Portfolio
        </Link>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Link href="/portfolio" className="text-gray-500 hover:text-gray-700">
              Portfolio
            </Link>
            <span className="text-gray-400">/</span>
            <span className="text-gray-900">{loan.loan_id}</span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900">{loan.company_name}</h1>
          <p className="text-gray-500 capitalize">{loan.industry} - {loan.region}</p>
        </div>
        <div className="flex gap-2">
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(loan.status)}`}>
            {loan.status}
          </span>
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${getRiskGradeColor(loan.risk_grade)}`}>
            {loan.risk_grade}
          </span>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border p-4">
          <p className="text-sm text-gray-500">Outstanding Balance</p>
          <p className="text-2xl font-bold text-gray-900">{formatCurrency(loan.outstanding_balance)}</p>
          <p className="text-sm text-gray-400">of {formatCurrency(loan.original_balance)} original</p>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <p className="text-sm text-gray-500">Interest Rate</p>
          <p className="text-2xl font-bold text-gray-900">{(loan.interest_rate * 100).toFixed(2)}%</p>
          <p className="text-sm text-gray-400">{loan.term_months} month term</p>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <p className="text-sm text-gray-500">Days Past Due</p>
          <p className={`text-2xl font-bold ${loan.days_past_due > 0 ? "text-red-600" : "text-green-600"}`}>
            {loan.days_past_due}
          </p>
          <p className={`text-sm ${getPaymentStatusColor(loan.payment_status)}`}>
            {loan.payment_status}
          </p>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <p className="text-sm text-gray-500">Expected Loss</p>
          <p className="text-2xl font-bold text-orange-600">{formatCurrency(loan.expected_loss || 0)}</p>
          <p className="text-sm text-gray-400">
            {((loan.expected_loss || 0) / loan.outstanding_balance * 100).toFixed(2)}% of balance
          </p>
        </div>
      </div>

      {/* Details Grid */}
      <div className="grid grid-cols-2 gap-6">
        {/* Risk Metrics */}
        <div className="bg-white rounded-lg border p-5">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Risk Metrics</h2>
          <div className="space-y-3">
            <div className="flex justify-between py-2 border-b">
              <span className="text-gray-600">Probability of Default (PD)</span>
              <span className="font-semibold">{(loan.pd_score * 100).toFixed(2)}%</span>
            </div>
            <div className="flex justify-between py-2 border-b">
              <span className="text-gray-600">Loss Given Default (LGD)</span>
              <span className="font-semibold">{(loan.lgd_score * 100).toFixed(2)}%</span>
            </div>
            <div className="flex justify-between py-2 border-b">
              <span className="text-gray-600">Exposure at Default (EAD)</span>
              <span className="font-semibold">{formatCurrency(loan.outstanding_balance)}</span>
            </div>
            <div className="flex justify-between py-2 border-b">
              <span className="text-gray-600">Risk Weighted Assets</span>
              <span className="font-semibold">{formatCurrency(loan.risk_weighted_assets || 0)}</span>
            </div>
            <div className="flex justify-between py-2">
              <span className="text-gray-600">Regulatory Capital</span>
              <span className="font-semibold">{formatCurrency(loan.regulatory_capital || 0)}</span>
            </div>
          </div>
        </div>

        {/* Loan Details */}
        <div className="bg-white rounded-lg border p-5">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Loan Details</h2>
          <div className="space-y-3">
            <div className="flex justify-between py-2 border-b">
              <span className="text-gray-600">Purpose</span>
              <span className="font-semibold capitalize">{loan.purpose || "-"}</span>
            </div>
            <div className="flex justify-between py-2 border-b">
              <span className="text-gray-600">Collateral Type</span>
              <span className="font-semibold capitalize">{loan.collateral_type || "Unsecured"}</span>
            </div>
            <div className="flex justify-between py-2 border-b">
              <span className="text-gray-600">Collateral Value</span>
              <span className="font-semibold">{formatCurrency(loan.collateral_value || 0)}</span>
            </div>
            <div className="flex justify-between py-2 border-b">
              <span className="text-gray-600">Disbursement Date</span>
              <span className="font-semibold">
                {loan.disbursement_date ? new Date(loan.disbursement_date).toLocaleDateString() : "-"}
              </span>
            </div>
            <div className="flex justify-between py-2">
              <span className="text-gray-600">Maturity Date</span>
              <span className="font-semibold">
                {loan.maturity_date ? new Date(loan.maturity_date).toLocaleDateString() : "-"}
              </span>
            </div>
          </div>
        </div>

        {/* Company Financials */}
        <div className="bg-white rounded-lg border p-5">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Company Financials</h2>
          <div className="space-y-3">
            <div className="flex justify-between py-2 border-b">
              <span className="text-gray-600">Annual Revenue</span>
              <span className="font-semibold">{formatCurrency(loan.annual_revenue || 0)}</span>
            </div>
            <div className="flex justify-between py-2 border-b">
              <span className="text-gray-600">Net Income</span>
              <span className="font-semibold">{formatCurrency(loan.net_income || 0)}</span>
            </div>
            <div className="flex justify-between py-2 border-b">
              <span className="text-gray-600">Total Assets</span>
              <span className="font-semibold">{formatCurrency(loan.total_assets || 0)}</span>
            </div>
            <div className="flex justify-between py-2">
              <span className="text-gray-600">Total Liabilities</span>
              <span className="font-semibold">{formatCurrency(loan.total_liabilities || 0)}</span>
            </div>
          </div>
        </div>

        {/* Last Payment */}
        <div className="bg-white rounded-lg border p-5">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Last Payment</h2>
          {loan.last_payment_date ? (
            <div className="space-y-3">
              <div className="flex justify-between py-2 border-b">
                <span className="text-gray-600">Date</span>
                <span className="font-semibold">{new Date(loan.last_payment_date).toLocaleDateString()}</span>
              </div>
              <div className="flex justify-between py-2 border-b">
                <span className="text-gray-600">Amount</span>
                <span className="font-semibold">{formatCurrency(loan.last_payment_amount || 0)}</span>
              </div>
              <div className="flex justify-between py-2">
                <span className="text-gray-600">Days Since Payment</span>
                <span className="font-semibold">
                  {Math.floor((Date.now() - new Date(loan.last_payment_date).getTime()) / (1000 * 60 * 60 * 24))}
                </span>
              </div>
            </div>
          ) : (
            <p className="text-gray-500">No payment recorded yet</p>
          )}
        </div>
      </div>

      {/* Repayment History */}
      <div className="bg-white rounded-lg border p-5">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Repayment History</h2>
        {repayments.length > 0 ? (
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Payment Amount</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Principal</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Interest</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Balance After</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {repayments.map((payment) => (
                <tr key={payment.repayment_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm text-gray-900">
                    {new Date(payment.payment_date).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-sm text-right font-medium">
                    {formatCurrency(payment.payment_amount)}
                  </td>
                  <td className="px-4 py-3 text-sm text-right text-gray-600">
                    {formatCurrency(payment.principal_amount)}
                  </td>
                  <td className="px-4 py-3 text-sm text-right text-gray-600">
                    {formatCurrency(payment.interest_amount)}
                  </td>
                  <td className="px-4 py-3 text-sm text-right">
                    {formatCurrency(payment.balance_after)}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`px-2 py-1 text-xs rounded ${
                      payment.status === "completed"
                        ? "bg-green-100 text-green-800"
                        : payment.status === "pending"
                        ? "bg-yellow-100 text-yellow-800"
                        : "bg-red-100 text-red-800"
                    }`}>
                      {payment.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="text-gray-500 text-center py-8">No repayment records found</p>
        )}
      </div>
    </div>
  );
}
