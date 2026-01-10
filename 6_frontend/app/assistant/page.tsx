"use client";

import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { assistantApi, ChatResponse, portfolioApi, PortfolioSummary } from "@/lib/api";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Array<{ title: string; category: string }>;
  timestamp: Date;
}

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

export default function AssistantPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [portfolioSummary, setPortfolioSummary] = useState<PortfolioSummary | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Load portfolio summary for context panel
    portfolioApi.getSummary().then(setPortfolioSummary).catch(console.error);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await assistantApi.chat(input.trim(), true);

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: response.message,
        sources: response.sources,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "Sorry, I encountered an error processing your request. Please try again.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const suggestedQuestions = [
    "What is our current portfolio risk profile?",
    "Which industries have the highest concentration?",
    "What is our expected loss exposure?",
    "How much regulatory capital do we hold?",
    "Are there any large single-name exposures?",
    "What is the average PD across the portfolio?",
  ];

  return (
    <div className="h-[calc(100vh-4rem)] flex">
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="border-b px-6 py-4">
          <h1 className="text-xl font-bold text-gray-900">Portfolio AI Assistant</h1>
          <p className="text-sm text-gray-500">Ask questions about portfolio risk, concentration, and capital</p>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center">
              <div className="bg-blue-100 rounded-full p-4 mb-4">
                <svg className="w-8 h-8 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
              </div>
              <h2 className="text-lg font-semibold text-gray-900 mb-2">How can I help you?</h2>
              <p className="text-gray-500 mb-6 max-w-md">
                Ask me anything about your loan portfolio - risk metrics, concentration analysis,
                capital requirements, or specific loan details.
              </p>

              {/* Suggested Questions */}
              <div className="w-full max-w-2xl">
                <p className="text-sm text-gray-400 mb-3">Try asking:</p>
                <div className="grid grid-cols-2 gap-2">
                  {suggestedQuestions.map((question, idx) => (
                    <button
                      key={idx}
                      onClick={() => setInput(question)}
                      className="text-left px-4 py-3 bg-gray-50 hover:bg-gray-100 rounded-lg text-sm text-gray-700 transition-colors"
                    >
                      {question}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <>
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-3xl rounded-lg px-4 py-3 ${
                      message.role === "user"
                        ? "bg-blue-600 text-white"
                        : "bg-gray-100 text-gray-900"
                    }`}
                  >
                    {message.role === "user" ? (
                      <div className="whitespace-pre-wrap">{message.content}</div>
                    ) : (
                      <div className="prose prose-sm max-w-none prose-headings:mt-2 prose-headings:mb-1 prose-p:my-1 prose-table:my-2 prose-th:bg-gray-200 prose-th:px-2 prose-th:py-1 prose-td:px-2 prose-td:py-1 prose-td:border prose-th:border">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {message.content}
                        </ReactMarkdown>
                      </div>
                    )}
                    {message.sources && message.sources.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-gray-200">
                        <p className="text-xs text-gray-500 mb-1">Sources:</p>
                        <div className="flex flex-wrap gap-1">
                          {message.sources.map((source, idx) => (
                            <span
                              key={idx}
                              className="text-xs px-2 py-1 bg-white rounded text-gray-600"
                            >
                              {source.title}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    <div className="text-xs mt-2 opacity-60">
                      {message.timestamp.toLocaleTimeString()}
                    </div>
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-gray-100 rounded-lg px-4 py-3">
                    <div className="flex space-x-2">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0.2s" }}></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0.4s" }}></div>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* Input */}
        <div className="border-t p-4">
          <form onSubmit={handleSubmit} className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about your portfolio..."
              className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
            >
              Send
            </button>
          </form>
        </div>
      </div>

      {/* Context Panel */}
      <div className="w-80 border-l bg-gray-50 p-4 overflow-y-auto">
        <h3 className="font-semibold text-gray-900 mb-4">Portfolio Context</h3>

        {portfolioSummary ? (
          <div className="space-y-4">
            <div className="bg-white rounded-lg border p-3">
              <p className="text-xs text-gray-500 uppercase mb-1">Total Exposure</p>
              <p className="text-lg font-bold text-gray-900">{formatCurrency(portfolioSummary.total_exposure)}</p>
              <p className="text-xs text-gray-400">{portfolioSummary.loan_count} loans</p>
            </div>

            <div className="bg-white rounded-lg border p-3">
              <p className="text-xs text-gray-500 uppercase mb-1">Risk Metrics</p>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Avg PD</span>
                  <span className="font-medium">{portfolioSummary.avg_pd.toFixed(2)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Avg LGD</span>
                  <span className="font-medium">{portfolioSummary.avg_lgd.toFixed(2)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Expected Loss</span>
                  <span className="font-medium text-orange-600">{formatCurrency(portfolioSummary.expected_loss)}</span>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg border p-3">
              <p className="text-xs text-gray-500 uppercase mb-1">Capital</p>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Regulatory</span>
                  <span className="font-medium">{formatCurrency(portfolioSummary.regulatory_capital)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Economic</span>
                  <span className="font-medium">{formatCurrency(portfolioSummary.economic_capital)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">VaR 99.9%</span>
                  <span className="font-medium">{formatCurrency(portfolioSummary.var_999)}</span>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg border p-3">
              <p className="text-xs text-gray-500 uppercase mb-1">Portfolio Health</p>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Current</span>
                  <span className="font-medium text-green-600">{portfolioSummary.current_count}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Delinquent</span>
                  <span className="font-medium text-yellow-600">{portfolioSummary.delinquent_count}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Default</span>
                  <span className="font-medium text-red-600">{portfolioSummary.default_count}</span>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="animate-pulse space-y-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="bg-gray-200 rounded-lg h-24"></div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
