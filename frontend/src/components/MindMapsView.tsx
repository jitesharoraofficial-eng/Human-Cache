"use client";

import React, { useEffect, useState } from "react";
import { Network, Sparkles, Plus, AlertCircle, FileText, BookOpen, Layers } from "lucide-react";
import {
  ReactFlow,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  BackgroundVariant
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { api } from "@/lib/api";
import { Card, Button, Badge } from "./ui";

export function MindMapsView() {
  const [mindMaps, setMindMaps] = useState<any[]>([]);
  const [selectedMap, setSelectedMap] = useState<any>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [newTopicInput, setNewTopicInput] = useState("");
  const [detailLevel, setDetailLevel] = useState<string>("semi-detailed");
  const [generating, setGenerating] = useState(false);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // User materials for quick grounded generation
  const [userTopics, setUserTopics] = useState<any[]>([]);
  const [userDocs, setUserDocs] = useState<any[]>([]);
  const [selectedTopicId, setSelectedTopicId] = useState<string>("");
  const [selectedDocId, setSelectedDocId] = useState<string>("");

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const [maps, topics, docs] = await Promise.all([
        api.getMindMaps().catch(() => []),
        api.getTopics().catch(() => []),
        api.getDocuments().catch(() => []),
      ]);

      setMindMaps(maps);
      setUserTopics(topics);
      setUserDocs(docs);

      if (maps && maps.length > 0) {
        displayMap(maps[0]);
      } else {
        setSelectedMap(null);
        setNodes([]);
        setEdges([]);
      }
    } catch (e: any) {
      console.error(e);
      setErrorMessage(e.message || "Failed to load mind maps data.");
    } finally {
      setLoading(false);
    }
  };

  const displayMap = (m: any) => {
    setSelectedMap(m);
    setErrorMessage(null);
    if (m.structure_json?.nodes) {
      setNodes(m.structure_json.nodes);
      setEdges(m.structure_json.edges || []);
    } else {
      setNodes([]);
      setEdges([]);
    }
  };

  const generateNewMap = async (
    topicTitle: string,
    level: string = detailLevel,
    topicId?: string,
    docId?: string
  ) => {
    if (!topicTitle.trim() || generating) return;
    setGenerating(true);
    setErrorMessage(null);

    try {
      const res = await api.generateMindMap(
        topicTitle.trim(),
        level,
        topicId || selectedTopicId || undefined,
        docId || selectedDocId || undefined
      );

      setMindMaps((prev) => [res, ...prev]);
      displayMap(res);
      setNewTopicInput("");
      setSelectedTopicId("");
      setSelectedDocId("");
    } catch (e: any) {
      const detailMsg = e.message || "Failed to generate mind map.";
      setErrorMessage(detailMsg);
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="space-y-4 max-w-7xl mx-auto h-[calc(100vh-140px)] flex flex-col">
      {/* Top Header & Generation Toolbar */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 shrink-0">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Mind Maps & Hierarchical Schemas</h2>
          <p className="text-xs text-slate-500">
            Concept hierarchies grounded in your actual uploaded notes, definitions, and curriculum documents.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          {/* Detail Level Selector */}
          <div className="flex items-center bg-slate-100 p-1 rounded-xl border border-slate-200 text-xs font-medium">
            <span className="text-[11px] text-slate-500 px-2 font-semibold">Detail:</span>
            {(["brief", "semi-detailed", "detailed"] as const).map((lvl) => (
              <button
                key={lvl}
                onClick={() => {
                  setDetailLevel(lvl);
                  if (selectedMap?.central_topic) {
                    generateNewMap(
                      selectedMap.central_topic,
                      lvl,
                      selectedMap.topic_id,
                      selectedMap.document_id
                    );
                  }
                }}
                disabled={generating}
                className={`px-2.5 py-1 rounded-lg capitalize transition-all cursor-pointer ${
                  detailLevel === lvl
                    ? "bg-white text-indigo-700 shadow-xs font-semibold"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                {lvl.replace("-", " ")}
              </button>
            ))}
          </div>

          {/* Quick Select from User Materials */}
          {userTopics.length > 0 && (
            <select
              value={selectedTopicId}
              onChange={(e) => {
                const id = e.target.value;
                setSelectedTopicId(id);
                if (id) {
                  const found = userTopics.find((t) => t.id === id);
                  if (found) {
                    setNewTopicInput(found.canonical_name || found.name);
                  }
                }
              }}
              disabled={generating}
              className="text-xs border border-slate-200/90 rounded-xl px-2.5 py-2 bg-white/95 shadow-2xs text-slate-700 focus:outline-indigo-500 max-w-[150px] truncate"
            >
              <option value="">Quick Pick Concept...</option>
              {userTopics.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.canonical_name || t.name}
                </option>
              ))}
            </select>
          )}

          {/* Search or Free-text Concept Input */}
          <div className="flex items-center gap-2">
            <input
              type="text"
              placeholder="Concept to map (e.g. VSEPR Theory)..."
              value={newTopicInput}
              onChange={(e) => setNewTopicInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && newTopicInput.trim() && !generating) {
                  generateNewMap(newTopicInput, detailLevel, selectedTopicId, selectedDocId);
                }
              }}
              disabled={generating}
              className="text-xs border border-slate-200/90 rounded-xl px-3 py-2 bg-white/95 shadow-2xs focus:outline-indigo-500 w-48 sm:w-60"
            />
            <Button
              size="sm"
              onClick={() => generateNewMap(newTopicInput, detailLevel, selectedTopicId, selectedDocId)}
              disabled={generating || !newTopicInput.trim()}
              className="bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl shadow-xs shrink-0 cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5 mr-1" />
              {generating ? "Mapping..." : "Generate"}
            </Button>
          </div>
        </div>
      </div>

      {/* Inline Error Notification Banner */}
      {errorMessage && (
        <div className="shrink-0 flex items-start gap-2.5 p-3 rounded-2xl bg-amber-50/90 border border-amber-200/90 text-amber-900 text-xs shadow-2xs">
          <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-semibold text-amber-950">Generation Notice</p>
            <p className="text-amber-800 text-[11px] mt-0.5">{errorMessage}</p>
          </div>
          <button
            onClick={() => setErrorMessage(null)}
            className="text-amber-700 hover:text-amber-950 text-xs font-bold px-1.5 py-0.5 rounded-md hover:bg-amber-100"
          >
            ✕
          </button>
        </div>
      )}

      {/* Main Workspace: React Flow Canvas & Saved Schemas Bento */}
      <div className="flex-1 flex flex-col lg:flex-row gap-5 min-h-0">
        {/* Mind Map Canvas */}
        <div className="flex-1 clay-card bg-white rounded-3xl overflow-hidden relative border-slate-200/80 shadow-md flex flex-col">
          {/* Top Canvas Toolbar */}
          <div className="h-10 px-4 bg-slate-50/80 border-b border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <div className="flex items-center gap-2 font-medium">
              <span className={`w-2 h-2 rounded-full ${nodes.length > 0 ? "bg-emerald-500" : "bg-slate-300"}`}></span>
              <span className="text-slate-800 font-semibold">{selectedMap?.title || "Concept Hierarchy Canvas"}</span>
              {selectedMap && (
                <>
                  <span className="text-slate-300">•</span>
                  <span className="text-[11px] text-slate-500 capitalize">{selectedMap?.detail_level || detailLevel}</span>
                  <Badge variant={selectedMap?.is_grounded ? "success" : "purple"}>
                    {selectedMap?.is_grounded ? "Source-Grounded" : "Topic Outline"}
                  </Badge>
                </>
              )}
            </div>
            <span className="text-[11px] text-slate-400 font-mono">
              {nodes.length} nodes • {edges.length} connections
            </span>
          </div>

          <div className="flex-1 relative">
            {loading ? (
              <div className="flex flex-col items-center justify-center h-full text-slate-400 text-sm gap-2">
                <Sparkles className="w-6 h-6 animate-spin text-indigo-500" />
                <span className="font-medium text-slate-700">Loading concept hierarchies...</span>
              </div>
            ) : generating ? (
              <div className="flex flex-col items-center justify-center h-full text-slate-400 text-sm gap-2">
                <Sparkles className="w-6 h-6 animate-spin text-indigo-500" />
                <span className="font-medium text-slate-700">Extracting grounded cognitive schema...</span>
                <span className="text-xs text-slate-400">Grounding nodes in user source materials and relationships</span>
              </div>
            ) : nodes.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center p-8 text-slate-400">
                <div className="w-14 h-14 rounded-3xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 mb-3 shadow-xs">
                  <Network className="w-7 h-7" />
                </div>
                <h3 className="font-bold text-slate-900 text-base mb-1">No Mind Maps Generated Yet</h3>
                <p className="text-xs text-slate-500 max-w-sm mb-4">
                  {userTopics.length > 0
                    ? "Select one of your tracked concepts or enter a topic above to generate a grounded hierarchical mind map."
                    : "No mind maps yet. Upload learning materials or create study notes to generate your first grounded concept map."}
                </p>

                {userTopics.length > 0 && (
                  <div className="flex flex-wrap items-center justify-center gap-1.5 max-w-md">
                    <span className="text-[11px] text-slate-400 w-full mb-1">Available concepts in your library:</span>
                    {userTopics.slice(0, 4).map((t) => (
                      <button
                        key={t.id}
                        onClick={() => {
                          setNewTopicInput(t.canonical_name || t.name);
                          setSelectedTopicId(t.id);
                          generateNewMap(t.canonical_name || t.name, detailLevel, t.id);
                        }}
                        className="text-[11px] font-medium bg-slate-100 hover:bg-indigo-50 hover:text-indigo-600 text-slate-700 px-2.5 py-1 rounded-lg border border-slate-200 transition-colors cursor-pointer"
                      >
                        + {t.canonical_name || t.name}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                fitView
              >
                <Background variant={BackgroundVariant.Dots} gap={24} size={1.5} color="#e2e8f0" />
                <Controls className="bg-white/90 border border-slate-200 rounded-xl shadow-xs overflow-hidden" />
              </ReactFlow>
            )}
          </div>
        </div>

        {/* Saved Mind Maps Bento Sidebar */}
        <div className="w-full lg:w-72 clay-card bg-white rounded-3xl p-4 shrink-0 flex flex-col overflow-hidden border-slate-200/80 shadow-md">
          <div className="flex items-center justify-between mb-3 px-1">
            <h4 className="font-bold text-xs text-slate-900 uppercase tracking-wider">Saved Schemas</h4>
            <Badge variant="purple">{mindMaps.length}</Badge>
          </div>

          <div className="flex-1 overflow-y-auto space-y-2 pr-1">
            {mindMaps.length === 0 ? (
              <div className="text-center py-8 text-slate-400 text-xs">
                <p className="font-medium text-slate-600">No saved schemas</p>
                <p className="text-[11px] text-slate-400 mt-1">Grounded mind maps will be stored here</p>
              </div>
            ) : (
              mindMaps.map((m) => {
                const isSelected = selectedMap?.id === m.id;
                return (
                  <button
                    key={m.id}
                    onClick={() => displayMap(m)}
                    className={`w-full text-left p-3 rounded-2xl text-xs transition-all cursor-pointer ${
                      isSelected
                        ? "bg-gradient-to-r from-indigo-600 to-indigo-700 text-white shadow-md shadow-indigo-600/30 scale-[1.01]"
                        : "text-slate-700 bg-slate-50/70 hover:bg-slate-100/90 border border-slate-100"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <p className="truncate font-bold text-xs leading-tight">{m.title}</p>
                    </div>
                    <div className="flex items-center justify-between text-[10px] mt-1.5 opacity-80">
                      <span className="capitalize">{m.detail_level || "Semi-detailed"}</span>
                      <span>{new Date(m.created_at).toLocaleDateString()}</span>
                    </div>
                    {m.is_grounded && (
                      <div className="mt-1 text-[9px] font-semibold tracking-wider uppercase opacity-90">
                        ✓ Grounded
                      </div>
                    )}
                  </button>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

