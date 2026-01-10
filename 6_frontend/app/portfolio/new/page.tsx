"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { loansApi } from "@/lib/api";

const industries = [
  "technology",
  "healthcare",
  "manufacturing",
  "retail",
  "financial_services",
  "real_estate",
  "construction",
  "transportation",
  "energy",
  "agriculture",
];

const regions = [
  "North America",
  "Europe",
  "Asia Pacific",
  "Latin America",
  "Middle East",
  "Africa",
];

const purposes = [
  "working_capital",
  "expansion",
  "equipment",
  "real_estate",
  "refinancing",
  "acquisition",
];

const collateralTypes = [
  "unsecured",
  "real_estate",
  "equipment",
  "inventory",
  "receivables",
  "cash",
];


export default function AddLoanPage() {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [formData, setFormData] = useState({
    company_name: "",
    industry: "technology",
    region: "North America",
    country: "USA",
    loan_amount: "",
    interest_rate: "5.0",
    term_months: "36",
    purpose: "working_capital",
    collateral_type: "unsecured",
    collateral_value: "0",
    // PD/LGD will be predicted by the model based on financials
    annual_revenue: "",
    net_income: "",
    total_assets: "",
    total_liabilities: "",
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const payload = {
        company_name: formData.company_name,
        industry: formData.industry,
        region: formData.region,
        country: formData.country,
        loan_amount: parseFloat(formData.loan_amount),
        interest_rate: parseFloat(formData.interest_rate) / 100,
        term_months: parseInt(formData.term_months),
        purpose: formData.purpose,
        collateral_type: formData.collateral_type,
        collateral_value: parseFloat(formData.collateral_value) || 0,
        // PD/LGD will be predicted by the backend model
        annual_revenue: parseFloat(formData.annual_revenue) || 0,
        net_income: parseFloat(formData.net_income) || 0,
        total_assets: parseFloat(formData.total_assets) || 0,
        total_liabilities: parseFloat(formData.total_liabilities) || 0,
      };

      await loansApi.create(payload);
      router.push("/portfolio");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add loan");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-2">
          <Link href="/portfolio" className="text-gray-500 hover:text-gray-700">
            Portfolio
          </Link>
          <span className="text-gray-400">/</span>
          <span className="text-gray-900">Add Loan</span>
        </div>
        <h1 className="text-2xl font-bold text-gray-900">Add New Loan</h1>
        <p className="text-gray-500">PD and LGD scores will be predicted by ML models based on company financials</p>
      </div>

      {error && (
        <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Company Information */}
        <div className="bg-white rounded-lg border p-5">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Company Information</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Company Name *
              </label>
              <input
                type="text"
                name="company_name"
                value={formData.company_name}
                onChange={handleChange}
                required
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter company name"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Industry *
              </label>
              <select
                name="industry"
                value={formData.industry}
                onChange={handleChange}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {industries.map((ind) => (
                  <option key={ind} value={ind}>
                    {ind.charAt(0).toUpperCase() + ind.slice(1).replace("_", " ")}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Region *
              </label>
              <select
                name="region"
                value={formData.region}
                onChange={handleChange}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {regions.map((reg) => (
                  <option key={reg} value={reg}>
                    {reg}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Country *
              </label>
              <input
                type="text"
                name="country"
                value={formData.country}
                onChange={handleChange}
                required
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>

        {/* Loan Details */}
        <div className="bg-white rounded-lg border p-5">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Loan Details</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Loan Amount ($) *
              </label>
              <input
                type="number"
                name="loan_amount"
                value={formData.loan_amount}
                onChange={handleChange}
                required
                min="1000"
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="1000000"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Interest Rate (%)
              </label>
              <input
                type="number"
                name="interest_rate"
                value={formData.interest_rate}
                onChange={handleChange}
                step="0.1"
                min="0"
                max="50"
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Term (months)
              </label>
              <input
                type="number"
                name="term_months"
                value={formData.term_months}
                onChange={handleChange}
                min="1"
                max="360"
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Purpose
              </label>
              <select
                name="purpose"
                value={formData.purpose}
                onChange={handleChange}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {purposes.map((p) => (
                  <option key={p} value={p}>
                    {p.charAt(0).toUpperCase() + p.slice(1).replace("_", " ")}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Collateral Type
              </label>
              <select
                name="collateral_type"
                value={formData.collateral_type}
                onChange={handleChange}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {collateralTypes.map((c) => (
                  <option key={c} value={c}>
                    {c.charAt(0).toUpperCase() + c.slice(1).replace("_", " ")}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Collateral Value ($)
              </label>
              <input
                type="number"
                name="collateral_value"
                value={formData.collateral_value}
                onChange={handleChange}
                min="0"
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>

        {/* Company Financials - Used for PD/LGD Model Prediction */}
        <div className="bg-white rounded-lg border p-5">
          <h2 className="text-lg font-semibold text-gray-900 mb-2">Company Financials</h2>
          <p className="text-sm text-gray-500 mb-4">Used by ML models to predict PD and LGD scores</p>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Annual Revenue ($)
              </label>
              <input
                type="number"
                name="annual_revenue"
                value={formData.annual_revenue}
                onChange={handleChange}
                min="0"
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="0"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Net Income ($)
              </label>
              <input
                type="number"
                name="net_income"
                value={formData.net_income}
                onChange={handleChange}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="0"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Total Assets ($)
              </label>
              <input
                type="number"
                name="total_assets"
                value={formData.total_assets}
                onChange={handleChange}
                min="0"
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="0"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Total Liabilities ($)
              </label>
              <input
                type="number"
                name="total_liabilities"
                value={formData.total_liabilities}
                onChange={handleChange}
                min="0"
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="0"
              />
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-3">
          <Link
            href="/portfolio"
            className="px-6 py-2 border rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={isSubmitting}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            {isSubmitting ? "Adding..." : "Add Loan"}
          </button>
        </div>
      </form>
    </div>
  );
}
