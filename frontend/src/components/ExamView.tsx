"use client";

import React, { useEffect, useState, useRef } from "react";
import { CalendarDays, Upload, Plus, CheckCircle, Clock, Sparkles, BookOpen } from "lucide-react";
import { api } from "@/lib/api";
import { Card, Button, Badge } from "./ui";

export function ExamView() {
  const [exams, setExams] = useState<any[]>([]);
  const [selectedExamId, setSelectedExamId] = useState<string>("");
  const [tasks, setTasks] = useState<any[]>([]);
  const [extracting, setExtracting] = useState(false);
  const [extractedReview, setExtractedReview] = useState<any[] | null>(null);
  const [manualSubject, setManualSubject] = useState("");
  const [manualDate, setManualDate] = useState("");
  const [rawDateSheetText, setRawDateSheetText] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadExams();
  }, []);

  const loadExams = async () => {
    try {
      const res = await api.getExams();
      setExams(res);
      if (res.length > 0) {
        setSelectedExamId(res[0].id);
        loadTasks(res[0].id);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const loadTasks = async (examId: string) => {
    try {
      const res = await api.getExamTasks(examId);
      setTasks(res);
    } catch (e) {
      console.error(e);
    }
  };

  const handleDateSheetUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setExtracting(true);
    try {
      const res = await api.extractDateSheet(file);
      setExtractedReview(res.extracted_exams);
    } catch (e: any) {
      alert("Extraction error: " + e.message);
    } finally {
      setExtracting(false);
    }
  };

  const handleParseRawText = async () => {
    if (!rawDateSheetText.trim()) return;
    setExtracting(true);
    try {
      const res = await api.extractDateSheet(undefined, rawDateSheetText);
      setExtractedReview(res.extracted_exams);
    } catch (e: any) {
      alert("Error: " + e.message);
    } finally {
      setExtracting(false);
    }
  };

  const handleConfirmExtractedExam = async (item: any) => {
    try {
      await api.createExam({
        subject: item.subject,
        exam_date: item.exam_date,
        exam_time_str: item.exam_time_str,
        syllabus_summary: "Extracted from uploaded date-sheet schedule.",
      });
      setExtractedReview(null);
      setRawDateSheetText("");
      loadExams();
      alert(`Exam for '${item.subject}' confirmed & revision plan generated!`);
    } catch (e: any) {
      alert(e.message);
    }
  };

  const handleManualCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualSubject.trim() || !manualDate) return;
    try {
      await api.createExam({
        subject: manualSubject.trim(),
        exam_date: new Date(manualDate).toISOString(),
        exam_time_str: "10:00 AM",
      });
      setManualSubject("");
      setManualDate("");
      loadExams();
    } catch (e: any) {
      alert(e.message);
    }
  };

  const handleToggleTask = async (taskId: string) => {
    try {
      await api.toggleTask(taskId);
      if (selectedExamId) loadTasks(selectedExamId);
    } catch (e: any) {
      alert(e.message);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Exam Countdown & Date Sheet Planner</h2>
          <p className="text-xs sm:text-sm text-slate-500 mt-0.5">
            Upload timetables or date-sheet notices. The system automatically schedules prioritized spaced revision intervals.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="purple" className="px-3 py-1 text-xs">
            {exams.length} Active Target Exams
          </Badge>
        </div>
      </div>

      {/* Top Bento Row: Active Exam Countdowns */}
      {exams.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {exams.map((ex) => {
            const isSelected = selectedExamId === ex.id;
            const daysLeft = ex.days_left;
            const isUrgent = daysLeft <= 2;
            return (
              <div
                key={ex.id}
                onClick={() => {
                  setSelectedExamId(ex.id);
                  loadTasks(ex.id);
                }}
                className={`clay-card p-4 rounded-2xl cursor-pointer transition-all border ${
                  isSelected
                    ? "border-indigo-500/80 ring-2 ring-indigo-500/20 bg-gradient-to-br from-white to-indigo-50/40"
                    : "border-slate-200/80 hover:border-slate-300 bg-white"
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Target</span>
                  <span
                    className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${
                      isUrgent
                        ? "bg-rose-100 text-rose-700 font-extrabold animate-pulse"
                        : "bg-indigo-100 text-indigo-700"
                    }`}
                  >
                    {daysLeft === 0 ? "Today!" : daysLeft === 1 ? "Tomorrow!" : `${daysLeft} days left`}
                  </span>
                </div>
                <h4 className="font-extrabold text-sm text-slate-900 truncate">{ex.subject}</h4>
                <div className="flex items-center justify-between text-[11px] text-slate-500 mt-2">
                  <span>{new Date(ex.exam_date).toLocaleDateString([], { month: "short", day: "numeric" })}</span>
                  <span>{ex.exam_time_str || "10:00 AM"}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Date-Sheet Upload & Form (4 cols) */}
        <div className="lg:col-span-4 space-y-4">
          <Card className="p-5 border-indigo-200/60 bg-gradient-to-br from-white via-indigo-50/20 to-purple-50/20">
            <h3 className="font-bold text-slate-900 text-sm mb-1.5 flex items-center gap-2">
              <Upload className="w-4 h-4 text-indigo-600" /> Upload Date Sheet
            </h3>
            <p className="text-xs text-slate-500 mb-3 leading-relaxed">
              Upload PDF or TXT date-sheet timetable. AI parses exam deadlines and aligns spaced revision.
            </p>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.txt,.docx"
              onChange={handleDateSheetUpload}
              disabled={extracting}
              className="block w-full text-xs text-slate-500 file:mr-3 file:py-2 file:px-3 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-indigo-600 file:text-white hover:file:bg-indigo-700 cursor-pointer"
            />
            {extracting && (
              <div className="flex items-center gap-2 text-xs text-indigo-600 font-medium pt-3">
                <Sparkles className="w-4 h-4 animate-spin" /> Extracting subjects & dates...
              </div>
            )}
          </Card>

          {/* Quick Paste Date Sheet */}
          <Card className="p-5">
            <h3 className="font-bold text-slate-900 text-sm mb-1.5">Paste Timetable Snippet</h3>
            <textarea
              placeholder="e.g.:&#10;15/10/2026 - Organic Chemistry - 10:00 AM&#10;19/10/2026 - Wave Optics - 02:00 PM"
              value={rawDateSheetText}
              onChange={(e) => setRawDateSheetText(e.target.value)}
              rows={3}
              className="w-full text-xs border border-slate-200/90 rounded-xl p-3 mb-2 bg-slate-50/50 focus:bg-white focus:outline-indigo-500"
            />
            <Button size="sm" onClick={handleParseRawText} disabled={extracting} className="w-full">
              Parse Timetable Text
            </Button>
          </Card>

          {/* Manual Entry */}
          <Card className="p-5">
            <h3 className="font-bold text-slate-900 text-sm mb-2 flex items-center gap-2">
              <Plus className="w-4 h-4 text-indigo-600" /> Add Exam Manually
            </h3>
            <form onSubmit={handleManualCreate} className="space-y-2.5">
              <input
                type="text"
                placeholder="Subject (e.g. Modern Physics)"
                value={manualSubject}
                onChange={(e) => setManualSubject(e.target.value)}
                className="w-full text-xs border border-slate-200/90 rounded-xl p-2.5 bg-slate-50/50 focus:bg-white focus:outline-indigo-500"
                required
              />
              <input
                type="date"
                value={manualDate}
                onChange={(e) => setManualDate(e.target.value)}
                className="w-full text-xs border border-slate-200/90 rounded-xl p-2.5 bg-slate-50/50 focus:bg-white focus:outline-indigo-500"
                required
              />
              <Button type="submit" size="sm" className="w-full">
                Schedule Exam
              </Button>
            </form>
          </Card>
        </div>

        {/* Right Column: Review Confirmation & Study Tasks (8 cols) */}
        <div className="lg:col-span-8 space-y-4">
          {/* Extracted Review Screen */}
          {extractedReview && (
            <Card className="p-5 border-indigo-300 bg-indigo-50/40 shadow-md">
              <h3 className="font-bold text-sm text-indigo-950 mb-1 flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-indigo-600" /> Review Extracted Timetable
              </h3>
              <p className="text-xs text-indigo-800 mb-3">
                Confirm extracted items to generate automated daily revision plans.
              </p>
              <div className="space-y-2">
                {extractedReview.map((item, idx) => (
                  <div key={idx} className="p-3.5 bg-white rounded-xl border border-indigo-200/80 flex items-center justify-between shadow-2xs">
                    <div>
                      <h4 className="font-bold text-xs sm:text-sm text-slate-900">{item.subject}</h4>
                      <p className="text-xs text-slate-500 mt-0.5">
                        Date: {new Date(item.exam_date).toLocaleDateString()} • Time: {item.exam_time_str || "10:00 AM"}
                      </p>
                    </div>
                    <Button size="sm" onClick={() => handleConfirmExtractedExam(item)}>
                      Confirm & Schedule
                    </Button>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Generated Spaced Revision Plan */}
          <Card className="p-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-100 gap-2 mb-4">
              <div>
                <h3 className="font-bold text-base text-slate-900">
                  Targeted Revision Roadmap
                </h3>
                <p className="text-xs text-slate-500">
                  Calculated against your memory decay rates, syllabus topics, and exam deadline.
                </p>
              </div>
              <Badge variant="purple" className="self-start sm:self-auto">
                {tasks.filter((t) => t.is_completed).length}/{tasks.length} Completed
              </Badge>
            </div>

            {tasks.length === 0 ? (
              <div className="text-center py-12 text-slate-400">
                <CalendarDays className="w-10 h-10 mx-auto mb-2 opacity-30" />
                <p className="text-xs font-medium">Select an exam above or add a new exam to see prioritized daily tasks.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {tasks.map((task) => (
                  <div
                    key={task.id}
                    className={`p-4 rounded-2xl border flex items-start justify-between gap-3 transition-all ${
                      task.is_completed
                        ? "bg-emerald-50/30 border-emerald-200/80 text-slate-400"
                        : "bg-white border-slate-200/80 hover:border-indigo-300 shadow-2xs"
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <input
                        type="checkbox"
                        checked={task.is_completed}
                        onChange={() => handleToggleTask(task.id)}
                        className="mt-1 w-4 h-4 rounded text-indigo-600 cursor-pointer accent-indigo-600"
                      />
                      <div>
                        <h4 className={`text-xs sm:text-sm font-bold ${task.is_completed ? "line-through text-slate-400" : "text-slate-900"}`}>
                          {task.title}
                        </h4>
                        <p className="text-xs text-slate-500 mt-1 leading-relaxed">{task.description}</p>
                        <div className="flex items-center gap-3 mt-2 text-[11px] text-slate-400">
                          <span className="flex items-center gap-1 font-medium text-slate-500">
                            <Clock className="w-3 h-3 text-indigo-500" /> {task.allocated_minutes}m allocated
                          </span>
                          <span>•</span>
                          <span>Due: {new Date(task.scheduled_for).toLocaleDateString([], { month: "short", day: "numeric" })}</span>
                        </div>
                      </div>
                    </div>

                    <Badge variant={task.priority === "high" ? "danger" : "default"}>
                      {task.priority}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
