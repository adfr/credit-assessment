"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ChatInterface } from "@/components/analyst/ChatInterface";
import { RiskMetrics } from "@/components/analyst/RiskMetrics";
import { useApplications } from "@/hooks/useApplications";
import { analystApi } from "@/lib/api";

interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
  sources?: Array<{ title: string; category: string }>;
}

export default function AnalystPage() {
  const params = useParams();
  const applicationId = params.id as string;

  const { currentApplication, decision, getApplication, getDecision } =
    useApplications();

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>([]);
  const [riskSummary, setRiskSummary] = useState<{
    pdScore?: number;
    lgdScore?: number;
    expectedLoss?: number;
    riskGrade?: string;
  } | null>(null);

  useEffect(() => {
    if (applicationId) {
      getApplication(applicationId);
      getDecision(applicationId).catch(() => {});

      // Get suggestions
      analystApi.getSuggestions(applicationId).then((result) => {
        setSuggestedQuestions(result.suggestions);
      }).catch(() => {});

      // Get risk summary
      analystApi.getRiskSummary(applicationId).then((result) => {
        const summary = result.summary as {
          risk_metrics?: {
            pd_score?: number;
            lgd_score?: number;
            expected_loss?: number;
            risk_grade?: string;
          };
        };
        setRiskSummary({
          pdScore: summary.risk_metrics?.pd_score,
          lgdScore: summary.risk_metrics?.lgd_score,
          expectedLoss: summary.risk_metrics?.expected_loss,
          riskGrade: summary.risk_metrics?.risk_grade,
        });
      }).catch(() => {});
    }
  }, [applicationId, getApplication, getDecision]);

  const handleSendMessage = useCallback(async (content: string) => {
    // Add user message
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await analystApi.chat(content, applicationId, true);
      const message = response.message as {
        content?: string;
        timestamp?: string;
      };
      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: message.content || "I couldn't process that request.",
        timestamp: message.timestamp || new Date().toISOString(),
        sources: response.sources as Array<{ title: string; category: string }>,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage: ChatMessage = {
        id: `error-${Date.now()}`,
        role: "assistant",
        content: "Sorry, I encountered an error processing your request. Please try again.",
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }, [applicationId]);

  return (
    <div className="p-6 h-[calc(100vh-8rem)]">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">AI Analyst</h1>
          <p className="text-gray-500">
            {currentApplication?.company_name || "Loading..."}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[calc(100%-4rem)]">
        {/* Chat Interface */}
        <div className="lg:col-span-2">
          <Card className="h-full">
            <CardContent className="p-0 h-full">
              <ChatInterface
                applicationId={applicationId}
                messages={messages}
                onSendMessage={handleSendMessage}
                isLoading={isLoading}
                suggestedQuestions={suggestedQuestions}
              />
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6 overflow-y-auto">
          {/* Risk Metrics */}
          <RiskMetrics
            pdScore={riskSummary?.pdScore || decision?.pd_at_decision}
            lgdScore={riskSummary?.lgdScore || decision?.lgd_at_decision}
            expectedLoss={riskSummary?.expectedLoss || decision?.el_at_decision}
            riskGrade={riskSummary?.riskGrade}
          />

          {/* Application Summary */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Application Summary</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {currentApplication && (
                <>
                  <div>
                    <p className="text-xs text-gray-500">Company</p>
                    <p className="font-medium">{currentApplication.company_name}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Industry</p>
                    <p className="font-medium capitalize">
                      {currentApplication.industry}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Requested Amount</p>
                    <p className="font-medium">
                      ${currentApplication.requested_amount?.toLocaleString()}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Status</p>
                    <p className="font-medium capitalize">
                      {currentApplication.status}
                    </p>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          {/* Quick Actions */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Quick Questions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {[
                  "What are the key risk factors?",
                  "What policy requirements apply?",
                  "What is the approval authority?",
                  "What conditions should apply?",
                ].map((question, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSendMessage(question)}
                    disabled={isLoading}
                    className="w-full text-left text-sm p-2 rounded bg-gray-50 hover:bg-gray-100 transition-colors disabled:opacity-50"
                  >
                    {question}
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
