"use client";

import React from "react";

interface NodeData {
  id: string;
  type: string;
  label: string;
  x: number;
  y: number;
  status?: string;
}

interface EdgeData {
  from: string;
  to: string;
  label?: string;
}

interface WorkflowCanvasProps {
  nodes: NodeData[];
  edges: EdgeData[];
  onNodeClick?: (node: NodeData) => void;
}

export function WorkflowCanvas({ nodes, edges, onNodeClick }: WorkflowCanvasProps) {
  return (
    <div className="relative bg-gray-900/50 border border-gray-700/50 rounded-xl overflow-hidden" style={{ minHeight: 400 }}>
      <svg className="absolute inset-0 w-full h-full" style={{ zIndex: 0 }}>
        {edges.map((edge, i) => {
          const fromNode = nodes.find((n) => n.id === edge.from);
          const toNode = nodes.find((n) => n.id === edge.to);
          if (!fromNode || !toNode) return null;
          return (
            <g key={i}>
              <line x1={fromNode.x + 75} y1={fromNode.y + 25} x2={toNode.x + 75} y2={toNode.y + 25} stroke="#4B5563" strokeWidth="2" markerEnd="url(#arrow)" />
              {edge.label && (
                <text x={(fromNode.x + toNode.x) / 2 + 75} y={(fromNode.y + toNode.y) / 2 + 25} fill="#9CA3AF" fontSize="10" textAnchor="middle">{edge.label}</text>
              )}
            </g>
          );
        })}
        <defs>
          <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#4B5563" />
          </marker>
        </defs>
      </svg>
      {nodes.map((node) => (
        <div
          key={node.id}
          className="absolute bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 cursor-pointer hover:border-indigo-500 transition-colors z-10"
          style={{ left: node.x, top: node.y, minWidth: 120 }}
          onClick={() => onNodeClick?.(node)}
        >
          <div className="text-xs text-gray-500">{node.type}</div>
          <div className="text-sm font-medium text-gray-200">{node.label}</div>
          {node.status && (
            <div className={`text-xs mt-1 ${node.status === "completed" ? "text-green-400" : node.status === "running" ? "text-blue-400" : "text-gray-500"}`}>
              {node.status}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

interface WorkflowToolbarProps {
  onAddNode: (type: string) => void;
  onSave: () => void;
  onRun: () => void;
}

export function WorkflowToolbar({ onAddNode, onSave, onRun }: WorkflowToolbarProps) {
  const nodeTypes = [
    { type: "trigger", label: "Trigger" },
    { type: "action", label: "Action" },
    { type: "condition", label: "Condition" },
    { type: "llm", label: "LLM Call" },
    { type: "tool", label: "Tool Use" },
    { type: "output", label: "Output" },
  ];
  return (
    <div className="flex items-center gap-2 p-2 bg-gray-800 border-b border-gray-700 rounded-t-xl">
      {nodeTypes.map((nt) => (
        <button key={nt.type} onClick={() => onAddNode(nt.type)} className="px-3 py-1.5 text-xs bg-gray-700 text-gray-300 rounded hover:bg-gray-600 transition-colors">
          {nt.label}
        </button>
      ))}
      <div className="flex-1" />
      <button onClick={onSave} className="px-3 py-1.5 text-xs bg-gray-700 text-gray-300 rounded hover:bg-gray-600">Save</button>
      <button onClick={onRun} className="px-3 py-1.5 text-xs bg-indigo-600 text-white rounded hover:bg-indigo-500">Run</button>
    </div>
  );
}
