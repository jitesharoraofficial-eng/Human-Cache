"use client";

import React, { useState, useEffect } from "react";
import {
  Brain,
  LayoutDashboard,
  FolderUp,
  GraduationCap,
  Sparkles,
  CalendarDays,
  CreditCard,
  Network,
  Share2,
  FileText,
  LineChart,
  Bell,
  Settings,
  RefreshCw,
  LogOut,
  Sliders,
  Flame,
  UserCheck
} from "lucide-react";
import { api } from "@/lib/api";
import { AuthUser } from "./WelcomeAuthView";

export type NavTab =
  | "dashboard"
  | "uploads"
  | "learn"
  | "recall"
  | "exam"
  | "flashcards"
  | "mindmaps"
  | "graph"
  | "connectivity"
  | "notes"
  | "insights"
  | "notifications"
  | "settings";

interface ShellProps {
  currentTab: NavTab;
  onTabChange: (tab: NavTab) => void;
  user?: AuthUser | null;
  onLogout?: () => void;
  onLaunchOnboarding?: () => void;
  children: React.ReactNode;
}

export function AppShell({
  currentTab,
  onTabChange,
  user,
  onLogout,
  onLaunchOnboarding,
  children
}: ShellProps) {
  const [unreadNotifications, setUnreadNotifications] = useState<number>(0);
  const [streakDays, setStreakDays] = useState<number>(0);
  const [resetting, setResetting] = useState(false);

  useEffect(() => {
    loadHeaderStats();
  }, [user]);

  const loadHeaderStats = async () => {
    try {
      const [notifs, overview] = await Promise.allSettled([
        api.getNotifications(),
        api.getDashboardOverview()
      ]);
      if (notifs.status === "fulfilled" && Array.isArray(notifs.value)) {
        const unreadCount = notifs.value.filter((n: any) => !n.is_read).length;
        setUnreadNotifications(unreadCount);
      }
      if (overview.status === "fulfilled" && typeof overview.value.learning_streak_days === "number") {
        setStreakDays(overview.value.learning_streak_days);
      }
    } catch {
      // ignore
    }
  };

  const handleResetDemo = async () => {
    if (!confirm("Reset demo data to initial pristine demonstration state?")) return;
    setResetting(true);
    try {
      await api.resetDemo();
      window.location.reload();
    } catch (e: any) {
      alert("Error resetting: " + e.message);
    } finally {
      setResetting(false);
    }
  };

  const navItems = [
    { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
    { id: "uploads", label: "Categories & Uploads", icon: FolderUp },
    { id: "learn", label: "Learn (AI Tutor)", icon: GraduationCap },
    { id: "recall", label: "Recall & Quizzes", icon: Sparkles },
    { id: "exam", label: "Exam Tomorrow", icon: CalendarDays },
    { id: "flashcards", label: "Flashcards", icon: CreditCard },
    { id: "mindmaps", label: "Mind Maps", icon: Network },
    { id: "graph", label: "Knowledge Graph", icon: Share2 },
    { id: "connectivity", label: "Connectivity", icon: Network },
    { id: "notes", label: "Notes", icon: FileText },
    { id: "insights", label: "Memory Insights", icon: LineChart },
    { id: "notifications", label: "Notifications", icon: Bell, badge: unreadNotifications },
    { id: "settings", label: "Profile & Preferences", icon: Settings },
  ];

  const displayName = user?.name || "Alex Sharma";
  const displayRole = user?.role || "JEE & CBSE Track";
  const initials = displayName
    .split(" ")
    .map((n) => n[0])
    .join("")
    .slice(0, 2)
    .toUpperCase() || "HC";

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-50 font-sans text-slate-800">
      {/* Sidebar Navigation */}
      <aside className="w-64 bg-slate-900 text-slate-200 flex flex-col shrink-0 border-r border-slate-800 select-none">
        {/* Brand */}
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center shadow-lg shadow-indigo-500/30">
              <Brain className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-bold text-base tracking-tight text-white flex items-center gap-1.5">
                Human Cache
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-mono border border-indigo-500/30">
                  AI OS
                </span>
              </h1>
              <p className="text-[10px] text-slate-400">Proactive Learning Assistant</p>
            </div>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="flex-1 overflow-y-auto px-3 py-3 space-y-0.5">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onTabChange(item.id as NavTab)}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs sm:text-sm font-medium transition-all cursor-pointer ${
                  isActive
                    ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30 font-semibold"
                    : "text-slate-400 hover:text-slate-100 hover:bg-slate-800/60"
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <Icon className={`w-4 h-4 ${isActive ? "text-white" : "text-slate-400"}`} />
                  <span>{item.label}</span>
                </div>
                {item.badge ? (
                  <span
                    className={`text-[10px] px-1.5 py-0.2 rounded-full font-bold ${
                      isActive ? "bg-white text-indigo-600" : "bg-rose-500 text-white"
                    }`}
                  >
                    {item.badge}
                  </span>
                ) : null}
              </button>
            );
          })}
        </nav>

        {/* User Card & Actions Footer */}
        <div className="p-3 border-t border-slate-800 bg-slate-950/50 space-y-2">
          {/* Active Profile Pill */}
          <div className="bg-slate-800/90 rounded-xl p-2.5 flex items-center justify-between text-xs">
            <div
              onClick={() => onTabChange("settings")}
              className="flex items-center gap-2 overflow-hidden cursor-pointer flex-1 mr-2"
              title="Open Profile Settings"
            >
              <div className="w-7 h-7 rounded-lg bg-indigo-500/30 border border-indigo-400/30 flex items-center justify-center font-bold text-indigo-300 text-xs shrink-0">
                {initials}
              </div>
              <div className="overflow-hidden">
                <p className="text-white font-medium text-xs truncate">{displayName}</p>
                <p className="text-slate-400 text-[10px] truncate">{displayRole}</p>
              </div>
            </div>

            {/* Logout button */}
            {onLogout && (
              <button
                onClick={onLogout}
                title="Log Out & Switch User"
                className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-950/30 transition-colors cursor-pointer shrink-0"
              >
                <LogOut className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Quick controls row */}
          <div className="flex items-center justify-between text-[11px] px-1 text-slate-400">
            {onLaunchOnboarding && (
              <button
                onClick={onLaunchOnboarding}
                className="hover:text-indigo-300 flex items-center gap-1 cursor-pointer transition-colors"
                title="Re-run 5-step personalization onboarding"
              >
                <Sliders className="w-3 h-3 text-indigo-400" />
                <span>Onboarding</span>
              </button>
            )}

            <button
              onClick={handleResetDemo}
              disabled={resetting}
              title="Reset Database to Default State"
              className="hover:text-slate-200 text-slate-400 flex items-center gap-1 cursor-pointer transition-colors ml-auto"
            >
              <RefreshCw className={`w-3 h-3 ${resetting ? "animate-spin" : ""}`} />
              <span>Reset Data</span>
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col h-full overflow-hidden">
        {/* Top Header Bar */}
        <header className="h-14 border-b border-slate-200/90 bg-white/95 backdrop-blur-xs px-6 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <h2 className="font-bold text-slate-900 text-sm capitalize">
              {navItems.find((n) => n.id === currentTab)?.label}
            </h2>
            <span className="text-xs text-slate-300">|</span>
            <div className="hidden lg:flex items-center gap-1.5 text-xs text-slate-500 font-mono">
              <span>CAPTURE</span>
              <span className="text-slate-300">→</span>
              <span>EXTRACT</span>
              <span className="text-slate-300">→</span>
              <span>CONNECT</span>
              <span className="text-slate-300">→</span>
              <span>LEARN</span>
              <span className="text-slate-300">→</span>
              <span>RECALL</span>
              <span className="text-slate-300">→</span>
              <span className="text-indigo-600 font-bold">REVISE</span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-amber-700 bg-amber-50 px-3 py-1 rounded-full border border-amber-200/80 shadow-xs">
              <Flame className="w-3.5 h-3.5 text-amber-500 fill-amber-500" />
              <span>{streakDays} Day Streak</span>
            </div>

            <button
              onClick={() => onTabChange("notifications")}
              className="relative p-2 rounded-xl text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer border border-transparent hover:border-slate-200"
              title="Notifications"
            >
              <Bell className="w-4 h-4" />
              {unreadNotifications > 0 && (
                <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-rose-500"></span>
              )}
            </button>
          </div>
        </header>

        {/* Viewport content */}
        <div className="flex-1 overflow-y-auto p-6 bg-slate-50/70">
          {children}
        </div>
      </main>
    </div>
  );
}
