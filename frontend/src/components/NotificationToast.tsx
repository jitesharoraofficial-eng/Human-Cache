"use client";

import React, { useState } from "react";
import {
  Brain,
  Clock,
  Play,
  X,
  VolumeX,
  ChevronDown,
  Sparkles,
  ArrowRight
} from "lucide-react";
import { api } from "@/lib/api";
import { Button, Badge } from "./ui";

export interface ToastNotification {
  id: string;
  title: string;
  message: string;
  notification_type: string;
  topic_id?: string;
  action_url?: string;
  priority?: string;
}

interface NotificationToastProps {
  notification: ToastNotification | null;
  onClose: () => void;
  onNavigate: (tab: string, meta?: any) => void;
  onActionComplete?: () => void;
}

export function NotificationToast({
  notification,
  onClose,
  onNavigate,
  onActionComplete
}: NotificationToastProps) {
  const [snoozeOpen, setSnoozeOpen] = useState(false);
  const [loadingAction, setLoadingAction] = useState<string | null>(null);

  if (!notification) return null;

  const handleStart = async () => {
    setLoadingAction("start");
    try {
      const res = await api.startNotification(notification.id);
      onClose();
      if (onActionComplete) onActionComplete();
      // Navigate to target drill
      if (res.action_url === "/recall" || notification.notification_type.includes("quiz") || notification.notification_type.includes("review")) {
        onNavigate("recall", res.meta);
      } else if (res.action_url === "/flashcards") {
        onNavigate("flashcards", res.meta);
      } else if (res.action_url === "/exam" || notification.notification_type.includes("exam")) {
        onNavigate("exam");
      } else {
        onNavigate("learn");
      }
    } catch (e: any) {
      alert("Error starting review: " + e.message);
    } finally {
      setLoadingAction(null);
    }
  };

  const handleDismiss = async () => {
    setLoadingAction("dismiss");
    try {
      await api.dismissNotification(notification.id);
      onClose();
      if (onActionComplete) onActionComplete();
    } catch (e: any) {
      alert("Error dismissing notification: " + e.message);
    } finally {
      setLoadingAction(null);
    }
  };

  const handleSnooze = async (minutes: number) => {
    setLoadingAction("snooze");
    try {
      await api.snoozeNotification(notification.id, minutes);
      setSnoozeOpen(false);
      onClose();
      if (onActionComplete) onActionComplete();
    } catch (e: any) {
      alert("Error snoozing notification: " + e.message);
    } finally {
      setLoadingAction(null);
    }
  };

  const handleNoNeed = async () => {
    if (!confirm(`Are you sure? Reminders for this concept will be permanently suppressed (you can re-enable anytime in Settings).`)) {
      return;
    }
    setLoadingAction("no_need");
    try {
      const res = await api.noNeedNotification(notification.id);
      alert(res.message || "Concept reminders permanently muted.");
      onClose();
      if (onActionComplete) onActionComplete();
    } catch (e: any) {
      alert("Error muting concept: " + e.message);
    } finally {
      setLoadingAction(null);
    }
  };

  const isUrgent = notification.priority === "urgent" || notification.notification_type.includes("exam");

  return (
    <div
      role="alert"
      aria-live="assertive"
      className="fixed bottom-6 right-6 z-50 max-w-md w-full animate-slideUp bg-slate-900/95 backdrop-blur-md text-white border border-slate-800 rounded-2xl shadow-2xl p-4 sm:p-5 font-sans"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <div className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 ${isUrgent ? "bg-rose-500/20 text-rose-400" : "bg-indigo-500/20 text-indigo-400"}`}>
            <Brain className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-indigo-500/30 text-indigo-300">
                AI Memory Coach
              </span>
              {isUrgent && (
                <span className="text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-rose-500/30 text-rose-300">
                  Priority
                </span>
              )}
            </div>
            <h4 className="text-sm font-bold text-white mt-0.5 leading-snug">
              {notification.title}
            </h4>
          </div>
        </div>
        <button
          onClick={handleDismiss}
          disabled={loadingAction !== null}
          className="text-slate-400 hover:text-white transition-colors p-1 rounded-lg hover:bg-slate-800 cursor-pointer"
          aria-label="Dismiss notification"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <p className="text-xs text-slate-300 mt-2 leading-relaxed">
        {notification.message}
      </p>

      {/* 4 Action Buttons */}
      <div className="mt-4 pt-3 border-t border-slate-800 flex items-center gap-2 flex-wrap">
        {/* 1. START */}
        <Button
          size="sm"
          variant="primary"
          onClick={handleStart}
          disabled={loadingAction !== null}
          className="rounded-xl flex items-center gap-1.5 text-xs font-bold shadow-md cursor-pointer bg-indigo-600 hover:bg-indigo-500"
        >
          <Play className="w-3.5 h-3.5 fill-current" />
          <span>{loadingAction === "start" ? "Opening..." : "Start Drill"}</span>
        </Button>

        {/* 2. REMIND ME LATER (Dropdown) */}
        <div className="relative">
          <Button
            size="sm"
            variant="outline"
            onClick={() => setSnoozeOpen(!snoozeOpen)}
            disabled={loadingAction !== null}
            className="rounded-xl flex items-center gap-1 text-xs text-slate-200 border-slate-700 hover:bg-slate-800 cursor-pointer"
          >
            <Clock className="w-3 h-3" />
            <span>Remind Later</span>
            <ChevronDown className="w-3 h-3 text-slate-400" />
          </Button>

          {snoozeOpen && (
            <div className="absolute bottom-full left-0 mb-2 w-44 bg-slate-800 border border-slate-700 rounded-xl shadow-xl overflow-hidden py-1 z-50 text-xs">
              <button
                onClick={() => handleSnooze(60)}
                className="w-full text-left px-3 py-2 text-slate-200 hover:bg-slate-700 flex items-center justify-between cursor-pointer"
              >
                <span>In 1 hour</span>
                <span className="text-[10px] text-slate-400">60m</span>
              </button>
              <button
                onClick={() => handleSnooze(1440)}
                className="w-full text-left px-3 py-2 text-slate-200 hover:bg-slate-700 flex items-center justify-between cursor-pointer"
              >
                <span>Tomorrow</span>
                <span className="text-[10px] text-slate-400">24h</span>
              </button>
              <button
                onClick={() => handleSnooze(4320)}
                className="w-full text-left px-3 py-2 text-slate-200 hover:bg-slate-700 flex items-center justify-between cursor-pointer"
              >
                <span>In 3 days</span>
                <span className="text-[10px] text-slate-400">72h</span>
              </button>
            </div>
          )}
        </div>

        {/* 3. DISMISS */}
        <Button
          size="sm"
          variant="ghost"
          onClick={handleDismiss}
          disabled={loadingAction !== null}
          className="rounded-xl text-xs text-slate-400 hover:text-white hover:bg-slate-800 cursor-pointer"
        >
          {loadingAction === "dismiss" ? "Dismissing..." : "Dismiss"}
        </Button>

        {/* 4. NO NEED */}
        {notification.topic_id && (
          <Button
            size="sm"
            variant="ghost"
            onClick={handleNoNeed}
            disabled={loadingAction !== null}
            className="rounded-xl text-xs text-slate-400 hover:text-rose-400 hover:bg-rose-950/30 ml-auto cursor-pointer"
            title="Permanently mute notifications for this concept"
          >
            <VolumeX className="w-3 h-3 mr-1" />
            <span>No Need</span>
          </Button>
        )}
      </div>
    </div>
  );
}
