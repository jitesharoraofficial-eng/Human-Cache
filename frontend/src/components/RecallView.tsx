"use client";

import React, { useEffect, useState } from "react";
import {
  Sparkles,
  CheckCircle2,
  XCircle,
  ArrowRight,
  RotateCcw,
  AlertTriangle,
  TrendingUp,
  Brain,
  Zap,
  Target,
  Award,
  Clock,
  HelpCircle
} from "lucide-react";
import { api } from "@/lib/api";
import { Card, Button, Badge, ProgressBar } from "./ui";

export function RecallView() {
  const [topics, setTopics] = useState<any[]>([]);
  const [selectedTopicId, setSelectedTopicId] = useState<string>("");
  const [quiz, setQuiz] = useState<any>(null);
  const [userAnswers, setUserAnswers] = useState<Record<string, string>>({});
  const [quizResult, setQuizResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    loadTopics();
  }, []);

  const loadTopics = async () => {
    try {
      const res = await api.getTopics();
      setTopics(res);
      // Prioritize review_due topic if available
      const dueTopic = res.find((t: any) => t.status === "review_due" || t.status === "overdue") || res[0];
      if (dueTopic) {
        setSelectedTopicId(dueTopic.id);
        generateQuiz(dueTopic.id);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const generateQuiz = async (topicId: string) => {
    setLoading(true);
    setQuiz(null);
    setQuizResult(null);
    setUserAnswers({});
    try {
      const res = await api.generateQuiz({ topic_ids: [topicId], question_count: 4, difficulty: "medium" });
      setQuiz(res);
    } catch (e: any) {
      alert("Error generating quiz: " + e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectAnswer = (questionId: string, answer: string) => {
    setUserAnswers((prev) => ({ ...prev, [questionId]: answer }));
  };

  const handleSubmitQuiz = async () => {
    if (!quiz) return;
    setSubmitting(true);
    try {
      const res = await api.submitQuiz({
        quiz_id: quiz.id,
        user_answers: userAnswers,
      });
      setQuizResult(res);
    } catch (e: any) {
      alert("Submission error: " + e.message);
    } finally {
      setSubmitting(false);
    }
  };

  const answeredCount = quiz ? Object.keys(userAnswers).length : 0;
  const totalQuestions = quiz?.questions?.length || 0;
  const completionPct = totalQuestions > 0 ? (answeredCount / totalQuestions) * 100 : 0;

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-8 font-sans">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="purple">Neural Retrieval Practice</Badge>
            <span className="text-xs text-slate-400">• Spaced Repetition Reinforcement</span>
          </div>
          <h2 className="text-2xl font-black text-slate-900 tracking-tight">
            Recall Drills & Adaptive Quizzes
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 mt-0.5">
            Active recall tests strengthen neural memory pathways. Your score directly updates your Ebbinghaus retention curve.
          </p>
        </div>

        {quiz && !quizResult && (
          <div className="clay-pill bg-white px-3.5 py-1.5 border border-slate-200 text-xs font-bold text-slate-700 shadow-xs flex items-center gap-2 self-start sm:self-auto">
            <span>Progress: {answeredCount} / {totalQuestions} Answered</span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Topics Selector (4 cols) */}
        <div className="lg:col-span-4 space-y-4">
          <Card className="p-5">
            <div className="flex items-center justify-between mb-3.5">
              <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                <Target className="w-4 h-4 text-indigo-600" />
                <span>Select Topic to Test</span>
              </h3>
              <Badge variant="clay" className="text-[10px]">{topics.length} Available</Badge>
            </div>

            <div className="space-y-2 max-h-[460px] overflow-y-auto pr-1">
              {topics.map((t) => {
                const isSelected = selectedTopicId === t.id;
                const isDue = t.status === "review_due" || t.status === "overdue";
                return (
                  <button
                    key={t.id}
                    onClick={() => {
                      setSelectedTopicId(t.id);
                      generateQuiz(t.id);
                    }}
                    className={`w-full text-left p-3.5 rounded-2xl border transition-all cursor-pointer flex flex-col justify-between ${
                      isSelected
                        ? "bg-gradient-to-r from-indigo-50 to-violet-50/70 border-indigo-500 shadow-xs ring-1 ring-indigo-500/30"
                        : "bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50/70"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className={`font-bold text-xs sm:text-sm truncate pr-2 ${isSelected ? "text-indigo-950" : "text-slate-900"}`}>
                        {t.canonical_name}
                      </span>
                      <Badge
                        variant={isDue ? "warning" : "default"}
                        className="text-[10px] shrink-0 font-bold"
                      >
                        {t.status || "unlearned"}
                      </Badge>
                    </div>
                    <div className="flex items-center justify-between text-[11px] text-slate-400 mt-1.5">
                      <span>Retention: <strong className="text-slate-600">{t.estimated_retention || 80}%</strong></span>
                      <span className="text-indigo-600 font-semibold">{isSelected ? "Testing Now" : "Start Drill →"}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          </Card>
        </div>

        {/* Right Column: Quiz Arena or Results (8 cols) */}
        <div className="lg:col-span-8 space-y-4">
          {loading ? (
            <Card className="p-16 flex flex-col items-center justify-center text-slate-400 gap-3">
              <Sparkles className="w-8 h-8 text-indigo-600 animate-spin" />
              <p className="text-sm font-semibold text-slate-700">
                Synthesizing grounded active recall assessment from source documents...
              </p>
            </Card>
          ) : quiz && !quizResult ? (
            <Card className="p-6 sm:p-8 space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-100 gap-3">
                <div>
                  <Badge variant="purple" className="mb-1 text-[10px]">
                    Active Recall Drill
                  </Badge>
                  <h3 className="text-xl font-black text-slate-900 tracking-tight">
                    {quiz.title}
                  </h3>
                </div>
                <div className="text-right">
                  <span className="text-xs text-slate-400">Answered</span>
                  <p className="text-sm font-black text-indigo-600">
                    {answeredCount} of {totalQuestions}
                  </p>
                </div>
              </div>

              {/* Question list */}
              <div className="space-y-6">
                {quiz.questions.map((q: any, idx: number) => {
                  const isAnswered = Boolean(userAnswers[q.id]);
                  return (
                    <div
                      key={q.id}
                      className={`p-5 rounded-2xl border transition-all ${
                        isAnswered
                          ? "bg-slate-50/70 border-indigo-200/80"
                          : "bg-white border-slate-200"
                      }`}
                    >
                      <div className="flex items-start gap-3 mb-3">
                        <span className="w-7 h-7 rounded-xl bg-indigo-100 text-indigo-700 text-xs font-black flex items-center justify-center shrink-0 shadow-xs">
                          {idx + 1}
                        </span>
                        <p className="text-sm sm:text-base font-bold text-slate-900 leading-snug">
                          {q.question}
                        </p>
                      </div>

                      {q.type === "short" ? (
                        <input
                          type="text"
                          placeholder="Type your concise explanation here..."
                          value={userAnswers[q.id] || ""}
                          onChange={(e) => handleSelectAnswer(q.id, e.target.value)}
                          className="w-full text-xs sm:text-sm border border-slate-300 rounded-xl p-3 bg-white focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20"
                        />
                      ) : (
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-1">
                          {q.options?.map((opt: string, optIdx: number) => {
                            const isSelected = userAnswers[q.id] === opt;
                            return (
                              <button
                                key={optIdx}
                                type="button"
                                onClick={() => handleSelectAnswer(q.id, opt)}
                                className={`p-3.5 text-left rounded-xl text-xs font-semibold border transition-all cursor-pointer flex items-center justify-between ${
                                  isSelected
                                    ? "bg-indigo-600 text-white border-indigo-600 shadow-md shadow-indigo-600/25"
                                    : "bg-white border-slate-200 text-slate-700 hover:border-indigo-300 hover:bg-slate-50"
                                }`}
                              >
                                <span>{opt}</span>
                                <div
                                  className={`w-4 h-4 rounded-full border flex items-center justify-center shrink-0 ml-2 ${
                                    isSelected
                                      ? "border-white bg-white text-indigo-600"
                                      : "border-slate-300 bg-transparent"
                                  }`}
                                >
                                  {isSelected && <span className="w-2 h-2 rounded-full bg-indigo-600" />}
                                </div>
                              </button>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Submit Action */}
              <div className="flex items-center justify-between pt-4 border-t border-slate-100">
                <span className="text-xs text-slate-500">
                  Submitting recalculates your Ebbinghaus memory curve.
                </span>
                <Button
                  size="lg"
                  variant="primary"
                  onClick={handleSubmitQuiz}
                  disabled={submitting || answeredCount === 0}
                  className="shadow-lg shadow-indigo-600/30"
                >
                  <Sparkles className="w-4 h-4 mr-1.5" />
                  {submitting ? "Evaluating Neural Recall..." : "Submit & Update Memory"}
                </Button>
              </div>
            </Card>
          ) : quizResult ? (
            /* Results View */
            <Card className="p-6 sm:p-8 space-y-6">
              {/* Score Hero Banner */}
              <div className="clay-card bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white p-6 rounded-3xl shadow-xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <Badge variant="purple" className="bg-indigo-500/30 text-indigo-200 border-indigo-400/40 text-[10px] mb-2">
                    Evaluation Complete
                  </Badge>
                  <h3 className="text-3xl font-black tracking-tight text-white">
                    Score: {quizResult.score_percentage}%
                  </h3>
                  <p className="text-xs text-indigo-200 mt-1 font-medium">
                    {quizResult.correct_count} of {quizResult.total_questions} questions verified correct.
                  </p>
                </div>
                <div className="bg-white/10 backdrop-blur-xs p-3.5 rounded-2xl border border-white/15 text-right sm:text-right">
                  <span className="text-[11px] text-slate-300 block">Memory Curve Impact:</span>
                  <p className="text-xs font-bold text-emerald-300 mt-0.5">
                    {quizResult.next_review_suggestion}
                  </p>
                </div>
              </div>

              {/* Questions Breakdown */}
              <div className="space-y-4">
                <h4 className="font-bold text-sm text-slate-900">
                  Question-by-Question Grounding & Feedback
                </h4>
                {quiz.questions.map((q: any) => {
                  const res = quizResult.results[q.id];
                  const isCorrect = res?.is_correct;
                  return (
                    <div
                      key={q.id}
                      className={`p-4 sm:p-5 rounded-2xl border transition-all ${
                        isCorrect
                          ? "bg-emerald-50/40 border-emerald-200"
                          : "bg-rose-50/40 border-rose-200"
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        {isCorrect ? (
                          <div className="w-6 h-6 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center shrink-0 mt-0.5">
                            <CheckCircle2 className="w-4 h-4" />
                          </div>
                        ) : (
                          <div className="w-6 h-6 rounded-full bg-rose-100 text-rose-600 flex items-center justify-center shrink-0 mt-0.5">
                            <XCircle className="w-4 h-4" />
                          </div>
                        )}
                        <div className="flex-1">
                          <p className="text-xs sm:text-sm font-bold text-slate-900 leading-snug">
                            {q.question}
                          </p>
                          <p className="text-xs text-slate-600 mt-1">
                            <strong>Your Answer:</strong> {res?.user_answer || "Not answered"}
                          </p>
                          {!isCorrect && (
                            <p className="text-xs text-rose-700 font-semibold mt-0.5">
                              <strong>Correct:</strong> {res?.correct_answer}
                            </p>
                          )}
                          <div className="mt-2.5 text-xs text-slate-700 bg-white p-3 rounded-xl border border-slate-200">
                            💡 <strong>Explanation:</strong> {res?.explanation}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="flex justify-end pt-2">
                <Button
                  variant="outline"
                  size="md"
                  onClick={() => generateQuiz(selectedTopicId)}
                >
                  <RotateCcw className="w-4 h-4 mr-1.5" /> Retake Active Recall Drill
                </Button>
              </div>
            </Card>
          ) : null}
        </div>
      </div>
    </div>
  );
}
