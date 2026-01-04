"use client";

import { memo } from "react";
import { Handle, Position, NodeProps } from "reactflow";
import { cn } from "@/lib/utils";

interface ProcessNodeData {
  label: string;
  status: "pending" | "in_progress" | "completed" | "failed";
  isActive?: boolean;
  onClick?: () => void;
}

export const ProcessNode = memo(({ data }: NodeProps<ProcessNodeData>) => {
  const { label, status, isActive, onClick } = data;

  const statusStyles = {
    pending: "bg-gray-100 border-gray-300 text-gray-600",
    in_progress: "bg-blue-100 border-blue-500 text-blue-700",
    completed: "bg-green-100 border-green-500 text-green-700",
    failed: "bg-red-100 border-red-500 text-red-700",
  };

  const statusIcons = {
    pending: (
      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <circle cx="12" cy="12" r="10" strokeWidth={2} />
      </svg>
    ),
    in_progress: (
      <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
      </svg>
    ),
    completed: (
      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
      </svg>
    ),
    failed: (
      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
      </svg>
    ),
  };

  return (
    <div
      className={cn(
        "px-4 py-3 rounded-lg border-2 min-w-[140px] cursor-pointer transition-all",
        statusStyles[status],
        isActive && "ring-2 ring-offset-2 ring-blue-500"
      )}
      onClick={onClick}
    >
      <Handle type="target" position={Position.Left} className="!bg-gray-400" />

      <div className="flex items-center space-x-2">
        {statusIcons[status]}
        <span className="font-medium text-sm">{label}</span>
      </div>

      <Handle type="source" position={Position.Right} className="!bg-gray-400" />
    </div>
  );
});

ProcessNode.displayName = "ProcessNode";
