"use client";

import { useCallback, useMemo } from "react";
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
} from "reactflow";
import "reactflow/dist/style.css";
import { ProcessNode } from "./ProcessNode";

interface WorkflowStep {
  name: string;
  label: string;
  status: "pending" | "in_progress" | "completed" | "failed";
  data?: Record<string, unknown>;
}

interface WorkflowCanvasProps {
  steps: WorkflowStep[];
  currentStep?: string;
  onStepClick?: (stepName: string) => void;
}

const nodeTypes = {
  process: ProcessNode,
};

export function WorkflowCanvas({ steps, currentStep, onStepClick }: WorkflowCanvasProps) {
  // Create nodes from steps
  const initialNodes: Node[] = useMemo(() => {
    return steps.map((step, index) => ({
      id: step.name,
      type: "process",
      position: { x: 50 + index * 200, y: 100 },
      data: {
        label: step.label,
        status: step.status,
        isActive: step.name === currentStep,
        onClick: () => onStepClick?.(step.name),
      },
    }));
  }, [steps, currentStep, onStepClick]);

  // Create edges between consecutive nodes
  const initialEdges: Edge[] = useMemo(() => {
    return steps.slice(0, -1).map((step, index) => ({
      id: `${step.name}-${steps[index + 1].name}`,
      source: step.name,
      target: steps[index + 1].name,
      animated: step.status === "completed" && steps[index + 1].status === "in_progress",
      style: {
        stroke: step.status === "completed" ? "#10b981" : "#d1d5db",
        strokeWidth: 2,
      },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: step.status === "completed" ? "#10b981" : "#d1d5db",
      },
    }));
  }, [steps]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  return (
    <div className="h-[400px] w-full border border-gray-200 rounded-lg bg-gray-50">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        attributionPosition="bottom-left"
      >
        <Controls />
        <MiniMap
          nodeColor={(node) => {
            const status = node.data?.status;
            if (status === "completed") return "#10b981";
            if (status === "in_progress") return "#3b82f6";
            if (status === "failed") return "#ef4444";
            return "#d1d5db";
          }}
        />
        <Background color="#aaa" gap={16} />
      </ReactFlow>
    </div>
  );
}
