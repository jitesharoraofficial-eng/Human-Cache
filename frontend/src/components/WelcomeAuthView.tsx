"use client";

import React, { useState } from "react";
import {
  Brain,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  Lock,
  Mail,
  User,
  GraduationCap,
  Network,
  Activity,
  Flame,
  Zap,
  BookOpen,
  Calendar,
  Layers,
  ChevronRight
} from "lucide-react";
import { Card, Button, Badge } from "./ui";

export interface AuthUser {
  id: string;
  name: string;
  email: string;
  role: string;
  target_exam?: string;
  onboarding_completed: boolean;
}

interface WelcomeAuthViewProps {
  onLoginSuccess: (user: AuthUser, needsOnboarding: boolean) => void;
}

export function WelcomeAuthView({ onLoginSuccess }: WelcomeAuthViewProps) {
  const [authMode, setAuthMode] = useState<"welcome" | "login" | "signup">("welcome");
  const [activePreviewTab, setActivePreviewTab] = useState<"radar" | "graph" | "tutor">("radar");

  // Form states
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [loading, setLoading] = useState(false);

  // Preset demo personas for immediate one-click testing
  const demoProfiles: AuthUser[] = [
    {
      id: "demo-aarav",
      name: "Alex Sharma",
      email: "alex.sharma@study.edu",
      role: "JEE & CBSE Aspirant",
      target_exam: "JEE Advanced 2026",
      onboarding_completed: true
    },
    {
      id: "demo-priya",
      name: "Dr. Priya Patel",
      email: "priya.patel@med.edu",
      role: "Medical / NEET Aspirant",
      target_exam: "NEET UG",
      onboarding_completed: true
    },
    {
      id: "demo-david",
      name: "David Miller",
      email: "david.miller@techcorp.io",
      role: "Software Professional",
      target_exam: "System Architecture",
      onboarding_completed: true
    }
  ];

  const handleQuickDemoLogin = (profile: AuthUser) => {
    localStorage.setItem("humancache_user", JSON.stringify(profile));
    onLoginSuccess(profile, false);
  };

  const handleNewStudentStart = () => {
    const newUser: AuthUser = {
      id: "user-" + Date.now(),
      name: "New Student",
      email: "learner@humancache.ai",
      role: "Student",
      onboarding_completed: false
    };
    localStorage.setItem("humancache_user", JSON.stringify(newUser));
    onLoginSuccess(newUser, true);
  };

  const handleLoginSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg("");

    if (!email.trim()) {
      setErrorMsg("Please enter your email or username");
      return;
    }
    if (!password) {
      setErrorMsg("Please enter your password");
      return;
    }

    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      // Demo authentication lookup or create
      const existingStr = localStorage.getItem("humancache_user");
      let user: AuthUser;
      if (existingStr) {
        try {
          user = JSON.parse(existingStr);
          user.email = email;
        } catch {
          user = {
            id: "user-" + Date.now(),
            name: email.split("@")[0] || "Learner",
            email,
            role: "Lifelong Learner",
            onboarding_completed: true
          };
        }
      } else {
        user = {
          id: "user-" + Date.now(),
          name: email.split("@")[0] || "Learner",
          email,
          role: "Lifelong Learner",
          onboarding_completed: true
        };
      }

      localStorage.setItem("humancache_user", JSON.stringify(user));
      onLoginSuccess(user, !user.onboarding_completed);
    }, 400);
  };

  const handleSignupSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg("");

    if (!name.trim()) {
      setErrorMsg("Please enter your full name");
      return;
    }
    if (!email.trim() || !email.includes("@")) {
      setErrorMsg("Please enter a valid email address");
      return;
    }
    if (password.length < 4) {
      setErrorMsg("Password must be at least 4 characters long");
      return;
    }
    if (password !== confirmPassword) {
      setErrorMsg("Passwords do not match");
      return;
    }

    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      const newUser: AuthUser = {
        id: "user-" + Date.now(),
        name: name.trim(),
        email: email.trim(),
        role: "New Learner",
        onboarding_completed: false
      };
      localStorage.setItem("humancache_user", JSON.stringify(newUser));
      // Newly registered users always go through onboarding!
      onLoginSuccess(newUser, true);
    }, 450);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 via-indigo-50/20 to-slate-100 text-slate-800 flex flex-col font-sans">
      {/* Top Navbar */}
      <header className="w-full max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center shadow-lg shadow-indigo-500/25 border border-indigo-400/40">
            <Brain className="w-5 h-5 text-white" />
          </div>
          <div>
            <span className="font-bold text-lg tracking-tight text-slate-900 flex items-center gap-2">
              Human Cache
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-700 font-semibold border border-indigo-200">
                Cognitive OS
              </span>
            </span>
            <p className="text-[11px] text-slate-500 hidden sm:block">Proactive Personal Memory & Learning Engine</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setAuthMode("login");
              setErrorMsg("");
            }}
          >
            Log In
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={() => {
              setAuthMode("signup");
              setErrorMsg("");
            }}
          >
            Create Account
          </Button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl mx-auto px-6 py-8 flex flex-col justify-center">
        {authMode === "welcome" ? (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
            {/* Left Column: Hero & Value Proposition */}
            <div className="lg:col-span-7 space-y-6">
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-indigo-50 border border-indigo-200/80 text-indigo-700 text-xs font-semibold shadow-xs">
                <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
                <span>Next-Gen Active Recall & Spaced Repetition</span>
              </div>

              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-slate-900 leading-[1.12]">
                Never Forget What You Learn.{" "}
                <span className="bg-gradient-to-r from-indigo-600 via-violet-600 to-indigo-800 bg-clip-text text-transparent">
                  Automated by AI.
                </span>
              </h1>

              <p className="text-base sm:text-lg text-slate-600 max-w-2xl leading-relaxed">
                Human Cache turns your raw study notes, textbooks, and exam syllabi into an interactive
                personal second brain. It extracts concepts, connects knowledge graphs, prepares daily recall drills,
                and schedules revisions <strong className="text-slate-800">right before you forget</strong>.
              </p>

              {/* Action Buttons */}
              <div className="flex flex-wrap items-center gap-3 pt-2">
                <Button
                  size="lg"
                  variant="primary"
                  onClick={handleNewStudentStart}
                  className="shadow-lg shadow-indigo-600/30 text-base"
                >
                  Get Started Free
                  <ArrowRight className="w-4 h-4 ml-1" />
                </Button>

                <Button
                  size="lg"
                  variant="outline"
                  onClick={() => setAuthMode("login")}
                  className="bg-white/80"
                >
                  Sign In to Workspace
                </Button>
              </div>

              {/* Feature Highlights Pills */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-4 border-t border-slate-200/80">
                <div className="flex items-center gap-2 text-xs font-medium text-slate-700">
                  <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                  <span>Ebbinghaus Memory Radar</span>
                </div>
                <div className="flex items-center gap-2 text-xs font-medium text-slate-700">
                  <CheckCircle2 className="w-4 h-4 text-indigo-500 shrink-0" />
                  <span>Multi-Persona AI Tutor</span>
                </div>
                <div className="flex items-center gap-2 text-xs font-medium text-slate-700">
                  <CheckCircle2 className="w-4 h-4 text-violet-500 shrink-0" />
                  <span>Syllabus & Exam Planner</span>
                </div>
              </div>

              {/* Instant 1-Click Demo Profiles */}
              <div className="clay-card-tint p-4 rounded-2xl border border-indigo-100">
                <div className="flex items-center justify-between mb-2.5">
                  <span className="text-xs font-bold text-slate-700 flex items-center gap-1.5 uppercase tracking-wider">
                    <Zap className="w-3.5 h-3.5 text-amber-500" />
                    Instant Demo Profiles (Click to test):
                  </span>
                  <span className="text-[11px] text-slate-500">Pre-seeded with real study materials</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                  {demoProfiles.map((p) => (
                    <button
                      key={p.id}
                      onClick={() => handleQuickDemoLogin(p)}
                      className="p-3 rounded-xl bg-white border border-slate-200/90 hover:border-indigo-300 hover:shadow-md transition-all text-left group cursor-pointer"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-xs text-slate-900 group-hover:text-indigo-600">
                          {p.name}
                        </span>
                        <ChevronRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-indigo-600 transition-transform group-hover:translate-x-0.5" />
                      </div>
                      <p className="text-[11px] text-slate-500 mt-0.5 truncate">{p.role}</p>
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Right Column: Interactive Workspace Preview Card */}
            <div className="lg:col-span-5">
              <div className="clay-card p-6 bg-white/95 border border-slate-200 shadow-xl rounded-3xl relative overflow-hidden">
                {/* Preview Navigation Tabs */}
                <div className="flex items-center justify-between border-b border-slate-100 pb-4 mb-4">
                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={() => setActivePreviewTab("radar")}
                      className={`px-3 py-1.5 rounded-lg text-xs font-semibold cursor-pointer transition-all ${
                        activePreviewTab === "radar"
                          ? "bg-indigo-600 text-white shadow-xs"
                          : "text-slate-600 hover:bg-slate-100"
                      }`}
                    >
                      Memory Radar
                    </button>
                    <button
                      onClick={() => setActivePreviewTab("graph")}
                      className={`px-3 py-1.5 rounded-lg text-xs font-semibold cursor-pointer transition-all ${
                        activePreviewTab === "graph"
                          ? "bg-indigo-600 text-white shadow-xs"
                          : "text-slate-600 hover:bg-slate-100"
                      }`}
                    >
                      Knowledge Graph
                    </button>
                    <button
                      onClick={() => setActivePreviewTab("tutor")}
                      className={`px-3 py-1.5 rounded-lg text-xs font-semibold cursor-pointer transition-all ${
                        activePreviewTab === "tutor"
                          ? "bg-indigo-600 text-white shadow-xs"
                          : "text-slate-600 hover:bg-slate-100"
                      }`}
                    >
                      Persona Tutor
                    </button>
                  </div>
                  <Badge variant="purple" className="text-[10px]">Live Simulation</Badge>
                </div>

                {/* Tab 1: Memory Radar Simulation */}
                {activePreviewTab === "radar" && (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between text-xs text-slate-500">
                      <span>Retention Decay Curve (Ebbinghaus)</span>
                      <span className="font-semibold text-emerald-600">82% Avg Stability</span>
                    </div>

                    <div className="space-y-2.5">
                      <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-between">
                        <div>
                          <p className="font-semibold text-xs text-slate-900">Chemical Bonding & VSEPR</p>
                          <p className="text-[11px] text-slate-500">4 days since last recall • Interval: 7d</p>
                        </div>
                        <div className="text-right">
                          <span className="text-xs font-bold text-emerald-600">92%</span>
                          <span className="block text-[10px] text-emerald-500">Stable</span>
                        </div>
                      </div>

                      <div className="p-3 rounded-xl bg-amber-50/50 border border-amber-100 flex items-center justify-between">
                        <div>
                          <p className="font-semibold text-xs text-slate-900">Newton's Laws of Motion</p>
                          <p className="text-[11px] text-amber-700">Review due in 12 hours</p>
                        </div>
                        <div className="text-right">
                          <span className="text-xs font-bold text-amber-600">68%</span>
                          <span className="block text-[10px] text-amber-600">Review Due</span>
                        </div>
                      </div>

                      <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-between">
                        <div>
                          <p className="font-semibold text-xs text-slate-900">Thermodynamics: Entropy</p>
                          <p className="text-[11px] text-slate-500">1 day since last recall • Interval: 3d</p>
                        </div>
                        <div className="text-right">
                          <span className="text-xs font-bold text-indigo-600">86%</span>
                          <span className="block text-[10px] text-indigo-500">Strengthening</span>
                        </div>
                      </div>
                    </div>

                    <div className="p-3 rounded-xl bg-indigo-50/60 border border-indigo-100 text-xs text-indigo-900 flex items-start gap-2.5">
                      <Sparkles className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" />
                      <div>
                        <span className="font-semibold">Proactive Memory Trigger:</span>
                        <p className="text-[11px] text-indigo-700 mt-0.5">
                          "You're about to forget Newton's 2nd Law derivation before tomorrow's test. Recommended 3-minute active recall drill."
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Tab 2: Knowledge Graph Preview */}
                {activePreviewTab === "graph" && (
                  <div className="space-y-4">
                    <div className="h-44 rounded-2xl bg-gradient-to-tr from-slate-900 via-indigo-950 to-slate-900 p-4 text-white flex flex-col justify-between relative overflow-hidden">
                      <div className="absolute inset-0 opacity-20 pointer-events-none bg-[radial-gradient(#818cf8_1px,transparent_1px)] [background-size:16px_16px]"></div>
                      <div className="flex items-center justify-between relative z-10">
                        <span className="text-xs font-semibold text-indigo-300">Semantic Web View</span>
                        <span className="text-[10px] bg-indigo-500/30 px-2 py-0.5 rounded-full border border-indigo-400/40">12 Connected Nodes</span>
                      </div>
                      <div className="flex items-center justify-around py-2 relative z-10">
                        <div className="text-center">
                          <div className="w-10 h-10 rounded-full bg-indigo-600 flex items-center justify-center font-bold text-xs mx-auto shadow-lg shadow-indigo-500/50">
                            Bonding
                          </div>
                          <span className="text-[10px] text-slate-300 mt-1 block">Chemistry</span>
                        </div>
                        <div className="h-[2px] w-12 bg-indigo-500/50"></div>
                        <div className="text-center">
                          <div className="w-10 h-10 rounded-full bg-violet-600 flex items-center justify-center font-bold text-xs mx-auto shadow-lg shadow-violet-500/50">
                            VSEPR
                          </div>
                          <span className="text-[10px] text-slate-300 mt-1 block">Geometry</span>
                        </div>
                        <div className="h-[2px] w-12 bg-indigo-500/50"></div>
                        <div className="text-center">
                          <div className="w-10 h-10 rounded-full bg-emerald-600 flex items-center justify-center font-bold text-xs mx-auto shadow-lg shadow-emerald-500/50">
                            Dipole
                          </div>
                          <span className="text-[10px] text-slate-300 mt-1 block">Forces</span>
                        </div>
                      </div>
                      <div className="text-[11px] text-slate-400 text-center relative z-10">
                        Cross-disciplinary concept links extracted automatically from documents
                      </div>
                    </div>
                  </div>
                )}

                {/* Tab 3: Persona Tutor Preview */}
                {activePreviewTab === "tutor" && (
                  <div className="space-y-3">
                    <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                      <div className="flex items-center gap-2 mb-1">
                        <Badge variant="purple">JEE Aspirant Mode</Badge>
                        <span className="text-[11px] text-slate-500">Rigorous & Exam-Focused</span>
                      </div>
                      <p className="text-xs text-slate-700 italic">
                        "For JEE, beware the classic trap: bond angles deviate when lone pairs occupy equatorial positions in trigonal bipyramidal geometry..."
                      </p>
                    </div>

                    <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                      <div className="flex items-center gap-2 mb-1">
                        <Badge variant="success">Beginner / Lifelong Mode</Badge>
                        <span className="text-[11px] text-slate-500">Intuitive & Conceptual</span>
                      </div>
                      <p className="text-xs text-slate-700 italic">
                        "Think of electron pairs like balloons tied together at their nozzles — they push each other away until they find maximum space..."
                      </p>
                    </div>
                  </div>
                )}

                {/* Card footer CTA */}
                <div className="mt-5 pt-4 border-t border-slate-100 flex items-center justify-between">
                  <span className="text-xs text-slate-500">Ready to personalize your memory engine?</span>
                  <Button size="sm" variant="primary" onClick={handleNewStudentStart}>
                    Start Setup <ChevronRight className="w-3.5 h-3.5" />
                  </Button>
                </div>
              </div>
            </div>
          </div>
        ) : (
          /* Authentication Modals (Login / Signup) */
          <div className="max-w-md mx-auto w-full">
            <Card className="p-8 shadow-2xl border-slate-200">
              {/* Header */}
              <div className="text-center mb-6">
                <div className="w-12 h-12 rounded-2xl bg-indigo-600 flex items-center justify-center mx-auto mb-3 shadow-lg shadow-indigo-600/30 text-white">
                  <Brain className="w-6 h-6" />
                </div>
                <h2 className="text-2xl font-bold text-slate-900">
                  {authMode === "login" ? "Welcome Back" : "Create Your Account"}
                </h2>
                <p className="text-xs text-slate-500 mt-1">
                  {authMode === "login"
                    ? "Enter your credentials to access your personalized learning workspace"
                    : "Set up your profile to activate your proactive AI second brain"}
                </p>
              </div>

              {/* Error Alert */}
              {errorMsg && (
                <div className="mb-4 p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs font-medium flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-rose-500"></div>
                  <span>{errorMsg}</span>
                </div>
              )}

              {/* Form */}
              <form onSubmit={authMode === "login" ? handleLoginSubmit : handleSignupSubmit} className="space-y-4">
                {authMode === "signup" && (
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">Full Name</label>
                    <div className="relative">
                      <User className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                      <input
                        type="text"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        placeholder="e.g. Alex Sharma"
                        className="w-full pl-9 pr-3 py-2 text-sm rounded-xl border border-slate-200 focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                      />
                    </div>
                  </div>
                )}

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Email Address</label>
                  <div className="relative">
                    <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="you@domain.com"
                      className="w-full pl-9 pr-3 py-2 text-sm rounded-xl border border-slate-200 focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Password</label>
                  <div className="relative">
                    <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                    <input
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      className="w-full pl-9 pr-3 py-2 text-sm rounded-xl border border-slate-200 focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                    />
                  </div>
                </div>

                {authMode === "signup" && (
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">Confirm Password</label>
                    <div className="relative">
                      <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                      <input
                        type="password"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        placeholder="••••••••"
                        className="w-full pl-9 pr-3 py-2 text-sm rounded-xl border border-slate-200 focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                      />
                    </div>
                  </div>
                )}

                <Button
                  type="submit"
                  variant="primary"
                  size="md"
                  disabled={loading}
                  className="w-full justify-center shadow-md shadow-indigo-600/25 mt-2"
                >
                  {loading ? (
                    <Sparkles className="w-4 h-4 animate-spin" />
                  ) : authMode === "login" ? (
                    "Sign In to Dashboard"
                  ) : (
                    "Continue to Learning Onboarding"
                  )}
                </Button>
              </form>

              {/* Mode switch */}
              <div className="mt-5 text-center text-xs text-slate-500">
                {authMode === "login" ? (
                  <span>
                    Don't have an account yet?{" "}
                    <button
                      onClick={() => {
                        setAuthMode("signup");
                        setErrorMsg("");
                      }}
                      className="text-indigo-600 font-semibold hover:underline cursor-pointer"
                    >
                      Create one now
                    </button>
                  </span>
                ) : (
                  <span>
                    Already have an account?{" "}
                    <button
                      onClick={() => {
                        setAuthMode("login");
                        setErrorMsg("");
                      }}
                      className="text-indigo-600 font-semibold hover:underline cursor-pointer"
                    >
                      Sign In
                    </button>
                  </span>
                )}
              </div>

              {/* Back to landing */}
              <div className="mt-4 pt-4 border-t border-slate-100 text-center">
                <button
                  onClick={() => {
                    setAuthMode("welcome");
                    setErrorMsg("");
                  }}
                  className="text-xs text-slate-400 hover:text-slate-600 cursor-pointer"
                >
                  ← Return to Human Cache Overview
                </button>
              </div>
            </Card>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="w-full max-w-7xl mx-auto px-6 py-6 border-t border-slate-200/80 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 gap-3">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-600" />
          <span>Local-Demo Mode — User profiles & memory states safely preserved locally.</span>
        </div>
        <div className="flex items-center gap-4">
          <span>Active Recall Engine</span>
          <span>•</span>
          <span>Knowledge Graph</span>
          <span>•</span>
          <span>Spaced Repetition</span>
        </div>
      </footer>
    </div>
  );
}
