"use client";

import React, { useState } from "react";
import {
  Brain,
  Mail,
  Lock,
  Eye,
  EyeOff,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  Zap,
  Info,
  CheckCircle2,
  Atom,
  Dna,
  BookOpen,
  Activity,
  Layers,
  HelpCircle,
  X
} from "lucide-react";
import { Button } from "./ui";
import { api } from "@/lib/api";

export interface AuthUser {
  id: string;
  name: string;
  email: string;
  role: string;
  target_exam?: string;
  onboarding_completed: boolean;
}

interface LoginPageProps {
  onLoginSuccess: (user: AuthUser) => void;
  onExploreDemo: () => void;
  onNavigateSignUp?: () => void;
}

interface ConceptNode {
  id: string;
  label: string;
  category: string;
  retention: number;
  x: number;
  y: number;
  color: string;
  glow: string;
}

export function LoginPage({
  onLoginSuccess,
  onExploreDemo,
  onNavigateSignUp
}: LoginPageProps) {
  // Form fields
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);

  // States
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showForgotModal, setShowForgotModal] = useState(false);
  const [hoveredNode, setHoveredNode] = useState<ConceptNode | null>(null);

  // Sign up mode toggle (if user clicks "Sign up")
  const [isSignUpMode, setIsSignUpMode] = useState(false);
  const [fullName, setFullName] = useState("");

  // Graph nodes for the interactive left illustration
  const graphNodes: ConceptNode[] = [
    {
      id: "memory",
      label: "Memory",
      category: "Cognitive",
      retention: 94,
      x: 180,
      y: 190,
      color: "#818cf8", // indigo
      glow: "rgba(129, 140, 248, 0.4)"
    },
    {
      id: "learning",
      label: "Learning",
      category: "Methodology",
      retention: 88,
      x: 340,
      y: 160,
      color: "#a855f7", // purple
      glow: "rgba(168, 85, 247, 0.4)"
    },
    {
      id: "physics",
      label: "Physics",
      category: "Sciences",
      retention: 76,
      x: 120,
      y: 330,
      color: "#38bdf8", // sky
      glow: "rgba(56, 189, 248, 0.4)"
    },
    {
      id: "chemistry",
      label: "Chemistry",
      category: "Sciences",
      retention: 92,
      x: 270,
      y: 310,
      color: "#34d399", // emerald
      glow: "rgba(52, 211, 153, 0.4)"
    },
    {
      id: "biology",
      label: "Biology",
      category: "Sciences",
      retention: 81,
      x: 410,
      y: 320,
      color: "#f43f5e", // rose
      glow: "rgba(244, 63, 94, 0.4)"
    },
    {
      id: "recall",
      label: "Active Recall",
      category: "Technique",
      retention: 96,
      x: 230,
      y: 80,
      color: "#fbbf24", // amber
      glow: "rgba(251, 191, 36, 0.4)"
    }
  ];

  // Edges connecting concepts
  const graphEdges = [
    { from: "memory", to: "learning" },
    { from: "memory", to: "physics" },
    { from: "memory", to: "chemistry" },
    { from: "learning", to: "biology" },
    { from: "chemistry", to: "biology" },
    { from: "recall", to: "memory" },
    { from: "recall", to: "learning" },
    { from: "physics", to: "chemistry" }
  ];

  const validateEmail = (val: string) => {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val.trim());
  };

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isLoading) return; // Prevent duplicate submissions

    setErrorMsg(null);

    // Form validations
    if (!email.trim()) {
      setErrorMsg("Please enter your email address.");
      return;
    }
    if (!validateEmail(email)) {
      setErrorMsg("Please enter a valid email address (e.g. alex@example.com).");
      return;
    }
    if (!password) {
      setErrorMsg("Please enter your password.");
      return;
    }
    if (password.length < 4) {
      setErrorMsg("Password must be at least 4 characters.");
      return;
    }

    if (isSignUpMode && !fullName.trim()) {
      setErrorMsg("Please enter your full name to create an account.");
      return;
    }

    setIsLoading(true);

    try {
      let res: any;
      if (isSignUpMode) {
        try {
          res = await api.register({
            email: email.trim(),
            password: password,
            name: fullName.trim()
          });
          localStorage.removeItem("humancache_onboarding_draft");
        } catch (regErr: any) {
          const errMsg = (regErr.message || "").toLowerCase();
          if (errMsg.includes("already exists")) {
            // User already registered! Try logging in automatically with the provided credentials
            try {
              res = await api.login({
                email: email.trim(),
                password: password
              });
            } catch {
              throw new Error("An account with this email already exists. Please switch to Log In with your password.");
            }
          } else {
            throw regErr;
          }
        }
      } else {
        res = await api.login({
          email: email.trim(),
          password: password
        });
      }

      const user: AuthUser = {
        id: res.user.id,
        name: res.user.name,
        email: res.user.email,
        role: res.user.role || "Learner",
        target_exam: res.user.target_exam || "",
        onboarding_completed: Boolean(res.user.onboarding_completed)
      };

      if (rememberMe) {
        localStorage.setItem("humancache_user", JSON.stringify(user));
      } else {
        sessionStorage.setItem("humancache_user", JSON.stringify(user));
      }

      onLoginSuccess(user);
    } catch (err: any) {
      setErrorMsg(err.message || "An unexpected authentication error occurred. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleDemoClick = async () => {
    if (isLoading) return;
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const res = await api.login({
        email: "demo@humancache.ai",
        password: "demouser123"
      });

      const demoUser: AuthUser = {
        id: res.user.id,
        name: res.user.name,
        email: res.user.email,
        role: "JEE & CBSE Track",
        target_exam: "JEE Advanced 2026",
        onboarding_completed: true
      };

      localStorage.setItem("humancache_user", JSON.stringify(demoUser));
      onLoginSuccess(demoUser);
    } catch (err: any) {
      // If demo user login encounters an issue, fallback to parent explore handler
      onExploreDemo();
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full bg-slate-950 text-slate-100 flex items-stretch font-sans select-none overflow-hidden relative">
      {/* Background radial atmosphere */}
      <div className="absolute top-0 left-0 w-full h-full bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(99,102,241,0.18),rgba(255,255,255,0))] pointer-events-none"></div>

      {/* Split Screen Layout Container */}
      <div className="w-full grid grid-cols-1 lg:grid-cols-12 min-h-screen relative z-10">
        {/* ========================================================= */}
        {/* LEFT SECTION: Brand Identity & Interactive Knowledge Graph */}
        {/* ========================================================= */}
        <div className="hidden lg:flex lg:col-span-7 bg-gradient-to-br from-slate-950 via-indigo-950/70 to-slate-900 border-r border-slate-800/80 p-12 flex-col justify-between relative overflow-hidden">
          {/* Subtle background grid pattern */}
          <div className="absolute inset-0 opacity-[0.07] pointer-events-none bg-[radial-gradient(#a5b4fc_1px,transparent_1px)] [background-size:24px_24px]"></div>

          {/* Top Brand Bar */}
          <div className="relative z-10 flex items-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-indigo-500 via-indigo-600 to-violet-500 flex items-center justify-center shadow-lg shadow-indigo-500/30 border border-indigo-400/40">
              <Brain className="w-6 h-6 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-2xl tracking-tight text-white">
                  Human Cache
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 font-semibold border border-indigo-500/30 uppercase tracking-wider">
                  AI Memory OS
                </span>
              </div>
              <p className="text-xs text-indigo-300/80 font-medium">Personal Cognitive Assistant</p>
            </div>
          </div>

          {/* Centerpiece: Knowledge Graph Illustration */}
          <div className="relative z-10 my-auto py-6 flex flex-col items-center">
            {/* Tagline & Short Description */}
            <div className="max-w-xl text-left w-full mb-6">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-400/20 text-indigo-300 text-xs font-semibold mb-3 backdrop-blur-xs">
                <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                <span>Active Knowledge Connectivity & Recall</span>
              </div>
              <h1 className="text-3xl xl:text-4xl font-extrabold tracking-tight text-white leading-tight">
                Your second brain. Your knowledge.{" "}
                <span className="bg-gradient-to-r from-indigo-400 via-violet-300 to-purple-400 bg-clip-text text-transparent">
                  Never forgotten.
                </span>
              </h1>
              <p className="text-sm text-slate-300/90 mt-2.5 leading-relaxed">
                Learn smarter, connect ideas, and remember what matters with your personal AI learning assistant.
              </p>
            </div>

            {/* Interactive Knowledge Graph SVG Canvas */}
            <div className="w-full max-w-lg h-[360px] bg-slate-900/60 rounded-3xl border border-indigo-500/20 backdrop-blur-md p-4 relative shadow-2xl shadow-indigo-950/50 flex items-center justify-center overflow-hidden">
              {/* Background Graph Ambient Rings */}
              <div className="absolute w-72 h-72 rounded-full border border-indigo-500/10 animate-pulse pointer-events-none"></div>
              <div className="absolute w-96 h-96 rounded-full border border-violet-500/5 pointer-events-none"></div>

              {/* SVG Link Lines */}
              <svg className="w-full h-full absolute inset-0 pointer-events-none">
                <defs>
                  <linearGradient id="edgeGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#6366f1" stopOpacity="0.4" />
                    <stop offset="100%" stopColor="#a855f7" stopOpacity="0.2" />
                  </linearGradient>
                </defs>
                {graphEdges.map((edge, idx) => {
                  const source = graphNodes.find((n) => n.id === edge.from);
                  const target = graphNodes.find((n) => n.id === edge.to);
                  if (!source || !target) return null;
                  const isHighlighted =
                    hoveredNode?.id === source.id || hoveredNode?.id === target.id;
                  return (
                    <line
                      key={idx}
                      x1={source.x}
                      y1={source.y}
                      x2={target.x}
                      y2={target.y}
                      stroke={isHighlighted ? "#818cf8" : "url(#edgeGrad)"}
                      strokeWidth={isHighlighted ? 2.5 : 1.5}
                      strokeDasharray={isHighlighted ? "none" : "3 3"}
                      className="transition-all duration-300"
                    />
                  );
                })}
              </svg>

              {/* Interactive Nodes */}
              {graphNodes.map((node) => {
                const isHovered = hoveredNode?.id === node.id;
                return (
                  <div
                    key={node.id}
                    onMouseEnter={() => setHoveredNode(node)}
                    onMouseLeave={() => setHoveredNode(null)}
                    style={{
                      left: `${node.x}px`,
                      top: `${node.y}px`,
                      transform: `translate(-50%, -50%) scale(${isHovered ? 1.15 : 1})`,
                      boxShadow: isHovered
                        ? `0 0 24px ${node.glow}`
                        : `0 0 12px ${node.glow}`
                    }}
                    className="absolute cursor-pointer transition-all duration-200 z-10 flex flex-col items-center group"
                  >
                    <div
                      style={{
                        backgroundColor: node.color,
                        borderColor: isHovered ? "#ffffff" : "rgba(255,255,255,0.3)"
                      }}
                      className="w-11 h-11 rounded-2xl flex items-center justify-center text-slate-950 font-bold border-2 shadow-lg transition-transform"
                    >
                      {node.id === "physics" ? (
                        <Atom className="w-5 h-5 text-slate-950" />
                      ) : node.id === "biology" ? (
                        <Dna className="w-5 h-5 text-slate-950" />
                      ) : node.id === "chemistry" ? (
                        <Layers className="w-5 h-5 text-slate-950" />
                      ) : node.id === "recall" ? (
                        <Zap className="w-5 h-5 text-slate-950" />
                      ) : (
                        <Brain className="w-5 h-5 text-slate-950" />
                      )}
                    </div>
                    <span className="text-[11px] font-bold text-slate-200 mt-1 bg-slate-950/80 px-2 py-0.5 rounded-md border border-slate-800 backdrop-blur-xs whitespace-nowrap">
                      {node.label}
                    </span>
                  </div>
                );
              })}

              {/* Node Inspection Tooltip pill */}
              <div className="absolute bottom-3 left-4 right-4 bg-slate-950/80 backdrop-blur-md rounded-xl p-2.5 border border-slate-800 flex items-center justify-between text-xs">
                {hoveredNode ? (
                  <>
                    <div className="flex items-center gap-2">
                      <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: hoveredNode.color }}></span>
                      <span className="font-semibold text-white">{hoveredNode.label}</span>
                      <span className="text-[10px] text-slate-400">({hoveredNode.category})</span>
                    </div>
                    <div className="flex items-center gap-1.5 font-bold text-emerald-400">
                      <span>{hoveredNode.retention}% Retained</span>
                      <span className="text-[10px] text-slate-400 font-normal">• Ebbinghaus Curve</span>
                    </div>
                  </>
                ) : (
                  <span className="text-slate-400 text-[11px] flex items-center gap-1.5 mx-auto">
                    <Info className="w-3.5 h-3.5 text-indigo-400" />
                    Hover any concept to inspect cognitive retention state
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Left Footer Badges */}
          <div className="relative z-10 flex items-center justify-between text-xs text-slate-400 pt-4 border-t border-slate-800/80">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>Adaptive Spaced Repetition Engine</span>
            </div>
            <div className="flex items-center gap-3">
              <span>Knowledge Graph</span>
              <span>•</span>
              <span>Persona AI Tutor</span>
              <span>•</span>
              <span>Memory Radar</span>
            </div>
          </div>
        </div>

        {/* ========================================================= */}
        {/* RIGHT SECTION: Professional AI Login Form                */}
        {/* ========================================================= */}
        <div className="lg:col-span-5 bg-white text-slate-900 p-8 sm:p-12 md:p-16 flex flex-col justify-between overflow-y-auto">
          {/* Mobile Header (Brand shown on small viewports) */}
          <div className="lg:hidden flex items-center gap-3 mb-8 pb-4 border-b border-slate-200">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-600 flex items-center justify-center shadow-md text-white">
              <Brain className="w-5 h-5" />
            </div>
            <div>
              <span className="font-bold text-lg text-slate-900">Human Cache</span>
              <p className="text-xs text-slate-500">Your second brain. Never forgotten.</p>
            </div>
          </div>

          {/* Form Container */}
          <div className="max-w-md w-full mx-auto my-auto space-y-7">
            {/* Headings */}
            <div className="space-y-1.5">
              <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900">
                {isSignUpMode ? "Create your account" : "Welcome back"}
              </h2>
              <p className="text-sm text-slate-500">
                {isSignUpMode
                  ? "Start capturing, understanding, and retaining knowledge."
                  : "Continue your learning journey."}
              </p>
            </div>

            {/* Error Message Alert */}
            {errorMsg && (
              <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs font-medium flex flex-col gap-2 animate-fadeIn">
                <div className="flex items-start gap-2.5">
                  <div className="w-2 h-2 rounded-full bg-rose-500 mt-1 shrink-0"></div>
                  <div className="flex-1 leading-relaxed">{errorMsg}</div>
                  <button
                    type="button"
                    onClick={() => setErrorMsg(null)}
                    className="text-rose-400 hover:text-rose-700 cursor-pointer"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
                {errorMsg.toLowerCase().includes("switch to log in") && (
                  <button
                    type="button"
                    onClick={() => {
                      setIsSignUpMode(false);
                      setErrorMsg(null);
                    }}
                    className="self-start text-[11px] font-bold text-indigo-700 hover:underline bg-indigo-50/80 hover:bg-indigo-100 px-2.5 py-1 rounded-lg border border-indigo-200 cursor-pointer"
                  >
                    Switch to Log In →
                  </button>
                )}
                {errorMsg.toLowerCase().includes("offline") && (
                  <button
                    type="button"
                    onClick={handleDemoClick}
                    className="self-start text-[11px] font-bold text-amber-700 hover:underline bg-amber-50/80 hover:bg-amber-100 px-2.5 py-1 rounded-lg border border-amber-200 cursor-pointer flex items-center gap-1"
                  >
                    ⚡ Explore with Demo Profile Instead →
                  </button>
                )}
              </div>
            )}

            {/* Login / Sign Up Form */}
            <form onSubmit={handleLoginSubmit} className="space-y-4">
              {/* Optional Full Name in Sign Up mode */}
              {isSignUpMode && (
                <div className="space-y-1.5">
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                    Full Name
                  </label>
                  <input
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="e.g. Alex Sharma"
                    disabled={isLoading}
                    className="w-full px-4 py-2.5 text-sm rounded-xl border border-slate-300 focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 transition-all bg-slate-50/50 hover:bg-white"
                  />
                </div>
              )}

              {/* Email Input */}
              <div className="space-y-1.5">
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-slate-400 absolute left-3.5 top-3.5 pointer-events-none" />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@domain.com"
                    autoComplete="email"
                    disabled={isLoading}
                    className="w-full pl-10 pr-4 py-2.5 text-sm rounded-xl border border-slate-300 focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 transition-all bg-slate-50/50 hover:bg-white"
                  />
                </div>
              </div>

              {/* Password Input */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                    Password
                  </label>
                  {!isSignUpMode && (
                    <button
                      type="button"
                      onClick={() => setShowForgotModal(true)}
                      className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 hover:underline cursor-pointer"
                    >
                      Forgot password?
                    </button>
                  )}
                </div>
                <div className="relative">
                  <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-3.5 pointer-events-none" />
                  <input
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    autoComplete={isSignUpMode ? "new-password" : "current-password"}
                    disabled={isLoading}
                    className="w-full pl-10 pr-11 py-2.5 text-sm rounded-xl border border-slate-300 focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 transition-all bg-slate-50/50 hover:bg-white"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    tabIndex={-1}
                    className="absolute right-3.5 top-3 text-slate-400 hover:text-slate-600 cursor-pointer p-0.5"
                    title={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? (
                      <EyeOff className="w-4 h-4" />
                    ) : (
                      <Eye className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </div>

              {/* Remember Me Checkbox */}
              <div className="flex items-center justify-between pt-1">
                <label className="flex items-center gap-2 text-xs font-medium text-slate-600 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    disabled={isLoading}
                    className="w-4 h-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 cursor-pointer"
                  />
                  <span>Remember me on this browser</span>
                </label>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-3 px-4 rounded-xl font-bold text-sm text-white bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-700 hover:to-violet-700 shadow-md shadow-indigo-600/25 transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-60 disabled:pointer-events-none active:scale-[0.99]"
              >
                {isLoading ? (
                  <>
                    <Sparkles className="w-4 h-4 animate-spin" />
                    <span>Signing in to Human Cache...</span>
                  </>
                ) : (
                  <>
                    <span>{isSignUpMode ? "Create Account" : "Log In"}</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>

            {/* Divider */}
            <div className="relative flex items-center justify-center">
              <div className="border-t border-slate-200 w-full"></div>
              <span className="bg-white px-3 text-[11px] font-semibold text-slate-400 uppercase tracking-wider relative">
                or
              </span>
            </div>

            {/* Explore Demo Button */}
            <div className="space-y-2">
              <button
                type="button"
                onClick={handleDemoClick}
                disabled={isLoading}
                className="w-full py-2.5 px-4 rounded-xl font-semibold text-xs text-indigo-700 bg-indigo-50 hover:bg-indigo-100/80 border border-indigo-200/90 transition-all flex items-center justify-center gap-2 cursor-pointer active:scale-[0.99] shadow-xs"
              >
                <Zap className="w-3.5 h-3.5 text-amber-500 fill-amber-500" />
                <span>Explore Demo (Instant Access with Pre-loaded Topics)</span>
              </button>
              <p className="text-[11px] text-center text-slate-400">
                Local-demo profile with pre-seeded Physics, Chemistry & Biology graphs.
              </p>
            </div>

            {/* Toggle Between Login & Sign Up */}
            <div className="text-center pt-2 text-xs text-slate-600">
              {isSignUpMode ? (
                <span>
                  Already have an account?{" "}
                  <button
                    type="button"
                    onClick={() => {
                      setIsSignUpMode(false);
                      setErrorMsg(null);
                    }}
                    className="font-bold text-indigo-600 hover:text-indigo-800 hover:underline cursor-pointer"
                  >
                    Log In
                  </button>
                </span>
              ) : (
                <span>
                  Don't have an account?{" "}
                  <button
                    type="button"
                    onClick={() => {
                      if (onNavigateSignUp) {
                        onNavigateSignUp();
                      } else {
                        setIsSignUpMode(true);
                        setErrorMsg(null);
                      }
                    }}
                    className="font-bold text-indigo-600 hover:text-indigo-800 hover:underline cursor-pointer"
                  >
                    Sign up
                  </button>
                </span>
              )}
            </div>
          </div>

          {/* Form Bottom Privacy & Info */}
          <div className="text-center text-[11px] text-slate-400 mt-8">
            Human Cache local instance • All memory states stored securely in local database
          </div>
        </div>
      </div>

      {/* Forgot Password Modal */}
      {showForgotModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white text-slate-900 rounded-2xl max-w-sm w-full p-6 shadow-2xl border border-slate-200 space-y-4 animate-fadeIn">
            <div className="flex items-center justify-between">
              <div className="w-9 h-9 rounded-xl bg-amber-100 flex items-center justify-center text-amber-700">
                <HelpCircle className="w-5 h-5" />
              </div>
              <button
                onClick={() => setShowForgotModal(false)}
                className="text-slate-400 hover:text-slate-600 cursor-pointer p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">Password Recovery Notice</h3>
              <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                This is a local demonstration prototype running on SQLite. Real remote email recovery is not configured.
              </p>
              <div className="mt-3 p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-700">
                <p className="font-semibold text-slate-800 mb-1">To access your workspace:</p>
                <ul className="list-disc pl-4 space-y-1 text-slate-600 text-[11px]">
                  <li>Click <strong>"Explore Demo"</strong> for instant full access.</li>
                  <li>Or enter any username and password (saved locally in your browser).</li>
                </ul>
              </div>
            </div>
            <Button
              variant="primary"
              size="sm"
              onClick={() => setShowForgotModal(false)}
              className="w-full justify-center"
            >
              Understood
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
