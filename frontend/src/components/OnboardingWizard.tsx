"use client";

import React, { useState, useEffect } from "react";
import {
  Brain,
  Sparkles,
  Check,
  ArrowRight,
  ArrowLeft,
  GraduationCap,
  BookOpen,
  Briefcase,
  Award,
  Compass,
  School,
  Target,
  Sliders,
  Bell,
  Clock,
  Code,
  Atom,
  Dna,
  Layers,
  HelpCircle,
  Plus,
  X,
  VolumeX,
  FileCheck2,
  CheckCircle2,
  AlertCircle,
  TrendingUp,
  Scale,
  Globe
} from "lucide-react";
import { Card, Button, Badge } from "./ui";
import { api } from "@/lib/api";
import {
  UNIVERSAL_GOALS,
  UNIVERSAL_ROLES,
  TAXONOMY_STREAMS,
  POPULAR_EXAMS,
  getRecommendedSubjects
} from "@/lib/personalization";

interface OnboardingWizardProps {
  onComplete: () => void;
  onCancel?: () => void;
}

const getDraftKey = () => {
  try {
    const u = localStorage.getItem("humancache_user") || sessionStorage.getItem("humancache_user");
    if (u) {
      const parsed = JSON.parse(u);
      if (parsed.id) return `humancache_onboarding_draft_${parsed.id}`;
    }
  } catch {}
  return "humancache_onboarding_draft";
};

export function OnboardingWizard({ onComplete, onCancel }: OnboardingWizardProps) {
  const [step, setStep] = useState(1);
  const [saving, setSaving] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  // ==========================================
  // STEP 1: What brings you to Human Cache?
  // ==========================================
  const [goals, setGoals] = useState<string[]>([]);
  const [goalOther, setGoalOther] = useState("");

  // ==========================================
  // STEP 2: Tell us about yourself (Roles & Context)
  // ==========================================
  const [roles, setRoles] = useState<string[]>([]);
  const [roleOther, setRoleOther] = useState("");

  // Conditional fields for roles
  const [classGrade, setClassGrade] = useState("Class 12");
  const [curriculum, setCurriculum] = useState("CBSE / NCERT");
  const [curriculumOther, setCurriculumOther] = useState("");
  const [academicYear, setAcademicYear] = useState("2026-2027");

  const [targetExam, setTargetExam] = useState("JEE Advanced & Main");
  const [targetExamOther, setTargetExamOther] = useState("");
  const [prepStage, setPrepStage] = useState("Starting Out (Concepts & Fundamentals)");
  const [examDate, setExamDate] = useState("");

  const [collegeDegree, setCollegeDegree] = useState("");
  const [collegeField, setCollegeField] = useState("");

  const [professionRole, setProfessionRole] = useState("");
  const [professionIndustry, setProfessionIndustry] = useState("");
  const [professionSkills, setProfessionSkills] = useState("");

  const [researchField, setResearchField] = useState("");
  const [researchTopics, setResearchTopics] = useState("");

  const [otherContext, setOtherContext] = useState("");

  // ==========================================
  // STEP 3: What do you want to learn? (Subjects)
  // ==========================================
  const [subjects, setSubjects] = useState<string[]>([]);
  const [subjectOtherInput, setSubjectOtherInput] = useState("");
  const [customSubjectsList, setCustomSubjectsList] = useState<string[]>([]);
  const [activeStreamFilter, setActiveStreamFilter] = useState<string>("all");

  // ==========================================
  // STEP 4: How should your AI tutor teach you?
  // ==========================================
  const [teachingStyles, setTeachingStyles] = useState<string[]>([
    "simple_first",
    "step_by_step",
    "analogies"
  ]);
  const [styleOther, setStyleOther] = useState("");
  const [explanationDepth, setExplanationDepth] = useState("balanced");
  const [language, setLanguage] = useState("en");
  const [languageOther, setLanguageOther] = useState("");
  const [quizDifficulty, setQuizDifficulty] = useState("adaptive");

  // ==========================================
  // STEP 5: Study routine and automation
  // ==========================================
  const [dailyMinutes, setDailyMinutes] = useState(45);
  const [preferredHours, setPreferredHours] = useState("evening");
  const [quietStart, setQuietStart] = useState("22:00");
  const [quietEnd, setQuietEnd] = useState("08:00");
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
  const [graphDetail, setGraphDetail] = useState("semi-detailed");
  const [mindmapDetail, setMindmapDetail] = useState("semi-detailed");

  // Dynamic recommendations based on Step 1 & Step 2 selections
  const recommendedSubjects = getRecommendedSubjects(
    goals,
    roles,
    roles.includes("competitive_aspirant") ? (targetExam === "other" ? targetExamOther : targetExam) : undefined,
    collegeDegree,
    collegeField
  );

  // Auto-populate subjects from recommendations when entering step 3 if user has not yet selected subjects
  useEffect(() => {
    if (step === 3 && subjects.length === 0 && recommendedSubjects.length > 0) {
      setSubjects(recommendedSubjects);
      const degLower = (collegeDegree || "").toLowerCase();
      if (degLower.includes("b.tech") || degLower.includes("btech") || degLower.includes("engineering")) {
        setActiveStreamFilter("engineering_tech");
      } else if (degLower.includes("b.com") || degLower.includes("bcom") || degLower.includes("commerce") || degLower.includes("bba")) {
        setActiveStreamFilter("commerce_management");
      } else if (degLower.includes("mbbs") || degLower.includes("medical") || degLower.includes("nursing")) {
        setActiveStreamFilter("medical_health");
      } else if (degLower.includes("law") || degLower.includes("ll.b") || degLower.includes("llb")) {
        setActiveStreamFilter("law_governance");
      }
    }
  }, [step, recommendedSubjects, subjects.length, collegeDegree]);

  // Restore draft from storage on mount
  useEffect(() => {
    try {
      const savedDraft = localStorage.getItem(getDraftKey());
      if (savedDraft) {
        const d = JSON.parse(savedDraft);
        if (d.step) setStep(d.step);
        if (d.goals && d.goals.length > 0) setGoals(d.goals);
        if (d.goalOther) setGoalOther(d.goalOther);
        if (d.roles && d.roles.length > 0) setRoles(d.roles);
        if (d.roleOther) setRoleOther(d.roleOther);
        if (d.classGrade) setClassGrade(d.classGrade);
        if (d.curriculum) setCurriculum(d.curriculum);
        if (d.curriculumOther) setCurriculumOther(d.curriculumOther);
        if (d.academicYear) setAcademicYear(d.academicYear);
        if (d.targetExam) setTargetExam(d.targetExam);
        if (d.targetExamOther) setTargetExamOther(d.targetExamOther);
        if (d.prepStage) setPrepStage(d.prepStage);
        if (d.examDate) setExamDate(d.examDate);
        if (d.collegeDegree) setCollegeDegree(d.collegeDegree);
        if (d.collegeField) setCollegeField(d.collegeField);
        if (d.professionRole) setProfessionRole(d.professionRole);
        if (d.professionIndustry) setProfessionIndustry(d.professionIndustry);
        if (d.professionSkills) setProfessionSkills(d.professionSkills);
        if (d.researchField) setResearchField(d.researchField);
        if (d.researchTopics) setResearchTopics(d.researchTopics);
        if (d.otherContext) setOtherContext(d.otherContext);
        if (d.subjects && d.subjects.length > 0) setSubjects(d.subjects);
        if (d.customSubjectsList) setCustomSubjectsList(d.customSubjectsList);
        if (d.teachingStyles) setTeachingStyles(d.teachingStyles);
        if (d.styleOther) setStyleOther(d.styleOther);
        if (d.explanationDepth) setExplanationDepth(d.explanationDepth);
        if (d.language) setLanguage(d.language);
        if (d.languageOther) setLanguageOther(d.languageOther);
        if (d.quizDifficulty) setQuizDifficulty(d.quizDifficulty);
        if (d.dailyMinutes) setDailyMinutes(d.dailyMinutes);
        if (d.preferredHours) setPreferredHours(d.preferredHours);
        if (d.quietStart) setQuietStart(d.quietStart);
        if (d.quietEnd) setQuietEnd(d.quietEnd);
        if (d.notificationsEnabled !== undefined) setNotificationsEnabled(d.notificationsEnabled);
        if (d.notificationCategories) setNotificationCategories(d.notificationCategories);
        if (d.autoReviewReminders !== undefined) setAutoReviewReminders(d.autoReviewReminders);
        if (d.autoQuizPrep !== undefined) setAutoQuizPrep(d.autoQuizPrep);
        if (d.autoExamRevision !== undefined) setAutoExamRevision(d.autoExamRevision);
        if (d.graphDetail) setGraphDetail(d.graphDetail);
        if (d.mindmapDetail) setMindmapDetail(d.mindmapDetail);
      }
    } catch {
      // ignore draft parse error
    }
  }, []);

  // Auto-save draft whenever answers change
  useEffect(() => {
    try {
      const draftState = {
        step,
        goals,
        goalOther,
        roles,
        roleOther,
        classGrade,
        curriculum,
        curriculumOther,
        academicYear,
        targetExam,
        targetExamOther,
        prepStage,
        examDate,
        collegeDegree,
        collegeField,
        professionRole,
        professionIndustry,
        professionSkills,
        researchField,
        researchTopics,
        otherContext,
        subjects,
        customSubjectsList,
        teachingStyles,
        styleOther,
        explanationDepth,
        language,
        languageOther,
        quizDifficulty,
        dailyMinutes,
        preferredHours,
        quietStart,
        quietEnd,
        notificationsEnabled,
        notificationCategories,
        autoReviewReminders,
        autoQuizPrep,
        autoExamRevision,
        graphDetail,
        mindmapDetail
      };
      localStorage.setItem(getDraftKey(), JSON.stringify(draftState));
    } catch {
      // ignore
    }
  }, [
    step,
    goals,
    goalOther,
    roles,
    roleOther,
    classGrade,
    curriculum,
    curriculumOther,
    academicYear,
    targetExam,
    targetExamOther,
    prepStage,
    examDate,
    collegeDegree,
    collegeField,
    professionRole,
    professionIndustry,
    professionSkills,
    researchField,
    researchTopics,
    otherContext,
    subjects,
    customSubjectsList,
    teachingStyles,
    styleOther,
    explanationDepth,
    language,
    languageOther,
    quizDifficulty,
    dailyMinutes,
    preferredHours,
    quietStart,
    quietEnd,
    notificationsEnabled,
    notificationCategories,
    autoReviewReminders,
    autoQuizPrep,
    autoExamRevision,
    graphDetail,
    mindmapDetail
  ]);

  // Helper for multi-select arrays
  const toggleArrayItem = (list: string[], setList: (val: string[]) => void, item: string) => {
    if (list.includes(item)) {
      setList(list.filter((x) => x !== item));
    } else {
      setList([...list, item]);
    }
  };

  // Add custom subject
  const handleAddCustomSubject = () => {
    const trimmed = subjectOtherInput.trim();
    if (trimmed && !customSubjectsList.includes(trimmed) && !subjects.includes(trimmed)) {
      setCustomSubjectsList([...customSubjectsList, trimmed]);
      setSubjects([...subjects, trimmed]);
      setSubjectOtherInput("");
    }
  };

  const handleRemoveCustomSubject = (subj: string) => {
    setCustomSubjectsList(customSubjectsList.filter((s) => s !== subj));
    setSubjects(subjects.filter((s) => s !== subj));
  };

  // Step navigation & validations
  const validateAndNext = () => {
    setValidationError(null);

    if (step === 1) {
      if (goals.length === 0) {
        setValidationError("Please select at least one purpose for using Human Cache.");
        return;
      }
      if (goals.includes("other") && !goalOther.trim()) {
        setValidationError("Please describe your purpose in the text field provided.");
        return;
      }
    }

    if (step === 2) {
      if (roles.length === 0) {
        setValidationError("Please select at least one role describing yourself.");
        return;
      }
      if (roles.includes("other") && !roleOther.trim()) {
        setValidationError("Please specify your role in the text field provided.");
        return;
      }
    }

    if (step === 3) {
      if (subjects.length === 0) {
        setValidationError("Please select at least one subject area of interest.");
        return;
      }
    }

    if (step === 4) {
      if (teachingStyles.length === 0) {
        setValidationError("Please select at least one preferred teaching method.");
        return;
      }
    }

    setStep((prev) => Math.min(5, prev + 1));
  };

  const handleBack = () => {
    setValidationError(null);
    setStep((prev) => Math.max(1, prev - 1));
  };

  // Finish Onboarding
  const handleFinishSetup = async () => {
    if (saving) return; // Prevent double submit
    setValidationError(null);
    setSaving(true);

    try {
      const customOthers: Record<string, string> = {};
      if (goals.includes("other") && goalOther.trim()) customOthers["goal_other"] = goalOther.trim();
      if (roles.includes("other") && roleOther.trim()) customOthers["role_other"] = roleOther.trim();
      if (curriculum === "other" && curriculumOther.trim()) customOthers["curriculum_other"] = curriculumOther.trim();
      if (targetExam === "other" && targetExamOther.trim()) customOthers["exam_other"] = targetExamOther.trim();
      if (teachingStyles.includes("other") && styleOther.trim()) customOthers["style_other"] = styleOther.trim();
      if (language === "other" && languageOther.trim()) customOthers["language_other"] = languageOther.trim();

      const isCompetitive = roles.includes("competitive_aspirant") || goals.includes("competitive_exam");
      const isSchool = roles.includes("school_student") || goals.includes("school_studies");
      const isCollege = roles.includes("college_student") || goals.includes("college_university");
      const isProfessional = roles.includes("working_professional") || goals.includes("professional_career");
      const isResearcher = roles.includes("researcher_academic") || goals.includes("academic_research");

      const effectiveExam = isCompetitive
        ? (targetExam === "other" && targetExamOther.trim() ? targetExamOther.trim() : (targetExam || ""))
        : "";
      const effectiveCurriculum = isSchool
        ? (curriculum === "other" && curriculumOther.trim() ? curriculumOther.trim() : (curriculum || ""))
        : "";
      const effectiveLanguage = language === "other" && languageOther.trim() ? languageOther.trim() : language;

      const learningContextObj: Record<string, any> = {
        grade: isSchool ? classGrade : "",
        academic_year: isSchool ? academicYear : "",
        prep_stage: isCompetitive ? prepStage : "",
        exam_date: isCompetitive ? examDate : "",
        college_degree: isCollege ? collegeDegree : (collegeDegree || ""),
        college_field: isCollege ? collegeField : (collegeField || ""),
        profession_role: isProfessional ? professionRole : (professionRole || ""),
        profession_industry: isProfessional ? professionIndustry : (professionIndustry || ""),
        profession_skills: isProfessional ? professionSkills : (professionSkills || ""),
        research_field: isResearcher ? researchField : (researchField || ""),
        research_topics: isResearcher ? researchTopics : (researchTopics || ""),
        other_context: otherContext
      };

      // 1. Persist to Backend
      await api.updateUserPreferences({
        user_roles: roles,
        learning_goals_list: goals,
        learning_goals: goals.join(", ") + (goalOther ? ` (${goalOther})` : ""),
        target_exam: effectiveExam,
        curriculum: effectiveCurriculum,
        learning_context: learningContextObj,
        subjects_of_interest: subjects,
        custom_subjects: customSubjectsList,
        explanation_depth: explanationDepth,
        teaching_styles: teachingStyles,
        language: effectiveLanguage,
        quiz_difficulty: quizDifficulty,
        daily_study_time_minutes: dailyMinutes,
        preferred_study_hours: preferredHours,
        quiet_hours_start: quietStart,
        quiet_hours_end: quietEnd,
        notifications_enabled: notificationsEnabled,
        notification_categories: notificationCategories,
        auto_review_reminders: autoReviewReminders,
        auto_quiz_prep: autoQuizPrep,
        auto_exam_revision: autoExamRevision,
        graph_detail_level: graphDetail,
        mindmap_detail_level: mindmapDetail,
        custom_other_responses: customOthers,
        onboarding_completed: true
      });

      // 2. Persist to active local session
      const storedStr = localStorage.getItem("humancache_user") || sessionStorage.getItem("humancache_user");
      let activeUser: any = {
        id: "user-" + Date.now(),
        name: "Learner",
        email: "learner@humancache.ai",
        role: "Learner",
        target_exam: effectiveExam,
        onboarding_completed: true
      };

      if (storedStr) {
        try {
          activeUser = JSON.parse(storedStr);
          activeUser.onboarding_completed = true;
          activeUser.target_exam = effectiveExam;
          if (roles.includes("competitive_aspirant")) activeUser.role = "Competitive Aspirant";
          else if (roles.includes("school_student")) activeUser.role = "School Student";
          else if (roles.includes("college_student")) activeUser.role = "College Student";
          else if (roles.includes("working_professional")) activeUser.role = "Working Professional";
          else if (roles.includes("creative_artist")) activeUser.role = "Creative / Artist";
        } catch {
          // ignore
        }
      }

      localStorage.setItem("humancache_user", JSON.stringify(activeUser));
      sessionStorage.setItem("humancache_user", JSON.stringify(activeUser));

      // 3. Clean up draft
      localStorage.removeItem(getDraftKey());
      localStorage.removeItem("humancache_onboarding_draft");

      // 4. Trigger completion
      onComplete();
    } catch (err: any) {
      setValidationError("Failed to save preferences to server: " + (err.message || "Network error"));
    } finally {
      setSaving(false);
    }
  };

  const teachingStyleOptions = [
    { id: "simple_first", label: "Explain in simple language first" },
    { id: "basics_to_advanced", label: "Build from basics to advanced concepts" },
    { id: "detailed_conceptual", label: "Give detailed conceptual explanations" },
    { id: "examples_first", label: "Use examples before theory" },
    { id: "step_by_step", label: "Explain step by step" },
    { id: "analogies", label: "Use analogies and real-world examples" },
    { id: "exam_focused", label: "Focus on exam preparation & question types" },
    { id: "problem_solving", label: "Include problem-solving strategies & traps" },
    { id: "concise_notes", label: "Provide concise revision notes" },
    { id: "visual_diagrams", label: "Use visual explanations & diagrams" },
    { id: "connect_concepts", label: "Connect concepts across disciplines" },
    { id: "practical_applications", label: "Focus on real-world practical applications" },
    { id: "other", label: "+ Other Teaching Style" }
  ];

  return (
    <div className="max-w-3xl w-full mx-auto my-auto p-4 sm:p-6 select-none font-sans">
      <Card className="clay-card p-6 sm:p-8 md:p-10 border-slate-200/90 shadow-2xl relative overflow-hidden bg-white/98">
        {/* Top Header: Brand & Progress Indicator */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-slate-100 gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-indigo-600 to-violet-600 flex items-center justify-center text-white shadow-md shadow-indigo-600/30">
              <Brain className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-base text-slate-900 tracking-tight">
                  Human Cache
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 font-semibold border border-indigo-200">
                  Step {step} of 5
                </span>
              </div>
              <p className="text-xs text-slate-500 font-medium">Personalize Your AI Second Brain</p>
            </div>
          </div>

          {/* Stepper Progress Bar */}
          <div className="flex items-center gap-1.5">
            {[1, 2, 3, 4, 5].map((s) => (
              <div
                key={s}
                className={`h-2 rounded-full transition-all duration-300 ${
                  s === step
                    ? "w-8 bg-indigo-600 shadow-xs"
                    : s < step
                    ? "w-4 bg-emerald-500"
                    : "w-3 bg-slate-200"
                }`}
              />
            ))}
          </div>
        </div>

        {/* Validation Error Banner */}
        {validationError && (
          <div className="mt-4 p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs font-medium flex items-center justify-between animate-fadeIn">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
              <span>{validationError}</span>
            </div>
            <button
              onClick={() => setValidationError(null)}
              className="text-rose-400 hover:text-rose-700 cursor-pointer"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* Step Contents */}
        <div className="py-6 space-y-6">
          {/* ==================================================== */}
          {/* STEP 1: WHAT BRINGS YOU TO HUMAN CACHE?              */}
          {/* ==================================================== */}
          {step === 1 && (
            <div className="space-y-5 animate-fadeIn">
              <div>
                <h2 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight">
                  What brings you to Human Cache?
                </h2>
                <p className="text-xs sm:text-sm text-slate-500 mt-1">
                  Select all that apply. Human Cache adapts to school, arts, commerce, sciences, skills, exams, and personal passions.
                </p>
              </div>

              {/* Multi-select Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 max-h-[380px] overflow-y-auto pr-1">
                {UNIVERSAL_GOALS.map((opt) => {
                  const isSelected = goals.includes(opt.id);
                  return (
                    <button
                      key={opt.id}
                      type="button"
                      onClick={() => toggleArrayItem(goals, setGoals, opt.id)}
                      className={`p-3 rounded-2xl border text-left transition-all flex items-start justify-between cursor-pointer group ${
                        isSelected
                          ? "bg-indigo-50/70 border-indigo-500/80 shadow-xs ring-1 ring-indigo-500/30"
                          : "bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50/60"
                      }`}
                    >
                      <div className="pr-2">
                        <p className={`text-xs font-bold ${isSelected ? "text-indigo-950" : "text-slate-800"}`}>
                          {opt.label}
                        </p>
                        <p className="text-[11px] text-slate-500 mt-0.5 leading-relaxed">{opt.desc}</p>
                      </div>
                      <div
                        className={`w-4 h-4 rounded-md border flex items-center justify-center shrink-0 mt-0.5 ${
                          isSelected
                            ? "bg-indigo-600 border-indigo-600 text-white"
                            : "border-slate-300 bg-white group-hover:border-slate-400"
                        }`}
                      >
                        {isSelected && <Check className="w-3 h-3 stroke-[3]" />}
                      </div>
                    </button>
                  );
                })}
              </div>

              {/* Conditional "Other" text input */}
              {goals.includes("other") && (
                <div className="p-3.5 rounded-2xl bg-indigo-50/40 border border-indigo-200/80 space-y-1.5 animate-fadeIn">
                  <label className="block text-xs font-bold text-slate-700">
                    Describe your purpose:
                  </label>
                  <input
                    type="text"
                    value={goalOther}
                    onChange={(e) => setGoalOther(e.target.value)}
                    placeholder="e.g. Master CFA economics, music production, philosophy, state PSC, etc."
                    className="w-full px-3 py-2 text-xs sm:text-sm rounded-xl border border-slate-300 bg-white focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
                  />
                </div>
              )}
            </div>
          )}

          {/* ==================================================== */}
          {/* STEP 2: TELL US ABOUT YOURSELF (Roles & Context)     */}
          {/* ==================================================== */}
          {step === 2 && (
            <div className="space-y-5 animate-fadeIn">
              <div>
                <h2 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight">
                  Help us personalize your learning experience.
                </h2>
                <p className="text-xs sm:text-sm text-slate-500 mt-1">
                  Select all that fit you. Your AI tutor calibrates its tone, depth, and cognitive models accordingly.
                </p>
              </div>

              {/* Roles Multi-select */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                {UNIVERSAL_ROLES.map((opt) => {
                  const isSelected = roles.includes(opt.id);
                  return (
                    <button
                      key={opt.id}
                      type="button"
                      onClick={() => toggleArrayItem(roles, setRoles, opt.id)}
                      className={`p-3 rounded-2xl border text-center transition-all flex flex-col items-center justify-center gap-1.5 cursor-pointer ${
                        isSelected
                          ? "bg-indigo-50/80 border-indigo-600 text-indigo-900 shadow-xs ring-1 ring-indigo-500/30"
                          : "bg-white border-slate-200 hover:border-slate-300 text-slate-700"
                      }`}
                    >
                      <span className="text-xs font-bold leading-tight">{opt.label}</span>
                      <span className="text-[10px] text-slate-400 line-clamp-1">{opt.desc}</span>
                    </button>
                  );
                })}
              </div>

              {/* Custom Role other input */}
              {roles.includes("other") && (
                <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200 space-y-1.5 animate-fadeIn">
                  <label className="block text-xs font-bold text-slate-700">Specify your role:</label>
                  <input
                    type="text"
                    value={roleOther}
                    onChange={(e) => setRoleOther(e.target.value)}
                    placeholder="e.g. Chartered Accountant, Medical Resident, Musician, Lawyer"
                    className="w-full px-3 py-2 text-xs rounded-xl border border-slate-300 bg-white focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20"
                  />
                </div>
              )}

              {/* CONDITIONAL FOLLOW-UP SECTIONS */}
              <div className="space-y-3 pt-2">
                {/* 1. School Student Follow-up */}
                {roles.includes("school_student") && (
                  <div className="p-4 rounded-2xl bg-slate-50/70 border border-slate-200/90 space-y-3 animate-fadeIn">
                    <div className="flex items-center gap-2 text-xs font-bold text-indigo-900 uppercase tracking-wider">
                      <School className="w-4 h-4 text-indigo-600" />
                      <span>School Student Details</span>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      <div>
                        <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                          Class / Grade
                        </label>
                        <select
                          value={classGrade}
                          onChange={(e) => setClassGrade(e.target.value)}
                          className="w-full px-3 py-2 text-xs rounded-xl border border-slate-300 bg-white"
                        >
                          <option>Class 9</option>
                          <option>Class 10</option>
                          <option>Class 11</option>
                          <option>Class 12</option>
                          <option>Middle School (6-8)</option>
                          <option>Other Grade</option>
                        </select>
                      </div>

                      <div>
                        <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                          Board / Curriculum
                        </label>
                        <select
                          value={curriculum}
                          onChange={(e) => setCurriculum(e.target.value)}
                          className="w-full px-3 py-2 text-xs rounded-xl border border-slate-300 bg-white"
                        >
                          <option>CBSE / NCERT</option>
                          <option>ICSE / ISC</option>
                          <option>State Board</option>
                          <option>IB / Cambridge</option>
                          <option value="other">Other Curriculum</option>
                        </select>
                        {curriculum === "other" && (
                          <input
                            type="text"
                            placeholder="Enter board name"
                            value={curriculumOther}
                            onChange={(e) => setCurriculumOther(e.target.value)}
                            className="mt-1.5 w-full px-2.5 py-1.5 text-xs rounded-lg border border-slate-300 bg-white"
                          />
                        )}
                      </div>

                      <div>
                        <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                          Academic Year
                        </label>
                        <input
                          type="text"
                          value={academicYear}
                          onChange={(e) => setAcademicYear(e.target.value)}
                          placeholder="e.g. 2026-2027"
                          className="w-full px-3 py-2 text-xs rounded-xl border border-slate-300 bg-white"
                        />
                      </div>
                    </div>
                  </div>
                )}

                {/* 2. Competitive Aspirant Follow-up */}
                {roles.includes("competitive_aspirant") && (
                  <div className="p-4 rounded-2xl bg-amber-50/40 border border-amber-200/80 space-y-3 animate-fadeIn">
                    <div className="flex items-center gap-2 text-xs font-bold text-amber-900 uppercase tracking-wider">
                      <Target className="w-4 h-4 text-amber-600" />
                      <span>Competitive Exam Aspirant Details</span>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      <div>
                        <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                          Target Examination
                        </label>
                        <select
                          value={targetExam}
                          onChange={(e) => setTargetExam(e.target.value)}
                          className="w-full px-3 py-2 text-xs rounded-xl border border-slate-300 bg-white"
                        >
                          <option>JEE Advanced & Main</option>
                          <option>NEET UG</option>
                          <option>UPSC Civil Services (CSE)</option>
                          <option>CA (Foundation / Inter / Final)</option>
                          <option>CLAT / Law Entrances</option>
                          <option>GATE Engineering</option>
                          <option>CAT / MBA</option>
                          <option>IBPS / Banking Exam</option>
                          <option>SSC CGL / State PCS</option>
                          <option>SAT / GRE / GMAT</option>
                          <option value="other">Other Competitive Exam</option>
                        </select>
                        {targetExam === "other" && (
                          <input
                            type="text"
                            placeholder="Enter exam name"
                            value={targetExamOther}
                            onChange={(e) => setTargetExamOther(e.target.value)}
                            className="mt-1.5 w-full px-2.5 py-1.5 text-xs rounded-lg border border-slate-300 bg-white"
                          />
                        )}
                      </div>

                      <div>
                        <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                          Preparation Stage
                        </label>
                        <select
                          value={prepStage}
                          onChange={(e) => setPrepStage(e.target.value)}
                          className="w-full px-3 py-2 text-xs rounded-xl border border-slate-300 bg-white"
                        >
                          <option>Starting Out (Concepts & Fundamentals)</option>
                          <option>Mid-syllabus & Problem Solving</option>
                          <option>Revision & Full Mock Tests</option>
                          <option>Final Crunch (&lt; 30 days)</option>
                        </select>
                      </div>

                      <div>
                        <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                          Target Exam Date (Optional)
                        </label>
                        <input
                          type="date"
                          value={examDate}
                          onChange={(e) => setExamDate(e.target.value)}
                          className="w-full px-3 py-2 text-xs rounded-xl border border-slate-300 bg-white"
                        />
                      </div>
                    </div>
                  </div>
                )}

                {/* 3. College Student Follow-up */}
                {roles.includes("college_student") && (
                  <div className="p-4 rounded-2xl bg-indigo-50/40 border border-indigo-200/80 space-y-3 animate-fadeIn">
                    <div className="flex items-center gap-2 text-xs font-bold text-indigo-900 uppercase tracking-wider">
                      <GraduationCap className="w-4 h-4 text-indigo-600" />
                      <span>University & Degree Context</span>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div>
                        <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                          Degree / Program
                        </label>
                        <input
                          type="text"
                          value={collegeDegree}
                          onChange={(e) => setCollegeDegree(e.target.value)}
                          placeholder="e.g. B.A. History, B.Com, MBBS, B.Tech, LL.B, B.Sc"
                          className="w-full px-3 py-2 text-xs rounded-xl border border-slate-300 bg-white"
                        />
                      </div>
                      <div>
                        <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                          Specialization / Major
                        </label>
                        <input
                          type="text"
                          value={collegeField}
                          onChange={(e) => setCollegeField(e.target.value)}
                          placeholder="e.g. Political Science, Taxation, Psychology, CS"
                          className="w-full px-3 py-2 text-xs rounded-xl border border-slate-300 bg-white"
                        />
                      </div>
                    </div>
                  </div>
                )}

                {/* 4. Professional Follow-up */}
                {roles.includes("working_professional") && (
                  <div className="p-4 rounded-2xl bg-emerald-50/40 border border-emerald-200/80 space-y-3 animate-fadeIn">
                    <div className="flex items-center gap-2 text-xs font-bold text-emerald-900 uppercase tracking-wider">
                      <Briefcase className="w-4 h-4 text-emerald-600" />
                      <span>Professional Role & Industry</span>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      <div>
                        <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                          Current Role
                        </label>
                        <input
                          type="text"
                          value={professionRole}
                          onChange={(e) => setProfessionRole(e.target.value)}
                          placeholder="e.g. Financial Analyst, Architect, Manager"
                          className="w-full px-3 py-2 text-xs rounded-xl border border-slate-300 bg-white"
                        />
                      </div>
                      <div>
                        <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                          Industry
                        </label>
                        <input
                          type="text"
                          value={professionIndustry}
                          onChange={(e) => setProfessionIndustry(e.target.value)}
                          placeholder="e.g. Media, Legal, Healthcare, Tech"
                          className="w-full px-3 py-2 text-xs rounded-xl border border-slate-300 bg-white"
                        />
                      </div>
                      <div>
                        <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                          Key Skills to Master
                        </label>
                        <input
                          type="text"
                          value={professionSkills}
                          onChange={(e) => setProfessionSkills(e.target.value)}
                          placeholder="e.g. Leadership, Taxation, System Design"
                          className="w-full px-3 py-2 text-xs rounded-xl border border-slate-300 bg-white"
                        />
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ==================================================== */}
          {/* STEP 3: WHAT DO YOU WANT TO LEARN? (Subjects)       */}
          {/* ==================================================== */}
          {step === 3 && (
            <div className="space-y-5 animate-fadeIn">
              <div>
                <h2 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight">
                  Which subjects or areas should Human Cache help you with?
                </h2>
                <p className="text-xs sm:text-sm text-slate-500 mt-1">
                  We adapt recommendations to your goals while keeping every discipline available.
                </p>
              </div>

              {/* Recommended For You Section */}
              {recommendedSubjects.length > 0 && (
                <div className="p-3.5 rounded-2xl bg-gradient-to-r from-indigo-50/80 to-violet-50/80 border border-indigo-200/90 space-y-2">
                  <div className="flex items-center gap-1.5 text-xs font-bold text-indigo-900">
                    <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
                    <span>Recommended for you based on previous steps</span>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {recommendedSubjects.map((subj) => {
                      const isSelected = subjects.includes(subj);
                      return (
                        <button
                          key={subj}
                          type="button"
                          onClick={() => toggleArrayItem(subjects, setSubjects, subj)}
                          className={`px-3 py-1.5 rounded-xl text-xs font-bold border transition-all cursor-pointer flex items-center gap-1.5 ${
                            isSelected
                              ? "bg-indigo-600 text-white border-indigo-600 shadow-xs"
                              : "bg-white text-indigo-950 border-indigo-200 hover:border-indigo-300 hover:bg-indigo-50/60"
                          }`}
                        >
                          {isSelected ? <Check className="w-3.5 h-3.5 stroke-[3]" /> : <Plus className="w-3.5 h-3.5 text-indigo-500" />}
                          <span>{subj}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Taxonomy Stream Filter Pills */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs font-bold text-slate-700">
                  <span>Explore all subjects by discipline:</span>
                  <span className="text-[11px] font-medium text-slate-400">
                    {subjects.length} selected
                  </span>
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

              {/* Stream Subjects List */}
              <div className="space-y-4 max-h-[300px] overflow-y-auto pr-1">
                {TAXONOMY_STREAMS.filter(
                  (str) => activeStreamFilter === "all" || activeStreamFilter === str.id
                ).map((stream) => (
                  <div key={stream.id} className="space-y-1.5">
                    <p className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                      {stream.label}
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {stream.subjects.map((subj) => {
                        const isSelected = subjects.includes(subj);
                        return (
                          <button
                            key={subj}
                            type="button"
                            onClick={() => toggleArrayItem(subjects, setSubjects, subj)}
                            className={`px-2.5 py-1.5 rounded-xl text-xs font-medium border transition-all cursor-pointer flex items-center gap-1.5 ${
                              isSelected
                                ? "bg-indigo-600 text-white border-indigo-600 font-bold shadow-xs"
                                : "bg-white text-slate-700 border-slate-200 hover:border-slate-300 hover:bg-slate-50"
                            }`}
                          >
                            {isSelected ? <Check className="w-3 h-3 stroke-[3]" /> : <Plus className="w-3 h-3 text-slate-400" />}
                            <span>{subj}</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>

              {/* Custom Subject Entry */}
              <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200 space-y-2">
                <label className="block text-xs font-bold text-slate-700">
                  Add custom subject, skill or topic:
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={subjectOtherInput}
                    onChange={(e) => setSubjectOtherInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        handleAddCustomSubject();
                      }
                    }}
                    placeholder="e.g. Corporate Finance, Classical Indian Music, Vedic History, Cloud Architecture"
                    className="flex-1 px-3 py-2 text-xs rounded-xl border border-slate-300 bg-white focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20"
                  />
                  <Button
                    size="sm"
                    variant="primary"
                    onClick={handleAddCustomSubject}
                  >
                    Add
                  </Button>
                </div>

                {/* Display added custom subjects */}
                {customSubjectsList.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {customSubjectsList.map((cs) => (
                      <span
                        key={cs}
                        className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-100 text-indigo-800 border border-indigo-200"
                      >
                        {cs}
                        <button
                          type="button"
                          onClick={() => handleRemoveCustomSubject(cs)}
                          className="hover:text-rose-600 cursor-pointer p-0.5"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ==================================================== */}
          {/* STEP 4: HOW SHOULD YOUR AI TUTOR TEACH YOU?          */}
          {/* ==================================================== */}
          {step === 4 && (
            <div className="space-y-5 animate-fadeIn">
              <div>
                <h2 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight">
                  How do you prefer to understand new concepts?
                </h2>
                <p className="text-xs sm:text-sm text-slate-500 mt-1">
                  Choose your cognitive explanation preferences, explanation depth, and default difficulty.
                </p>
              </div>

              {/* Teaching Styles Multi-select */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 max-h-[260px] overflow-y-auto pr-1">
                {teachingStyleOptions.map((st) => {
                  const isSelected = teachingStyles.includes(st.id);
                  return (
                    <button
                      key={st.id}
                      type="button"
                      onClick={() => toggleArrayItem(teachingStyles, setTeachingStyles, st.id)}
                      className={`p-2.5 rounded-xl border text-left transition-all flex items-center justify-between cursor-pointer ${
                        isSelected
                          ? "bg-indigo-50 border-indigo-600 text-indigo-950 font-bold shadow-xs"
                          : "bg-white border-slate-200 hover:border-slate-300 text-slate-700 text-xs font-medium"
                      }`}
                    >
                      <span className="text-xs">{st.label}</span>
                      <div
                        className={`w-4 h-4 rounded-md border flex items-center justify-center shrink-0 ml-2 ${
                          isSelected
                            ? "bg-indigo-600 border-indigo-600 text-white"
                            : "border-slate-300 bg-white"
                        }`}
                      >
                        {isSelected && <Check className="w-3 h-3 stroke-[3]" />}
                      </div>
                    </button>
                  );
                })}
              </div>

              {/* Custom style textarea if 'other' is selected */}
              {teachingStyles.includes("other") && (
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-1 animate-fadeIn">
                  <label className="block text-xs font-bold text-slate-700">
                    Describe your preferred teaching style:
                  </label>
                  <textarea
                    value={styleOther}
                    onChange={(e) => setStyleOther(e.target.value)}
                    rows={2}
                    placeholder="e.g. Socratic questioning, historical case studies, or first-principles proofs"
                    className="w-full p-2.5 text-xs rounded-xl border border-slate-300 bg-white"
                  />
                </div>
              )}

              {/* Explanation Depth, Language & Quiz Difficulty Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 border-t border-slate-100">
                <div className="space-y-1">
                  <label className="block text-xs font-bold text-slate-700">
                    Explanation Depth
                  </label>
                  <select
                    value={explanationDepth}
                    onChange={(e) => setExplanationDepth(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-xl border border-slate-300 bg-white font-medium"
                  >
                    <option value="brief">Brief (Concise summaries)</option>
                    <option value="balanced">Balanced (Standard depth)</option>
                    <option value="detailed">Detailed (In-depth rigor & nuances)</option>
                    <option value="adaptive">Adaptive (Auto-scales by performance)</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="block text-xs font-bold text-slate-700">
                    Preferred Language
                  </label>
                  <select
                    value={language}
                    onChange={(e) => setLanguage(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-xl border border-slate-300 bg-white font-medium"
                  >
                    <option value="en">English</option>
                    <option value="hi">Hindi (हिंदी)</option>
                    <option value="hinglish">Hinglish</option>
                    <option value="other">Other Language</option>
                  </select>
                  {language === "other" && (
                    <input
                      type="text"
                      placeholder="Language name"
                      value={languageOther}
                      onChange={(e) => setLanguageOther(e.target.value)}
                      className="mt-1 w-full px-2 py-1 text-xs rounded-lg border border-slate-300 bg-white"
                    />
                  )}
                </div>

                <div className="space-y-1">
                  <label className="block text-xs font-bold text-slate-700">
                    Quiz Difficulty
                  </label>
                  <select
                    value={quizDifficulty}
                    onChange={(e) => setQuizDifficulty(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-xl border border-slate-300 bg-white font-medium"
                  >
                    <option value="easy">Easy (Concept recall)</option>
                    <option value="medium">Medium (Standard testing)</option>
                    <option value="hard">Hard (Multi-concept traps)</option>
                    <option value="adaptive">Adaptive (Smart scaling)</option>
                  </select>
                </div>
              </div>
            </div>
          )}

          {/* ==================================================== */}
          {/* STEP 5: STUDY ROUTINE AND AUTOMATION                 */}
          {/* ==================================================== */}
          {step === 5 && (
            <div className="space-y-5 animate-fadeIn">
              <div>
                <h2 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight">
                  How should Human Cache help you stay on track?
                </h2>
                <p className="text-xs sm:text-sm text-slate-500 mt-1">
                  Configure your daily cadence, notification triggers, and visual graph detail levels.
                </p>
              </div>

              {/* Study Routine Row */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200">
                  <div className="flex items-center gap-1.5 text-xs font-bold text-slate-800 mb-1">
                    <Clock className="w-3.5 h-3.5 text-indigo-600" />
                    <span>Daily Study Target</span>
                  </div>
                  <select
                    value={dailyMinutes}
                    onChange={(e) => setDailyMinutes(Number(e.target.value))}
                    className="w-full px-3 py-2 text-xs rounded-xl border border-slate-300 bg-white font-semibold mt-1"
                  >
                    <option value={15}>15 Minutes / day</option>
                    <option value={30}>30 Minutes / day</option>
                    <option value={45}>45 Minutes / day</option>
                    <option value={60}>60 Minutes / day</option>
                    <option value={90}>90 Minutes / day</option>
                    <option value={120}>120 Minutes / day</option>
                  </select>
                </div>

                <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200">
                  <div className="flex items-center gap-1.5 text-xs font-bold text-slate-800 mb-1">
                    <Sliders className="w-3.5 h-3.5 text-violet-600" />
                    <span>Preferred Study Hours</span>
                  </div>
                  <select
                    value={preferredHours}
                    onChange={(e) => setPreferredHours(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-xl border border-slate-300 bg-white font-semibold mt-1"
                  >
                    <option value="morning">Morning (06:00 - 10:00)</option>
                    <option value="afternoon">Afternoon (12:00 - 16:00)</option>
                    <option value="evening">Evening (17:00 - 21:00)</option>
                    <option value="night">Night (21:00 - 01:00)</option>
                  </select>
                </div>

                <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200">
                  <div className="flex items-center gap-1.5 text-xs font-bold text-slate-800 mb-1">
                    <VolumeX className="w-3.5 h-3.5 text-slate-600" />
                    <span>Quiet Hours</span>
                  </div>
                  <div className="flex items-center gap-1 mt-1">
                    <input
                      type="text"
                      value={quietStart}
                      onChange={(e) => setQuietStart(e.target.value)}
                      placeholder="22:00"
                      className="w-1/2 px-2 py-1.5 text-xs rounded-lg border border-slate-300 bg-white text-center"
                    />
                    <span className="text-xs text-slate-400">to</span>
                    <input
                      type="text"
                      value={quietEnd}
                      onChange={(e) => setQuietEnd(e.target.value)}
                      placeholder="08:00"
                      className="w-1/2 px-2 py-1.5 text-xs rounded-lg border border-slate-300 bg-white text-center"
                    />
                  </div>
                </div>
              </div>

              {/* Detail Levels */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200">
                  <label className="block text-xs font-bold text-slate-800 mb-1">
                    Knowledge Graph Detail Level
                  </label>
                  <select
                    value={graphDetail}
                    onChange={(e) => setGraphDetail(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-xl border border-slate-300 bg-white"
                  >
                    <option value="brief">Brief (Central hub concepts only)</option>
                    <option value="semi-detailed">Semi-detailed (Hubs + direct connections)</option>
                    <option value="detailed">Detailed (Full semantic web)</option>
                  </select>
                </div>

                <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200">
                  <label className="block text-xs font-bold text-slate-800 mb-1">
                    Mind Map Detail Level
                  </label>
                  <select
                    value={mindmapDetail}
                    onChange={(e) => setMindmapDetail(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-xl border border-slate-300 bg-white"
                  >
                    <option value="brief">Brief (Core principles only)</option>
                    <option value="semi-detailed">Semi-detailed (Balanced subtopics)</option>
                    <option value="detailed">Detailed (Deep hierarchy & examples)</option>
                  </select>
                </div>
              </div>

              {/* Notification Categories & Automation Toggles */}
              <div className="p-4 rounded-2xl bg-indigo-50/40 border border-indigo-200 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Bell className="w-4 h-4 text-indigo-600" />
                    <span className="text-xs font-bold text-slate-900">Notification Alerts</span>
                  </div>
                  <label className="flex items-center gap-2 text-xs font-semibold text-slate-700 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={notificationsEnabled}
                      onChange={(e) => setNotificationsEnabled(e.target.checked)}
                      className="w-4 h-4 rounded text-indigo-600 focus:ring-indigo-500"
                    />
                    <span>Master Enable</span>
                  </label>
                </div>

                {notificationsEnabled && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2 border-t border-indigo-100">
                    {[
                      { id: "review_due", label: "Review due (Spaced repetition triggers)" },
                      { id: "weak_recall", label: "Weak recall (Reinforce fragile concepts)" },
                      { id: "upcoming_exams", label: "Upcoming exams (Syllabus milestones)" },
                      { id: "unlearned_topics", label: "Unlearned topics (Extracted materials)" },
                      { id: "study_materials", label: "Prepared quizzes & mind maps" }
                    ].map((nc) => (
                      <label key={nc.id} className="flex items-center gap-2 text-xs text-slate-700 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={notificationCategories.includes(nc.id)}
                          onChange={() => toggleArrayItem(notificationCategories, setNotificationCategories, nc.id)}
                          className="w-3.5 h-3.5 rounded text-indigo-600"
                        />
                        <span>{nc.label}</span>
                      </label>
                    ))}
                  </div>
                )}

                {/* Proactive Automations */}
                <div className="pt-2 border-t border-indigo-100 space-y-1.5">
                  <label className="flex items-center gap-2 text-xs text-slate-800 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={autoReviewReminders}
                      onChange={(e) => setAutoReviewReminders(e.target.checked)}
                      className="w-3.5 h-3.5 rounded text-indigo-600"
                    />
                    <span className="font-medium">Automatic review reminders right before forgetting</span>
                  </label>
                  <label className="flex items-center gap-2 text-xs text-slate-800 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={autoQuizPrep}
                      onChange={(e) => setAutoQuizPrep(e.target.checked)}
                      className="w-3.5 h-3.5 rounded text-indigo-600"
                    />
                    <span className="font-medium">Automatically prepare active recall quizzes for due topics</span>
                  </label>
                  <label className="flex items-center gap-2 text-xs text-slate-800 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={autoExamRevision}
                      onChange={(e) => setAutoExamRevision(e.target.checked)}
                      className="w-3.5 h-3.5 rounded text-indigo-600"
                    />
                    <span className="font-medium">Generate exam-oriented revision schedules & date-sheet plans</span>
                  </label>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer Actions: Back / Continue / Finish Setup */}
        <div className="pt-6 border-t border-slate-100 flex items-center justify-between">
          <div>
            {step > 1 ? (
              <Button
                variant="outline"
                size="md"
                onClick={handleBack}
                disabled={saving}
                className="flex items-center gap-1.5"
              >
                <ArrowLeft className="w-4 h-4" />
                <span>Back</span>
              </Button>
            ) : onCancel ? (
              <Button
                variant="ghost"
                size="md"
                onClick={onCancel}
                className="text-xs text-slate-400"
              >
                Cancel
              </Button>
            ) : null}
          </div>

          <div className="flex items-center gap-2.5">
            {step < 5 ? (
              <Button
                variant="primary"
                size="md"
                onClick={validateAndNext}
                className="flex items-center gap-1.5 shadow-md shadow-indigo-600/25"
              >
                <span>Continue</span>
                <ArrowRight className="w-4 h-4" />
              </Button>
            ) : (
              <Button
                variant="primary"
                size="lg"
                onClick={handleFinishSetup}
                disabled={saving}
                className="flex items-center gap-2 bg-gradient-to-r from-emerald-600 to-indigo-600 hover:from-emerald-700 hover:to-indigo-700 text-white shadow-lg shadow-indigo-600/30"
              >
                {saving ? (
                  <>
                    <Sparkles className="w-4 h-4 animate-spin" />
                    <span>Configuring Workspace...</span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-5 h-5 text-emerald-200" />
                    <span>Finish Setup & Open Workspace</span>
                  </>
                )}
              </Button>
            )}
          </div>
        </div>
      </Card>
    </div>
  );
}
