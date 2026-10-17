"use client";

import React, { useEffect, useState } from "react";
import { Network, Sparkles, ArrowRight, BookOpen, ExternalLink, FileText, CheckCircle2 } from "lucide-react";
import { api } from "@/lib/api";
import { Card, Button, Badge } from "./ui";

export function ConnectivityView({
  onExploreTopic
}: {
  onExploreTopic?: (sourceId: string, targetId?: string, relId?: string) => void;
}) {
  const [connections, setConnections] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState<string>("all");

  useEffect(() => {
    loadConnectivity();
  }, []);

  const loadConnectivity = async () => {
    try {
      const data = await api.getConnectivity();
      setConnections(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const filteredConnections = connections.filter((c) => {
    if (filterType === "cross") return c.is_cross_document;
    if (filterType === "prereq") return c.relationship_type.toLowerCase().includes("prerequisite");
    return true;
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Cross-Document Connectivity</h2>
          <p className="text-xs sm:text-sm text-slate-500 mt-0.5">
            Discovers inter-disciplinary synergies, prerequisite chains, and contrasting conceptual frameworks across your study vault.
          </p>
        </div>
        
        <div className="flex items-center gap-2">
          {/* Filter Pills */}
          <div className="flex items-center bg-white p-1 rounded-2xl border border-slate-200/90 text-xs font-semibold shadow-xs">
            <button
              onClick={() => setFilterType("all")}
              className={`px-3 py-1 rounded-xl transition-all cursor-pointer ${
                filterType === "all" ? "bg-indigo-600 text-white font-bold" : "text-slate-600 hover:text-slate-900"
              }`}
            >
              All ({connections.length})
            </button>
            <button
              onClick={() => setFilterType("cross")}
              className={`px-3 py-1 rounded-xl transition-all cursor-pointer ${
                filterType === "cross" ? "bg-purple-600 text-white font-bold" : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Cross-Document ({connections.filter((c) => c.is_cross_document).length})
            </button>
            <button
              onClick={() => setFilterType("prereq")}
              className={`px-3 py-1 rounded-xl transition-all cursor-pointer ${
                filterType === "prereq" ? "bg-amber-600 text-white font-bold" : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Prerequisites ({connections.filter((c) => c.relationship_type.toLowerCase().includes("prerequisite")).length})
            </button>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center p-12 text-slate-400">
          <Sparkles className="w-6 h-6 animate-spin text-indigo-500 mb-2" />
          <p className="text-sm font-medium text-slate-600">Analyzing vault connectivity...</p>
        </div>
      ) : connections.length === 0 ? (
        <Card className="p-12 text-center flex flex-col items-center justify-center">
          <div className="w-14 h-14 rounded-3xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 mb-3 shadow-xs">
            <Network className="w-7 h-7" />
          </div>
          <h3 className="font-bold text-slate-900 text-base mb-1">No Semantic Bridges Discovered</h3>
          <p className="text-xs text-slate-500 max-w-md mb-4">
            Cross-document bridges and prerequisite chains are synthesized automatically once you upload multi-topic study materials or notes to your vault.
          </p>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {filteredConnections.map((c) => {
            const confidencePct = Math.round((c.confidence || 0.8) * 100);
            const isPrereq = c.relationship_type.toLowerCase().includes("prerequisite");
            const isCross = c.is_cross_document;

            return (
              <Card key={c.id} className="p-6 flex flex-col justify-between space-y-4 hover:border-indigo-300 transition-all bg-white">
                <div>
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <Badge variant={isPrereq ? "warning" : isCross ? "purple" : "default"}>
                        {c.relationship_type}
                      </Badge>
                      {isCross && (
                        <Badge variant="purple" className="text-[10px]">
                          Cross-Document Bridge
                        </Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-1.5 text-xs font-bold text-slate-500">
                      <span className="text-[11px] text-slate-400">Confidence:</span>
                      <span className="text-indigo-600 font-extrabold">{confidencePct}%</span>
                    </div>
                  </div>

                  {/* Visual Connection Card */}
                  <div className="flex items-center justify-between gap-3 p-4 bg-gradient-to-r from-slate-50 via-indigo-50/30 to-slate-50 rounded-2xl border border-slate-200/80 shadow-2xs">
                    <div className="flex-1 truncate">
                      <span className="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">Source Concept</span>
                      <span className="font-extrabold text-xs sm:text-sm text-slate-900 block truncate">{c.source_topic}</span>
                      {c.source_document_title && (
                        <span className="text-[10px] text-slate-500 block truncate mt-0.5">
                          📂 {c.source_document_title}
                        </span>
                      )}
                    </div>
                    <div className="w-8 h-8 rounded-full bg-white border border-indigo-200 flex items-center justify-center shrink-0 shadow-xs">
                      <ArrowRight className="w-4 h-4 text-indigo-600" />
                    </div>
                    <div className="flex-1 text-right truncate">
                      <span className="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">Linked Target</span>
                      <span className="font-extrabold text-xs sm:text-sm text-slate-900 block truncate">{c.target_topic}</span>
                      {c.target_document_title && (
                        <span className="text-[10px] text-slate-500 block truncate mt-0.5">
                          📂 {c.target_document_title}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Plain-English Connection Reason */}
                  {c.simple_reason && (
                    <div className="mt-3 p-3 bg-indigo-50/50 rounded-xl border border-indigo-100/70">
                      <span className="text-[10px] font-bold text-indigo-800 uppercase tracking-wider block mb-0.5">Why They Connect:</span>
                      <p className="text-xs text-slate-700 leading-relaxed">
                        {c.simple_reason}
                      </p>
                    </div>
                  )}

                  {/* Grounding Evidence */}
                  <div className="mt-2.5 p-3 bg-slate-50/60 rounded-xl border border-slate-200/60">
                    <p className="text-xs text-slate-600 leading-relaxed">
                      <strong className="text-slate-800">Grounding Evidence:</strong> {c.evidence_text}
                    </p>
                  </div>
                </div>

                <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
                  <span className="text-[11px] text-slate-400 font-medium">Automatic vault synthesis</span>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => onExploreTopic && onExploreTopic(c.source_topic_id, c.target_topic_id, c.id)}
                    className="rounded-xl hover:bg-indigo-50 hover:text-indigo-700 hover:border-indigo-300"
                  >
                    Explore in Graph <ExternalLink className="w-3.5 h-3.5 ml-1.5" />
                  </Button>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
