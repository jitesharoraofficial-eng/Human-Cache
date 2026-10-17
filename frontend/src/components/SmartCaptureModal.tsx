"use client";

import React, { useEffect, useState } from "react";
import {
  Inbox,
  Link,
  FileText,
  Sparkles,
  CheckCircle2,
  XCircle,
  Clock,
  ArrowRight,
  Plus,
  RefreshCw,
  ExternalLink,
  ShieldCheck,
  AlertTriangle
} from "lucide-react";
import { api } from "@/lib/api";
import { Card, Button, Badge } from "./ui";

interface CaptureItemData {
  id: string;
  source_type: string;
  source_url?: string;
  title: string;
  content_preview: string;
  file_type?: string;
  file_size_bytes?: number;
  recommended_category_id?: string;
  recommended_category_name?: string;
  recommendation_confidence?: number;
  recommendation_reason?: string;
  alternative_categories?: Array<{ id?: string; name: string; is_existing: boolean }>;
  status: string;
  error_message?: string;
  document_id?: string;
  created_at: string;
}

interface CategoryOption {
  id: string;
  name: string;
  color?: string;
}

interface SmartShareModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (documentId: string) => void;
  initialUrl?: string;
  initialText?: string;
}

export function SmartCaptureModal({
  isOpen,
  onClose,
  onSuccess,
  initialUrl = "",
  initialText = ""
}: SmartShareModalProps) {
  const [activeMode, setActiveMode] = useState<"url" | "text" | "inbox">("url");
  const [inputUrl, setInputUrl] = useState(initialUrl);
  const [inputText, setInputText] = useState(initialText);
  const [inputTitle, setInputTitle] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Active Pending Capture State for Review
  const [pendingCapture, setPendingCapture] = useState<CaptureItemData | null>(null);
  const [categories, setCategories] = useState<CategoryOption[]>([]);
  const [selectedCatId, setSelectedCatId] = useState<string>("");
  const [newCatName, setNewCatName] = useState<string>("");
  const [isCreatingNewCat, setIsCreatingNewCat] = useState<boolean>(false);
  const [editedTitle, setEditedTitle] = useState<string>("");
  const [confirming, setConfirming] = useState<boolean>(false);

  // Inbox List State
  const [inboxItems, setInboxItems] = useState<CaptureItemData[]>([]);
  const [loadingInbox, setLoadingInbox] = useState(false);

  useEffect(() => {
    if (isOpen) {
      loadCategories();
      loadInbox();
      if (initialUrl) {
        setInputUrl(initialUrl);
        setActiveMode("url");
      } else if (initialText) {
        setInputText(initialText);
        setActiveMode("text");
      }
    }
  }, [isOpen, initialUrl, initialText]);

  const loadCategories = async () => {
    try {
      const cats = await api.getCategories();
      setCategories(cats || []);
    } catch {
      // ignore
    }
  };

  const loadInbox = async () => {
    setLoadingInbox(true);
    try {
      const items = await api.getCaptureInbox();
      setInboxItems(items || []);
    } catch {
      // ignore
    } finally {
      setLoadingInbox(false);
    }
  };

  const handleCaptureUrl = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputUrl.trim()) return;
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await api.captureUrl(inputUrl.trim());
      setupReviewState(res);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to capture URL.");
    } finally {
      setLoading(false);
    }
  };

  const handleCaptureText = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim()) return;
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await api.captureText({
        content_text: inputText.trim(),
        title: inputTitle.trim() || undefined
      });
      setupReviewState(res);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to capture text.");
    } finally {
      setLoading(false);
    }
  };

  const setupReviewState = (capture: CaptureItemData) => {
    setPendingCapture(capture);
    setEditedTitle(capture.title);
    if (capture.recommended_category_id) {
      setSelectedCatId(capture.recommended_category_id);
      setIsCreatingNewCat(false);
      setNewCatName("");
    } else if (capture.recommended_category_name) {
      setSelectedCatId("");
      setIsCreatingNewCat(true);
      setNewCatName(capture.recommended_category_name);
    } else {
      setSelectedCatId(categories[0]?.id || "");
      setIsCreatingNewCat(false);
    }
  };

  const handleConfirmSave = async () => {
    if (!pendingCapture) return;
    setConfirming(true);
    setErrorMsg(null);
    try {
      const payload: { category_id?: string; new_category_name?: string; custom_title?: string } = {
        custom_title: editedTitle.trim() || pendingCapture.title
      };
      if (isCreatingNewCat && newCatName.trim()) {
        payload.new_category_name = newCatName.trim();
      } else if (selectedCatId) {
        payload.category_id = selectedCatId;
      }

      const res = await api.confirmCapture(pendingCapture.id, payload);
      setPendingCapture(null);
      await loadInbox();
      onSuccess(res.document_id);
      onClose();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to confirm capture.");
    } finally {
      setConfirming(false);
    }
  };

  const handleDiscard = async () => {
    if (!pendingCapture) return;
    try {
      await api.discardCapture(pendingCapture.id);
      setPendingCapture(null);
      loadInbox();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to discard capture.");
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
      <div className="bg-white rounded-3xl shadow-2xl max-w-2xl w-full border border-slate-200 overflow-hidden flex flex-col max-h-[90vh] animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="p-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-indigo-600 flex items-center justify-center text-white shadow-md shadow-indigo-600/30">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-extrabold text-lg text-slate-900">Smart Capture & AI Ingestion</h3>
                <Badge variant="purple" className="text-[10px]">Judges Edition</Badge>
              </div>
              <p className="text-xs text-slate-500">
                Safely capture articles, research links, or study notes with automated AI categorization.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full flex items-center justify-center text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-all cursor-pointer"
          >
            ✕
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1">
          {errorMsg && (
            <div className="p-3.5 rounded-2xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0 text-rose-600" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Pending Capture Review Step */}
          {pendingCapture ? (
            <div className="space-y-5">
              <div className="p-4 rounded-2xl bg-indigo-50/60 border border-indigo-100/80 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-700">
                    Step 2: AI Category Recommendation & Confirmation
                  </span>
                  <Badge variant="default" className="text-[10px]">
                    {pendingCapture.source_type.replace("_", " ")}
                  </Badge>
                </div>

                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">Resource Title</label>
                  <input
                    type="text"
                    value={editedTitle}
                    onChange={(e) => setEditedTitle(e.target.value)}
                    className="w-full px-3 py-2 text-sm bg-white border border-slate-200 rounded-xl focus:outline-hidden focus:ring-2 focus:ring-indigo-500 font-semibold text-slate-900"
                  />
                </div>

                {/* Content Preview */}
                <div>
                  <label className="text-[11px] font-semibold text-slate-500 block mb-1">Extracted Content Preview</label>
                  <div className="p-3 bg-white/90 border border-slate-200/80 rounded-xl max-h-36 overflow-y-auto text-xs text-slate-600 leading-relaxed font-mono">
                    {pendingCapture.content_preview}
                  </div>
                </div>

                {/* AI Recommendation Banner */}
                <div className="p-3 rounded-xl bg-white border border-indigo-200 shadow-2xs space-y-1.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5 text-xs font-bold text-indigo-900">
                      <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
                      <span>Suggested Category:</span>
                      <span className="text-indigo-600 font-extrabold">{pendingCapture.recommended_category_name}</span>
                    </div>
                    {pendingCapture.recommendation_confidence ? (
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-100 font-bold text-indigo-700">
                        {Math.round(pendingCapture.recommendation_confidence * 100)}% match
                      </span>
                    ) : null}
                  </div>
                  {pendingCapture.recommendation_reason && (
                    <p className="text-[11px] text-slate-500 leading-tight">
                      {pendingCapture.recommendation_reason}
                    </p>
                  )}
                </div>
              </div>

              {/* Category Assignment Options */}
              <div className="space-y-3">
                <label className="text-xs font-bold text-slate-800 block">
                  Assign Knowledge Collection
                </label>

                <div className="flex items-center gap-3">
                  <label className="flex items-center gap-2 text-xs font-medium text-slate-700 cursor-pointer">
                    <input
                      type="radio"
                      name="cat_choice"
                      checked={!isCreatingNewCat}
                      onChange={() => setIsCreatingNewCat(false)}
                      className="accent-indigo-600"
                    />
                    <span>Existing Category</span>
                  </label>
                  <label className="flex items-center gap-2 text-xs font-medium text-slate-700 cursor-pointer">
                    <input
                      type="radio"
                      name="cat_choice"
                      checked={isCreatingNewCat}
                      onChange={() => setIsCreatingNewCat(true)}
                      className="accent-indigo-600"
                    />
                    <span>Create New Category</span>
                  </label>
                </div>

                {!isCreatingNewCat ? (
                  <select
                    value={selectedCatId}
                    onChange={(e) => setSelectedCatId(e.target.value)}
                    className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl font-medium text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                  >
                    {categories.map((c) => (
                      <option key={c.id} value={c.id}>
                        📁 {c.name}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    type="text"
                    placeholder="Enter new category name (e.g. Organic Chemistry)"
                    value={newCatName}
                    onChange={(e) => setNewCatName(e.target.value)}
                    className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl font-medium text-slate-800 focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                  />
                )}
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-between pt-3 border-t border-slate-100">
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={handleDiscard}
                  disabled={confirming}
                  className="rounded-xl text-slate-400 hover:text-slate-600"
                >
                  Discard
                </Button>

                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setPendingCapture(null)}
                    disabled={confirming}
                    className="rounded-xl"
                  >
                    Back to Inputs
                  </Button>
                  <Button
                    size="sm"
                    onClick={handleConfirmSave}
                    disabled={confirming}
                    className="rounded-xl shadow-md cursor-pointer flex items-center gap-1.5"
                  >
                    {confirming ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        <span>Ingesting Vault...</span>
                      </>
                    ) : (
                      <>
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>Confirm & Ingest</span>
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </div>
          ) : (
            <>
              {/* Mode Selector */}
              <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
                <button
                  type="button"
                  onClick={() => setActiveMode("url")}
                  className={`px-3 py-1.5 text-xs font-bold rounded-xl transition-all flex items-center gap-1.5 cursor-pointer ${
                    activeMode === "url"
                      ? "bg-indigo-600 text-white shadow-xs"
                      : "text-slate-600 hover:text-slate-900 bg-slate-100"
                  }`}
                >
                  <Link className="w-3.5 h-3.5" />
                  <span>Web Link / Article</span>
                </button>
                <button
                  type="button"
                  onClick={() => setActiveMode("text")}
                  className={`px-3 py-1.5 text-xs font-bold rounded-xl transition-all flex items-center gap-1.5 cursor-pointer ${
                    activeMode === "text"
                      ? "bg-indigo-600 text-white shadow-xs"
                      : "text-slate-600 hover:text-slate-900 bg-slate-100"
                  }`}
                >
                  <FileText className="w-3.5 h-3.5" />
                  <span>Text / Excerpt</span>
                </button>
                <button
                  type="button"
                  onClick={() => setActiveMode("inbox")}
                  className={`px-3 py-1.5 text-xs font-bold rounded-xl transition-all flex items-center gap-1.5 cursor-pointer ml-auto ${
                    activeMode === "inbox"
                      ? "bg-slate-900 text-white shadow-xs"
                      : "text-slate-600 hover:text-slate-900 bg-slate-100"
                  }`}
                >
                  <Inbox className="w-3.5 h-3.5" />
                  <span>Pending Inbox ({inboxItems.length})</span>
                </button>
              </div>

              {/* Mode 1: URL Capture */}
              {activeMode === "url" && (
                <form onSubmit={handleCaptureUrl} className="space-y-4">
                  <div>
                    <label className="text-xs font-bold text-slate-800 block mb-1">
                      Webpage, Research Paper, or Article URL
                    </label>
                    <input
                      type="url"
                      required
                      placeholder="https://en.wikipedia.org/wiki/Photosynthesis or https://arxiv.org/..."
                      value={inputUrl}
                      onChange={(e) => setInputUrl(e.target.value)}
                      className="w-full px-3.5 py-2.5 text-xs bg-slate-50 border border-slate-200 rounded-xl font-mono text-slate-900 focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                    />
                    <div className="flex items-center gap-1 text-[11px] text-slate-400 mt-1.5">
                      <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                      <span>SSRF-resistant engine with DNS validation & payload safety checks.</span>
                    </div>
                  </div>

                  <Button
                    type="submit"
                    disabled={loading || !inputUrl.trim()}
                    className="w-full rounded-xl cursor-pointer shadow-md flex items-center justify-center gap-2"
                  >
                    {loading ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        <span>Fetching & Inspecting Content...</span>
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-3.5 h-3.5" />
                        <span>Analyze & Generate Category Suggestion</span>
                      </>
                    )}
                  </Button>
                </form>
              )}

              {/* Mode 2: Text Snippet Capture */}
              {activeMode === "text" && (
                <form onSubmit={handleCaptureText} className="space-y-4">
                  <div>
                    <label className="text-xs font-bold text-slate-800 block mb-1">
                      Resource Title (Optional)
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Fundamental Theorem of Calculus notes"
                      value={inputTitle}
                      onChange={(e) => setInputTitle(e.target.value)}
                      className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl text-slate-900 focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>

                  <div>
                    <label className="text-xs font-bold text-slate-800 block mb-1">
                      Copied Text / Excerpt
                    </label>
                    <textarea
                      required
                      rows={5}
                      placeholder="Paste text snippet or lecture excerpt here..."
                      value={inputText}
                      onChange={(e) => setInputText(e.target.value)}
                      className="w-full px-3.5 py-2.5 text-xs bg-slate-50 border border-slate-200 rounded-xl text-slate-900 focus:outline-hidden focus:ring-2 focus:ring-indigo-500 font-mono leading-relaxed"
                    />
                  </div>

                  <Button
                    type="submit"
                    disabled={loading || !inputText.trim()}
                    className="w-full rounded-xl cursor-pointer shadow-md flex items-center justify-center gap-2"
                  >
                    {loading ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        <span>Analyzing Text...</span>
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-3.5 h-3.5" />
                        <span>Analyze & Generate Category Suggestion</span>
                      </>
                    )}
                  </Button>
                </form>
              )}

              {/* Mode 3: Pending Inbox View */}
              {activeMode === "inbox" && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between text-xs text-slate-500">
                    <span>Pending Captures awaiting your final review</span>
                    <button
                      onClick={loadInbox}
                      className="text-indigo-600 hover:underline flex items-center gap-1"
                    >
                      <RefreshCw className="w-3 h-3" /> Refresh
                    </button>
                  </div>

                  {loadingInbox ? (
                    <div className="p-8 text-center text-xs text-slate-400">Loading inbox...</div>
                  ) : inboxItems.length === 0 ? (
                    <div className="p-8 text-center bg-slate-50 rounded-2xl border border-slate-200/60 text-slate-400">
                      <Inbox className="w-8 h-8 mx-auto mb-2 text-slate-300" />
                      <p className="text-xs font-semibold text-slate-600">Your Capture Inbox is empty</p>
                      <p className="text-[11px] text-slate-400 mt-0.5">Captures from the browser extension or share target appear here.</p>
                    </div>
                  ) : (
                    inboxItems.map((item) => (
                      <div
                        key={item.id}
                        className="p-3.5 rounded-2xl border border-slate-200 bg-white hover:border-indigo-300 transition-all flex items-center justify-between gap-3 shadow-2xs"
                      >
                        <div className="flex-1 truncate">
                          <h4 className="text-xs font-bold text-slate-900 truncate">{item.title}</h4>
                          <p className="text-[11px] text-slate-400 truncate mt-0.5 font-mono">{item.content_preview}</p>
                          <div className="flex items-center gap-2 mt-1.5">
                            <span className="text-[10px] px-2 py-0.5 rounded-md bg-indigo-50 text-indigo-700 font-bold">
                              {item.recommended_category_name || "General"}
                            </span>
                            <span className="text-[10px] text-slate-400">{new Date(item.created_at).toLocaleDateString()}</span>
                          </div>
                        </div>

                        <div className="flex items-center gap-1.5 shrink-0">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setupReviewState(item)}
                            className="rounded-xl text-xs py-1"
                          >
                            Review & Save
                          </Button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer Privacy Disclosure */}
        <div className="p-3.5 bg-slate-50 border-t border-slate-100 text-center">
          <p className="text-[10px] text-slate-400">
            🔒 <strong>Privacy Disclosure:</strong> Content is analyzed using Gemini to classify domain concepts. No permanent record is created in your library until you explicitly confirm.
          </p>
        </div>
      </div>
    </div>
  );
}
