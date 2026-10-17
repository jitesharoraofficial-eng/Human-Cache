"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  MessageSquare,
  Send,
  Sparkles,
  X,
  Bot,
  User as UserIcon,
  Plus,
  Trash2,
  ChevronLeft,
  BookOpen,
  Globe,
  RefreshCw,
  AlertCircle,
  Clock,
  Layers
} from "lucide-react";
import { api } from "@/lib/api";
import { MarkdownRenderer } from "./MarkdownRenderer";

interface Citation {
  source_type: "uploaded_document" | "general_knowledge" | string;
  title: string;
  locator?: string;
  snippet?: string;
  document_id?: string;
}

interface MessageTurn {
  id?: string;
  role: "user" | "assistant" | "system";
  content: string;
  citations?: Citation[];
  created_at?: string;
  meta?: {
    model?: string;
    language?: string;
    latency_ms?: number;
  };
}

interface ConversationItem {
  id: string;
  title: string;
  target_exam?: string;
  subject?: string;
  message_count: number;
  created_at: string;
  updated_at?: string;
}

const STORAGE_ACTIVE_THREAD_KEY = "humancache_agent_active_thread";

export function PersistentAITutor({ userName }: { userName?: string }) {
  const [isOpen, setIsOpen] = useState(false);
  const [showThreadDrawer, setShowThreadDrawer] = useState(false);
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [activeTitle, setActiveTitle] = useState<string>("Study Session");
  const [messages, setMessages] = useState<MessageTurn[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const displayName = userName ? userName.split(" ")[0] : "Learner";

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [messages, isOpen, loading]);

  // Load conversations when tutor is first opened
  useEffect(() => {
    if (isOpen && conversations.length === 0) {
      loadConversations();
    }
  }, [isOpen]);

  const loadConversations = async () => {
    setInitialLoading(true);
    setErrorMsg(null);
    try {
      const data = await api.getAgentConversations(0, 30);
      const list: ConversationItem[] = Array.isArray(data) ? data : data.conversations || [];
      setConversations(list);

      const savedThreadId = typeof window !== "undefined" ? localStorage.getItem(STORAGE_ACTIVE_THREAD_KEY) : null;
      const savedThread = list.find((c) => c.id === savedThreadId);
      const threadWithMessages = list.find((c) => (c.message_count || 0) > 0);
      
      // If saved thread exists and has real messages, use it.
      // Else if another thread has messages, pick the latest thread with messages so yesterday's learning session is visible!
      // Otherwise fallback to savedThread or list[0].
      const targetThread = (savedThread && (savedThread.message_count || 0) > 0)
        ? savedThread
        : (threadWithMessages || savedThread || list[0]);

      if (targetThread) {
        await selectConversation(targetThread.id, targetThread.title);
      } else {
        // Start first thread
        await handleCreateNewThread("Initial Study Session");
      }
    } catch (err: any) {
      console.warn("Could not load agent conversations:", err);
      // Graceful offline fallback
      setMessages([
        {
          role: "assistant",
          content: `Hello ${displayName}! I am your Human Cache AI Learning Agent. You are currently in offline fallback mode. Ask me anything, or connect to review notes!`,
          citations: [
            {
              source_type: "general_knowledge",
              title: "AI General Knowledge",
              locator: "Offline Ready",
              snippet: "Foundational learning model ready to assist.",
            },
          ],
        },
      ]);
    } finally {
      setInitialLoading(false);
    }
  };

  const selectConversation = async (conversationId: string, title?: string) => {
    setActiveConversationId(conversationId);
    if (title) setActiveTitle(title);
    setShowThreadDrawer(false);
    setErrorMsg(null);
    if (typeof window !== "undefined") {
      localStorage.setItem(STORAGE_ACTIVE_THREAD_KEY, conversationId);
    }

    try {
      setLoading(true);
      const data = await api.getAgentConversation(conversationId);
      setActiveTitle(data.title || "Study Session");
      const fetchedMessages: MessageTurn[] = (data.messages || []).map((m: any) => ({
        id: m.id,
        role: m.role,
        content: m.content,
        citations: m.citations || [],
        created_at: m.created_at,
        meta: m.meta,
      }));

      if (fetchedMessages.length === 0) {
        setMessages([
          {
            role: "assistant",
            content: `Hello ${displayName}! This is a fresh study session. Ask a question, explore a topic from your notes, or ask in Hinglish/English!`,
            citations: [
              {
                source_type: "general_knowledge",
                title: "Human Cache AI Agent",
                locator: "Adaptive Mentor",
                snippet: "Ready to guide your conceptual mastery.",
              },
            ],
          },
        ]);
      } else {
        setMessages(fetchedMessages);
      }
    } catch (err: any) {
      console.error("Failed to load conversation thread:", err);
      setErrorMsg("Failed to load thread messages. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateNewThread = async (customTitle?: string) => {
    setErrorMsg(null);
    try {
      setLoading(true);
      const newThread = await api.createAgentConversation({
        title: customTitle || `Session on ${new Date().toLocaleDateString("en-US", { month: "short", day: "numeric" })}`,
      });
      setConversations((prev) => [newThread, ...prev]);
      setActiveConversationId(newThread.id);
      setActiveTitle(newThread.title);
      setShowThreadDrawer(false);
      if (typeof window !== "undefined") {
        localStorage.setItem(STORAGE_ACTIVE_THREAD_KEY, newThread.id);
      }
      setMessages([
        {
          role: "assistant",
          content: `New session started! What topic or material would you like to focus on today?`,
          citations: [
            {
              source_type: "general_knowledge",
              title: "Human Cache AI Agent",
              locator: "Fresh Thread",
            },
          ],
        },
      ]);
    } catch (err: any) {
      console.error("Failed to create new session:", err);
      setErrorMsg("Could not create new thread. Falling back to temporary chat.");
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteConversation = async (e: React.MouseEvent, conversationId: string) => {
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this study session?")) return;

    try {
      await api.deleteAgentConversation(conversationId);
      setConversations((prev) => prev.filter((c) => c.id !== conversationId));
      if (activeConversationId === conversationId) {
        const remaining = conversations.filter((c) => c.id !== conversationId);
        if (remaining.length > 0) {
          selectConversation(remaining[0].id, remaining[0].title);
        } else {
          handleCreateNewThread();
        }
      }
    } catch (err) {
      console.error("Failed to delete thread:", err);
      setErrorMsg("Could not delete session.");
    }
  };

  const handleSend = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!input.trim() || loading) return;

    const userText = input.trim();
    setInput("");
    setErrorMsg(null);

    // Optimistically append user message
    const optimisticTurn: MessageTurn = {
      role: "user",
      content: userText,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimisticTurn]);
    setLoading(true);

    try {
      if (activeConversationId) {
        // Multi-turn persistent agent API
        const assistantRes = await api.postAgentMessage(activeConversationId, {
          content: userText,
        });

        const assistantTurn: MessageTurn = {
          id: assistantRes.id,
          role: "assistant",
          content: assistantRes.content,
          citations: assistantRes.citations || [],
          created_at: assistantRes.created_at,
          meta: assistantRes.meta,
        };

        setMessages((prev) => [...prev, assistantTurn]);

        // Update conversation in list message count and timestamp
        setConversations((prev) =>
          prev.map((c) =>
            c.id === activeConversationId
              ? { ...c, message_count: c.message_count + 2, updated_at: new Date().toISOString() }
              : c
          )
        );
      } else {
        // Fallback to legacy chat if thread couldn't be initialized
        const historyPayload = messages.slice(-4).map((m) => ({
          role: m.role,
          content: m.content,
        }));
        const res = await api.tutorChat({
          message: userText,
          conversation_history: historyPayload,
        });

        let reply = res.reply;
        let citations: Citation[] = [];
        if (res.citations && res.citations.length > 0) {
          citations = res.citations.map((c: string) => ({
            source_type: "uploaded_document",
            title: c,
            locator: "Extracted Reference",
          }));
        }

        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: reply,
            citations: citations.length > 0 ? citations : undefined,
          },
        ]);
      }
    } catch (err: any) {
      console.error("Agent message turn failed:", err);
      setErrorMsg("Could not reach tutor service. Response generated in local knowledge mode.");
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Regarding "${userText}": Connected to your knowledge base. Upload study materials or notes to expand source grounding.`,
          citations: [
            {
              source_type: "general_knowledge",
              title: "Local Knowledge Fallback",
              locator: "Offline Recovery",
            },
          ],
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Floating Toggle Pill */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed bottom-6 right-6 z-50 flex items-center gap-2 px-4 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-full shadow-lg hover:shadow-indigo-500/25 transition-all transform hover:-translate-y-0.5 cursor-pointer"
          aria-label="Open AI Learning Agent"
        >
          <Sparkles className="w-5 h-5 text-amber-300 animate-pulse" />
          <span className="font-medium text-sm">Ask AI Agent</span>
          {conversations.length > 0 && (
            <span className="ml-1 px-1.5 py-0.5 text-[10px] font-semibold bg-indigo-500/40 rounded-full border border-indigo-400/30">
              Active
            </span>
          )}
        </button>
      )}

      {/* Main Agent Modal Drawer */}
      {isOpen && (
        <div className="fixed inset-x-3 bottom-3 top-16 sm:inset-auto sm:bottom-6 sm:right-6 sm:w-[440px] sm:h-[620px] z-50 bg-white rounded-2xl shadow-2xl border border-slate-200 flex flex-col overflow-hidden animate-in fade-in slide-in-from-bottom-6 duration-200">
          {/* Header */}
          {/* Header */}
          <div className="bg-slate-900 text-white px-4 py-3 flex items-center justify-between border-b border-slate-800">
            <div className="flex items-center gap-2.5 min-w-0">
              <button
                onClick={() => setShowThreadDrawer(!showThreadDrawer)}
                className="flex items-center gap-1.5 px-2.5 py-1 bg-slate-800 hover:bg-slate-700 rounded-lg text-xs font-semibold text-indigo-300 border border-slate-700/60 shadow-xs transition-colors shrink-0 cursor-pointer"
                title="View All Study Sessions"
              >
                <Layers className="w-3.5 h-3.5 text-indigo-400" />
                <span>Sessions</span>
                <span className="bg-indigo-950 text-indigo-300 px-1.5 py-0.5 rounded-full text-[10px] font-bold border border-indigo-700/50">
                  {conversations.length}
                </span>
              </button>
              <div className="min-w-0">
                <div className="flex items-center gap-1.5">
                  <h3 className="font-semibold text-xs sm:text-sm leading-tight truncate text-slate-100">
                    {activeTitle}
                  </h3>
                </div>
                <p className="text-[10px] text-slate-400 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                  Grounded Second Brain
                </p>
              </div>
            </div>

            <div className="flex items-center gap-1.5">
              <button
                onClick={() => handleCreateNewThread()}
                className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors cursor-pointer"
                title="New Study Session"
              >
                <Plus className="w-4 h-4" />
              </button>
              <button
                onClick={() => setIsOpen(false)}
                className="text-slate-400 hover:text-white p-1.5 rounded-lg hover:bg-slate-800 transition-colors cursor-pointer"
                title="Close AI Agent"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Session History Drawer (Slide-down with Date Grouping) */}
          {showThreadDrawer && (
            <div className="bg-slate-900 text-white border-b border-slate-800 p-3 max-h-64 overflow-y-auto space-y-2.5 text-xs animate-in slide-in-from-top duration-150">
              <div className="flex items-center justify-between pb-1.5 border-b border-slate-800 text-slate-400 text-[11px]">
                <span className="font-bold uppercase tracking-wider text-slate-300">All Study Sessions ({conversations.length})</span>
                <button
                  onClick={() => handleCreateNewThread()}
                  className="text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-semibold"
                >
                  <Plus className="w-3 h-3" /> New Session
                </button>
              </div>
              {conversations.length === 0 ? (
                <p className="text-slate-500 py-2 text-center">No previous sessions found.</p>
              ) : (
                (() => {
                  const groups: Record<string, ConversationItem[]> = {};
                  for (const c of conversations) {
                    try {
                      const d = new Date(c.created_at);
                      const now = new Date();
                      const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
                      const sessDate = new Date(d.getFullYear(), d.getMonth(), d.getDate());
                      const diffDays = Math.round((today.getTime() - sessDate.getTime()) / (1000 * 3600 * 24));
                      const label = diffDays === 0 ? "Today" : (diffDays === 1 ? "Yesterday" : (diffDays < 7 ? "Earlier This Week" : "Older Sessions"));
                      if (!groups[label]) groups[label] = [];
                      groups[label].push(c);
                    } catch {
                      if (!groups["Sessions"]) groups["Sessions"] = [];
                      groups["Sessions"].push(c);
                    }
                  }

                  return Object.entries(groups).map(([groupName, groupItems]) => (
                    <div key={groupName} className="space-y-1">
                      <div className="text-[10px] font-bold uppercase tracking-wider text-indigo-400/90 px-1 pt-1">
                        📅 {groupName} ({groupItems.length})
                      </div>
                      {groupItems.map((c) => (
                        <div
                          key={c.id}
                          onClick={() => selectConversation(c.id, c.title)}
                          className={`flex items-center justify-between p-2 rounded-lg cursor-pointer transition-colors ${
                            c.id === activeConversationId
                              ? "bg-indigo-600/30 border border-indigo-500/40 text-white"
                              : "hover:bg-slate-800 text-slate-300"
                          }`}
                        >
                          <div className="min-w-0 pr-2">
                            <p className="font-medium truncate">{c.title}</p>
                            <p className="text-[10px] text-slate-400">
                              {c.message_count} messages • {new Date(c.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </p>
                          </div>
                          <button
                            onClick={(e) => handleDeleteConversation(e, c.id)}
                            className="p-1 text-slate-500 hover:text-rose-400 transition-colors"
                            title="Delete thread"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      ))}
                    </div>
                  ));
                })()
              )}
            </div>
          )}

          {/* Error Banner */}
          {errorMsg && (
            <div className="bg-amber-50 text-amber-800 px-3 py-1.5 text-xs border-b border-amber-200 flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <AlertCircle className="w-3.5 h-3.5 shrink-0 text-amber-600" />
                <span>{errorMsg}</span>
              </div>
              <button
                onClick={() => setErrorMsg(null)}
                className="text-amber-700 hover:text-amber-900 font-bold ml-2"
              >
                ×
              </button>
            </div>
          )}

          {/* Messages Body */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3.5 bg-slate-50/60 text-sm">
            {initialLoading ? (
              <div className="h-full flex flex-col items-center justify-center text-slate-400 text-xs gap-2 py-8">
                <RefreshCw className="w-5 h-5 animate-spin text-indigo-500" />
                Loading conversation thread...
              </div>
            ) : (
              messages.map((m, idx) => (
                <div
                  key={m.id || idx}
                  className={`flex gap-2.5 ${m.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  {m.role === "assistant" && (
                    <div className="w-7 h-7 rounded-full bg-indigo-100 flex items-center justify-center shrink-0 text-indigo-600 mt-0.5">
                      <Bot className="w-4 h-4" />
                    </div>
                  )}

                  <div
                    className={`max-w-[85%] rounded-xl px-3.5 py-2.5 text-xs sm:text-sm leading-relaxed shadow-xs ${
                      m.role === "user"
                        ? "bg-indigo-600 text-white rounded-br-none whitespace-pre-line"
                        : "bg-white border border-slate-200 text-slate-800 rounded-bl-none"
                    }`}
                  >
                    {m.role === "assistant" ? (
                      <div>
                        <MarkdownRenderer content={m.content} className="text-xs sm:text-sm" />

                        {/* Grounding & Citations Footer */}
                        {m.citations && m.citations.length > 0 && (
                          <div className="mt-3 pt-2.5 border-t border-slate-100 flex flex-wrap gap-1.5">
                            {m.citations.map((cite, cIdx) => (
                              <div
                                key={cIdx}
                                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium border ${
                                  cite.source_type === "uploaded_document"
                                    ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                                    : "bg-slate-100 text-slate-600 border-slate-200"
                                }`}
                                title={cite.snippet || cite.locator || cite.title}
                              >
                                {cite.source_type === "uploaded_document" ? (
                                  <BookOpen className="w-3 h-3 text-emerald-600" />
                                ) : (
                                  <Globe className="w-3 h-3 text-slate-500" />
                                )}
                                <span className="truncate max-w-[170px]">
                                  {cite.title} {cite.locator ? `(${cite.locator})` : ""}
                                </span>
                              </div>
                            ))}
                          </div>
                        )}

                        {/* Turn Metadata Badge */}
                        {m.meta?.language && m.meta.language !== "en" && (
                          <div className="mt-1 text-[10px] text-slate-400">
                            Recognized mode: {m.meta.language}
                          </div>
                        )}
                      </div>
                    ) : (
                      m.content
                    )}
                  </div>

                  {m.role === "user" && (
                    <div className="w-7 h-7 rounded-full bg-slate-200 flex items-center justify-center shrink-0 text-slate-700 mt-0.5">
                      <UserIcon className="w-4 h-4" />
                    </div>
                  )}
                </div>
              ))
            )}

            {messages.length <= 1 && conversations.some(c => c.id !== activeConversationId && (c.message_count || 0) > 0) && (
              <div className="bg-indigo-50 border border-indigo-200/80 rounded-xl p-3 text-xs text-indigo-900 flex flex-col gap-1.5 shadow-2xs">
                <div className="flex items-center gap-1.5 font-bold text-indigo-700">
                  <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
                  <span>Resume Previous Day&apos;s Session</span>
                </div>
                <p className="text-[11px] text-slate-600">
                  You have earlier study conversations saved with your questions and notes.
                </p>
                <button
                  onClick={() => setShowThreadDrawer(true)}
                  className="text-left font-semibold text-indigo-600 hover:text-indigo-800 text-[11px] underline flex items-center gap-1 cursor-pointer"
                >
                  <Layers className="w-3 h-3" /> View and resume past sessions ({conversations.length}) →
                </button>
              </div>
            )}

            {loading && (
              <div className="flex gap-2 items-center text-xs text-slate-500 italic bg-white p-2.5 rounded-lg border border-slate-200 w-fit">
                <Sparkles className="w-3.5 h-3.5 text-indigo-500 animate-spin" />
                Synthesizing response grounded in your materials...
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Footer */}
          <form
            onSubmit={handleSend}
            className="p-3 bg-white border-t border-slate-200 flex gap-2 items-center"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask in English, Hindi, or Hinglish..."
              className="flex-1 text-xs sm:text-sm px-3.5 py-2 rounded-lg border border-slate-200 focus:outline-hidden focus:border-indigo-500 placeholder:text-slate-400"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="p-2.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-40 transition-colors shrink-0 cursor-pointer"
              title="Send Message"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      )}
    </>
  );
}
