"use client";

import React, { useEffect, useState, useCallback } from "react";
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  BackgroundVariant,
  Handle,
  Position,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import {
  Share2,
  Sparkles,
  Filter,
  Info,
  Brain,
  Zap,
  GraduationCap,
  ArrowRight,
  Network,
  Eye,
  Layers,
  Compass,
  FileText,
  RotateCcw,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  BookOpen
} from "lucide-react";
import { api } from "@/lib/api";
import { Card, Badge, Button } from "./ui";

function TopicNode({ data, selected }: any) {
  const isLearned = data.status === "learned";
  const isDue = data.status === "review_due" || data.status === "overdue";
  const isFocused = data.is_focused;

  let borderColor = "#6366f1";
  let bgGradient = "#ffffff";

  if (isFocused) {
    borderColor = "#ec4899";
    bgGradient = "linear-gradient(135deg, #fdf2f8 0%, #fce7f3 100%)";
  } else if (isLearned) {
    borderColor = "#10b981";
    bgGradient = "linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%)";
  } else if (isDue) {
    borderColor = "#f59e0b";
    bgGradient = "linear-gradient(135deg, #fefce8 0%, #fef08a 100%)";
  }

  return (
    <div
      style={{
        background: bgGradient,
        border: `2.5px solid ${borderColor}`,
        borderRadius: "18px",
        padding: "10px 16px",
        fontSize: "12px",
        fontWeight: 700,
        color: "#0f172a",
        boxShadow: selected || isFocused
          ? "0 10px 25px -3px rgba(236, 72, 153, 0.35), 0 4px 6px -4px rgba(236, 72, 153, 0.2)"
          : "0 6px 18px -2px rgba(15, 23, 42, 0.08)",
        minWidth: "120px",
        textAlign: "center",
      }}
    >
      <Handle type="target" position={Position.Top} className="!w-2 !h-2 !bg-indigo-400" />
      <div>{data.label}</div>
      {data.category && (
        <div style={{ fontSize: "10px", fontWeight: 500, color: "#64748b", marginTop: "2px" }}>
          {data.category}
        </div>
      )}
      <Handle type="source" position={Position.Bottom} className="!w-2 !h-2 !bg-indigo-400" />
    </div>
  );
}

const nodeTypes = {
  topicNode: TopicNode,
};

export function KnowledgeGraphView({
  onSelectTopic,
  onNavigate,
  focusTopicId: propFocusTopicId,
  focusTargetTopicId,
  focusRelId,
  onClearFocus
}: {
  onSelectTopic?: (topicId: string) => void;
  onNavigate?: (tab: string, meta?: any) => void;
  focusTopicId?: string;
  focusTargetTopicId?: string;
  focusRelId?: string;
  onClearFocus?: () => void;
}) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [stats, setStats] = useState<any>(null);
  const [clusters, setClusters] = useState<any[]>([]);
  const [selectedNodeData, setSelectedNodeData] = useState<any>(null);
  const [conceptDetails, setConceptDetails] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [loadingDetails, setLoadingDetails] = useState(false);
  
  // Progressive disclosure levels: 'simple' (Default Level 1), 'explore' (Level 2), 'detailed' (Level 3)
  const [detailLevel, setDetailLevel] = useState<"simple" | "explore" | "detailed">("simple");
  const [focusTopicId, setFocusTopicId] = useState<string | null>(propFocusTopicId || null);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  useEffect(() => {
    if (propFocusTopicId) {
      setFocusTopicId(propFocusTopicId);
    }
  }, [propFocusTopicId]);

  useEffect(() => {
    loadGraph(detailLevel, focusTopicId, selectedCategory);
  }, [detailLevel, focusTopicId, selectedCategory]);

  const loadGraph = async (level: string, focusId: string | null, catId: string | null) => {
    setLoading(true);
    try {
      const data = await api.getKnowledgeGraph(level, focusId || undefined, catId || undefined);
      
      // Style nodes nicely with claymorphic card styling
      const styledNodes = (data.nodes || []).map((n: any) => {
        const isLearned = n.data.status === "learned";
        const isDue = n.data.status === "review_due" || n.data.status === "overdue";
        const isFocused = n.id === focusId || n.data.is_focused || (focusTargetTopicId && n.id === focusTargetTopicId);

        let borderColor = "#6366f1";
        let bgGradient = "#ffffff";

        if (isFocused) {
          borderColor = "#ec4899";
          bgGradient = "linear-gradient(135deg, #fdf2f8 0%, #fce7f3 100%)";
        } else if (isLearned) {
          borderColor = "#10b981";
          bgGradient = "linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%)";
        } else if (isDue) {
          borderColor = "#f59e0b";
          bgGradient = "linear-gradient(135deg, #fefce8 0%, #fef08a 100%)";
        }

        return {
          ...n,
          style: {
            background: bgGradient,
            border: `2.5px solid ${borderColor}`,
            borderRadius: "18px",
            padding: "12px 18px",
            fontSize: "12px",
            fontWeight: 700,
            color: "#0f172a",
            boxShadow: isFocused
              ? "0 10px 25px -3px rgba(236, 72, 153, 0.45), 0 4px 6px -4px rgba(236, 72, 153, 0.3)"
              : "0 6px 18px -2px rgba(15, 23, 42, 0.08), -2px -2px 10px rgba(255, 255, 255, 0.9)",
            letterSpacing: "-0.01em",
            cursor: "pointer",
            minWidth: "140px",
            textAlign: "center" as const
          },
        };
      });

      // Style edges: highlight cross-document, prerequisites, and focused relationships
      const styledEdges = (data.edges || []).map((e: any) => {
        const isCross = e.data?.is_cross_document;
        const isPrereq = e.data?.relationship_type?.includes("prerequisite");
        const isTargetRel = (focusRelId && e.id === focusRelId) || 
                            (focusId && focusTargetTopicId && ((e.source === focusId && e.target === focusTargetTopicId) || (e.source === focusTargetTopicId && e.target === focusId)));

        let strokeColor = isCross ? "#a855f7" : isPrereq ? "#f59e0b" : "#818cf8";
        let strokeWidth = isCross ? 2.5 : 1.8;

        if (isTargetRel) {
          strokeColor = "#ec4899";
          strokeWidth = 3.5;
        }
        
        return {
          ...e,
          style: {
            stroke: strokeColor,
            strokeWidth: strokeWidth,
            opacity: isTargetRel ? 1.0 : (focusId ? 0.75 : 0.85)
          },
          labelStyle: { fill: strokeColor, fontWeight: 700, fontSize: isTargetRel ? 11 : 10 },
          animated: isPrereq || isCross || isTargetRel
        };
      });

      setNodes(styledNodes);
      setEdges(styledEdges);
      setStats(data.stats);
      setClusters(data.clusters || []);

      if (styledNodes.length > 0 && !selectedNodeData) {
        handleSelectNode(styledNodes[0].data);
      }
    } catch (e) {
      console.error("Failed to load knowledge graph:", e);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectNode = async (nodeData: any) => {
    setSelectedNodeData(nodeData);
    if (!nodeData?.id) return;
    setLoadingDetails(true);
    try {
      const details = await api.getConceptDetails(nodeData.id);
      setConceptDetails(details);
    } catch (e) {
      console.error("Failed to load concept details:", e);
      setConceptDetails(null);
    } finally {
      setLoadingDetails(false);
    }
  };

  const onNodeClick = useCallback((event: any, node: any) => {
    handleSelectNode(node.data);
  }, []);

  const handleResetFocus = () => {
    setFocusTopicId(null);
    setSelectedCategory(null);
    if (onClearFocus) onClearFocus();
  };

  return (
    <div className="space-y-4 max-w-7xl mx-auto h-[calc(100vh-140px)] flex flex-col font-sans pb-4">
      {/* Header, Level Switcher & Filtering */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 shrink-0">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="purple" className="flex items-center gap-1 font-bold">
              <Layers className="w-3 h-3" />
              <span>Knowledge Connectivity</span>
            </Badge>
            <span className="text-xs text-slate-400">• Progressive Disclosure</span>
            {focusTopicId && (
              <button onClick={handleResetFocus} className="cursor-pointer">
                <Badge variant="warning">
                  Focused Concept (Click to Clear) ✕
                </Badge>
              </button>
            )}
          </div>
          <h2 className="text-2xl font-black text-slate-900 tracking-tight">
            Knowledge Connectivity & Graph
          </h2>
          <p className="text-xs text-slate-500">
            {detailLevel === "simple"
              ? "Simple View: Key high-level concepts and how they connect in plain English."
              : detailLevel === "explore"
              ? "Explore View: Discover subtopics, prerequisites, and cross-document links."
              : "Detailed View: Full academic topology, source evidence, and network centrality."}
          </p>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          {/* 3 Progressive Disclosure Levels */}
          <div className="flex items-center bg-white p-1 rounded-2xl border border-slate-200/90 text-xs font-semibold shadow-xs">
            <span className="text-[10px] text-slate-400 px-2 font-bold uppercase tracking-wider">Level:</span>
            
            <button
              onClick={() => setDetailLevel("simple")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl transition-all cursor-pointer ${
                detailLevel === "simple"
                  ? "bg-indigo-600 text-white shadow-xs font-bold"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>1. Simple</span>
            </button>

            <button
              onClick={() => setDetailLevel("explore")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl transition-all cursor-pointer ${
                detailLevel === "explore"
                  ? "bg-indigo-600 text-white shadow-xs font-bold"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              <Compass className="w-3.5 h-3.5" />
              <span>2. Explore</span>
            </button>

            <button
              onClick={() => setDetailLevel("detailed")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl transition-all cursor-pointer ${
                detailLevel === "detailed"
                  ? "bg-indigo-600 text-white shadow-xs font-bold"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              <Eye className="w-3.5 h-3.5" />
              <span>3. Detailed</span>
            </button>
          </div>

          {stats && (
            <div className="flex items-center gap-2 text-xs bg-white px-3.5 py-1.5 rounded-2xl border border-slate-200/90 shadow-xs font-bold text-slate-700">
              <span className="text-indigo-600">{stats.total_nodes} Shown</span>
              {stats.full_vault_nodes > stats.total_nodes && (
                <span className="text-slate-400 text-[11px]">({stats.full_vault_nodes} total)</span>
              )}
              <span className="text-slate-300">•</span>
              <span className="text-violet-600">{stats.total_edges} Connections</span>
            </div>
          )}
        </div>
      </div>

      {/* Focused Subgraph Notification & Quick-Exit Banner */}
      {focusTopicId && (
        <div className="bg-indigo-950/90 text-white px-4 py-2.5 rounded-2xl flex items-center justify-between gap-3 border border-indigo-800 shadow-md">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-7 h-7 rounded-lg bg-pink-500/20 border border-pink-400/40 flex items-center justify-center text-pink-400 shrink-0">
              <Compass className="w-4 h-4" />
            </div>
            <div className="truncate">
              <p className="text-xs font-bold text-pink-200">Focused Subgraph Explorer</p>
              <p className="text-[11px] text-slate-300 truncate">
                Isolating targeted concept and its immediate 1st-degree neighbors ({nodes.length} nodes active).
              </p>
            </div>
          </div>
          <Button
            size="sm"
            variant="secondary"
            onClick={handleResetFocus}
            className="text-xs bg-slate-800 hover:bg-slate-700 text-white border-slate-700 shrink-0"
          >
            <Eye className="w-3.5 h-3.5 mr-1" /> View Full Graph
          </Button>
        </div>
      )}

      {/* Main Canvas and Inspector */}
      <div className="flex-1 flex gap-4 min-h-0">
        {/* React Flow Canvas */}
        <div className="flex-1 clay-card overflow-hidden relative shadow-lg rounded-3xl border border-slate-200/90 bg-slate-50/40">
          {loading ? (
            <div className="flex flex-col items-center justify-center h-full text-slate-400 text-sm gap-2">
              <Sparkles className="w-6 h-6 animate-spin text-indigo-600" />
              <span className="font-semibold text-slate-600">Structuring simplified knowledge network...</span>
            </div>
          ) : nodes.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center p-8 text-slate-400">
              <div className="w-14 h-14 rounded-3xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 mb-3 shadow-xs">
                <Network className="w-7 h-7" />
              </div>
              <h3 className="font-bold text-slate-900 text-base mb-1">Knowledge Connectivity is Ready</h3>
              <p className="text-xs text-slate-500 max-w-sm mb-4">
                Upload your notes, textbooks, or captures to see high-level concept clusters, relationships, and cross-document synergies emerge automatically.
              </p>
            </div>
          ) : (
            <ReactFlow
              nodes={nodes}
              edges={edges}
              nodeTypes={nodeTypes}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onNodeClick={onNodeClick}
              fitView
              minZoom={0.3}
              maxZoom={1.8}
            >
              <Background variant={BackgroundVariant.Dots} gap={24} size={1.2} color="#cbd5e1" />
              <Controls className="clay-card !bg-white/95 !border-slate-200 !rounded-2xl !shadow-md" />
              <MiniMap
                className="clay-card !rounded-2xl !overflow-hidden !border-slate-200"
                nodeStrokeWidth={3}
                zoomable
                pannable
              />
            </ReactFlow>
          )}

          {/* Canvas Legend & Plain-English Helper */}
          <div className="absolute top-4 left-4 bg-white/95 backdrop-blur-md p-3.5 rounded-2xl border border-slate-200/90 text-xs space-y-1.5 shadow-md z-10 max-w-xs">
            <div className="flex items-center justify-between">
              <span className="font-black text-slate-900 block text-[11px] uppercase tracking-wider">
                Concept Legend
              </span>
              <span className="text-[10px] text-indigo-600 font-bold capitalize">Level: {detailLevel}</span>
            </div>
            
            <div className="grid grid-cols-2 gap-x-2 gap-y-1 pt-1 text-[11px]">
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 shrink-0"></span>
                <span className="text-slate-700 font-medium truncate">Learned & Stable</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500 shrink-0"></span>
                <span className="text-slate-700 font-medium truncate">Review Due</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-purple-500 shrink-0"></span>
                <span className="text-slate-700 font-medium truncate">Cross-Document</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-pink-500 shrink-0"></span>
                <span className="text-slate-700 font-medium truncate">Focused Concept</span>
              </div>
            </div>

            {detailLevel === "simple" && (
              <p className="text-[10px] text-slate-500 pt-1 border-t border-slate-100 italic">
                💡 Showing main concepts. Switch to <strong>Explore</strong> or <strong>Detailed</strong> to reveal all subtopics.
              </p>
            )}
          </div>
        </div>

        {/* Selected Concept Inspector Drawer */}
        {selectedNodeData && (
          <div className="w-88 clay-card p-5 sm:p-6 flex flex-col justify-between shrink-0 rounded-3xl border border-slate-200/90 shadow-xl overflow-y-auto bg-white/95">
            <div className="space-y-4">
              {/* Concept Title & Badges */}
              <div className="border-b border-slate-100 pb-3">
                <div className="flex items-center justify-between gap-1 mb-1.5 flex-wrap">
                  <Badge
                    variant={selectedNodeData.status === "learned" ? "success" : "warning"}
                    className="text-[10px] font-bold uppercase"
                  >
                    {selectedNodeData.status || "unlearned"}
                  </Badge>
                  {selectedNodeData.category && (
                    <Badge variant="purple" className="text-[10px]">
                      {selectedNodeData.category}
                    </Badge>
                  )}
                </div>

                <h3 className="font-black text-xl text-slate-900 leading-snug tracking-tight">
                  {selectedNodeData.label}
                </h3>
                {selectedNodeData.document_title && (
                  <span className="text-xs text-slate-500 flex items-center gap-1 mt-1 font-medium">
                    <FileText className="w-3.5 h-3.5 text-indigo-500 shrink-0" />
                    <span className="truncate">{selectedNodeData.document_title}</span>
                  </span>
                )}
              </div>

              {/* Concept Description in Plain English */}
              <div>
                <h4 className="text-xs font-bold text-slate-700 mb-1.5 uppercase tracking-wider flex items-center justify-between">
                  <span>Concept Meaning</span>
                  <span className="text-[10px] text-slate-400 font-normal">Grounded</span>
                </h4>
                <p className="text-xs text-slate-700 leading-relaxed bg-slate-50 p-3 rounded-2xl border border-slate-200/80">
                  {selectedNodeData.description || "Foundational topic extracted from your vault study material."}
                </p>
              </div>

              {/* Retention & Memory Metrics */}
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="p-3 rounded-2xl bg-indigo-50/70 border border-indigo-100">
                  <span className="text-[10px] text-indigo-700 font-bold block uppercase">Retention</span>
                  <span className="text-lg font-black text-indigo-950">
                    {Math.round((selectedNodeData.retention || 1) * 100)}%
                  </span>
                </div>
                <div className="p-3 rounded-2xl bg-slate-50 border border-slate-200/80">
                  <span className="text-[10px] text-slate-500 font-bold block uppercase">Stability</span>
                  <span className="text-lg font-black text-slate-800">
                    {selectedNodeData.stability || 1.0}d
                  </span>
                </div>
              </div>

              {/* Connected Relationships with Plain-English Explanations */}
              <div>
                <h4 className="text-xs font-bold text-slate-700 mb-1.5 uppercase tracking-wider">
                  How This Connects
                </h4>
                {loadingDetails ? (
                  <div className="text-xs text-slate-400 py-3 text-center">Loading connections...</div>
                ) : conceptDetails?.connections && conceptDetails.connections.length > 0 ? (
                  <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                    {conceptDetails.connections.slice(0, 4).map((c: any, idx: number) => (
                      <div
                        key={idx}
                        className="p-2.5 rounded-xl border border-slate-100 bg-slate-50/60 hover:bg-indigo-50/50 hover:border-indigo-200 transition-all cursor-pointer"
                        onClick={() => {
                          setFocusTopicId(c.topic_id);
                          handleSelectNode({ id: c.topic_id, label: c.topic_name });
                        }}
                      >
                        <div className="flex items-center justify-between text-[11px] mb-1 font-bold">
                          <span className="text-slate-900 truncate">{c.topic_name}</span>
                          <span className="text-[10px] text-indigo-600 bg-white px-1.5 py-0.5 rounded border border-indigo-100">
                            {c.relationship_type}
                          </span>
                        </div>
                        <p className="text-[10px] text-slate-600 leading-tight">
                          {c.simple_explanation}
                        </p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-3 bg-slate-50 rounded-xl text-[11px] text-slate-500 italic">
                    Independent core topic. Connects dynamically as more course units are ingested.
                  </div>
                )}
              </div>

              {/* Focus / Expand Controls */}
              <div className="flex items-center gap-2 pt-1">
                <Button
                  size="sm"
                  variant="outline"
                  className="flex-1 text-xs justify-center rounded-xl"
                  onClick={() => setFocusTopicId(focusTopicId === selectedNodeData.id ? null : selectedNodeData.id)}
                >
                  <Filter className="w-3.5 h-3.5 mr-1" />
                  <span>{focusTopicId === selectedNodeData.id ? "Show All" : "Focus on Concept"}</span>
                </Button>
                {focusTopicId && (
                  <Button
                    size="sm"
                    variant="ghost"
                    className="text-xs text-slate-500 rounded-xl px-2"
                    onClick={handleResetFocus}
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                  </Button>
                )}
              </div>
            </div>

            {/* Direct Navigation to Real Learning Resources */}
            <div className="pt-4 border-t border-slate-100 space-y-2 mt-4">
              <Button
                size="md"
                variant="primary"
                className="w-full justify-center shadow-md shadow-indigo-600/25"
                onClick={() => {
                  if (onSelectTopic) onSelectTopic(selectedNodeData.id);
                  if (onNavigate) onNavigate("learn", { topic: selectedNodeData.label });
                }}
              >
                <GraduationCap className="w-4 h-4 mr-1.5" />
                <span>Explain in Learn</span>
              </Button>

              <div className="grid grid-cols-2 gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  className="w-full justify-center text-xs rounded-xl"
                  onClick={() => {
                    if (onNavigate) onNavigate("flashcards", { topic_id: selectedNodeData.id });
                  }}
                >
                  <Zap className="w-3.5 h-3.5 mr-1 text-amber-500" />
                  <span>Flashcards</span>
                </Button>

                <Button
                  size="sm"
                  variant="outline"
                  className="w-full justify-center text-xs rounded-xl"
                  onClick={() => {
                    if (onNavigate) onNavigate("recall", { topic_id: selectedNodeData.id });
                  }}
                >
                  <Brain className="w-3.5 h-3.5 mr-1 text-indigo-500" />
                  <span>Active Quiz</span>
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
