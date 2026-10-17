"use client";

import React, { useEffect, useState } from "react";
import {
  Brain,
  Sparkles,
  BookOpen,
  Calendar,
  AlertTriangle,
  ArrowUpRight,
  TrendingUp,
  Clock,
  CheckCircle2,
  FolderUp,
  FileText,
  Network,
  CreditCard,
  Flame,
  Zap,
  Target,
  Share2,
  GraduationCap,
  ArrowRight,
  ShieldCheck,
  RefreshCw,
  BellRing
} from "lucide-react";
import { api } from "@/lib/api";
import { Card, Button, Badge } from "./ui";
import { NavTab } from "./AppShell";

export function DashboardView({ onNavigate }: { onNavigate: (tab: NavTab) => void }) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeRadarFilter, setActiveRadarFilter] = useState<"all" | "urgent" | "stable">("all");

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getDashboardOverview();
      setData(res);
    } catch (e: any) {
      console.error(e);
      setError(e?.message || "Failed to load dashboard metrics.");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-96 text-slate-400 text-sm">
        <Sparkles className="w-6 h-6 animate-spin text-indigo-500 mb-2" />
        <span>Synthesizing cognitive dashboard & memory graph...</span>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex flex-col items-center justify-center h-96 text-center max-w-md mx-auto p-6 bg-white rounded-3xl border border-rose-100 shadow-sm">
        <div className="w-12 h-12 rounded-2xl bg-rose-50 border border-rose-200 flex items-center justify-center text-rose-500 mb-3">
          <AlertTriangle className="w-6 h-6" />
        </div>
        <h3 className="font-bold text-slate-900 text-base mb-1">Failed to Load Dashboard</h3>
        <p className="text-xs text-slate-500 mb-4">{error || "Unable to retrieve personal cognitive data."}</p>
        <button
          onClick={loadData}
          className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-xl text-white bg-indigo-600 hover:bg-indigo-500 transition-all cursor-pointer shadow-sm"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Retry</span>
        </button>
      </div>
    );
  }

  // Filter topics for the memory radar
  const allReviewTopics = data.review_due_topics || [];
  const urgentTopics = allReviewTopics.filter((t: any) => t.retention < 0.75 || t.overdue);
  const stableTopics = allReviewTopics.filter((t: any) => t.retention >= 0.75 && !t.overdue);
  const radarTopics =
    activeRadarFilter === "urgent"
      ? urgentTopics
      : activeRadarFilter === "stable"
      ? stableTopics
      : allReviewTopics;

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-8">
      {/* 1. Hero Bento Header */}
      <div className="clay-card-dark bg-slate-950 bg-gradient-to-r from-slate-950 via-indigo-950 to-slate-900 text-white p-6 sm:p-8 rounded-3xl relative overflow-hidden border border-indigo-900/60 shadow-xl">
        <div className="absolute right-0 top-0 bottom-0 w-1/3 bg-[radial-gradient(circle_at_center,#6366f1_0,transparent_70%)] opacity-30 pointer-events-none"></div>

        <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-2.5">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/25 border border-indigo-400/40 text-indigo-200 text-xs font-semibold">
              <Sparkles className="w-3.5 h-3.5 text-indigo-300" />
              <span>Proactive AI Memory Engine Active</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white drop-shadow-xs">
              Welcome back, {data.welcome_name} 👋
            </h1>
            <p className="text-sm text-indigo-100 max-w-2xl leading-relaxed">
              {data.topics_discovered > 0 ? (
                <>
                  Today&apos;s cognitive focus is <strong className="text-white underline decoration-indigo-400 underline-offset-4">{data.daily_study_focus}</strong>.
                  {" "}Your average retention across {data.topics_discovered} topics is calculated at{" "}
                  <strong className="text-emerald-400 font-bold">{data.retention_average}%</strong>.
                </>
              ) : (
                <>
                  {data.daily_study_focus === "Your learning journey starts here" ? (
                    <>
                      <strong className="text-white underline decoration-indigo-400 underline-offset-4">Your learning journey starts here</strong>.
                      {" "}{data.cognitive_focus_prompt || "Upload your first resource to build your personal knowledge graph."}
                    </>
                  ) : (
                    <>
                      Today&apos;s learning focus: <strong className="text-white underline decoration-indigo-400 underline-offset-4">{data.daily_study_focus}</strong>.
                      {" "}{data.cognitive_focus_prompt || "Upload your notes to start building your personal knowledge graph."}
                    </>
                  )}
                </>
              )}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 shrink-0">
            <button
              type="button"
              onClick={() => onNavigate("uploads")}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-xl text-white bg-slate-800/90 hover:bg-slate-700/90 border border-slate-600/80 shadow-md transition-all cursor-pointer active:scale-95"
            >
              <FolderUp className="w-4 h-4 text-indigo-300" />
              <span>Upload Material</span>
            </button>
            <button
              type="button"
              onClick={() => onNavigate("recall")}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-xl text-white bg-indigo-600 hover:bg-indigo-500 border border-indigo-400/50 shadow-lg shadow-indigo-600/30 transition-all cursor-pointer active:scale-95"
            >
              <Zap className="w-4 h-4 text-amber-300" />
              <span>Start Active Recall</span>
            </button>
          </div>
        </div>
      </div>

      {/* 2. Bento Quick Metric Pills */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Metric 1 */}
        <div className="clay-card p-5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-500 text-xs font-semibold">
            <span>Topics Discovered</span>
            <div className="w-7 h-7 rounded-lg bg-indigo-50 flex items-center justify-center text-indigo-600">
              <Brain className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-3xl font-black text-slate-900">{data.topics_discovered}</div>
            <p className="text-xs text-slate-500 mt-1">
              <span className="font-semibold text-emerald-600">{data.topics_learned} learned</span> •{" "}
              <span className="font-semibold text-amber-600">{data.topics_left_to_learn} pending</span>
            </p>
          </div>
        </div>

        {/* Metric 2 */}
        <div className="clay-card p-5 flex flex-col justify-between border-amber-200/70 bg-gradient-to-br from-white to-amber-50/30">
          <div className="flex items-center justify-between text-amber-800 text-xs font-semibold">
            <span>Learn Again (Due)</span>
            <div className="w-7 h-7 rounded-lg bg-amber-100/80 flex items-center justify-center text-amber-700">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-3xl font-black text-amber-900">{data.review_due_count}</div>
            <p className="text-xs text-amber-700 mt-1">
              <span className="font-semibold">{data.overdue_count} overdue</span> reviews
            </p>
          </div>
        </div>

        {/* Metric 3 */}
        <div className="clay-card p-5 flex flex-col justify-between border-emerald-200/70 bg-gradient-to-br from-white to-emerald-50/20">
          <div className="flex items-center justify-between text-emerald-800 text-xs font-semibold">
            <span>Memory Retention</span>
            <div className="w-7 h-7 rounded-lg bg-emerald-100/80 flex items-center justify-center text-emerald-700">
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-3xl font-black text-emerald-700">
              {data.topics_discovered > 0 ? `${data.retention_average}%` : "—"}
            </div>
            <p className="text-xs text-emerald-600 mt-1">
              {data.topics_discovered > 0 ? "Ebbinghaus stability score" : "No concept activity yet"}
            </p>
          </div>
        </div>

        {/* Metric 4 */}
        <div className="clay-card p-5 flex flex-col justify-between border-violet-200/70 bg-gradient-to-br from-white to-violet-50/20">
          <div className="flex items-center justify-between text-violet-800 text-xs font-semibold">
            <span>Target Exams</span>
            <div className="w-7 h-7 rounded-lg bg-violet-100/80 flex items-center justify-center text-violet-700">
              <Calendar className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-3xl font-black text-violet-900">{data.upcoming_exams?.length || 0}</div>
            <p className="text-xs text-violet-600 mt-1">Countdown & prep active</p>
          </div>
        </div>
      </div>

      {/* 3. Bento Grid: Core Interactive Intelligence Modules */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Bento Cell A: Cognitive Memory Radar & Learn Again (8 cols) */}
        <div className="lg:col-span-8 space-y-6">
          {/* Card: Memory Radar & Spaced Repetition Queue */}
          <Card className="p-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-100 gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-xl bg-indigo-50 border border-indigo-200 flex items-center justify-center text-indigo-600">
                    <Target className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-900 text-base">Cognitive Memory Radar</h3>
                    <p className="text-xs text-slate-500">
                      Predicting memory decay based on spaced repetition stability
                    </p>
                  </div>
                </div>
              </div>

              {/* Filter Pills */}
              <div className="flex items-center gap-1.5 bg-slate-100/80 p-1 rounded-xl">
                <button
                  onClick={() => setActiveRadarFilter("all")}
                  className={`px-2.5 py-1 text-xs font-semibold rounded-lg transition-all cursor-pointer ${
                    activeRadarFilter === "all"
                      ? "bg-white text-slate-900 shadow-xs"
                      : "text-slate-600 hover:text-slate-900"
                  }`}
                >
                  All ({allReviewTopics.length})
                </button>
                <button
                  onClick={() => setActiveRadarFilter("urgent")}
                  className={`px-2.5 py-1 text-xs font-semibold rounded-lg transition-all cursor-pointer ${
                    activeRadarFilter === "urgent"
                      ? "bg-amber-500 text-white shadow-xs"
                      : "text-slate-600 hover:text-slate-900"
                  }`}
                >
                  Urgent ({urgentTopics.length})
                </button>
                <button
                  onClick={() => setActiveRadarFilter("stable")}
                  className={`px-2.5 py-1 text-xs font-semibold rounded-lg transition-all cursor-pointer ${
                    activeRadarFilter === "stable"
                      ? "bg-emerald-600 text-white shadow-xs"
                      : "text-slate-600 hover:text-slate-900"
                  }`}
                >
                  Stable ({stableTopics.length})
                </button>
              </div>
            </div>

            {/* Radar Topic List */}
            <div className="mt-4 space-y-3">
              {radarTopics.length === 0 ? (
                <div className="text-center py-8 text-slate-400 text-xs">
                  <CheckCircle2 className="w-8 h-8 mx-auto mb-2 text-emerald-500/60" />
                  No topics matching this retention criteria. Memory is completely stabilized!
                </div>
              ) : (
                radarTopics.map((t: any) => {
                  const retentionPercent = Math.round((t.retention || 0.5) * 100);
                  const isUrgent = retentionPercent < 75;
                  return (
                    <div
                      key={t.id}
                      className={`p-3.5 rounded-2xl border transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
                        isUrgent
                          ? "bg-gradient-to-r from-amber-50/40 to-rose-50/20 border-amber-200/90 hover:border-amber-300"
                          : "bg-slate-50/60 border-slate-200/80 hover:border-slate-300"
                      }`}
                    >
                      <div className="space-y-1.5 flex-1">
                        <div className="flex items-center gap-2">
                          <h4 className="font-bold text-sm text-slate-900">{t.name}</h4>
                          <Badge
                            variant={isUrgent ? "warning" : "success"}
                            className="text-[10px]"
                          >
                            {isUrgent ? "Review Due" : "Stable"}
                          </Badge>
                        </div>

                        {/* Progress Bar for Retention */}
                        <div className="flex items-center gap-3">
                          <div className="w-32 bg-slate-200 h-2 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full transition-all ${
                                retentionPercent < 70
                                  ? "bg-amber-500"
                                  : retentionPercent < 85
                                  ? "bg-indigo-500"
                                  : "bg-emerald-500"
                              }`}
                              style={{ width: `${retentionPercent}%` }}
                            ></div>
                          </div>
                          <span className="text-xs font-bold text-slate-700">
                            {retentionPercent}% Retention
                          </span>
                          <span className="text-[11px] text-slate-400 hidden sm:inline">
                            • Interval: {t.stability}d
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        <Button
                          size="sm"
                          variant={isUrgent ? "primary" : "outline"}
                          onClick={() => onNavigate("recall")}
                        >
                          <Zap className="w-3.5 h-3.5" />
                          <span>Recall Drill</span>
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => onNavigate("learn")}
                          title="Open in AI Tutor"
                        >
                          <GraduationCap className="w-3.5 h-3.5" />
                        </Button>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* Bottom Actions */}
            <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
              <span className="text-slate-500">
                Spaced repetition algorithm prevents forgetting through active retrieval drills.
              </span>
              <Button size="sm" variant="ghost" onClick={() => onNavigate("recall")}>
                Full Recall Queue <ArrowRight className="w-3.5 h-3.5 ml-1" />
              </Button>
            </div>
          </Card>

          {/* Card: Things Left to Learn & Automatic Study Prep */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Things Left to Learn */}
            <Card className="p-5 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                    <BookOpen className="w-4 h-4 text-indigo-600" />
                    Things Left to Learn
                  </h3>
                  <Badge variant="purple" className="text-[10px]">
                    {data.topics_left_to_learn} Pending
                  </Badge>
                </div>
                <p className="text-xs text-slate-500 mb-3">
                  Extracted concepts from uploaded materials awaiting first learning session:
                </p>

                <div className="space-y-2">
                  {data.left_to_learn_topics?.length === 0 ? (
                    <p className="text-xs text-slate-400 py-2">All discovered topics have been studied!</p>
                  ) : (
                    data.left_to_learn_topics?.slice(0, 4).map((t: any) => (
                      <div
                        key={t.id}
                        className="p-2.5 rounded-xl bg-slate-50 border border-slate-200/80 hover:border-indigo-300 flex items-center justify-between transition-colors"
                      >
                        <span className="text-xs font-medium text-slate-800 truncate mr-2">
                          {t.name}
                        </span>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => onNavigate("learn")}
                          className="text-[11px] py-1 px-2 shrink-0"
                        >
                          Study Now
                        </Button>
                      </div>
                    ))
                  )}
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-100">
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => onNavigate("learn")}
                  className="w-full justify-center text-xs"
                >
                  Explore in AI Tutor <ArrowRight className="w-3.5 h-3.5 ml-1" />
                </Button>
              </div>
            </Card>

            {/* Automatic Study Prep */}
            <Card className="p-5 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-violet-600" />
                    Automatic Study Prep
                  </h3>
                  <Badge variant={(data.flashcard_count > 0 || data.mind_map_count > 0 || data.note_count > 0) ? "success" : "default"} className="text-[10px]">
                    {(data.flashcard_count > 0 || data.mind_map_count > 0 || data.note_count > 0) ? "AI Prepared" : "Awaiting Materials"}
                  </Badge>
                </div>
                <p className="text-xs text-slate-500 mb-3">
                  AI-synthesized resources ready for your daily study block:
                </p>

                <div className="space-y-2.5">
                  <div
                    onClick={() => onNavigate("flashcards")}
                    className="p-2.5 rounded-xl bg-violet-50/50 border border-violet-100 hover:border-violet-300 flex items-center justify-between cursor-pointer transition-all"
                  >
                    <div className="flex items-center gap-2.5">
                      <CreditCard className="w-4 h-4 text-violet-600" />
                      <div>
                        <p className="text-xs font-semibold text-slate-900">Active Recall Flashcards</p>
                        <p className="text-[10px] text-slate-500">
                          {data.flashcard_count > 0 ? `${data.flashcard_count} smart cards available` : "No cards generated yet"}
                        </p>
                      </div>
                    </div>
                    <ArrowRight className="w-3.5 h-3.5 text-violet-600" />
                  </div>

                  <div
                    onClick={() => onNavigate("mindmaps")}
                    className="p-2.5 rounded-xl bg-indigo-50/50 border border-indigo-100 hover:border-indigo-300 flex items-center justify-between cursor-pointer transition-all"
                  >
                    <div className="flex items-center gap-2.5">
                      <Network className="w-4 h-4 text-indigo-600" />
                      <div>
                        <p className="text-xs font-semibold text-slate-900">Concept Mind Maps</p>
                        <p className="text-[10px] text-slate-500">
                          {data.mind_map_count > 0 ? `${data.mind_map_count} schemas synthesized` : "Generate from topics or notes"}
                        </p>
                      </div>
                    </div>
                    <ArrowRight className="w-3.5 h-3.5 text-indigo-600" />
                  </div>

                  <div
                    onClick={() => onNavigate("notes")}
                    className="p-2.5 rounded-xl bg-emerald-50/50 border border-emerald-100 hover:border-emerald-300 flex items-center justify-between cursor-pointer transition-all"
                  >
                    <div className="flex items-center gap-2.5">
                      <FileText className="w-4 h-4 text-emerald-600" />
                      <div>
                        <p className="text-xs font-semibold text-slate-900">Structured Notes</p>
                        <p className="text-[10px] text-slate-500">
                          {data.note_count > 0 ? `${data.note_count} notes stored` : "Save takeaways from AI Tutor"}
                        </p>
                      </div>
                    </div>
                    <ArrowRight className="w-3.5 h-3.5 text-emerald-600" />
                  </div>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-100">
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => onNavigate("flashcards")}
                  className="w-full justify-center text-xs"
                >
                  Open Study Tools <ArrowRight className="w-3.5 h-3.5 ml-1" />
                </Button>
              </div>
            </Card>
          </div>
        </div>

        {/* Bento Cell B: AI Study Assistant & Knowledge Graph Preview (4 cols) */}
        <div className="lg:col-span-4 space-y-6">
          {/* Card: Proactive AI Study Assistant */}
          <div className="clay-card-dark p-6 bg-slate-950 bg-gradient-to-br from-slate-950 via-indigo-950 to-slate-900 text-white rounded-3xl border border-indigo-900/60 shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-lg bg-indigo-500/30 border border-indigo-400/40 flex items-center justify-center text-indigo-300">
                  <Sparkles className="w-4 h-4" />
                </div>
                <h3 className="font-bold text-sm text-white">AI Study Assistant</h3>
              </div>
              <Badge variant="purple" className="bg-indigo-500/30 text-indigo-200 border-indigo-400/40 text-[10px]">
                Proactive
              </Badge>
            </div>

            <div className="space-y-3">
              <div className="p-3.5 rounded-xl bg-slate-900/80 border border-indigo-900/60 text-xs text-indigo-100 leading-relaxed shadow-inner">
                <p className="font-bold text-white mb-1">Recommended Next Action:</p>
                {data.review_due_topics?.length > 0 ? (
                  <span>
                    Revise <strong className="text-amber-300 font-bold">{data.review_due_topics[0].name}</strong>. Retention is decaying ({Math.round(data.review_due_topics[0].retention * 100)}%) and due for spaced repetition.
                  </span>
                ) : data.topics_left_to_learn > 0 ? (
                  <span>
                    Begin learning newly extracted concepts in the <strong className="text-indigo-300 font-bold">AI Tutor</strong> to establish memory stability baselines.
                  </span>
                ) : data.topics_discovered > 0 ? (
                  <span>
                    All current concepts are stabilized! Launch an active recall drill to test long-term retention.
                  </span>
                ) : (
                  <span>
                    Upload your first course syllabus, lecture PDF, or notes in the <strong className="text-indigo-300 font-bold">Uploads</strong> tab to begin personalized AI tutoring.
                  </span>
                )}
              </div>

              {/* Target Exam Readiness - only shown when exams and topics exist */}
              <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 text-xs text-indigo-200">
                <div className="flex items-center justify-between text-[11px] mb-1.5 font-medium">
                  <span className="text-slate-300">Target Exam Readiness</span>
                  <span className={`font-extrabold ${data.topics_discovered > 0 ? "text-emerald-400" : "text-slate-400"}`}>
                    {data.topics_discovered > 0
                      ? `${Math.round(Math.min(100, (data.topics_learned / Math.max(1, data.topics_discovered)) * 100))}% Prepared`
                      : "Awaiting Study Material"}
                  </span>
                </div>
                <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden border border-slate-700/50">
                  <div
                    className="bg-emerald-400 h-full rounded-full transition-all"
                    style={{
                      width: data.topics_discovered > 0
                        ? `${Math.round(Math.min(100, (data.topics_learned / Math.max(1, data.topics_discovered)) * 100))}%`
                        : "0%"
                    }}
                  ></div>
                </div>
              </div>

              <button
                type="button"
                onClick={() => onNavigate("learn")}
                className="w-full py-2.5 px-4 rounded-xl text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-500 border border-indigo-500/50 shadow-md shadow-indigo-600/30 transition-all cursor-pointer active:scale-95 flex items-center justify-center gap-1.5"
              >
                <GraduationCap className="w-4 h-4 text-indigo-200" />
                <span>Launch AI Tutor Session</span>
              </button>
            </div>
          </div>

          {/* Card: Knowledge Graph Mini Preview */}
          <Card className="p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                <Share2 className="w-4 h-4 text-indigo-600" />
                Knowledge Graph
              </h3>
              <Button size="sm" variant="ghost" onClick={() => onNavigate("graph")}>
                Full Graph <ArrowUpRight className="w-3.5 h-3.5" />
              </Button>
            </div>

            {/* Mini Visual Topic Web */}
            <div
              onClick={() => onNavigate("graph")}
              className="h-44 rounded-2xl bg-slate-950 bg-gradient-to-tr from-slate-950 via-indigo-950 to-slate-900 p-3.5 text-white flex flex-col justify-between cursor-pointer group hover:border-indigo-400 transition-all border border-slate-800 relative overflow-hidden"
            >
              <div className="flex items-center justify-between text-[11px] text-slate-300">
                <span className="font-mono text-slate-300 font-semibold">Central Hubs</span>
                <span className="bg-indigo-500/25 px-2 py-0.5 rounded-full text-indigo-200 border border-indigo-400/40 text-[10px] font-semibold">
                  {data.topics_discovered > 0 ? `${data.topics_discovered} Nodes` : "Empty State"}
                </span>
              </div>

              {data.topics_discovered > 0 ? (
                <div className="flex items-center justify-center gap-2 py-2">
                  <div className="px-3 py-1.5 rounded-xl bg-indigo-600 text-white text-xs font-bold shadow-md group-hover:scale-105 transition-transform border border-indigo-400/40 truncate max-w-[140px]">
                    {data.review_due_topics?.[0]?.name || data.left_to_learn_topics?.[0]?.name || "Core Concept"}
                  </div>
                  {data.topics_discovered > 1 && (
                    <>
                      <div className="w-4 h-[2px] bg-indigo-400"></div>
                      <div className="px-3 py-1.5 rounded-xl bg-violet-600 text-white text-xs font-bold shadow-md group-hover:scale-105 transition-transform border border-violet-400/40 truncate max-w-[140px]">
                        {data.review_due_topics?.[1]?.name || data.left_to_learn_topics?.[1]?.name || "Related Node"}
                      </div>
                    </>
                  )}
                </div>
              ) : (
                <div className="text-center py-2 text-slate-400 text-xs">
                  <p className="font-semibold text-slate-300">Knowledge Graph is Empty</p>
                  <p className="text-[11px] text-slate-400 mt-1">Upload study materials to discover topic clusters</p>
                </div>
              )}

              <p className="text-[11px] text-slate-300 text-center group-hover:text-white transition-colors">
                {data.topics_discovered > 0
                  ? "Click to explore cross-subject semantic connections →"
                  : "Click to open graph explorer →"}
              </p>
            </div>
          </Card>

          {/* Card: Upcoming Examinations */}
          <Card className="p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                <Calendar className="w-4 h-4 text-violet-600" />
                Upcoming Exams
              </h3>
              <Button size="sm" variant="ghost" onClick={() => onNavigate("exam")}>
                Date Sheet <ArrowRight className="w-3.5 h-3.5" />
              </Button>
            </div>

            <div className="space-y-2.5">
              {data.upcoming_exams?.length === 0 ? (
                <p className="text-xs text-slate-400 py-2">No upcoming exams scheduled.</p>
              ) : (
                data.upcoming_exams?.map((ex: any) => (
                  <div
                    key={ex.id}
                    className="p-3 rounded-xl bg-indigo-50/50 border border-indigo-100 flex items-center justify-between"
                  >
                    <div>
                      <h4 className="text-xs font-bold text-indigo-950">{ex.subject}</h4>
                      <p className="text-[11px] text-indigo-600 mt-0.5">
                        {ex.date} • {ex.time}
                      </p>
                    </div>
                    <Badge variant="purple" className="text-[10px]">
                      Scheduled
                    </Badge>
                  </div>
                ))
              )}
            </div>
          </Card>

          {/* Card: Recent Learning Activity */}
          <Card className="p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                <Clock className="w-4 h-4 text-indigo-600" />
                Recent Activity
              </h3>
            </div>

            <div className="space-y-2.5">
              {!data.recent_activity || data.recent_activity.length === 0 ? (
                <div className="text-center py-4 text-slate-400 text-xs">
                  <p className="font-medium text-slate-600">No recent learning activity</p>
                  <p className="text-[11px] text-slate-400 mt-0.5">Activities will record here as you review and drill concepts</p>
                </div>
              ) : (
                data.recent_activity.map((act: any, idx: number) => (
                  <div
                    key={idx}
                    className="p-3 rounded-xl bg-slate-50/70 border border-slate-200/80 flex items-center justify-between text-xs"
                  >
                    <div>
                      <p className="font-semibold text-slate-900">{act.action}</p>
                      <p className="text-[11px] text-slate-500 truncate max-w-[180px]">{act.topic}</p>
                    </div>
                    <div className="text-right shrink-0">
                      <span className="text-[11px] text-slate-400">{act.time}</span>
                      {act.score && (
                        <p className="text-[10px] font-bold text-emerald-600">{act.score}</p>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
