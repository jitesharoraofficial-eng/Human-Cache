"use client";

import React, { useEffect, useState } from "react";
import {
  Settings,
  User,
  Bell,
  Clock,
  Save,
  RefreshCw,
  Key,
  Check,
  Sparkles,
  BookOpen,
  Sliders,
  SlidersHorizontal,
  Plus,
  X,
  VolumeX,
  CheckCircle2,
  Undo2,
  Atom,
  TrendingUp,
  Scale,
  Globe
} from "lucide-react";
import { api } from "@/lib/api";
import { Card, Button, Badge } from "./ui";
import {
  UNIVERSAL_GOALS,
  UNIVERSAL_ROLES,
  TAXONOMY_STREAMS,
  getRecommendedSubjects
} from "@/lib/personalization";

export function SettingsView({ onLaunchOnboarding }: { onLaunchOnboarding?: () => void }) {
  const [profile, setProfile] = useState<any>(null);
  const [userRoles, setUserRoles] = useState<string[]>([]);
  const [goalsList, setGoalsList] = useState<string[]>([]);
  const [targetExam, setTargetExam] = useState("");
  const [curriculum, setCurriculum] = useState("");
  const [collegeDegree, setCollegeDegree] = useState("");
  const [collegeField, setCollegeField] = useState("");
  const [learningContext, setLearningContext] = useState<Record<string, any>>({});
  const [teachingStyles, setTeachingStyles] = useState<string[]>([]);
  const [subjects, setSubjects] = useState<string[]>([]);
  const [customSubjects, setCustomSubjects] = useState<string[]>([]);
  const [newCustomSubjectInput, setNewCustomSubjectInput] = useState("");
  const [activeStreamFilter, setActiveStreamFilter] = useState("all");
  const [explanationDepth, setExplanationDepth] = useState("balanced");
  const [language, setLanguage] = useState("en");
  const [quizDifficulty, setQuizDifficulty] = useState("adaptive");
  const [dailyMinutes, setDailyMinutes] = useState(45);
  const [preferredHours, setPreferredHours] = useState("evening");
  const [quietStart, setQuietStart] = useState("22:00");
  const [quietEnd, setQuietEnd] = useState("08:00");
  const [graphDetail, setGraphDetail] = useState("semi-detailed");
  const [mindmapDetail, setMindmapDetail] = useState("semi-detailed");
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [notificationCategories, setNotificationCategories] = useState<string[]>([
    "review_due",
    "weak_recall",
    "upcoming_exams",
    "study_materials"
  ]);
  const [autoReviewReminders, setAutoReviewReminders] = useState(true);
  const [autoQuizPrep, setAutoQuizPrep] = useState(true);
  const [autoExamRevision, setAutoExamRevision] = useState(true);
  const [customOthers, setCustomOthers] = useState<Record<string, string>>({});
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [loading, setLoading] = useState(false);
  const [suppressedTopics, setSuppressedTopics] = useState<any[]>([]);
  const [loadingSuppressed, setLoadingSuppressed] = useState(false);
  const [pushSubscribed, setPushSubscribed] = useState(false);

  // Dynamic recommendations based on active roles and goals
  const recommendedSubjects = getRecommendedSubjects(goalsList, userRoles, targetExam);

  useEffect(() => {
    loadProfile();
    loadSuppressedTopics();
    checkPushSubscription();
  }, []);

  const loadSuppressedTopics = async () => {
    setLoadingSuppressed(true);
    try {
      const data = await api.getSuppressedTopics();
      setSuppressedTopics(Array.isArray(data) ? data : []);
    } catch (e) {
      console.warn("Could not load suppressed topics:", e);
    } finally {
      setLoadingSuppressed(false);
    }
  };

  const handleUnsuppressTopic = async (topicId: string) => {
    try {
      await api.unsuppressTopic(topicId);
      setSuppressedTopics((prev) => prev.filter((t) => t.topic_id !== topicId));
      alert("Concept reminders re-enabled! Future retention reviews will be scheduled normally.");
    } catch (e: any) {
      alert("Error re-enabling concept: " + e.message);
    }
  };

  const checkPushSubscription = async () => {
    if (typeof window !== "undefined" && "serviceWorker" in navigator && "PushManager" in window) {
      try {
        const reg = await navigator.serviceWorker.getRegistration();
        if (reg) {
          const sub = await reg.pushManager.getSubscription();
          setPushSubscribed(!!sub);
        }
      } catch {
        // ignore
      }
    }
  };

  const togglePushNotifications = async () => {
    if (typeof window === "undefined" || !("serviceWorker" in navigator) || !("PushManager" in window)) {
      alert("Web Push is not supported in this browser environment.");
      return;
    }

    try {
      if (pushSubscribed) {
        const reg = await navigator.serviceWorker.getRegistration();
        if (reg) {
          const sub = await reg.pushManager.getSubscription();
          if (sub) {
            await sub.unsubscribe();
            await api.unsubscribeWebPush(sub.endpoint);
          }
        }
        setPushSubscribed(false);
        alert("Web Push notifications disabled.");
      } else {
        const perm = await Notification.requestPermission();
        if (perm !== "granted") {
          alert("Notification permission was denied in your browser settings.");
          return;
        }

        const reg = await navigator.serviceWorker.register("/sw.js");
        await navigator.serviceWorker.ready;

        let sub = await reg.pushManager.getSubscription();

        if (sub) {
          const keyP256dh = sub.getKey ? btoa(String.fromCharCode.apply(null, Array.from(new Uint8Array(sub.getKey("p256dh") || new ArrayBuffer(0))))) : "";
          const keyAuth = sub.getKey ? btoa(String.fromCharCode.apply(null, Array.from(new Uint8Array(sub.getKey("auth") || new ArrayBuffer(0))))) : "";
          await api.subscribeWebPush({
            endpoint: sub.endpoint,
            p256dh: keyP256dh,
            auth: keyAuth,
            user_agent: navigator.userAgent
          });
        }
        setPushSubscribed(true);
        alert("Browser notifications enabled!");
      }
    } catch (e: any) {
      alert("Notification setup status: " + e.message);
    }
  };

  const loadProfile = async () => {
    try {
      const data = await api.getUserProfile();
      setProfile(data);
      if (data.preferences) {
        setUserRoles(data.preferences.user_roles || []);
        setGoalsList(data.preferences.learning_goals_list || []);
        setTargetExam(data.preferences.target_exam || "");
        setCurriculum(data.preferences.curriculum || "");
        const ctx = data.preferences.learning_context || {};
        setLearningContext(ctx);
        setCollegeDegree(ctx.college_degree || "");
        setCollegeField(ctx.college_field || "");
        setTeachingStyles(data.preferences.teaching_styles || []);
        setSubjects(data.preferences.subjects_of_interest || []);
        setCustomSubjects(data.preferences.custom_subjects || []);
        setExplanationDepth(data.preferences.explanation_depth || "balanced");
        setLanguage(data.preferences.language || "en");
        setQuizDifficulty(data.preferences.quiz_difficulty || "adaptive");
        setDailyMinutes(data.preferences.daily_study_time_minutes || 45);
        setPreferredHours(data.preferences.preferred_study_hours || "evening");
        setQuietStart(data.preferences.quiet_hours_start || "22:00");
        setQuietEnd(data.preferences.quiet_hours_end || "08:00");
        setGraphDetail(data.preferences.graph_detail_level || "semi-detailed");
        setMindmapDetail(data.preferences.mindmap_detail_level || "semi-detailed");
        setNotificationsEnabled(data.preferences.notifications_enabled ?? true);
        setNotificationCategories(data.preferences.notification_categories || ["review_due", "weak_recall", "upcoming_exams", "study_materials"]);
        setAutoReviewReminders(data.preferences.auto_review_reminders ?? true);
        setAutoQuizPrep(data.preferences.auto_quiz_prep ?? true);
        setAutoExamRevision(data.preferences.auto_exam_revision ?? true);
        setCustomOthers(data.preferences.custom_other_responses || {});
      }
    } catch (e) {
      console.error(e);
    }
  };

  const toggleItem = (list: string[], setList: (val: string[]) => void, item: string) => {
    if (list.includes(item)) {
      setList(list.filter((x) => x !== item));
    } else {
      setList([...list, item]);
    }
  };

  const handleAddCustomSubject = () => {
    const trimmed = newCustomSubjectInput.trim();
    if (trimmed && !customSubjects.includes(trimmed) && !subjects.includes(trimmed)) {
      setCustomSubjects([...customSubjects, trimmed]);
      setSubjects([...subjects, trimmed]);
      setNewCustomSubjectInput("");
    }
  };

  const handleRemoveCustomSubject = (subj: string) => {
    setCustomSubjects(customSubjects.filter((s) => s !== subj));
    setSubjects(subjects.filter((s) => s !== subj));
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const updatedContext = {
        ...learningContext,
        college_degree: collegeDegree,
        college_field: collegeField
      };
      await api.updateUserPreferences({
        user_roles: userRoles,
        learning_goals_list: goalsList,
        learning_goals: goalsList.join(", "),
        target_exam: targetExam,
        curriculum: curriculum,
        learning_context: updatedContext,
        teaching_styles: teachingStyles,
        subjects_of_interest: subjects,
        custom_subjects: customSubjects,
        explanation_depth: explanationDepth,
        language: language,
        quiz_difficulty: quizDifficulty,
        daily_study_time_minutes: dailyMinutes,
        preferred_study_hours: preferredHours,
        quiet_hours_start: quietStart,
        quiet_hours_end: quietEnd,
        graph_detail_level: graphDetail,
        mindmap_detail_level: mindmapDetail,
        notifications_enabled: notificationsEnabled,
        notification_categories: notificationCategories,
        auto_review_reminders: autoReviewReminders,
        auto_quiz_prep: autoQuizPrep,
        auto_exam_revision: autoExamRevision,
        custom_other_responses: customOthers,
        onboarding_completed: true
      });

      // Update local storage representation
      const stored = localStorage.getItem("humancache_user");
      if (stored) {
        try {
          const u = JSON.parse(stored);
          u.target_exam = targetExam;
          localStorage.setItem("humancache_user", JSON.stringify(u));
        } catch {
          // ignore
        }
      }

      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3500);
    } catch (e: any) {
      alert("Error saving preferences: " + e.message);
    } finally {
      setLoading(false);
    }
  };

  const teachingStyleOptions = [
    { id: "simple_first", label: "Simple Language First" },
    { id: "basics_to_advanced", label: "Basics to Advanced" },
    { id: "detailed_conceptual", label: "Detailed Conceptual" },
    { id: "examples_first", label: "Examples Before Theory" },
    { id: "step_by_step", label: "Step-by-Step" },
    { id: "analogies", label: "Real-world Analogies" },
    { id: "exam_focused", label: "Exam Traps & Tricks" },
    { id: "problem_solving", label: "Problem Solving Strategies" },
    { id: "concise_notes", label: "Concise Revision Notes" },
    { id: "visual_diagrams", label: "Visual Diagrams & Schemas" },
  ];

  return (
    <div className="space-y-6 max-w-4xl mx-auto pb-8 font-sans">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight">
            Profile & Cognitive Preferences
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 mt-0.5">
            Manage your multi-select learning goals, curriculum, teaching styles, and spaced repetition triggers.
          </p>
        </div>

        {onLaunchOnboarding && (
          <Button
            size="sm"
            variant="outline"
            onClick={onLaunchOnboarding}
            className="self-start sm:self-auto shadow-xs"
          >
            <Sparkles className="w-3.5 h-3.5 mr-1.5 text-indigo-600" /> Re-run Setup Wizard
          </Button>
        )}
      </div>

      <form onSubmit={handleSave} className="space-y-6">
        {/* User Identity Card */}
        <Card className="p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-indigo-600 to-violet-600 text-white flex items-center justify-center font-bold text-lg shadow-md shadow-indigo-600/30 shrink-0">
              {profile?.name
                ? profile.name
                    .split(" ")
                    .map((n: string) => n[0])
                    .join("")
                    .slice(0, 2)
                    .toUpperCase()
                : "HC"}
            </div>
            <div>
              <h3 className="font-bold text-base text-slate-900">{profile?.name || "Learner"}</h3>
              <p className="text-xs text-slate-500">{profile?.email || "learner@humancache.ai"}</p>
              <div className="flex gap-1.5 mt-1.5 flex-wrap">
                {userRoles.map((r) => (
                  <Badge key={r} variant="purple" className="capitalize text-[10px]">
                    {r.replace(/_/g, " ")}
                  </Badge>
                ))}
              </div>
            </div>
          </div>
          <Badge variant="success" className="self-start sm:self-auto">
            Proactive Memory Engine Active
          </Badge>
        </Card>

        {/* Roles & Goals Section */}
        <Card className="p-6 space-y-5">
          <div>
            <h3 className="font-bold text-sm text-slate-900">User Roles (Multi-Select)</h3>
            <p className="text-xs text-slate-500 mt-0.5">Who you are and how your background is modeled.</p>
            <div className="flex flex-wrap gap-1.5 mt-2.5">
              {UNIVERSAL_ROLES.map((r) => {
                const isSel = userRoles.includes(r.id);
                return (
                  <button
                    type="button"
                    key={r.id}
                    onClick={() => toggleItem(userRoles, setUserRoles, r.id)}
                    className={`px-3 py-1.5 rounded-xl border text-xs font-semibold cursor-pointer transition-colors ${
                      isSel
                        ? "bg-indigo-600 text-white border-indigo-600 shadow-xs"
                        : "bg-white border-slate-200 text-slate-700 hover:bg-slate-50"
                    }`}
                  >
                    {r.label}
                  </button>
                );
              })}
            </div>
            {userRoles.includes("other") && (
              <input
                type="text"
                placeholder="Describe your custom role..."
                value={customOthers["role_other"] || ""}
                onChange={(e) => setCustomOthers({ ...customOthers, role_other: e.target.value })}
                className="mt-2.5 w-full text-xs border border-slate-300 rounded-xl p-2.5 bg-slate-50/50"
              />
            )}
          </div>

          <div>
            <h3 className="font-bold text-sm text-slate-900">Learning Goals (Multi-Select)</h3>
            <p className="text-xs text-slate-500 mt-0.5">Your active objectives across all streams and interests.</p>
            <div className="flex flex-wrap gap-1.5 mt-2.5">
              {UNIVERSAL_GOALS.map((g) => {
                const isSel = goalsList.includes(g.id);
                return (
                  <button
                    type="button"
                    key={g.id}
                    onClick={() => toggleItem(goalsList, setGoalsList, g.id)}
                    className={`px-3 py-1.5 rounded-xl border text-xs font-semibold cursor-pointer transition-colors ${
                      isSel
                        ? "bg-indigo-600 text-white border-indigo-600 shadow-xs"
                        : "bg-white border-slate-200 text-slate-700 hover:bg-slate-50"
                    }`}
                  >
                    {g.label}
                  </button>
                );
              })}
            </div>
            {goalsList.includes("other") && (
              <input
                type="text"
                placeholder="Describe your custom goal (e.g. UPSC, Machine Learning, CFA)..."
                value={customOthers["goal_other"] || ""}
                onChange={(e) => setCustomOthers({ ...customOthers, goal_other: e.target.value })}
                className="mt-2.5 w-full text-xs border border-slate-300 rounded-xl p-2.5 bg-slate-50/50"
              />
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Target Examination</label>
              <input
                type="text"
                value={targetExam}
                onChange={(e) => setTargetExam(e.target.value)}
                placeholder="e.g. UPSC Civil Services, CA Final, JEE, NEET, GATE, CLAT"
                className="w-full text-xs border border-slate-300 rounded-xl p-2.5 bg-white"
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Curriculum Standard</label>
              <input
                type="text"
                value={curriculum}
                onChange={(e) => setCurriculum(e.target.value)}
                placeholder="e.g. CBSE / NCERT, ICSE, University Syllabus, State Board"
                className="w-full text-xs border border-slate-300 rounded-xl p-2.5 bg-white"
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">College Degree / Program</label>
              <input
                type="text"
                value={collegeDegree}
                onChange={(e) => setCollegeDegree(e.target.value)}
                placeholder="e.g. B.Com, BBA, B.Tech, LL.B, MBBS, B.A."
                className="w-full text-xs border border-slate-300 rounded-xl p-2.5 bg-white"
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Major / Specialization</label>
              <input
                type="text"
                value={collegeField}
                onChange={(e) => setCollegeField(e.target.value)}
                placeholder="e.g. Business Management, Finance, CS, Taxation"
                className="w-full text-xs border border-slate-300 rounded-xl p-2.5 bg-white"
              />
            </div>
          </div>
        </Card>

        {/* Subjects of Interest Section */}
        <Card className="p-6 space-y-4">
          <div>
            <h3 className="font-bold text-sm text-slate-900">Subjects & Specializations</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              These subjects feed your knowledge graph and automatically curate non-duplicate study categories.
            </p>
          </div>

          {/* Recommended Pills */}
          {recommendedSubjects.length > 0 && (
            <div className="p-3 rounded-2xl bg-indigo-50/70 border border-indigo-200/90 space-y-2">
              <div className="flex items-center gap-1.5 text-xs font-bold text-indigo-900">
                <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
                <span>Recommended based on your active goals & roles:</span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {recommendedSubjects.map((s) => {
                  const isSel = subjects.includes(s);
                  return (
                    <button
                      type="button"
                      key={s}
                      onClick={() => toggleItem(subjects, setSubjects, s)}
                      className={`px-3 py-1.5 rounded-xl border text-xs font-semibold cursor-pointer transition-colors ${
                        isSel
                          ? "bg-indigo-600 text-white border-indigo-600 shadow-xs"
                          : "bg-white border-indigo-200 text-indigo-950 hover:bg-indigo-50"
                      }`}
                    >
                      {s}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Stream Filter Pills */}
          <div className="space-y-2 pt-2">
            <div className="flex items-center justify-between text-xs font-bold text-slate-700">
              <span>All Disciplines & Streams:</span>
              <span className="text-[11px] font-medium text-slate-400">{subjects.length} selected</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              <button
                type="button"
                onClick={() => setActiveStreamFilter("all")}
                className={`px-3 py-1 rounded-lg text-xs font-semibold cursor-pointer transition-all ${
                  activeStreamFilter === "all"
                    ? "bg-slate-900 text-white shadow-xs"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                All Streams
              </button>
              {TAXONOMY_STREAMS.map((str) => (
                <button
                  key={str.id}
                  type="button"
                  onClick={() => setActiveStreamFilter(str.id)}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold cursor-pointer transition-all ${
                    activeStreamFilter === str.id
                      ? "bg-indigo-600 text-white shadow-xs"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  {str.label}
                </button>
              ))}
            </div>
          </div>

          {/* Subjects Grid */}
          <div className="space-y-3 max-h-[300px] overflow-y-auto pr-1">
            {TAXONOMY_STREAMS.filter(
              (str) => activeStreamFilter === "all" || activeStreamFilter === str.id
            ).map((stream) => (
              <div key={stream.id} className="space-y-1.5">
                <p className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">{stream.label}</p>
                <div className="flex flex-wrap gap-1.5">
                  {stream.subjects.map((s) => {
                    const isSel = subjects.includes(s);
                    return (
                      <button
                        type="button"
                        key={s}
                        onClick={() => toggleItem(subjects, setSubjects, s)}
                        className={`px-2.5 py-1.5 rounded-xl border text-xs font-medium cursor-pointer transition-colors ${
                          isSel
                            ? "bg-indigo-600 text-white border-indigo-600 font-bold shadow-xs"
                            : "bg-white border-slate-200 text-slate-700 hover:bg-slate-50"
                        }`}
                      >
                        {s}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>

          {/* Custom Subjects Manager */}
          <div className="pt-2 space-y-2">
            <label className="block text-xs font-bold text-slate-700">Add Custom Subjects & Skills</label>
            <div className="flex gap-2">
              <input
                type="text"
                value={newCustomSubjectInput}
                onChange={(e) => setNewCustomSubjectInput(e.target.value)}
                placeholder="e.g. Classical Guitar, Vedic Philosophy, Microeconomics"
                className="flex-1 text-xs border border-slate-300 rounded-xl p-2.5 bg-white"
              />
              <Button size="sm" variant="secondary" onClick={handleAddCustomSubject}>
                <Plus className="w-3.5 h-3.5 mr-1" /> Add
              </Button>
            </div>

            {customSubjects.length > 0 && (
              <div className="flex flex-wrap gap-1.5 pt-1">
                {customSubjects.map((cs) => (
                  <span
                    key={cs}
                    className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200"
                  >
                    {cs}
                    <button
                      type="button"
                      onClick={() => handleRemoveCustomSubject(cs)}
                      className="hover:text-rose-600 cursor-pointer"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>
        </Card>

        {/* Pedagogical & Teaching Style Preferences */}
        <Card className="p-6 space-y-5">
          <div>
            <h3 className="font-bold text-sm text-slate-900">Teaching Style & Explanation Depth</h3>
            <p className="text-xs text-slate-500 mt-0.5">Defines how the AI Tutor formats explanations and exercises.</p>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1.5">
              Preferred Teaching Methods (Multi-Select)
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {teachingStyleOptions.map((ts) => {
                const isSel = teachingStyles.includes(ts.id);
                return (
                  <button
                    type="button"
                    key={ts.id}
                    onClick={() => toggleItem(teachingStyles, setTeachingStyles, ts.id)}
                    className={`p-2.5 rounded-xl border text-left flex items-center justify-between text-xs font-medium cursor-pointer transition-colors ${
                      isSel
                        ? "bg-indigo-50 border-indigo-600 text-indigo-900 font-bold shadow-xs"
                        : "bg-white border-slate-200 text-slate-700 hover:bg-slate-50"
                    }`}
                  >
                    <span>{ts.label}</span>
                    <div
                      className={`w-4 h-4 rounded-md border flex items-center justify-center shrink-0 ${
                        isSel ? "bg-indigo-600 border-indigo-600 text-white" : "border-slate-300 bg-white"
                      }`}
                    >
                      {isSel && <Check className="w-3 h-3 stroke-[3]" />}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 border-t border-slate-100">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Explanation Depth</label>
              <select
                value={explanationDepth}
                onChange={(e) => setExplanationDepth(e.target.value)}
                className="w-full text-xs border border-slate-300 rounded-xl p-2.5 bg-white font-medium"
              >
                <option value="brief">Brief (Concise summaries)</option>
                <option value="balanced">Balanced (Standard depth)</option>
                <option value="detailed">Detailed (Deep proofs & nuances)</option>
                <option value="adaptive">Adaptive (Auto-scales by performance)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Preferred Language</label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="w-full text-xs border border-slate-300 rounded-xl p-2.5 bg-white font-medium"
              >
                <option value="en">English</option>
                <option value="hi">Hindi (हिंदी)</option>
                <option value="hinglish">Hinglish</option>
                <option value="other">Other Language</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Quiz Difficulty</label>
              <select
                value={quizDifficulty}
                onChange={(e) => setQuizDifficulty(e.target.value)}
                className="w-full text-xs border border-slate-300 rounded-xl p-2.5 bg-white font-medium"
              >
                <option value="easy">Easy (Concept recall)</option>
                <option value="medium">Medium (Standard testing)</option>
                <option value="hard">Hard (Multi-concept traps)</option>
                <option value="adaptive">Adaptive (Smart scaling)</option>
              </select>
            </div>
          </div>
        </Card>

        {/* Study Routine & Notifications */}
        <Card className="p-6 space-y-5">
          <div>
            <h3 className="font-bold text-sm text-slate-900">Study Cadence & Notifications</h3>
            <p className="text-xs text-slate-500 mt-0.5">Control how Human Cache prompts you to review topics.</p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Daily Study Target</label>
              <select
                value={dailyMinutes}
                onChange={(e) => setDailyMinutes(Number(e.target.value))}
                className="w-full text-xs border border-slate-300 rounded-xl p-2.5 bg-white font-medium"
              >
                <option value={15}>15 Minutes / day</option>
                <option value={30}>30 Minutes / day</option>
                <option value={45}>45 Minutes / day</option>
                <option value={60}>60 Minutes / day</option>
                <option value={90}>90 Minutes / day</option>
                <option value={120}>120 Minutes / day</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Preferred Study Hours</label>
              <select
                value={preferredHours}
                onChange={(e) => setPreferredHours(e.target.value)}
                className="w-full text-xs border border-slate-300 rounded-xl p-2.5 bg-white font-medium"
              >
                <option value="morning">Morning (06:00 - 10:00)</option>
                <option value="afternoon">Afternoon (12:00 - 16:00)</option>
                <option value="evening">Evening (17:00 - 21:00)</option>
                <option value="night">Night (21:00 - 01:00)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Quiet Hours</label>
              <div className="flex items-center gap-1">
                <input
                  type="text"
                  value={quietStart}
                  onChange={(e) => setQuietStart(e.target.value)}
                  placeholder="22:00"
                  className="w-1/2 text-xs border border-slate-300 rounded-xl p-2 text-center bg-white"
                />
                <span className="text-xs text-slate-400">to</span>
                <input
                  type="text"
                  value={quietEnd}
                  onChange={(e) => setQuietEnd(e.target.value)}
                  placeholder="08:00"
                  className="w-1/2 text-xs border border-slate-300 rounded-xl p-2 text-center bg-white"
                />
              </div>
            </div>
          </div>

          {/* Visual Detail Levels */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 border-t border-slate-100">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Knowledge Graph Detail</label>
              <select
                value={graphDetail}
                onChange={(e) => setGraphDetail(e.target.value)}
                className="w-full text-xs border border-slate-300 rounded-xl p-2.5 bg-white font-medium"
              >
                <option value="brief">Brief (Central hub concepts only)</option>
                <option value="semi-detailed">Semi-detailed (Hubs + direct connections)</option>
                <option value="detailed">Detailed (Full semantic web)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Mind Map Detail</label>
              <select
                value={mindmapDetail}
                onChange={(e) => setMindmapDetail(e.target.value)}
                className="w-full text-xs border border-slate-300 rounded-xl p-2.5 bg-white font-medium"
              >
                <option value="brief">Brief (Core principles only)</option>
                <option value="semi-detailed">Semi-detailed (Balanced subtopics)</option>
                <option value="detailed">Detailed (Deep hierarchy & examples)</option>
              </select>
            </div>
          </div>

          {/* Notifications Toggles */}
          <div className="p-4 rounded-2xl bg-indigo-50/40 border border-indigo-200 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-900">Notification Channels</span>
              <label className="flex items-center gap-2 text-xs font-semibold text-slate-700 cursor-pointer">
                <input
                  type="checkbox"
                  checked={notificationsEnabled}
                  onChange={(e) => setNotificationsEnabled(e.target.checked)}
                  className="w-4 h-4 rounded text-indigo-600"
                />
                <span>Master Enable</span>
              </label>
            </div>

            {notificationsEnabled && (
              <div className="space-y-3 pt-2 border-t border-indigo-100">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {[
                    { id: "review_due", label: "Review due (Spaced repetition triggers)" },
                    { id: "weak_recall", label: "Weak recall (Reinforce fragile concepts)" },
                    { id: "upcoming_exams", label: "Upcoming exams (Syllabus milestones)" },
                    { id: "study_materials", label: "Prepared quizzes & mind maps" }
                  ].map((nc) => (
                    <label key={nc.id} className="flex items-center gap-2 text-xs text-slate-700 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={notificationCategories.includes(nc.id)}
                        onChange={() => toggleItem(notificationCategories, setNotificationCategories, nc.id)}
                        className="w-3.5 h-3.5 rounded text-indigo-600"
                      />
                      <span>{nc.label}</span>
                    </label>
                  ))}
                </div>

                {/* Web Push Background Subscription */}
                <div className="flex items-center justify-between p-3 rounded-xl bg-white border border-indigo-100 mt-2">
                  <div>
                    <h5 className="text-xs font-bold text-slate-900">Browser Web Push (Background Alerts)</h5>
                    <p className="text-[11px] text-slate-500">
                      Receive retention reminders even when the tab is closed via standards-based Web Push.
                    </p>
                  </div>
                  <Button
                    type="button"
                    size="sm"
                    variant={pushSubscribed ? "outline" : "primary"}
                    onClick={togglePushNotifications}
                    className="rounded-xl text-xs font-bold cursor-pointer"
                  >
                    {pushSubscribed ? "Push Enabled (Click to Disable)" : "Enable Web Push"}
                  </Button>
                </div>
              </div>
            )}
          </div>

          {/* Muted Concepts / "No Need" Topics Management */}
          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
                  <VolumeX className="w-4 h-4 text-slate-600" />
                  Muted Concepts ("No Need" Exclusions)
                </h4>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  Topics marked as "No Need" will not trigger proactive reviews. You can re-enable reminders anytime.
                </p>
              </div>
              <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-slate-200 text-slate-700">
                {suppressedTopics.length} Muted
              </span>
            </div>

            {loadingSuppressed ? (
              <p className="text-xs text-slate-400 py-2">Loading muted concepts...</p>
            ) : suppressedTopics.length === 0 ? (
              <p className="text-xs text-slate-400 italic py-2">
                No concepts have been suppressed. When you click "No Need" on a review alert, it will be listed here.
              </p>
            ) : (
              <div className="space-y-2 pt-2 border-t border-slate-200">
                {suppressedTopics.map((top) => (
                  <div
                    key={top.topic_id}
                    className="flex items-center justify-between p-2.5 rounded-xl bg-white border border-slate-200 text-xs"
                  >
                    <div>
                      <span className="font-bold text-slate-900">{top.canonical_name}</span>
                      <span className="text-[10px] text-slate-400 ml-2">Category: {top.category_name}</span>
                    </div>
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={() => handleUnsuppressTopic(top.topic_id)}
                      className="rounded-lg text-[11px] py-1 px-2.5 text-indigo-600 hover:bg-indigo-50 cursor-pointer"
                    >
                      <Undo2 className="w-3 h-3 mr-1" /> Re-enable Reminders
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Card>

        {/* Save Bar */}
        <div className="flex items-center justify-between pt-2">
          {savedSuccess && (
            <div className="flex items-center gap-1.5 text-xs text-emerald-600 font-bold bg-emerald-50 px-3 py-1.5 rounded-full border border-emerald-200 animate-fadeIn">
              <CheckCircle2 className="w-4 h-4" /> Preferences saved and synchronized!
            </div>
          )}
          <div className="ml-auto">
            <Button size="md" variant="primary" type="submit" disabled={loading} className="shadow-md">
              <Save className="w-4 h-4 mr-1.5" /> {loading ? "Saving..." : "Save Preferences"}
            </Button>
          </div>
        </div>
      </form>
    </div>
  );
}
