"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface ApplicationFormData {
  company_name: string;
  industry: string;
  requested_amount: number;
  requested_term_months: number;
  purpose: string;
  collateral_type: string;
  collateral_value: number;
  annual_revenue: number;
  net_income: number;
  total_assets: number;
  total_liabilities: number;
}

interface ApplicationFormProps {
  onSubmit: (data: ApplicationFormData) => Promise<void>;
  isLoading?: boolean;
}

const industries = [
  { value: "technology", label: "Technology" },
  { value: "healthcare", label: "Healthcare" },
  { value: "manufacturing", label: "Manufacturing" },
  { value: "retail", label: "Retail" },
  { value: "finance", label: "Finance" },
  { value: "real_estate", label: "Real Estate" },
  { value: "energy", label: "Energy" },
  { value: "other", label: "Other" },
];

const collateralTypes = [
  { value: "real_estate", label: "Real Estate" },
  { value: "equipment", label: "Equipment" },
  { value: "inventory", label: "Inventory" },
  { value: "accounts_receivable", label: "Accounts Receivable" },
  { value: "securities", label: "Securities" },
  { value: "none", label: "None" },
];

const loanPurposes = [
  { value: "working_capital", label: "Working Capital" },
  { value: "equipment_purchase", label: "Equipment Purchase" },
  { value: "expansion", label: "Business Expansion" },
  { value: "acquisition", label: "Acquisition" },
  { value: "refinancing", label: "Refinancing" },
  { value: "other", label: "Other" },
];

export function ApplicationForm({ onSubmit, isLoading }: ApplicationFormProps) {
  const [formData, setFormData] = useState<ApplicationFormData>({
    company_name: "",
    industry: "",
    requested_amount: 0,
    requested_term_months: 12,
    purpose: "",
    collateral_type: "",
    collateral_value: 0,
    annual_revenue: 0,
    net_income: 0,
    total_assets: 0,
    total_liabilities: 0,
  });

  const [errors, setErrors] = useState<Partial<Record<keyof ApplicationFormData, string>>>({});

  const validateForm = (): boolean => {
    const newErrors: Partial<Record<keyof ApplicationFormData, string>> = {};

    if (!formData.company_name) {
      newErrors.company_name = "Company name is required";
    }
    if (!formData.industry) {
      newErrors.industry = "Industry is required";
    }
    if (formData.requested_amount <= 0) {
      newErrors.requested_amount = "Amount must be greater than 0";
    }
    if (formData.requested_term_months <= 0) {
      newErrors.requested_term_months = "Term must be greater than 0";
    }
    if (!formData.purpose) {
      newErrors.purpose = "Purpose is required";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) return;
    await onSubmit(formData);
  };

  const updateField = (field: keyof ApplicationFormData, value: string | number) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: undefined }));
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Company Information */}
      <Card>
        <CardHeader>
          <CardTitle>Company Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Company Name *
            </label>
            <Input
              value={formData.company_name}
              onChange={(e) => updateField("company_name", e.target.value)}
              error={errors.company_name}
              placeholder="Enter company name"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Industry *
            </label>
            <Select
              value={formData.industry}
              onChange={(e) => updateField("industry", e.target.value)}
              options={industries}
              placeholder="Select industry"
              error={errors.industry}
            />
          </div>
        </CardContent>
      </Card>

      {/* Loan Details */}
      <Card>
        <CardHeader>
          <CardTitle>Loan Details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Requested Amount ($) *
              </label>
              <Input
                type="number"
                value={formData.requested_amount || ""}
                onChange={(e) => updateField("requested_amount", parseFloat(e.target.value) || 0)}
                error={errors.requested_amount}
                placeholder="0"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Term (Months) *
              </label>
              <Input
                type="number"
                value={formData.requested_term_months || ""}
                onChange={(e) => updateField("requested_term_months", parseInt(e.target.value) || 0)}
                error={errors.requested_term_months}
                placeholder="12"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Purpose *
            </label>
            <Select
              value={formData.purpose}
              onChange={(e) => updateField("purpose", e.target.value)}
              options={loanPurposes}
              placeholder="Select purpose"
              error={errors.purpose}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Collateral Type
              </label>
              <Select
                value={formData.collateral_type}
                onChange={(e) => updateField("collateral_type", e.target.value)}
                options={collateralTypes}
                placeholder="Select collateral type"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Collateral Value ($)
              </label>
              <Input
                type="number"
                value={formData.collateral_value || ""}
                onChange={(e) => updateField("collateral_value", parseFloat(e.target.value) || 0)}
                placeholder="0"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Financial Information */}
      <Card>
        <CardHeader>
          <CardTitle>Financial Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Annual Revenue ($)
              </label>
              <Input
                type="number"
                value={formData.annual_revenue || ""}
                onChange={(e) => updateField("annual_revenue", parseFloat(e.target.value) || 0)}
                placeholder="0"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Net Income ($)
              </label>
              <Input
                type="number"
                value={formData.net_income || ""}
                onChange={(e) => updateField("net_income", parseFloat(e.target.value) || 0)}
                placeholder="0"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Total Assets ($)
              </label>
              <Input
                type="number"
                value={formData.total_assets || ""}
                onChange={(e) => updateField("total_assets", parseFloat(e.target.value) || 0)}
                placeholder="0"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Total Liabilities ($)
              </label>
              <Input
                type="number"
                value={formData.total_liabilities || ""}
                onChange={(e) => updateField("total_liabilities", parseFloat(e.target.value) || 0)}
                placeholder="0"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Submit */}
      <div className="flex justify-end space-x-4">
        <Button type="button" variant="outline">
          Cancel
        </Button>
        <Button type="submit" loading={isLoading}>
          Submit Application
        </Button>
      </div>
    </form>
  );
}
