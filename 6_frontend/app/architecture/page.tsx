"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useState } from "react";

export default function ArchitecturePage() {
  const [activeTab, setActiveTab] = useState<"overview" | "pipeline" | "training" | "serving" | "apps">("overview");

  const dataSourcesInfo = [
    { name: "Companies", count: "5,000", desc: "Company financials" },
    { name: "Loan History", count: "10,000", desc: "Loan records" },
    { name: "Payment History", count: "~50,000", desc: "Payment transactions" },
    { name: "Bureau Data", count: "5,000", desc: "Credit scores" },
    { name: "SEC 10-K Filings", count: "~500", desc: "Annual reports" },
  ];

  const sparkJobs = [
    {
      name: "Data Loading",
      file: "load_to_iceberg.py",
      schedule: "On demand",
      desc: "Loads raw data to S3/Iceberg with partitioning",
      runtime: "CDE Spark",
      details: ["Partitions by industry, year, status", "Schema evolution support", "ACID transactions"],
    },
    {
      name: "Feature Engineering",
      file: "feature_engineering.py",
      schedule: "Daily @ 1:00 AM",
      desc: "Creates 23+ features from raw data",
      runtime: "CDE Spark",
      details: ["Financial ratios", "Bureau score derivatives", "Payment behavior metrics", "Industry risk factors"],
    },
    {
      name: "Batch Scoring",
      file: "batch_scoring.py",
      schedule: "Daily @ 2:00 AM",
      desc: "Scores all records with PD/LGD models",
      runtime: "CDE Spark",
      details: ["Loads models from S3", "Distributed scoring", "Writes to /scores/ partition"],
    },
  ];

  const trainingJobs = [
    {
      name: "PD Model Training",
      file: "train_pd_model.py",
      type: "Classification",
      algorithms: ["XGBoost", "Gradient Boosting", "Logistic Regression"],
      metrics: ["AUC-ROC", "Gini", "KS Statistic"],
      output: "pd_model_latest.pkl",
      runtime: "CML Job",
    },
    {
      name: "LGD Model Training",
      file: "train_lgd_model.py",
      type: "Regression",
      algorithms: ["Gradient Boosting"],
      metrics: ["MAE", "RMSE", "R²"],
      output: "lgd_model_latest.pkl",
      runtime: "CML Job",
    },
    {
      name: "Model Validation",
      file: "validate_models.py",
      type: "Validation",
      algorithms: ["Cross-validation", "Backtesting"],
      metrics: ["Stability", "Discrimination", "Calibration"],
      output: "validation_report.json",
      runtime: "CML Job",
    },
  ];

  const apiEndpoints = [
    { method: "POST", path: "/api/score", desc: "Real-time PD/LGD scoring" },
    { method: "GET", path: "/api/portfolio", desc: "Portfolio analytics" },
    { method: "GET", path: "/api/portfolio/{id}", desc: "Single loan details" },
    { method: "POST", path: "/api/applications", desc: "New loan applications" },
    { method: "POST", path: "/api/analyst", desc: "AI Assistant queries" },
    { method: "GET", path: "/api/models/metrics", desc: "Model performance" },
    { method: "WS", path: "/ws/analyst", desc: "Streaming AI responses" },
  ];

  const applications = [
    {
      name: "Credit Risk Frontend",
      tech: "Next.js / React",
      desc: "Dashboard, portfolio management, loan applications",
      features: ["Dashboard analytics", "Portfolio browser", "Loan details", "AI Assistant"],
    },
    {
      name: "FastAPI Backend",
      tech: "Python / FastAPI",
      desc: "REST API for scoring and analytics",
      features: ["Real-time scoring", "Portfolio queries", "Model serving", "WebSocket support"],
    },
    {
      name: "AI Credit Analyst",
      tech: "LangGraph / Claude",
      desc: "Intelligent assistant for credit analysis",
      features: ["Natural language queries", "Risk explanations", "Portfolio insights", "Regulatory guidance"],
    },
  ];

  const techStack = [
    { category: "Data Platform", items: ["Cloudera Data Platform (CDP)", "Apache Iceberg", "S3 Object Storage"] },
    { category: "Compute", items: ["CDE (Spark Jobs)", "CML (ML Workloads)", "Kubernetes"] },
    { category: "ML/AI", items: ["XGBoost", "Scikit-learn", "MLflow", "LangGraph", "Claude API"] },
    { category: "Backend", items: ["FastAPI", "Pydantic", "PyIceberg", "boto3"] },
    { category: "Frontend", items: ["Next.js 14", "React", "Tailwind CSS", "shadcn/ui"] },
  ];

  const icebergTables = [
    { table: "companies", partition: "industry", format: "Iceberg" },
    { table: "loan_history", partition: "year, status", format: "Iceberg" },
    { table: "payment_history", partition: "year, status", format: "Iceberg" },
    { table: "bureau_data", partition: "none", format: "Iceberg" },
    { table: "features", partition: "none", format: "Parquet" },
    { table: "scores", partition: "scoring_date", format: "Parquet" },
  ];

  const featureCategories = [
    { category: "Financial Ratios", features: ["Debt-to-Equity", "Current Ratio", "Quick Ratio", "Interest Coverage"] },
    { category: "Bureau Data", features: ["Credit Score", "Score Change", "Inquiries", "Utilization"] },
    { category: "Payment Behavior", features: ["Days Past Due Avg", "Late Payment Count", "Payment Trend", "Utilization Rate"] },
    { category: "Industry/Risk", features: ["Industry Risk Score", "Company Age", "Revenue Growth", "Loan Amount Ratio"] },
  ];

  const agentTools = [
    { tool: "get_portfolio_summary", desc: "Portfolio analytics" },
    { tool: "get_loan_details", desc: "Single loan data" },
    { tool: "score_company", desc: "Real-time PD/LGD" },
    { tool: "search_documents", desc: "RAG over 10-K filings" },
  ];

  const riskGrades = [
    { grade: "AAA", range: "0.0% - 0.5%", color: "bg-green-100 text-green-800" },
    { grade: "AA", range: "0.5% - 1.0%", color: "bg-green-100 text-green-700" },
    { grade: "A", range: "1.0% - 2.0%", color: "bg-green-50 text-green-700" },
    { grade: "BBB", range: "2.0% - 5.0%", color: "bg-yellow-50 text-yellow-700" },
    { grade: "BB", range: "5.0% - 10.0%", color: "bg-yellow-100 text-yellow-800" },
    { grade: "B", range: "10.0% - 20.0%", color: "bg-orange-100 text-orange-800" },
    { grade: "CCC", range: "20.0% - 50.0%", color: "bg-red-100 text-red-700" },
    { grade: "D", range: "50.0% - 100.0%", color: "bg-red-200 text-red-800" },
  ];

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Platform Architecture</h1>
        <p className="text-gray-500">End-to-end credit risk platform on Cloudera Data Platform</p>
      </div>

      {/* Navigation Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {[
            { id: "overview", label: "Overview" },
            { id: "pipeline", label: "Data Pipeline" },
            { id: "training", label: "Model Training" },
            { id: "serving", label: "Model Serving" },
            { id: "apps", label: "Applications" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
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

      {/* ==================== OVERVIEW TAB ==================== */}
      {activeTab === "overview" && (
        <>
          {/* Tech Stack Summary */}
          <Card>
            <CardHeader>
              <CardTitle>Technology Stack</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-5 gap-4">
                {techStack.map((stack) => (
                  <div key={stack.category} className="bg-gray-50 rounded-lg p-3">
                    <p className="font-medium text-sm text-gray-700 mb-2">{stack.category}</p>
                    <ul className="space-y-1">
                      {stack.items.map((item) => (
                        <li key={item} className="text-xs text-gray-600">{item}</li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Architecture Diagram */}
          <Card>
            <CardHeader>
              <CardTitle>Data Flow Architecture</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="relative overflow-x-auto">
                {/* Data Sources Layer */}
                <div className="flex justify-center mb-4">
                  <div className="bg-blue-50 border-2 border-blue-200 rounded-lg p-4 w-full max-w-4xl">
                    <p className="text-sm font-medium text-blue-800 text-center mb-3">DATA SOURCES</p>
                    <div className="grid grid-cols-5 gap-2">
                      {dataSourcesInfo.map((source) => (
                        <div key={source.name} className="bg-white rounded p-2 text-center border border-blue-100">
                          <p className="font-medium text-sm">{source.name}</p>
                          <p className="text-xs text-gray-500">{source.count}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Arrow */}
                <div className="flex justify-center mb-4">
                  <div className="flex flex-col items-center">
                    <div className="w-0.5 h-6 bg-gray-400"></div>
                    <svg className="w-4 h-4 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                    </svg>
                  </div>
                </div>

                {/* Spark Data Loading */}
                <div className="flex justify-center mb-4">
                  <div className="bg-orange-50 border-2 border-orange-200 rounded-lg px-6 py-3">
                    <div className="flex items-center space-x-2">
                      <svg className="w-5 h-5 text-orange-600" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clipRule="evenodd" />
                      </svg>
                      <span className="font-medium text-orange-800">Data Loading (CDE Spark)</span>
                    </div>
                    <p className="text-xs text-orange-600 text-center mt-1">load_to_iceberg.py</p>
                  </div>
                </div>

                {/* Arrow */}
                <div className="flex justify-center mb-4">
                  <div className="flex flex-col items-center">
                    <div className="w-0.5 h-6 bg-gray-400"></div>
                    <svg className="w-4 h-4 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                    </svg>
                  </div>
                </div>

                {/* S3 Storage / Iceberg Layer */}
                <div className="flex justify-center mb-4">
                  <div className="bg-green-50 border-2 border-green-200 rounded-lg p-4 w-full max-w-4xl">
                    <div className="flex items-center justify-center space-x-2 mb-3">
                      <svg className="w-5 h-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
                      </svg>
                      <p className="text-sm font-medium text-green-800">S3 DATA WAREHOUSE (Iceberg)</p>
                    </div>
                    <div className="grid grid-cols-6 gap-2">
                      {icebergTables.map((t) => (
                        <div key={t.table} className="bg-white rounded p-2 text-center border border-green-100">
                          <p className="font-medium text-xs">/{t.table}/</p>
                          <p className="text-xs text-gray-500">{t.format}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Arrow */}
                <div className="flex justify-center mb-4">
                  <div className="flex flex-col items-center">
                    <div className="w-0.5 h-6 bg-gray-400"></div>
                    <svg className="w-4 h-4 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                    </svg>
                  </div>
                </div>

                {/* Feature Engineering */}
                <div className="flex justify-center mb-4">
                  <div className="bg-orange-50 border-2 border-orange-200 rounded-lg px-6 py-3">
                    <div className="flex items-center space-x-2">
                      <svg className="w-5 h-5 text-orange-600" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clipRule="evenodd" />
                      </svg>
                      <span className="font-medium text-orange-800">Feature Engineering (CDE Spark)</span>
                      <Badge className="bg-orange-100 text-orange-700">Daily @ 1:00 AM</Badge>
                    </div>
                    <p className="text-xs text-orange-600 text-center mt-1">feature_engineering.py - Creates 23+ features</p>
                  </div>
                </div>

                {/* Branching Arrow */}
                <div className="flex justify-center mb-4">
                  <div className="w-0.5 h-6 bg-gray-400"></div>
                </div>

                {/* Three branches: PD Training, LGD Training, Batch Scoring */}
                <div className="grid grid-cols-3 gap-4 mb-4 max-w-4xl mx-auto">
                  <div className="flex flex-col items-center">
                    <div className="w-0.5 h-4 bg-gray-400 mb-2"></div>
                    <div className="bg-purple-50 border-2 border-purple-200 rounded-lg p-3 w-full">
                      <div className="flex items-center justify-center space-x-2 mb-2">
                        <svg className="w-4 h-4 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                        </svg>
                        <span className="font-medium text-purple-800 text-sm">PD Training</span>
                      </div>
                      <p className="text-xs text-purple-600 text-center">CML Job</p>
                      <p className="text-xs text-gray-500 text-center mt-1">XGBoost, GBM, LR</p>
                    </div>
                  </div>
                  <div className="flex flex-col items-center">
                    <div className="w-0.5 h-4 bg-gray-400 mb-2"></div>
                    <div className="bg-purple-50 border-2 border-purple-200 rounded-lg p-3 w-full">
                      <div className="flex items-center justify-center space-x-2 mb-2">
                        <svg className="w-4 h-4 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                        </svg>
                        <span className="font-medium text-purple-800 text-sm">LGD Training</span>
                      </div>
                      <p className="text-xs text-purple-600 text-center">CML Job</p>
                      <p className="text-xs text-gray-500 text-center mt-1">Gradient Boosting</p>
                    </div>
                  </div>
                  <div className="flex flex-col items-center">
                    <div className="w-0.5 h-4 bg-gray-400 mb-2"></div>
                    <div className="bg-orange-50 border-2 border-orange-200 rounded-lg p-3 w-full">
                      <div className="flex items-center justify-center space-x-2 mb-2">
                        <svg className="w-4 h-4 text-orange-600" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clipRule="evenodd" />
                        </svg>
                        <span className="font-medium text-orange-800 text-sm">Batch Scoring</span>
                      </div>
                      <p className="text-xs text-orange-600 text-center">CDE Spark</p>
                      <p className="text-xs text-gray-500 text-center mt-1">Daily @ 2:00 AM</p>
                    </div>
                  </div>
                </div>

                {/* Arrows to Models and Scores */}
                <div className="grid grid-cols-3 gap-4 mb-4 max-w-4xl mx-auto">
                  <div className="flex flex-col items-center col-span-2">
                    <div className="w-0.5 h-6 bg-gray-400"></div>
                    <svg className="w-4 h-4 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div className="flex flex-col items-center">
                    <div className="w-0.5 h-6 bg-gray-400"></div>
                    <svg className="w-4 h-4 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                    </svg>
                  </div>
                </div>

                {/* Models and Scores Storage */}
                <div className="grid grid-cols-3 gap-4 mb-4 max-w-4xl mx-auto">
                  <div className="col-span-2 bg-indigo-50 border-2 border-indigo-200 rounded-lg p-3">
                    <div className="flex items-center justify-center space-x-2 mb-2">
                      <svg className="w-5 h-5 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                      </svg>
                      <p className="font-medium text-indigo-800 text-sm">S3 Model Storage</p>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div className="bg-white rounded p-2 text-center border border-indigo-100">
                        <p className="font-medium text-xs">pd_model_latest.pkl</p>
                        <p className="text-xs text-gray-500">/models/pd/</p>
                      </div>
                      <div className="bg-white rounded p-2 text-center border border-indigo-100">
                        <p className="font-medium text-xs">lgd_model_latest.pkl</p>
                        <p className="text-xs text-gray-500">/models/lgd/</p>
                      </div>
                    </div>
                  </div>
                  <div className="bg-green-50 border-2 border-green-200 rounded-lg p-3">
                    <div className="flex items-center justify-center space-x-2 mb-2">
                      <svg className="w-5 h-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      <p className="font-medium text-green-800 text-sm">Scores</p>
                    </div>
                    <div className="bg-white rounded p-2 text-center border border-green-100">
                      <p className="font-medium text-xs">/scores/</p>
                      <p className="text-xs text-gray-500">by scoring_date</p>
                    </div>
                  </div>
                </div>

                {/* Arrow to API */}
                <div className="flex justify-center mb-4">
                  <div className="flex flex-col items-center">
                    <div className="w-0.5 h-6 bg-gray-400"></div>
                    <svg className="w-4 h-4 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                    </svg>
                  </div>
                </div>

                {/* API and Frontend */}
                <div className="flex justify-center">
                  <div className="bg-blue-50 border-2 border-blue-200 rounded-lg p-4 w-full max-w-3xl">
                    <p className="text-sm font-medium text-blue-800 text-center mb-3">CML APPLICATION</p>
                    <div className="grid grid-cols-4 gap-4">
                      <div className="bg-white rounded p-3 text-center border border-blue-100">
                        <svg className="w-6 h-6 text-blue-600 mx-auto mb-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                        </svg>
                        <p className="font-medium text-sm">Frontend</p>
                        <p className="text-xs text-gray-500">Next.js / React</p>
                      </div>
                      <div className="bg-white rounded p-3 text-center border border-blue-100">
                        <svg className="w-6 h-6 text-blue-600 mx-auto mb-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
                        </svg>
                        <p className="font-medium text-sm">API</p>
                        <p className="text-xs text-gray-500">FastAPI</p>
                      </div>
                      <div className="bg-white rounded p-3 text-center border border-blue-100">
                        <svg className="w-6 h-6 text-blue-600 mx-auto mb-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
                        </svg>
                        <p className="font-medium text-sm">Models</p>
                        <p className="text-xs text-gray-500">PD + LGD</p>
                      </div>
                      <div className="bg-white rounded p-3 text-center border border-blue-100">
                        <svg className="w-6 h-6 text-blue-600 mx-auto mb-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                        </svg>
                        <p className="font-medium text-sm">AI Assistant</p>
                        <p className="text-xs text-gray-500">LangGraph</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Risk Grade Reference */}
          <Card>
            <CardHeader>
              <CardTitle>Risk Grade Mapping</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-8 gap-2">
                {riskGrades.map((item) => (
                  <div key={item.grade} className={`p-3 rounded-lg text-center ${item.color}`}>
                    <p className="font-bold text-lg">{item.grade}</p>
                    <p className="text-xs mt-1">{item.range}</p>
                  </div>
                ))}
              </div>
              <p className="text-sm text-gray-500 mt-4 text-center">
                Risk grades are assigned based on Probability of Default (PD) ranges
              </p>
            </CardContent>
          </Card>
        </>
      )}

      {/* ==================== PIPELINE TAB ==================== */}
      {activeTab === "pipeline" && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>CDE Spark Jobs</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {sparkJobs.map((job) => (
                  <div key={job.name} className="p-4 bg-orange-50 rounded-lg border border-orange-200">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center space-x-2">
                        <svg className="w-5 h-5 text-orange-600" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clipRule="evenodd" />
                        </svg>
                        <p className="font-semibold text-orange-900">{job.name}</p>
                      </div>
                      <div className="flex space-x-2">
                        <Badge className="bg-orange-100 text-orange-700">{job.runtime}</Badge>
                        <Badge className="bg-gray-100 text-gray-700">{job.schedule}</Badge>
                      </div>
                    </div>
                    <p className="text-sm text-gray-600 mb-2">{job.desc}</p>
                    <p className="text-xs text-gray-500 font-mono mb-2">8_cde_jobs/spark_jobs/{job.file}</p>
                    <div className="flex flex-wrap gap-1">
                      {job.details.map((detail) => (
                        <span key={detail} className="text-xs bg-white px-2 py-0.5 rounded border border-orange-200">{detail}</span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <div className="grid grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Data Sources</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {dataSourcesInfo.map((source) => (
                    <div key={source.name} className="flex items-center justify-between p-3 bg-blue-50 rounded-lg border border-blue-100">
                      <div>
                        <p className="font-medium text-blue-900">{source.name}</p>
                        <p className="text-xs text-gray-500">{source.desc}</p>
                      </div>
                      <Badge className="bg-blue-100 text-blue-700">{source.count}</Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Iceberg Tables</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {icebergTables.map((item) => (
                    <div key={item.table} className="flex items-center justify-between p-3 bg-green-50 rounded-lg border border-green-100">
                      <div>
                        <p className="font-medium text-green-900 font-mono">{item.table}</p>
                        <p className="text-xs text-gray-500">Partition: {item.partition}</p>
                      </div>
                      <Badge className="bg-green-100 text-green-700">{item.format}</Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </>
      )}

      {/* ==================== TRAINING TAB ==================== */}
      {activeTab === "training" && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>CML Training Jobs</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {trainingJobs.map((job) => (
                  <div key={job.name} className="p-4 bg-purple-50 rounded-lg border border-purple-200">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center space-x-2">
                        <svg className="w-5 h-5 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                        </svg>
                        <p className="font-semibold text-purple-900">{job.name}</p>
                      </div>
                      <div className="flex space-x-2">
                        <Badge className="bg-purple-100 text-purple-700">{job.type}</Badge>
                        <Badge className="bg-gray-100 text-gray-700">{job.runtime}</Badge>
                      </div>
                    </div>
                    <p className="text-xs text-gray-500 font-mono mb-3">3_models/{job.file}</p>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-xs font-medium text-gray-700 mb-1">Algorithms</p>
                        <div className="flex flex-wrap gap-1">
                          {job.algorithms.map((alg) => (
                            <span key={alg} className="text-xs bg-white px-2 py-0.5 rounded border border-purple-200">{alg}</span>
                          ))}
                        </div>
                      </div>
                      <div>
                        <p className="text-xs font-medium text-gray-700 mb-1">Metrics</p>
                        <div className="flex flex-wrap gap-1">
                          {job.metrics.map((metric) => (
                            <span key={metric} className="text-xs bg-white px-2 py-0.5 rounded border border-purple-200">{metric}</span>
                          ))}
                        </div>
                      </div>
                    </div>
                    <div className="mt-3 pt-3 border-t border-purple-200">
                      <p className="text-xs text-gray-500">Output: <span className="font-mono">{job.output}</span></p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Feature Engineering</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-4 gap-4">
                {featureCategories.map((cat) => (
                  <div key={cat.category} className="bg-gray-50 rounded-lg p-3">
                    <p className="font-medium text-sm text-gray-700 mb-2">{cat.category}</p>
                    <ul className="space-y-1">
                      {cat.features.map((f) => (
                        <li key={f} className="text-xs text-gray-600">- {f}</li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </>
      )}

      {/* ==================== SERVING TAB ==================== */}
      {activeTab === "serving" && (
        <>
          <div className="grid grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Deployed Models</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="p-4 bg-indigo-50 rounded-lg border border-indigo-200">
                    <div className="flex items-center justify-between mb-2">
                      <p className="font-semibold text-indigo-900">PD Model (Probability of Default)</p>
                      <Badge className="bg-green-100 text-green-700">Active</Badge>
                    </div>
                    <p className="text-sm text-gray-600 mb-2">XGBoost classifier for default prediction</p>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div className="bg-white p-2 rounded border border-indigo-100">
                        <p className="text-gray-500">File</p>
                        <p className="font-mono">pd_model_latest.pkl</p>
                      </div>
                      <div className="bg-white p-2 rounded border border-indigo-100">
                        <p className="text-gray-500">Location</p>
                        <p className="font-mono">s3://bucket/models/pd/</p>
                      </div>
                    </div>
                  </div>
                  <div className="p-4 bg-indigo-50 rounded-lg border border-indigo-200">
                    <div className="flex items-center justify-between mb-2">
                      <p className="font-semibold text-indigo-900">LGD Model (Loss Given Default)</p>
                      <Badge className="bg-green-100 text-green-700">Active</Badge>
                    </div>
                    <p className="text-sm text-gray-600 mb-2">Gradient Boosting regressor for loss estimation</p>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div className="bg-white p-2 rounded border border-indigo-100">
                        <p className="text-gray-500">File</p>
                        <p className="font-mono">lgd_model_latest.pkl</p>
                      </div>
                      <div className="bg-white p-2 rounded border border-indigo-100">
                        <p className="text-gray-500">Location</p>
                        <p className="font-mono">s3://bucket/models/lgd/</p>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>API Endpoints</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {apiEndpoints.map((ep) => (
                    <div key={ep.path} className="flex items-center p-2 bg-gray-50 rounded border border-gray-200">
                      <Badge className={`mr-3 ${
                        ep.method === "POST" ? "bg-green-100 text-green-700" :
                        ep.method === "GET" ? "bg-blue-100 text-blue-700" :
                        "bg-purple-100 text-purple-700"
                      }`}>{ep.method}</Badge>
                      <div>
                        <p className="font-mono text-sm">{ep.path}</p>
                        <p className="text-xs text-gray-500">{ep.desc}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Scoring Pipeline</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div className="flex-1 text-center p-4 bg-blue-50 rounded-lg border border-blue-200 mx-2">
                  <p className="font-medium text-blue-900">Real-time Scoring</p>
                  <p className="text-xs text-gray-600 mt-1">FastAPI endpoint loads models on startup</p>
                  <p className="text-xs text-gray-500 mt-1">Latency: &lt;100ms</p>
                </div>
                <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
                </svg>
                <div className="flex-1 text-center p-4 bg-orange-50 rounded-lg border border-orange-200 mx-2">
                  <p className="font-medium text-orange-900">Batch Scoring</p>
                  <p className="text-xs text-gray-600 mt-1">CDE Spark job for portfolio-wide scoring</p>
                  <p className="text-xs text-gray-500 mt-1">Schedule: Daily @ 2:00 AM</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </>
      )}

      {/* ==================== APPS TAB ==================== */}
      {activeTab === "apps" && (
        <>
          <div className="grid grid-cols-3 gap-6">
            {applications.map((app) => (
              <Card key={app.name}>
                <CardHeader>
                  <div className="flex items-center space-x-2">
                    <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                    </svg>
                    <CardTitle className="text-lg">{app.name}</CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  <Badge className="bg-gray-100 text-gray-700 mb-3">{app.tech}</Badge>
                  <p className="text-sm text-gray-600 mb-3">{app.desc}</p>
                  <ul className="space-y-1">
                    {app.features.map((f) => (
                      <li key={f} className="text-xs text-gray-500 flex items-center">
                        <svg className="w-3 h-3 text-green-500 mr-1" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                        {f}
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            ))}
          </div>

          <Card>
            <CardHeader>
              <CardTitle>AI Credit Analyst Architecture</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div className="flex-1 p-4 bg-blue-50 rounded-lg border border-blue-200 mx-2 text-center">
                  <p className="font-medium text-blue-900">User Query</p>
                  <p className="text-xs text-gray-500 mt-1">Natural language</p>
                </div>
                <svg className="w-6 h-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
                <div className="flex-1 p-4 bg-purple-50 rounded-lg border border-purple-200 mx-2 text-center">
                  <p className="font-medium text-purple-900">LangGraph Agent</p>
                  <p className="text-xs text-gray-500 mt-1">State machine orchestration</p>
                </div>
                <svg className="w-6 h-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
                <div className="flex-1 p-4 bg-green-50 rounded-lg border border-green-200 mx-2 text-center">
                  <p className="font-medium text-green-900">Tools</p>
                  <p className="text-xs text-gray-500 mt-1">Portfolio, Scoring, RAG</p>
                </div>
                <svg className="w-6 h-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
                <div className="flex-1 p-4 bg-indigo-50 rounded-lg border border-indigo-200 mx-2 text-center">
                  <p className="font-medium text-indigo-900">Claude LLM</p>
                  <p className="text-xs text-gray-500 mt-1">Response generation</p>
                </div>
              </div>
              <div className="mt-4 grid grid-cols-4 gap-4">
                {agentTools.map((t) => (
                  <div key={t.tool} className="p-2 bg-gray-50 rounded border border-gray-200 text-center">
                    <p className="font-mono text-xs text-gray-700">{t.tool}</p>
                    <p className="text-xs text-gray-500">{t.desc}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>CML Deployment</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-4">
                <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                  <p className="font-medium text-blue-900 mb-2">CML Jobs</p>
                  <ul className="text-xs text-gray-600 space-y-1">
                    <li>- train_pd_model.py</li>
                    <li>- train_lgd_model.py</li>
                    <li>- validate_models.py</li>
                    <li>- register_models.py</li>
                  </ul>
                </div>
                <div className="p-4 bg-green-50 rounded-lg border border-green-200">
                  <p className="font-medium text-green-900 mb-2">CML Models</p>
                  <ul className="text-xs text-gray-600 space-y-1">
                    <li>- PD Model (XGBoost)</li>
                    <li>- LGD Model (Gradient Boosting)</li>
                    <li>- Model Registry integration</li>
                    <li>- Version tracking</li>
                  </ul>
                </div>
                <div className="p-4 bg-purple-50 rounded-lg border border-purple-200">
                  <p className="font-medium text-purple-900 mb-2">CML Application</p>
                  <ul className="text-xs text-gray-600 space-y-1">
                    <li>- FastAPI backend</li>
                    <li>- Next.js frontend</li>
                    <li>- WebSocket support</li>
                    <li>- Auto-scaling</li>
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
