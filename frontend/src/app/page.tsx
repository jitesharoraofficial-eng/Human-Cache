"use client";

import React, { useState, useEffect } from "react";
import { AppShell, NavTab } from "@/components/AppShell";
import { DashboardView } from "@/components/DashboardView";
import { UploadsView } from "@/components/UploadsView";
import { LearnView } from "@/components/LearnView";
import { RecallView } from "@/components/RecallView";
import { ExamView } from "@/components/ExamView";
import { FlashcardsView } from "@/components/FlashcardsView";
import { MindMapsView } from "@/components/MindMapsView";
import { KnowledgeGraphView } from "@/components/KnowledgeGraphView";
import { ConnectivityView } from "@/components/ConnectivityView";
import { NotesView } from "@/components/NotesView";
import { InsightsView } from "@/components/InsightsView";
import { NotificationsView } from "@/components/NotificationsView";
import { SettingsView } from "@/components/SettingsView";
import { PersistentAITutor } from "@/components/PersistentAITutor";
import { LoginPage, AuthUser } from "@/components/LoginPage";
import { OnboardingWizard } from "@/components/OnboardingWizard";
import { NotificationToast, ToastNotification } from "@/components/NotificationToast";
import { api } from "@/lib/api";

export default function Home() {
  const [currentTab, setCurrentTab] = useState<NavTab>("dashboard");
  const [authState, setAuthState] = useState<"login" | "onboarding" | "authenticated">("login");
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [isSessionChecking, setIsSessionChecking] = useState(true);
  const [activeToast, setActiveToast] = useState<ToastNotification | null>(null);
  const [graphFocus, setGraphFocus] = useState<{ topicId?: string; targetTopicId?: string; relId?: string } | null>(null);
  const [selectedLearnTopicId, setSelectedLearnTopicId] = useState<string | null>(null);

  useEffect(() => {
    // Validate session with backend via HttpOnly cookie
    let isMounted = true;
    api.getAuthMe()
      .then((user: any) => {
        if (!isMounted) return;
        const mappedUser: AuthUser = {
          id: user.id,
          name: user.name,
          email: user.email,
          role: user.role || "Learner",
          target_exam: user.target_exam || "",
          onboarding_completed: Boolean(user.onboarding_completed),
        };
        setAuthUser(mappedUser);
        localStorage.setItem("humancache_user", JSON.stringify(mappedUser));
        if (mappedUser.onboarding_completed) {
          setAuthState("authenticated");
        } else {
          setAuthState("onboarding");
        }
      })
      .catch(() => {
        if (!isMounted) return;
        // Session invalid or not logged in
        localStorage.removeItem("humancache_user");
        sessionStorage.removeItem("humancache_user");
        setAuthUser(null);
        setAuthState("login");
      })
      .finally(() => {
        if (isMounted) setIsSessionChecking(false);
      });

    // Check for PWA share_target parameters in URL query
    if (typeof window !== "undefined") {
      const urlParams = new URLSearchParams(window.location.search);
      const sharedTitle = urlParams.get("share_title") || urlParams.get("title");
      const sharedText = urlParams.get("share_text") || urlParams.get("text");
      const sharedUrl = urlParams.get("share_url") || urlParams.get("url");

      if (sharedUrl || sharedText) {
        // Switch to uploads tab to present capture workflow
        setCurrentTab("uploads");
        // Store incoming share in sessionStorage for UploadsView
        sessionStorage.setItem("humancache_incoming_share", JSON.stringify({
          title: sharedTitle || "",
          text: sharedText || "",
          url: sharedUrl || ""
        }));
        // Clean URL params without reloading page
        window.history.replaceState({}, document.title, window.location.pathname);
      }
    }

    return () => {
      isMounted = false;
    };
  }, []);

  // Proactive Memory Coach: periodically check for unread review alerts when authenticated
  useEffect(() => {
    if (authState !== "authenticated") return;

    let isMounted = true;
    const checkProactiveCoach = async () => {
      try {
        const notifs = await api.getNotifications();
        if (!isMounted || !Array.isArray(notifs)) return;

        // Retrieve session-dismissed toast IDs to prevent duplicate pop-up annoyance
        let dismissedIds: string[] = [];
        try {
          const raw = sessionStorage.getItem("humancache_dismissed_toast_ids");
          if (raw) dismissedIds = JSON.parse(raw);
        } catch {
          // ignore session storage read errors
        }

        // Priority weighting: urgent > high > normal > low
        const priorityWeight: Record<string, number> = { urgent: 4, high: 3, normal: 2, low: 1 };

        // Filter for eligible unread, active notifications not dismissed in this session
        const eligible = notifs
          .filter((n: any) =>
            !n.is_read &&
            !n.is_dismissed &&
            !n.is_snoozed &&
            (!n.action_state || n.action_state === "active" || n.action_state === "pending") &&
            !dismissedIds.includes(n.id)
          )
          .sort((a: any, b: any) => {
            const pA = priorityWeight[a.priority?.toLowerCase() || "normal"] || 2;
            const pB = priorityWeight[b.priority?.toLowerCase() || "normal"] || 2;
            if (pA !== pB) return pB - pA;
            return new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime();
          });

        const pending = eligible[0];
        if (pending && (!activeToast || activeToast.id !== pending.id)) {
          setActiveToast({
            id: pending.id,
            title: pending.title,
            message: pending.message,
            notification_type: pending.notification_type,
            topic_id: pending.topic_id,
            action_url: pending.action_url,
            priority: pending.priority,
          });
        }
      } catch {
        // ignore
      }
    };

    // Check after short delay on mount, then every 30s
    const timeout = setTimeout(checkProactiveCoach, 2500);
    const interval = setInterval(checkProactiveCoach, 30000);

    return () => {
      isMounted = false;
      clearTimeout(timeout);
      clearInterval(interval);
    };
  }, [authState, activeToast]);


  const handleLoginSuccess = (user: AuthUser) => {
    setAuthUser(user);
    localStorage.setItem("humancache_user", JSON.stringify(user));
    if (user.onboarding_completed) {
      setAuthState("authenticated");
    } else {
      setAuthState("onboarding");
    }
  };

  const handleExploreDemo = async () => {
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
      setAuthUser(demoUser);
      setAuthState("authenticated");
    } catch (e) {
      console.warn("Backend login failed, proceeding with offline demo profile:", e);
      const fallbackDemoUser: AuthUser = {
        id: "demo-user-master-id",
        name: "Alex Sharma",
        email: "alex.learner@humancache.ai",
        role: "JEE & CBSE Track",
        target_exam: "JEE Advanced 2026",
        onboarding_completed: true
      };
      localStorage.setItem("humancache_user", JSON.stringify(fallbackDemoUser));
      setAuthUser(fallbackDemoUser);
      setAuthState("authenticated");
    }
  };

  const handleOnboardingComplete = () => {
    if (authUser) {
      const updatedUser: AuthUser = { ...authUser, onboarding_completed: true };
      setAuthUser(updatedUser);
      localStorage.setItem("humancache_user", JSON.stringify(updatedUser));
    }
    setAuthState("authenticated");
  };

  const handleLogout = async () => {
    try {
      await api.logout();
    } catch {
      // ignore
    }
    if (authUser?.id) {
      localStorage.removeItem(`humancache_onboarding_draft_${authUser.id}`);
    }
    localStorage.removeItem("humancache_onboarding_draft");
    localStorage.removeItem("humancache_user");
    sessionStorage.removeItem("humancache_user");
    setAuthUser(null);
    setAuthState("login");
    setCurrentTab("dashboard");
  };

  // 1. Display Login Page when unauthenticated
  if (authState === "login") {
    return (
      <LoginPage
        onLoginSuccess={handleLoginSuccess}
        onExploreDemo={handleExploreDemo}
      />
    );
  }

  // 2. Display Onboarding Wizard after first login or incomplete onboarding
  if (authState === "onboarding") {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-indigo-950 to-slate-900 flex items-center justify-center p-4">
        <OnboardingWizard
          onComplete={handleOnboardingComplete}
          onCancel={() => {
            if (authUser?.onboarding_completed) {
              setAuthState("authenticated");
            }
          }}
        />
      </div>
    );
  }

  // 3. Authenticated User Workspace
  const renderContent = () => {
    switch (currentTab) {
      case "dashboard":
        return <DashboardView onNavigate={(tab) => setCurrentTab(tab as NavTab)} />;
      case "uploads":
        return (
          <UploadsView
            onLearnTopic={(topicOrDocId) => {
              if (topicOrDocId) setSelectedLearnTopicId(topicOrDocId);
              setCurrentTab("learn");
            }}
          />
        );
      case "learn":
        return <LearnView initialTopicId={selectedLearnTopicId || undefined} />;
      case "recall":
        return <RecallView />;
      case "exam":
        return <ExamView />;
      case "flashcards":
        return <FlashcardsView />;
      case "mindmaps":
        return <MindMapsView />;
      case "graph":
        return (
          <KnowledgeGraphView
            focusTopicId={graphFocus?.topicId}
            focusTargetTopicId={graphFocus?.targetTopicId}
            focusRelId={graphFocus?.relId}
            onClearFocus={() => setGraphFocus(null)}
            onSelectTopic={(topicId) => {
              setSelectedLearnTopicId(topicId);
              setCurrentTab("learn");
            }}
            onNavigate={(tab) => setCurrentTab(tab as NavTab)}
          />
        );
      case "connectivity":
        return (
          <ConnectivityView
            onExploreTopic={(sourceId, targetId, relId) => {
              setGraphFocus({ topicId: sourceId, targetTopicId: targetId, relId });
              setCurrentTab("graph");
            }}
          />
        );
      case "notes":
        return <NotesView />;
      case "insights":
        return <InsightsView />;
      case "notifications":
        return <NotificationsView onNavigate={(tab) => setCurrentTab(tab as NavTab)} />;
      case "settings":
        return <SettingsView onLaunchOnboarding={() => setAuthState("onboarding")} />;
      default:
        return <DashboardView onNavigate={(tab) => setCurrentTab(tab as NavTab)} />;
    }
  };

  const handleCloseToast = () => {
    if (activeToast) {
      try {
        const raw = sessionStorage.getItem("humancache_dismissed_toast_ids");
        const dismissed = raw ? JSON.parse(raw) : [];
        if (!dismissed.includes(activeToast.id)) {
          dismissed.push(activeToast.id);
          sessionStorage.setItem("humancache_dismissed_toast_ids", JSON.stringify(dismissed));
        }
      } catch {
        // ignore storage errors
      }
    }
    setActiveToast(null);
  };

  const handleActionComplete = () => {
    if (activeToast) {
      try {
        const raw = sessionStorage.getItem("humancache_dismissed_toast_ids");
        const dismissed = raw ? JSON.parse(raw) : [];
        if (!dismissed.includes(activeToast.id)) {
          dismissed.push(activeToast.id);
          sessionStorage.setItem("humancache_dismissed_toast_ids", JSON.stringify(dismissed));
        }
      } catch {
        // ignore storage errors
      }
    }
    setActiveToast(null);
  };

  return (
    <AppShell
      currentTab={currentTab}
      onTabChange={setCurrentTab}
      user={authUser}
      onLogout={handleLogout}
      onLaunchOnboarding={() => setAuthState("onboarding")}
    >
      {renderContent()}
      <PersistentAITutor userName={authUser?.name} />
      <NotificationToast
        notification={activeToast}
        onClose={handleCloseToast}
        onNavigate={(tab) => setCurrentTab(tab as NavTab)}
        onActionComplete={handleActionComplete}
      />
    </AppShell>
  );
}
