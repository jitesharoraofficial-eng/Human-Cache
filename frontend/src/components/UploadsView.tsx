"use client";

import React, { useEffect, useState, useRef } from "react";
import {
  FolderUp,
  Plus,
  FileText,
  CheckCircle2,
  Clock,
  AlertCircle,
  Sparkles,
  Trash2,
  Search,
  Filter,
  GraduationCap,
  ArrowRight,
  CreditCard,
  Layers,
  Tag,
  FileType,
  UploadCloud,
  Check,
  Link,
  Inbox
} from "lucide-react";
import { api } from "@/lib/api";
import { Card, Button, Badge } from "./ui";
import { SmartCaptureModal } from "./SmartCaptureModal";

export function UploadsView({ onLearnTopic }: { onLearnTopic?: (topicId: string) => void }) {
  const [categories, setCategories] = useState<any[]>([]);
  const [documents, setDocuments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [selectedCatFilter, setSelectedCatFilter] = useState<string>("all");
  const [targetUploadCatId, setTargetUploadCatId] = useState<string>("");
  const [newCatName, setNewCatName] = useState("");
  const [newCatColor, setNewCatColor] = useState("#6366f1");
  const [pastedText, setPastedText] = useState("");
  const [pastedTitle, setPastedTitle] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [activeTab, setActiveTab] = useState<"files" | "paste">("files");
  const [isCaptureModalOpen, setIsCaptureModalOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);


  useEffect(() => {
    loadData();

    // Check for incoming PWA share payload
    if (typeof window !== "undefined") {
      const stored = sessionStorage.getItem("humancache_incoming_share");
      if (stored) {
        try {
          const parsed = JSON.parse(stored);
          sessionStorage.removeItem("humancache_incoming_share");
          if (parsed.url || parsed.text) {
            setIsCaptureModalOpen(true);
          }
        } catch {
          // ignore
        }
      }
    }
  }, []);


  const loadData = async () => {
    try {
      const [cats, docs] = await Promise.all([api.getCategories(), api.getDocuments()]);
      setCategories(cats);
      setDocuments(docs);
      if (cats.length > 0 && !targetUploadCatId) setTargetUploadCatId(cats[0].id);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  // Poll for background learning suite preparation completion
  useEffect(() => {
    const hasPending = documents.some(
      (d) => d.resource_prep_status === "processing" || d.resource_prep_status === "pending"
    );
    if (!hasPending) return;

    const interval = setInterval(() => {
      loadData();
    }, 4000);
    return () => clearInterval(interval);
  }, [documents]);

  const handleRetryPrep = async (docId: string, docTitle: string) => {
    try {
      setStatusMessage(`Initiating learning suite preparation for "${docTitle}"...`);
      await api.prepareDocumentResources(docId);
      await loadData();
    } catch (e: any) {
      alert("Preparation trigger failed: " + e.message);
    }
  };

  const handleCreateCategory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCatName.trim()) return;
    try {
      await api.createCategory({ name: newCatName.trim(), color: newCatColor });
      setNewCatName("");
      await loadData();
      setStatusMessage("New category created successfully!");
      setTimeout(() => setStatusMessage(null), 3000);
    } catch (e: any) {
      alert(e.message);
    }
  };

  const processUploadedFile = async (file: File) => {
    setUploading(true);
    setStatusMessage(`Uploading and analyzing "${file.name}"...`);
    try {
      const res = await api.uploadDocument(file, targetUploadCatId || undefined);
      setStatusMessage(`Success! Extracted ${res.extracted_topics} canonical topics from "${file.name}". AI suite preparation started.`);
      await loadData();
    } catch (e: any) {
      alert("Upload failed: " + e.message);
      setStatusMessage("Extraction failed: " + e.message);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
      setTimeout(() => setStatusMessage(null), 4000);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    await processUploadedFile(file);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) {
      await processUploadedFile(file);
    }
  };

  const handlePastedUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pastedText.trim() || !pastedTitle.trim()) return;
    setUploading(true);
    try {
      const blob = new Blob([pastedText], { type: "text/plain" });
      const file = new File([blob], `${pastedTitle.trim().replace(/\s+/g, "_")}.txt`, { type: "text/plain" });
      const res = await api.uploadDocument(file, targetUploadCatId || undefined);
      setPastedText("");
      setPastedTitle("");
      setStatusMessage(`Success! Extracted ${res.extracted_topics} topics from pasted material.`);
      await loadData();
    } catch (e: any) {
      alert("Error: " + e.message);
    } finally {
      setUploading(false);
      setTimeout(() => setStatusMessage(null), 4000);
    }
  };

  // Filter documents
  const filteredDocuments = documents.filter((doc) => {
    const matchesCat = selectedCatFilter === "all" || doc.category_id === selectedCatFilter;
    const matchesSearch =
      doc.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      doc.filename.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (doc.category_name && doc.category_name.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesCat && matchesSearch;
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-8 font-sans">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="purple">Multi-Source Ingestion</Badge>
            <span className="text-xs text-slate-400">• PDF, DOCX, TXT & Syllabus Parsing</span>
          </div>
          <h2 className="text-2xl font-black text-slate-900 tracking-tight">
            Knowledge Vault & Document Ingestion
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 mt-0.5">
            Capture course packs, textbook chapters, and lecture notes. AI automatically extracts atomic topics and semantic relationships.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            size="sm"
            onClick={() => setIsCaptureModalOpen(true)}
            className="rounded-2xl bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-700 hover:to-violet-700 text-white shadow-md shadow-indigo-500/25 cursor-pointer flex items-center gap-2 px-4 py-2"
          >
            <Sparkles className="w-4 h-4" />
            <span className="font-bold text-xs sm:text-sm">Smart Share & Capture</span>
          </Button>

          {statusMessage && (
            <div className="flex items-center gap-2 text-xs bg-indigo-50 border border-indigo-200 text-indigo-700 px-4 py-2 rounded-2xl shadow-xs animate-fadeIn">
              <Sparkles className="w-4 h-4 text-indigo-600 shrink-0" />
              <span className="font-semibold">{statusMessage}</span>
            </div>
          )}
        </div>
      </div>


      {/* Categories Bento Row */}
      <div className="space-y-2.5">
        <div className="flex items-center justify-between">
          <h3 className="font-bold text-slate-900 text-xs sm:text-sm uppercase tracking-wider flex items-center gap-1.5">
            <Layers className="w-4 h-4 text-indigo-600" />
            <span>Curated Study Categories</span>
          </h3>
          <span className="text-xs text-slate-400">{categories.length} categories active</span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <button
            onClick={() => setSelectedCatFilter("all")}
            className={`p-3 rounded-2xl border text-left transition-all cursor-pointer ${
              selectedCatFilter === "all"
                ? "bg-indigo-600 text-white border-indigo-600 shadow-md shadow-indigo-600/25"
                : "bg-white border-slate-200 text-slate-700 hover:border-slate-300 hover:bg-slate-50"
            }`}
          >
            <p className="text-xs font-bold truncate">All Categories</p>
            <p className={`text-[10px] mt-0.5 ${selectedCatFilter === "all" ? "text-indigo-200" : "text-slate-400"}`}>
              {documents.length} Resources
            </p>
          </button>

          {categories.map((cat) => {
            const isSelected = selectedCatFilter === cat.id;
            const docCount = documents.filter((d) => d.category_id === cat.id).length;
            return (
              <button
                key={cat.id}
                onClick={() => setSelectedCatFilter(cat.id)}
                className={`p-3 rounded-2xl border text-left transition-all cursor-pointer group ${
                  isSelected
                    ? "bg-slate-900 text-white border-slate-800 shadow-md"
                    : "bg-white border-slate-200 text-slate-700 hover:border-indigo-300 hover:bg-slate-50"
                }`}
              >
                <div className="flex items-center gap-1.5">
                  <span
                    className="w-2.5 h-2.5 rounded-full shrink-0"
                    style={{ backgroundColor: cat.color || "#6366f1" }}
                  />
                  <p className="text-xs font-bold truncate">{cat.name}</p>
                </div>
                <p className={`text-[10px] mt-1 ${isSelected ? "text-slate-300" : "text-slate-400"}`}>
                  {docCount} docs
                </p>
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Grid: Upload Center (Left) & Document Vault (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Ingestion Engine (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          <Card className="p-5">
            {/* Tab switch between File and Paste */}
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
              <div className="flex items-center gap-1.5 bg-slate-100 p-1 rounded-xl">
                <button
                  type="button"
                  onClick={() => setActiveTab("files")}
                  className={`px-3 py-1 text-xs font-bold rounded-lg cursor-pointer transition-all ${
                    activeTab === "files"
                      ? "bg-white text-indigo-700 shadow-xs"
                      : "text-slate-600 hover:text-slate-900"
                  }`}
                >
                  File Upload
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab("paste")}
                  className={`px-3 py-1 text-xs font-bold rounded-lg cursor-pointer transition-all ${
                    activeTab === "paste"
                      ? "bg-white text-indigo-700 shadow-xs"
                      : "text-slate-600 hover:text-slate-900"
                  }`}
                >
                  Paste Text
                </button>
              </div>
              <Badge variant="purple" className="text-[10px]">Auto Extractor</Badge>
            </div>

            {/* Target Category Selector */}
            <div className="mb-4">
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Assign to Category:
              </label>
              <select
                value={targetUploadCatId}
                onChange={(e) => setTargetUploadCatId(e.target.value)}
                className="w-full text-xs rounded-xl px-3 py-2 border border-slate-300 bg-white font-medium"
              >
                <option value="">General (No specific category)</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>

            {activeTab === "files" ? (
              /* Drag-and-Drop File Upload Area */
              <div
                onDragOver={(e) => {
                  e.preventDefault();
                  setIsDragging(true);
                }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`p-6 rounded-2xl border-2 border-dashed transition-all cursor-pointer text-center flex flex-col items-center justify-center select-none ${
                  isDragging
                    ? "border-indigo-600 bg-indigo-50/70 scale-[1.01]"
                    : "border-slate-300 hover:border-indigo-400 bg-slate-50/50 hover:bg-slate-50"
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.docx,.doc,.txt,.md"
                  onChange={handleFileUpload}
                  disabled={uploading}
                  className="hidden"
                />

                <div className="w-12 h-12 rounded-2xl bg-indigo-50 border border-indigo-200 flex items-center justify-center text-indigo-600 mb-3 shadow-xs">
                  <UploadCloud className="w-6 h-6" />
                </div>

                <p className="text-xs sm:text-sm font-bold text-slate-800">
                  Drag and drop files here, or <span className="text-indigo-600 underline">browse</span>
                </p>
                <p className="text-[11px] text-slate-400 mt-1">
                  Supported: PDF, Word (DOCX), Markdown, Plain Text (Max 25MB)
                </p>

                {uploading && (
                  <div className="mt-3 flex items-center gap-2 text-xs font-bold text-indigo-600 bg-white px-3 py-1.5 rounded-full border border-indigo-200 shadow-xs">
                    <Sparkles className="w-4 h-4 animate-spin" />
                    <span>Extracting concepts and connecting graph...</span>
                  </div>
                )}
              </div>
            ) : (
              /* Paste Raw Text */
              <form onSubmit={handlePastedUpload} className="space-y-3">
                <input
                  type="text"
                  placeholder="Document Title (e.g. Chapter 4 Summary)"
                  value={pastedTitle}
                  onChange={(e) => setPastedTitle(e.target.value)}
                  className="w-full text-xs rounded-xl px-3 py-2 border border-slate-300 bg-white"
                  required
                />
                <textarea
                  placeholder="Paste lecture notes, study materials, or textbook paragraphs here..."
                  value={pastedText}
                  onChange={(e) => setPastedText(e.target.value)}
                  rows={4}
                  className="w-full text-xs rounded-xl p-3 border border-slate-300 bg-white"
                  required
                />
                <Button type="submit" size="sm" variant="primary" disabled={uploading} className="w-full justify-center">
                  <Sparkles className="w-3.5 h-3.5 mr-1" />
                  {uploading ? "Extracting..." : "Process Text"}
                </Button>
              </form>
            )}
          </Card>

          {/* Quick Create New Category */}
          <Card className="p-4">
            <h4 className="text-xs font-bold text-slate-800 mb-2 flex items-center gap-1.5">
              <Plus className="w-3.5 h-3.5 text-indigo-600" /> Create Custom Category
            </h4>
            <form onSubmit={handleCreateCategory} className="flex gap-2">
              <input
                type="text"
                placeholder="Category Name"
                value={newCatName}
                onChange={(e) => setNewCatName(e.target.value)}
                className="flex-1 text-xs rounded-xl px-3 py-2 border border-slate-300 bg-white"
              />
              <Button type="submit" size="sm" variant="secondary">
                Add
              </Button>
            </form>
          </Card>
        </div>

        {/* Right Column: Processed Documents Library (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="clay-card p-4 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <h3 className="font-bold text-slate-900 text-sm">
                Document Vault ({filteredDocuments.length})
              </h3>
              <Badge variant="clay" className="text-[10px]">Verified Chunks</Badge>
            </div>

            {/* Search Input */}
            <div className="relative w-full sm:w-64">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Search documents or topics..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full text-xs pl-8 pr-3 py-2 rounded-xl border border-slate-300 bg-white"
              />
            </div>
          </div>

          {/* Document Cards List */}
          <div className="space-y-3">
            {filteredDocuments.length === 0 ? (
              <Card className="p-12 text-center text-slate-400">
                <FileText className="w-10 h-10 mx-auto mb-2 opacity-40 text-indigo-400" />
                <p className="text-xs font-semibold">No documents found matching this filter.</p>
              </Card>
            ) : (
              filteredDocuments.map((doc) => (
                <div
                  key={doc.id}
                  className="clay-card p-4 sm:p-5 rounded-2xl border border-slate-200/90 hover:border-indigo-300 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                >
                  <div className="flex items-start gap-3 flex-1 overflow-hidden">
                    <div className="w-10 h-10 rounded-xl bg-indigo-50 border border-indigo-200 flex items-center justify-center text-indigo-600 shrink-0 shadow-xs">
                      <FileText className="w-5 h-5" />
                    </div>

                    <div className="overflow-hidden pr-2 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h4 className="font-bold text-sm text-slate-900 truncate">{doc.title}</h4>
                        {doc.is_demo && <Badge variant="purple" className="text-[10px]">Demo Grounded</Badge>}
                        <Badge
                          variant={doc.processing_status === "completed" ? "success" : "warning"}
                          className="text-[10px]"
                        >
                          {doc.processing_status}
                        </Badge>
                        {doc.resource_prep_status === "completed" && (
                          <Badge variant="success" className="text-[10px] bg-emerald-50 text-emerald-700 border border-emerald-200">
                            ✨ AI Materials Ready
                          </Badge>
                        )}
                        {doc.resource_prep_status === "processing" && (
                          <span className="inline-flex items-center gap-1 text-[10px] font-bold text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200 animate-pulse">
                            ⏳ Preparing Quizzes & Cards...
                          </span>
                        )}
                        {doc.resource_prep_status === "failed" && (
                          <button
                            onClick={() => handleRetryPrep(doc.id, doc.title)}
                            className="inline-flex items-center gap-1 text-[10px] font-bold text-rose-600 bg-rose-50 px-2 py-0.5 rounded-full border border-rose-200 hover:bg-rose-100 transition-colors"
                            title="Retry automatic study resource generation"
                          >
                            ⚠️ Retry Prep
                          </button>
                        )}
                      </div>

                      <p className="text-[11px] text-slate-500 mt-1">
                        {doc.filename} • {Math.round((doc.file_size_bytes || 4096) / 1024)} KB • Category:{" "}
                        <strong className="text-slate-700">{doc.category_name}</strong>
                      </p>

                      <div className="flex items-center gap-3 mt-2 flex-wrap">
                        <div className="flex items-center gap-1 text-indigo-600 text-xs font-semibold">
                          <Tag className="w-3 h-3" />
                          <span>{doc.extracted_topics_count || 3} topics extracted & connected in knowledge graph</span>
                        </div>
                        {doc.coverage_summary && (() => {
                          try {
                            const cov = typeof doc.coverage_summary === "string" ? JSON.parse(doc.coverage_summary) : doc.coverage_summary;
                            if (cov && cov.total_pages) {
                              return (
                                <span className="text-[11px] text-slate-500 font-medium bg-slate-100 px-2 py-0.5 rounded-md">
                                  📄 {cov.readable_pages}/{cov.total_pages} pages ({cov.coverage_percentage}%)
                                </span>
                              );
                            }
                          } catch {
                            // ignore
                          }
                          return null;
                        })()}
                      </div>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2 shrink-0 self-end sm:self-center">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => onLearnTopic && onLearnTopic(doc.id)}
                      className="text-xs"
                    >
                      <GraduationCap className="w-3.5 h-3.5 mr-1" /> Learn
                    </Button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Smart Share & Capture Modal */}
      <SmartCaptureModal
        isOpen={isCaptureModalOpen}
        onClose={() => setIsCaptureModalOpen(false)}
        onSuccess={async (newDocId) => {
          setStatusMessage("Successfully ingested resource into your knowledge vault!");
          await loadData();
          setTimeout(() => setStatusMessage(null), 4000);
        }}
      />
    </div>
  );
}

