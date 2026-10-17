"use client";

import React, { useEffect, useState } from "react";
import {
  Bell,
  Clock,
  CheckCircle2,
  VolumeX,
  Sparkles,
  AlertTriangle,
  ArrowRight,
  CheckCheck,
  BookOpen,
  CalendarDays,
  FileText,
  Layers,
  Inbox,
  Play,
  ChevronDown
} from "lucide-react";
import { api } from "@/lib/api";
import { Card, Button, Badge } from "./ui";

interface NotificationItem {
  id: string;
  user_id: string;
  topic_id?: string;
  title: string;
  message: string;
  notification_type: string;
  action_url?: string;
  entity_type?: string;
  entity_id?: string;
  priority?: "low" | "normal" | "high" | "urgent";
  action_state?: string;
  is_read: boolean;
  is_snoozed: boolean;
  created_at: string;
}

export function NotificationsView({ onNavigate }: { onNavigate?: (tab: string) => void }) {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"all" | "unread" | "review" | "exam" | "materials">("all");
  const [markingAll, setMarkingAll] = useState(false);
  const [snoozeDropdownId, setSnoozeDropdownId] = useState<string | null>(null);

  useEffect(() => {
    loadNotifications();
  }, []);

  const loadNotifications = async () => {
    try {
      const data = await api.getNotifications();
      setNotifications(Array.isArray(data) ? data : []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleMarkRead = async (id: string) => {
    try {
      await api.markNotificationRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
    } catch (e: any) {
      console.error("Failed to mark as read", e);
    }
  };

  const handleMarkAllRead = async () => {
    setMarkingAll(true);
    try {
      await api.markAllNotificationsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    } catch (e: any) {
      alert("Failed to mark all as read: " + e.message);
    } finally {
      setMarkingAll(false);
    }
  };

  const handleStart = async (notif: NotificationItem) => {
    try {
      const res = await api.startNotification(notif.id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === notif.id ? { ...n, is_read: true, action_state: "started" } : n))
      );
      if (onNavigate) {
        if (res.action_url === "/recall" || notif.notification_type.includes("quiz") || notif.notification_type.includes("review")) {
          onNavigate("recall");
        } else if (res.action_url === "/flashcards") {
          onNavigate("flashcards");
        } else if (res.action_url === "/exam" || notif.notification_type.includes("exam")) {
          onNavigate("exam");
        } else if (res.action_url === "/mindmaps") {
          onNavigate("mindmaps");
        } else {
          onNavigate("learn");
        }
      }
    } catch (e: any) {
      alert("Error starting review: " + e.message);
    }
  };

  const handleSnooze = async (id: string, mins: number) => {
    try {
      await api.snoozeNotification(id, mins);
      setNotifications((prev) => prev.filter((n) => n.id !== id));
    } catch (e: any) {
      alert("Error snoozing: " + e.message);
    }
  };

  const handleDismiss = async (id: string) => {
    try {
      await api.dismissNotification(id);
      setNotifications((prev) => prev.filter((n) => n.id !== id));
    } catch (e: any) {
      alert("Error dismissing: " + e.message);
    }
  };

  const handleNoNeed = async (id: string) => {
    if (!confirm("Permanently stop reminders for this concept? You can re-enable it anytime from Settings.")) {
      return;
    }
    try {
      const res = await api.noNeedNotification(id);
      alert(res.message || "Concept reminders permanently muted.");
      setNotifications((prev) => prev.filter((n) => n.id !== id));
    } catch (e: any) {
      alert("Error updating concept: " + e.message);
    }
  };

  const handleActionClick = (notif: NotificationItem) => {
    if (!notif.is_read) {
      handleMarkRead(notif.id);
    }
    if (onNavigate) {
      if (notif.action_url === "/exam" || notif.notification_type.includes("exam")) {
        onNavigate("exam");
      } else if (notif.action_url === "/recall" || notif.notification_type.includes("quiz") || notif.notification_type.includes("review")) {
        onNavigate("recall");
      } else if (notif.action_url === "/mindmaps" || notif.notification_type.includes("mindmap")) {
        onNavigate("mindmaps");
      } else if (notif.action_url === "/uploads" || notif.notification_type.includes("document")) {
        onNavigate("uploads");
      } else {
        onNavigate("learn");
      }
    }
  };

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  const filteredNotifications = notifications.filter((n) => {
    if (filter === "unread") return !n.is_read;
    if (filter === "review") return n.notification_type.includes("review") || n.notification_type.includes("risk") || n.notification_type.includes("weak");
    if (filter === "exam") return n.notification_type.includes("exam") || n.notification_type.includes("task");
    if (filter === "materials") return n.notification_type.includes("document") || n.notification_type.includes("mindmap");
    return true;
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-slate-900">Notifications & Intelligent Alerts</h2>
            {unreadCount > 0 && (
              <span className="px-2 py-0.5 text-xs font-bold rounded-full bg-indigo-100 text-indigo-700">
                {unreadCount} unread
              </span>
            )}
          </div>
          <p className="text-xs sm:text-sm text-slate-500 mt-0.5">
            Personalized alerts derived solely from your actual uploaded materials, recall drills, exam dates, and memory stability.
          </p>
        </div>

        {/* Global Actions */}
        {unreadCount > 0 && (
          <Button
            size="sm"
            variant="outline"
            onClick={handleMarkAllRead}
            disabled={markingAll}
            className="rounded-xl flex items-center gap-1.5 self-start sm:self-auto cursor-pointer"
          >
            <CheckCheck className="w-4 h-4 text-indigo-600" />
            <span>Mark all as read</span>
          </Button>
        )}
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-1.5 bg-slate-100/90 p-1 rounded-xl overflow-x-auto">
        <button
          onClick={() => setFilter("all")}
          className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all cursor-pointer whitespace-nowrap ${
            filter === "all" ? "bg-white text-slate-900 shadow-xs" : "text-slate-600 hover:text-slate-900"
          }`}
        >
          All ({notifications.length})
        </button>
        <button
          onClick={() => setFilter("unread")}
          className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all cursor-pointer whitespace-nowrap ${
            filter === "unread" ? "bg-indigo-600 text-white shadow-xs" : "text-slate-600 hover:text-slate-900"
          }`}
        >
          Unread ({unreadCount})
        </button>
        <button
          onClick={() => setFilter("review")}
          className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all cursor-pointer whitespace-nowrap ${
            filter === "review" ? "bg-amber-600 text-white shadow-xs" : "text-slate-600 hover:text-slate-900"
          }`}
        >
          Review & Retention
        </button>
        <button
          onClick={() => setFilter("exam")}
          className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all cursor-pointer whitespace-nowrap ${
            filter === "exam" ? "bg-rose-600 text-white shadow-xs" : "text-slate-600 hover:text-slate-900"
          }`}
        >
          Exams & Deadlines
        </button>
        <button
          onClick={() => setFilter("materials")}
          className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all cursor-pointer whitespace-nowrap ${
            filter === "materials" ? "bg-teal-600 text-white shadow-xs" : "text-slate-600 hover:text-slate-900"
          }`}
        >
          Materials & Mind Maps
        </button>
      </div>

      {/* Notification List */}
      <div className="space-y-3">
        {loading ? (
          <Card className="p-12 text-center text-slate-400">
            <div className="animate-spin w-6 h-6 border-2 border-indigo-600 border-t-transparent rounded-full mx-auto mb-2" />
            <p className="text-xs">Loading notifications...</p>
          </Card>
        ) : filteredNotifications.length === 0 ? (
          <Card className="p-16 text-center text-slate-400 bg-white">
            <Inbox className="w-12 h-12 mx-auto mb-3 text-slate-300" />
            <p className="text-sm font-semibold text-slate-700">All caught up! No notifications.</p>
            <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
              Real notifications appear automatically as you upload documents, take quizzes, and set real exam dates.
            </p>
          </Card>
        ) : (
          filteredNotifications.map((n) => {
            const isExam = n.notification_type.includes("exam");
            const isRisk = n.notification_type.includes("risk") || n.notification_type.includes("weak");
            const isMaterial = n.notification_type.includes("document") || n.notification_type.includes("mindmap");
            const isUrgent = n.priority === "urgent";

            return (
              <Card
                key={n.id}
                className={`p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-l-4 transition-all ${
                  !n.is_read
                    ? isExam
                      ? "border-l-rose-500 bg-rose-50/20 shadow-xs"
                      : isRisk
                      ? "border-l-amber-500 bg-amber-50/20 shadow-xs"
                      : "border-l-indigo-600 bg-indigo-50/20 shadow-xs"
                    : "border-l-slate-300 bg-white opacity-85"
                }`}
              >
                <div className="space-y-1.5 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    {!n.is_read && (
                      <span className="w-2 h-2 rounded-full bg-indigo-600 shrink-0" title="Unread" />
                    )}
                    <h4 className={`text-sm text-slate-900 ${!n.is_read ? "font-bold" : "font-semibold"}`}>
                      {n.title}
                    </h4>
                    <Badge
                      variant={isExam || isUrgent ? "danger" : isRisk ? "warning" : "default"}
                    >
                      {n.notification_type.replace(/_/g, " ")}
                    </Badge>
                  </div>
                  <p className="text-xs text-slate-600 leading-relaxed">{n.message}</p>
                  <div className="flex items-center gap-3 text-[11px] text-slate-400">
                    <div className="flex items-center gap-1">
                      <Clock className="w-3 h-3 text-slate-400" />
                      <span>
                        {new Date(n.created_at).toLocaleDateString([], { month: "short", day: "numeric" })}{" "}
                        {new Date(n.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </span>
                    </div>
                    {n.priority && (
                      <span className="capitalize text-[10px] text-slate-400 font-mono">
                        Priority: {n.priority}
                      </span>
                    )}
                  </div>
                </div>

                {/* 4 Proactive Actions */}
                <div className="flex items-center gap-2 flex-wrap self-end sm:self-center shrink-0">
                  {/* 1. START ACTION */}
                  <Button
                    size="sm"
                    variant="primary"
                    onClick={() => handleStart(n)}
                    className="rounded-xl shadow-xs cursor-pointer flex items-center gap-1.5 font-bold bg-indigo-600 hover:bg-indigo-700 text-white"
                  >
                    <Play className="w-3.5 h-3.5 fill-current" />
                    <span>
                      {isExam ? "Start Exam Plan" : isRisk ? "Start Drill" : isMaterial ? "Open Canvas" : "Start Review"}
                    </span>
                  </Button>

                  {/* 2. REMIND ME LATER ACTION (Dropdown) */}
                  <div className="relative">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setSnoozeDropdownId(snoozeDropdownId === n.id ? null : n.id)}
                      className="rounded-xl cursor-pointer flex items-center gap-1 text-slate-700 hover:bg-slate-100"
                      title="Snooze / Remind me later"
                    >
                      <Clock className="w-3.5 h-3.5" />
                      <span>Remind Later</span>
                      <ChevronDown className="w-3 h-3 text-slate-400" />
                    </Button>

                    {snoozeDropdownId === n.id && (
                      <div className="absolute right-0 top-full mt-1 w-44 bg-white border border-slate-200 rounded-xl shadow-lg overflow-hidden py-1 z-50 text-xs">
                        <button
                          onClick={() => {
                            setSnoozeDropdownId(null);
                            handleSnooze(n.id, 60);
                          }}
                          className="w-full text-left px-3 py-2 text-slate-700 hover:bg-slate-50 flex items-center justify-between cursor-pointer"
                        >
                          <span>In 1 hour</span>
                          <span className="text-[10px] text-slate-400 font-mono">60m</span>
                        </button>
                        <button
                          onClick={() => {
                            setSnoozeDropdownId(null);
                            handleSnooze(n.id, 1440);
                          }}
                          className="w-full text-left px-3 py-2 text-slate-700 hover:bg-slate-50 flex items-center justify-between cursor-pointer"
                        >
                          <span>Tomorrow</span>
                          <span className="text-[10px] text-slate-400 font-mono">24h</span>
                        </button>
                        <button
                          onClick={() => {
                            setSnoozeDropdownId(null);
                            handleSnooze(n.id, 4320);
                          }}
                          className="w-full text-left px-3 py-2 text-slate-700 hover:bg-slate-50 flex items-center justify-between cursor-pointer"
                        >
                          <span>In 3 days</span>
                          <span className="text-[10px] text-slate-400 font-mono">72h</span>
                        </button>
                      </div>
                    )}
                  </div>

                  {/* 3. DISMISS ACTION */}
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleDismiss(n.id)}
                    className="rounded-xl text-slate-500 hover:text-slate-700 hover:bg-slate-100 cursor-pointer"
                    title="Dismiss alert"
                  >
                    Dismiss
                  </Button>

                  {/* 4. NO NEED ACTION */}
                  {n.topic_id && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleNoNeed(n.id)}
                      title="Permanently suppress reminders for this concept"
                      className="rounded-xl text-slate-400 hover:text-rose-600 hover:bg-rose-50 cursor-pointer"
                    >
                      <VolumeX className="w-3.5 h-3.5 mr-1" />
                      <span>No Need</span>
                    </Button>
                  )}

                  {!n.is_read && (
                    <button
                      onClick={() => handleMarkRead(n.id)}
                      className="text-slate-400 hover:text-slate-600 p-1.5 rounded-lg hover:bg-slate-100 cursor-pointer"
                      title="Mark as read"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </Card>
            );
          })
        )}
      </div>
    </div>
  );
}
