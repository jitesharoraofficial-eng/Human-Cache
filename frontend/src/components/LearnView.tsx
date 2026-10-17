"use client";

import React, { useEffect, useState } from "react";
import {
  GraduationCap,
  Sparkles,
  BookOpen,
  Save,
  BookmarkCheck,
  ArrowRight,
  HelpCircle,
  Lightbulb,
  AlertTriangle,
  Send,
  MessageSquare,
  CheckCircle2,
  Layers,
  Zap,
  Target
} from "lucide-react";
import { api } from "@/lib/api";
import { Card, Button, Badge } from "./ui";
import { MarkdownRenderer } from "./MarkdownRenderer";

export function LearnView({ initialTopicId }: { initialTopicId?: string } = {}) {
  const [topics, setTopics] = useState<any[]>([]);
  const [selectedTopicId, setSelectedTopicId] = useState<string>("");
  const [depth, setDepth] = useState<string>("balanced");
  const [mode, setMode] = useState<string>("explain");
  const [personaOverride, setPersonaOverride] = useState<string>("auto");
  const [customQuestion, setCustomQuestion] = useState("");
  const [chatInput, setChatInput] = useState("");
  const [explanationData, setExplanationData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [savedNote, setSavedNote] = useState(false);

  useEffect(() => {
    loadTopics();
  }, [initialTopicId]);

  const loadTopics = async () => {
    try {
      const res = await api.getTopics();
      setTopics(res);
      if (res.length > 0) {
        const targetId = (initialTopicId && res.some((t: any) => t.id === initialTopicId)) ? initialTopicId : res[0].id;
        setSelectedTopicId(targetId);
        fetchExplanation(targetId, "balanced", "explain", undefined, "auto");
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchExplanation = async (
    topicId: string,
    depthVal: string,
    modeVal: string,
    query?: string,
    override?: string
  ) => {
    setLoading(true);
    setSavedNote(false);
    try {
      const res = await api.explainTopic({
        topic_ids: topicId ? [topicId] : [],
        depth: depthVal,
        mode: modeVal,
        query: query || undefined,
        persona_override: override && override !== "auto" ? override : undefined,
      });
      setExplanationData(res);
    } catch (e: any) {
      alert("Error: " + e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCustomSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim()) return;
    setCustomQuestion(chatInput);
    fetchExplanation(selectedTopicId, depth, mode, chatInput, personaOverride);
    setChatInput("");
  };

  const handleSaveAsNote = async () => {
    if (!explanationData) return;
    try {
      await api.saveLearnAsNote({
        title: `Synthesis: ${explanationData.topic_name}`,
        content: `${explanationData.explanation}\n\n**Takeaways:**\n${explanationData.key_takeaways?.join("\n")}`,
        topic_id: selectedTopicId || undefined,
      });
      setSavedNote(true);
      setTimeout(() => setSavedNote(false), 3000);
    } catch (e: any) {
      alert(e.message);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-8 font-sans">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="purple">Personalized AI Tutor</Badge>
            <span className="text-xs text-slate-400">• Dynamic Pedagogy & Exam Traps</span>
          </div>
          <h2 className="text-2xl font-black text-slate-900 tracking-tight">
            Learn & Concept Understanding
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 mt-0.5">
            Grounded conceptual tutoring driven by your documents. Every learning session automatically updates your Spaced Repetition memory stability.
          </p>
        </div>

        {explanationData?.persona_mode_indicator && (
          <div className="clay-pill bg-white px-3.5 py-1.5 border border-indigo-200 text-xs font-bold text-indigo-700 shadow-xs flex items-center gap-2 self-start sm:self-auto">
            <Target className="w-3.5 h-3.5 text-indigo-600" />
            <span>Mode: {explanationData.persona_mode_indicator}</span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Topic Selector & Pedagogical Controls (4 cols) */}
        <div className="lg:col-span-4 space-y-4">
          <Card className="p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-indigo-600" />
                <span>Concept Library</span>
              </h3>
              <Badge variant="clay" className="text-[10px]">{topics.length} Topics</Badge>
            </div>

            <div className="space-y-1.5 max-h-[360px] overflow-y-auto pr-1">
              {topics.map((t) => {
                const isSelected = selectedTopicId === t.id;
                return (
                  <button
                    key={t.id}
                    onClick={() => {
                      setSelectedTopicId(t.id);
                      fetchExplanation(t.id, depth, mode, undefined, personaOverride);
                    }}
                    className={`w-full text-left p-3 rounded-2xl border text-xs transition-all cursor-pointer flex items-center justify-between ${
                      isSelected
                        ? "bg-gradient-to-r from-indigo-50 to-violet-50/70 border-indigo-500 shadow-xs ring-1 ring-indigo-500/30"
                        : "bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50/70 text-slate-700"
                    }`}
                  >
                    <span className={`font-bold truncate pr-2 ${isSelected ? "text-indigo-950" : "text-slate-800"}`}>
                      {t.canonical_name}
                    </span>
                    <Badge
                      variant={t.status === "learned" ? "success" : "default"}
                      className="text-[10px] uppercase font-bold shrink-0"
                    >
                      {t.status || "unlearned"}
                    </Badge>
                  </button>
                );
              })}
            </div>
          </Card>

          {/* Depth & Mode Controls */}
          <Card className="p-5 space-y-3.5">
            <h3 className="font-bold text-slate-900 text-xs uppercase tracking-wider">
              Tutor Controls
            </h3>

            <div>
              <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                Target Persona Mode
              </label>
              <select
                value={personaOverride}
                onChange={(e) => {
                  setPersonaOverride(e.target.value);
                  fetchExplanation(selectedTopicId, depth, mode, undefined, e.target.value);
                }}
                className="w-full text-xs border border-indigo-200 rounded-xl p-2.5 bg-indigo-50/40 font-bold text-indigo-950"
              >
                <option value="auto">Auto (From Saved Profile)</option>
                <option value="jee_aspirant">🎯 JEE Advanced / Competitive</option>
                <option value="cbse_student">📚 CBSE School Curriculum</option>
                <option value="beginner">🌱 Beginner / Intuitive</option>
                <option value="professional">💼 Applied Professional</option>
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                Explanation Depth
              </label>
              <select
                value={depth}
                onChange={(e) => {
                  setDepth(e.target.value);
                  fetchExplanation(selectedTopicId, e.target.value, mode, undefined, personaOverride);
                }}
                className="w-full text-xs border border-slate-300 rounded-xl p-2.5 bg-white font-medium"
              >
                <option value="simple">Simple (Intuitive, jargon-free)</option>
                <option value="balanced">Balanced (Core principles & derivations)</option>
                <option value="detailed">Detailed (In-depth analysis & edge cases)</option>
                <option value="academic">Academic (Formal theoretical formulation)</option>
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                Pedagogical Mode
              </label>
              <select
                value={mode}
                onChange={(e) => {
                  setMode(e.target.value);
                  fetchExplanation(selectedTopicId, depth, e.target.value, undefined, personaOverride);
                }}
                className="w-full text-xs border border-slate-300 rounded-xl p-2.5 bg-white font-medium"
              >
                <option value="explain">Standard Explanation</option>
                <option value="analogy">Analogy First (Intuitive)</option>
                <option value="step_by_step">Step-by-Step Breakdown</option>
                <option value="examples">Real-world Problem Examples</option>
              </select>
            </div>
          </Card>
        </div>

        {/* Right Column: Explanation Panel & Interactive Tutor Chat (8 cols) */}
        <div className="lg:col-span-8 space-y-4">
          <Card className="p-6 sm:p-8">
            {loading ? (
              <div className="flex flex-col items-center justify-center py-20 text-slate-400 text-sm gap-3">
                <Sparkles className="w-8 h-8 animate-spin text-indigo-600" />
                <span className="font-semibold text-slate-600">
                  Synthesizing personalized academic explanation from source documents...
                </span>
              </div>
            ) : explanationData ? (
              <div className="space-y-6">
                {/* Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-100 gap-3">
                  <div>
                    <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                      <Badge variant="purple">AI Grounded Synthesis</Badge>
                      {explanationData.coverage_status && (
                        <Badge
                          variant={explanationData.coverage_status === "complete" ? "success" : "default"}
                          className="text-[10px]"
                        >
                          {explanationData.coverage_status === "complete"
                            ? "✓ Verified Coverage"
                            : `Coverage: ${explanationData.coverage_status}`}
                        </Badge>
                      )}
                      {explanationData.detail_level && (
                        <Badge variant="clay" className="text-[10px] uppercase font-bold tracking-wider">
                          {explanationData.detail_level}
                        </Badge>
                      )}
                      {explanationData.persona_mode_indicator && (
                        <Badge variant="success" className="text-[10px]">
                          {explanationData.persona_mode_indicator}
                        </Badge>
                      )}
                    </div>
                    <h3 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight">
                      {explanationData.topic_name}
                    </h3>
                    {explanationData.covered_concepts?.length > 0 && (
                      <div className="flex items-center gap-1.5 mt-2 flex-wrap">
                        <span className="text-[11px] font-bold text-slate-400">Covered Concepts:</span>
                        {explanationData.covered_concepts.map((concept: string, idx: number) => (
                          <span
                            key={idx}
                            className="text-[10px] font-medium px-2 py-0.5 rounded-md bg-indigo-50 text-indigo-700 border border-indigo-200/70"
                          >
                            {concept}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  <Button
                    size="sm"
                    variant={savedNote ? "secondary" : "outline"}
                    onClick={handleSaveAsNote}
                    className="self-start sm:self-auto shadow-xs"
                  >
                    {savedNote ? (
                      <>
                        <BookmarkCheck className="w-4 h-4 text-emerald-600 mr-1" />
                        <span>Saved to Notes</span>
                      </>
                    ) : (
                      <>
                        <Save className="w-4 h-4 mr-1" />
                        <span>Save as Note</span>
                      </>
                    )}
                  </Button>
                </div>

                {/* Exam Traps & Pitfalls Callout */}
                {explanationData.exam_traps?.length > 0 && (
                  <div className="p-4 rounded-2xl bg-rose-50/70 border border-rose-200 space-y-2">
                    <h4 className="text-xs font-bold text-rose-900 uppercase tracking-wider flex items-center gap-1.5">
                      <AlertTriangle className="w-4 h-4 text-rose-600" />
                      <span>Critical Exam Traps & Common Pitfalls</span>
                    </h4>
                    <ul className="text-xs text-rose-900 space-y-1.5 pl-1">
                      {explanationData.exam_traps.map((trap: string, i: number) => (
                        <li key={i} className="flex items-start gap-2">
                          <span className="font-bold text-rose-500">•</span>
                          <span>{trap}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Main Explanation Body */}
                <div className="py-1">
                  <MarkdownRenderer content={explanationData.explanation} />
                </div>

                {/* Analogies Section */}
                {explanationData.analogies?.length > 0 && (
                  <div className="p-4 rounded-2xl bg-amber-50/60 border border-amber-200">
                    <h4 className="text-xs font-bold text-amber-900 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                      <Lightbulb className="w-4 h-4 text-amber-600" />
                      <span>Intuitive Mental Model / Analogy</span>
                    </h4>
                    <p className="text-xs text-amber-900 leading-relaxed font-medium">
                      {explanationData.analogies[0]}
                    </p>
                  </div>
                )}

                {/* Key Takeaways Card */}
                {explanationData.key_takeaways?.length > 0 && (
                  <div className="p-4 rounded-2xl bg-indigo-50/60 border border-indigo-200/80">
                    <h4 className="text-xs font-bold text-indigo-950 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                      <CheckCircle2 className="w-4 h-4 text-indigo-600" />
                      <span>Key Takeaways for Active Retention</span>
                    </h4>
                    <ul className="space-y-1.5 text-xs text-indigo-900 pl-1">
                      {explanationData.key_takeaways.map((item: string, i: number) => (
                        <li key={i} className="flex items-start gap-2">
                          <span className="text-indigo-600 font-bold">•</span>
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Suggested Follow-up Questions */}
                {explanationData.follow_up_questions?.length > 0 && (
                  <div className="pt-2">
                    <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                      Suggested Follow-Up Enquiries:
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {explanationData.follow_up_questions.map((q: string, i: number) => (
                        <button
                          key={i}
                          onClick={() => {
                            setChatInput(q);
                            fetchExplanation(selectedTopicId, depth, mode, q, personaOverride);
                          }}
                          className="text-xs bg-slate-100/90 hover:bg-indigo-50 text-slate-700 hover:text-indigo-800 px-3 py-1.5 rounded-xl border border-slate-200/80 flex items-center gap-1.5 cursor-pointer text-left transition-colors"
                        >
                          <HelpCircle className="w-3.5 h-3.5 text-indigo-600 shrink-0" />
                          <span>{q}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : null}
          </Card>

          {/* Interactive AI Query Box */}
          <Card className="p-3">
            <form onSubmit={handleCustomSubmit} className="flex items-center gap-2">
              <input
                type="text"
                placeholder="Ask your AI tutor a specific question about this topic..."
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                className="flex-1 text-xs sm:text-sm px-3.5 py-2 rounded-xl border border-slate-300 focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20"
              />
              <Button type="submit" size="sm" variant="primary" disabled={loading || !chatInput.trim()}>
                <Send className="w-3.5 h-3.5 mr-1" /> Ask Tutor
              </Button>
            </form>
          </Card>
        </div>
      </div>
    </div>
  );
}
