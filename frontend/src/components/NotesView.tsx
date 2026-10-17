"use client";

import React, { useEffect, useState } from "react";
import { FileText, Plus, Trash2, Tag, Calendar, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import { Card, Button, Badge } from "./ui";
import { MarkdownRenderer } from "./MarkdownRenderer";

export function NotesView() {
  const [notes, setNotes] = useState<any[]>([]);
  const [selectedNote, setSelectedNote] = useState<any>(null);
  const [newTitle, setNewTitle] = useState("");
  const [newContent, setNewContent] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadNotes();
  }, []);

  const loadNotes = async () => {
    try {
      const data = await api.getNotes();
      setNotes(data);
      if (data.length > 0) setSelectedNote(data[0]);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim() || !newContent.trim()) return;
    try {
      const created = await api.createNote({
        title: newTitle.trim(),
        content: newContent.trim(),
        tags: ["personal", "study"],
      });
      setNotes((prev) => [created, ...prev]);
      setSelectedNote(created);
      setNewTitle("");
      setNewContent("");
    } catch (e: any) {
      alert(e.message);
    }
  };

  const handleDelete = async (noteId: string) => {
    if (!confirm("Delete this study note?")) return;
    try {
      await api.deleteNote(noteId);
      const updated = notes.filter((n) => n.id !== noteId);
      setNotes(updated);
      setSelectedNote(updated[0] || null);
    } catch (e: any) {
      alert(e.message);
    }
  };

  const [searchQuery, setSearchQuery] = useState("");
  const filteredNotes = notes.filter(
    (n) =>
      n.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      n.content.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Notes & Study Syntheses</h2>
          <p className="text-xs sm:text-sm text-slate-500 mt-0.5">
            Persistent repository of your handwritten summaries, personal reflections, and saved AI Tutor grounded explanations.
          </p>
        </div>
        <Badge variant="purple" className="self-start sm:self-auto px-3 py-1 text-xs">
          {notes.length} Syntheses Saved
        </Badge>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Note Creator & List (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          <Card className="p-5 border-indigo-200/70 bg-gradient-to-br from-white via-indigo-50/20 to-purple-50/20 shadow-md">
            <h3 className="font-bold text-slate-900 text-sm mb-2 flex items-center gap-2">
              <Plus className="w-4 h-4 text-indigo-600" /> Capture New Study Note
            </h3>
            <form onSubmit={handleCreate} className="space-y-2.5">
              <input
                type="text"
                placeholder="Title (e.g. Carnot Cycle Thermodynamics Summary)..."
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                className="w-full text-xs border border-slate-200/90 rounded-xl p-2.5 bg-white/90 focus:outline-indigo-500"
                required
              />
              <textarea
                placeholder="Write study notes, equations, or key insights..."
                value={newContent}
                onChange={(e) => setNewContent(e.target.value)}
                rows={3}
                className="w-full text-xs border border-slate-200/90 rounded-xl p-2.5 bg-white/90 focus:outline-indigo-500"
                required
              />
              <Button type="submit" size="sm" className="w-full bg-indigo-600 hover:bg-indigo-700 text-white shadow-xs">
                Save to Human Cache
              </Button>
            </form>
          </Card>

          <Card className="p-4 space-y-2">
            <div className="flex items-center justify-between px-1 mb-1">
              <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                Saved Notes ({filteredNotes.length})
              </h4>
            </div>

            <input
              type="text"
              placeholder="Search notes..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full text-xs border border-slate-200/90 rounded-xl px-3 py-1.5 mb-2 bg-slate-50/50 focus:bg-white focus:outline-indigo-500"
            />

            <div className="space-y-2 max-h-[380px] overflow-y-auto pr-1">
              {filteredNotes.length === 0 ? (
                <p className="text-xs text-slate-400 py-6 text-center">No notes found.</p>
              ) : (
                filteredNotes.map((n) => {
                  const isSelected = selectedNote?.id === n.id;
                  return (
                    <button
                      key={n.id}
                      onClick={() => setSelectedNote(n)}
                      className={`w-full text-left p-3.5 rounded-2xl text-xs transition-all cursor-pointer border ${
                        isSelected
                          ? "bg-gradient-to-r from-indigo-600 to-indigo-700 text-white shadow-md shadow-indigo-600/30 border-indigo-600"
                          : "bg-white border-slate-200/80 hover:border-slate-300 text-slate-700"
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <p className="font-bold truncate text-xs">{n.title}</p>
                        <span
                          className={`text-[10px] px-1.5 py-0.2 rounded font-semibold ${
                            isSelected
                              ? "bg-indigo-500/40 text-indigo-100"
                              : "bg-slate-100 text-slate-500"
                          }`}
                        >
                          {n.source_type === "ai_tutor" ? "AI Tutor" : "Self"}
                        </span>
                      </div>
                      <p
                        className={`text-[11px] truncate leading-relaxed ${
                          isSelected ? "text-indigo-100" : "text-slate-500"
                        }`}
                      >
                        {n.content}
                      </p>
                    </button>
                  );
                })
              )}
            </div>
          </Card>
        </div>

        {/* Right Column: Note Reader (7 cols) */}
        <div className="lg:col-span-7">
          {selectedNote ? (
            <Card className="p-6 space-y-4">
              <div className="flex items-start justify-between border-b border-slate-100 pb-4">
                <div>
                  <Badge variant={selectedNote.source_type === "ai_tutor" ? "purple" : "default"} className="mb-2">
                    {selectedNote.source_type === "ai_tutor" ? "AI Tutor Grounded" : "User Authored"}
                  </Badge>
                  <h3 className="text-lg font-extrabold text-slate-900">{selectedNote.title}</h3>
                  <p className="text-xs text-slate-400 mt-1">
                    Recorded {new Date(selectedNote.created_at || Date.now()).toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" })}
                  </p>
                </div>
                <Button
                  size="sm"
                  variant="danger"
                  onClick={() => handleDelete(selectedNote.id)}
                  className="rounded-xl"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </Button>
              </div>

              <div className="bg-slate-50/70 p-5 rounded-2xl border border-slate-200/70 font-sans shadow-2xs">
                <MarkdownRenderer content={selectedNote.content} />
              </div>

              <div className="flex items-center gap-2 pt-2">
                {selectedNote.tags?.map((tag: string, i: number) => (
                  <span
                    key={i}
                    className="text-[11px] bg-indigo-50 text-indigo-700 border border-indigo-200/60 px-2.5 py-1 rounded-lg flex items-center gap-1 font-medium"
                  >
                    <Tag className="w-3 h-3 text-indigo-500" /> {tag}
                  </span>
                ))}
              </div>
            </Card>
          ) : (
            <Card className="p-20 text-center text-slate-400">
              <FileText className="w-10 h-10 mx-auto mb-2 opacity-30" />
              <p className="text-sm font-medium">Select or create a note to view.</p>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
