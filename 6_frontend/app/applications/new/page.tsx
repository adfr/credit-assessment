"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { ApplicationForm } from "@/components/applications/ApplicationForm";
import { useApplications } from "@/hooks/useApplications";

export default function NewApplicationPage() {
  const router = useRouter();
  const { createApplication, isLoading, error } = useApplications();
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (data: unknown) => {
    try {
      const applicationId = await createApplication(data as Parameters<typeof createApplication>[0]);
      setSuccess(true);

      // Redirect to the application detail page after a short delay
      setTimeout(() => {
        router.push(`/applications/${applicationId}`);
      }, 1500);
    } catch (err) {
      // Error is handled by the hook
      console.error(err);
    }
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">New Application</h1>
        <p className="text-gray-500">Submit a new credit application</p>
      </div>

      {/* Success Message */}
      {success && (
        <div className="mb-6 bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex">
            <svg
              className="h-5 w-5 text-green-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
            <p className="ml-3 text-sm text-green-700">
              Application submitted successfully! Redirecting...
            </p>
          </div>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex">
            <svg
              className="h-5 w-5 text-red-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <p className="ml-3 text-sm text-red-700">{error}</p>
          </div>
        </div>
      )}

      <ApplicationForm onSubmit={handleSubmit} isLoading={isLoading} />
    </div>
  );
}
