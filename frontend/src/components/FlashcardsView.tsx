"use client";

import React, { useEffect, useState } from "react";
import {
  CreditCard,
  RotateCw,
  Sparkles,
  Plus,
  Check,
  ChevronLeft,
  ChevronRight,
  Flame,
  ThumbsUp,
  AlertCircle,
  HelpCircle,
  CheckCircle2,
  RefreshCw,
  Layers,
  Zap
} from "lucide-react";
import { api } from "@/lib/api";
import { Card, Button, Badge, ProgressBar } from "./ui";

export function FlashcardsView() {
  const [decks, setDecks] = useState<any[]>([]);
  const [selectedDeckId, setSelectedDeckId] = useState<string>("");
  const [cards, setCards] = useState<any[]>([]);
  const [currentCardIdx, setCurrentCardIdx] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);
  const [loading, setLoading] = useState(false);
  const [reviewedCards, setReviewedCards] = useState<Record<number, string>>({});
  const [topics, setTopics] = useState<any[]>([]);
  const [generatingDeck, setGeneratingDeck] = useState(false);
  const [selectedTopicToGen, setSelectedTopicToGen] = useState("");
  const [selectedDetailLevel, setSelectedDetailLevel] = useState<string>("semi-detailed");

  useEffect(() => {
    loadDecks();
    loadTopics();
  }, []);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (e.code === "Space") {
        e.preventDefault();
        setIsFlipped((prev) => !prev);
      } else if (e.code === "ArrowRight") {
        handleNext();
      } else if (e.code === "ArrowLeft") {
        handlePrev();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [currentCardIdx, cards.length]);

  const loadDecks = async () => {
    try {
      const res = await api.getFlashcardDecks();
      setDecks(res);
      if (res.length > 0) {
        setSelectedDeckId(res[0].id);
        loadCards(res[0].id);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const loadTopics = async () => {
    try {
      const t = await api.getTopics();
      setTopics(t);
      if (t.length > 0) setSelectedTopicToGen(t[0].id);
    } catch {
      // ignore
    }
  };

  const loadCards = async (deckId: string) => {
    setLoading(true);
    setCurrentCardIdx(0);
    setIsFlipped(false);
    setReviewedCards({});
    try {
      const res = await api.getDeckCards(deckId);
      setCards(res);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleNext = () => {
    if (currentCardIdx < cards.length - 1) {
      setCurrentCardIdx((prev) => prev + 1);
      setIsFlipped(false);
    }
  };

  const handlePrev = () => {
    if (currentCardIdx > 0) {
      setCurrentCardIdx((prev) => prev - 1);
      setIsFlipped(false);
    }
  };

  const handleRate = (rating: "hard" | "good" | "easy") => {
    setReviewedCards((prev) => ({ ...prev, [currentCardIdx]: rating }));
    setTimeout(() => {
      handleNext();
    }, 200);
  };

  const handleGenerateDeck = async () => {
    if (!selectedTopicToGen) return;
    setGeneratingDeck(true);
    try {
      await api.generateFlashcards(selectedTopicToGen, selectedDetailLevel);
      await loadDecks();
    } catch (e: any) {
      alert("Error generating deck: " + e.message);
    } finally {
      setGeneratingDeck(false);
    }
  };

  const currentCard = cards[currentCardIdx];
  const progressPct = cards.length > 0 ? ((currentCardIdx + 1) / cards.length) * 100 : 0;
  const reviewedCount = Object.keys(reviewedCards).length;

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-8 font-sans">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="purple">Active Retrieval Drill</Badge>
            <span className="text-xs text-slate-400">• Spaced Repetition Flashcards</span>
          </div>
          <h2 className="text-2xl font-black text-slate-900 tracking-tight">
            Flashcards & Conceptual Decks
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 mt-0.5">
            Master atomic principles, formulae, and tricky exam traps with 3D interactive active-recall cards.
          </p>
        </div>

        {/* Generate Deck Quick Form */}
        {topics.length > 0 && (
          <div className="flex flex-wrap items-center gap-2 bg-white p-1.5 rounded-2xl border border-slate-200/90 shadow-xs">
            <select
              value={selectedTopicToGen}
              onChange={(e) => setSelectedTopicToGen(e.target.value)}
              className="text-xs rounded-xl px-2.5 py-1.5 border border-slate-200 bg-slate-50 font-medium"
            >
              {topics.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
            <select
              value={selectedDetailLevel}
              onChange={(e) => setSelectedDetailLevel(e.target.value)}
              className="text-xs rounded-xl px-2.5 py-1.5 border border-indigo-200 bg-indigo-50/50 font-bold text-indigo-950"
            >
              <option value="brief">⚡ Brief (Core Facts)</option>
              <option value="semi-detailed">📘 Semi-Detailed (Standard)</option>
              <option value="detailed">🔬 Detailed (Full Nuance & Traps)</option>
            </select>
            <Button
              size="sm"
              variant="primary"
              disabled={generatingDeck}
              onClick={handleGenerateDeck}
            >
              <Sparkles className="w-3.5 h-3.5 mr-1" />
              {generatingDeck ? "Synthesizing..." : "AI Generate Deck"}
            </Button>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Decks Vault (4 cols) */}
        <div className="lg:col-span-4 space-y-4">
          <Card className="p-5">
            <div className="flex items-center justify-between mb-3.5">
              <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                <Layers className="w-4 h-4 text-indigo-600" />
                <span>Decks Vault</span>
              </h3>
              <Badge variant="clay" className="text-[10px]">{decks.length} Decks</Badge>
            </div>

            <div className="space-y-2">
              {decks.length === 0 ? (
                <p className="text-xs text-slate-400 py-4 text-center">No decks generated yet.</p>
              ) : (
                decks.map((d) => {
                  const isSelected = selectedDeckId === d.id;
                  const detailBadge = d.detail_level === "brief" 
                    ? { label: "Brief", variant: "neutral" as const }
                    : d.detail_level === "detailed"
                    ? { label: "Detailed", variant: "purple" as const }
                    : { label: "Semi-Detailed", variant: "default" as const };
                  return (
                    <button
                      key={d.id}
                      onClick={() => {
                        setSelectedDeckId(d.id);
                        loadCards(d.id);
                      }}
                      className={`w-full text-left p-3.5 rounded-2xl border transition-all cursor-pointer flex items-center justify-between ${
                        isSelected
                          ? "bg-gradient-to-r from-indigo-50 to-violet-50/60 border-indigo-400 shadow-xs ring-1 ring-indigo-400/30"
                          : "bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50/70"
                      }`}
                    >
                      <div className="overflow-hidden pr-2">
                        <div className="flex items-center gap-1.5 mb-0.5">
                          <p className={`font-bold text-xs sm:text-sm truncate ${isSelected ? "text-indigo-950" : "text-slate-800"}`}>
                            {d.title}
                          </p>
                        </div>
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className="text-[10px] px-1.5 py-0.5 rounded font-semibold bg-slate-100 text-slate-600">
                            {detailBadge.label}
                          </span>
                          <span className="text-[11px] text-slate-400 truncate">
                            {d.description || `${d.card_count} active recall cards`}
                          </span>
                        </div>
                      </div>
                      <span className={`text-xs font-bold px-2.5 py-1 rounded-full shrink-0 ${
                        isSelected ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-600"
                      }`}>
                        {d.card_count}
                      </span>
                    </button>
                  );
                })
              )}
            </div>
          </Card>

          {/* Quick study keyboard shortcuts */}
          <div className="clay-card-tint p-4 text-xs text-slate-600 rounded-2xl border border-slate-200/80 space-y-1.5">
            <p className="font-bold text-slate-800 text-[11px] uppercase tracking-wider flex items-center gap-1.5">
              <Zap className="w-3.5 h-3.5 text-amber-500" /> Keyboard Shortcuts
            </p>
            <div className="flex justify-between text-[11px]">
              <span className="text-slate-500">Flip card:</span>
              <kbd className="px-1.5 py-0.5 rounded bg-white border border-slate-200 font-mono text-[10px]">Space</kbd>
            </div>
            <div className="flex justify-between text-[11px]">
              <span className="text-slate-500">Next / Prev:</span>
              <div className="flex gap-1">
                <kbd className="px-1.5 py-0.5 rounded bg-white border border-slate-200 font-mono text-[10px]">←</kbd>
                <kbd className="px-1.5 py-0.5 rounded bg-white border border-slate-200 font-mono text-[10px]">→</kbd>
              </div>
            </div>
          </div>
        </div>

        {/* Center / Right Column: 3D Flashcard Player (8 cols) */}
        <div className="lg:col-span-8 space-y-5">
          {cards.length === 0 ? (
            <Card className="p-16 text-center text-slate-400">
              <CreditCard className="w-12 h-12 mx-auto mb-3 opacity-40 text-indigo-400" />
              <h3 className="font-bold text-base text-slate-700">No Flashcards in this Deck</h3>
              <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
                Generate flashcards using the top selector or explore another deck.
              </p>
            </Card>
          ) : (
            <div className="space-y-4">
              {/* Progress & Stats Bar */}
              <div className="clay-card p-4 rounded-2xl flex items-center justify-between gap-4">
                <div className="flex items-center gap-3 flex-1">
                  <span className="font-bold text-xs text-slate-800 shrink-0">
                    Card {currentCardIdx + 1} of {cards.length}
                  </span>
                  <div className="flex-1 bg-slate-100 rounded-full h-2 overflow-hidden border border-slate-200">
                    <div
                      className="bg-gradient-to-r from-indigo-500 to-violet-500 h-full rounded-full transition-all duration-300"
                      style={{ width: `${progressPct}%` }}
                    />
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <Badge variant="purple" className="text-[11px]">
                    {reviewedCount} Reviewed
                  </Badge>
                  <span className="text-xs text-slate-400 hidden sm:inline">• Click to flip</span>
                </div>
              </div>

              {/* 3D Perspective Flip Container */}
              <div className="perspective-1000 w-full min-h-[320px] cursor-pointer" onClick={() => setIsFlipped(!isFlipped)}>
                <div
                  className={`w-full min-h-[320px] transition-all duration-500 transform-style-preserve-3d relative rounded-3xl ${
                    isFlipped ? "rotate-y-180" : ""
                  }`}
                >
                  {/* FRONT FACE */}
                  <div className="clay-card absolute inset-0 backface-hidden p-8 flex flex-col justify-between rounded-3xl bg-white border border-slate-200/90 shadow-xl hover:border-indigo-300 transition-all select-none">
                    <div className="flex items-center justify-between gap-2 flex-wrap">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <Badge variant="default" className="text-xs px-3 py-1 font-bold">
                          Concept Prompt
                        </Badge>
                        {currentCard?.section_name && (
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 border border-slate-200">
                            📂 {currentCard.section_name}
                          </span>
                        )}
                        {currentCard?.concept_id && (
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-200">
                            #{currentCard.concept_id}
                          </span>
                        )}
                      </div>
                      <span className="text-xs text-slate-400 flex items-center gap-1">
                        <RotateCw className="w-3.5 h-3.5" /> Tap to reveal answer
                      </span>
                    </div>

                    <div className="my-auto py-6">
                      <p className="text-lg sm:text-2xl font-black text-slate-900 leading-snug tracking-tight">
                        {currentCard?.front}
                      </p>
                    </div>

                    <div className="pt-4 border-t border-slate-100 flex items-center justify-between text-xs">
                      {currentCard?.hint ? (
                        <p className="text-amber-700 italic flex items-center gap-1 font-medium text-xs">
                          💡 Hint: {currentCard.hint}
                        </p>
                      ) : (
                        <span className="text-slate-400 text-[11px]">Grounded conceptual prompt</span>
                      )}
                      <span className="text-indigo-600 font-semibold text-[11px]">Turn over →</span>
                    </div>
                  </div>

                  {/* BACK FACE */}
                  <div className="clay-card absolute inset-0 backface-hidden rotate-y-180 p-8 flex flex-col justify-between rounded-3xl bg-gradient-to-br from-slate-950 via-indigo-950 to-slate-900 text-white border border-indigo-500/30 shadow-2xl select-none">
                    <div className="flex items-center justify-between gap-2 flex-wrap">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <Badge variant="purple" className="bg-indigo-500/30 text-indigo-200 border-indigo-400/40 text-xs px-3 py-1 font-bold">
                          Active Recall Answer
                        </Badge>
                        {currentCard?.detail_level && (
                          <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-white/10 text-indigo-200">
                            {currentCard.detail_level}
                          </span>
                        )}
                      </div>
                      <span className="text-xs text-indigo-300 flex items-center gap-1">
                        <RotateCw className="w-3.5 h-3.5" /> Tap to flip back
                      </span>
                    </div>

                    <div className="my-auto py-5 space-y-3">
                      <p className="text-base sm:text-xl font-bold text-indigo-100 leading-relaxed">
                        {currentCard?.back}
                      </p>
                      {currentCard?.source_citation && (
                        <p className="text-[11px] text-indigo-300/80 bg-white/5 border border-white/10 rounded-xl p-2.5 font-mono">
                          📌 Source: {currentCard.source_citation}
                        </p>
                      )}
                    </div>

                    <div className="pt-4 border-t border-indigo-900/50 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                      <span className="text-slate-400 text-[11px]">
                        How well did you recall this concept?
                      </span>

                      {/* Recall rating buttons */}
                      <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                        <button
                          type="button"
                          onClick={() => handleRate("hard")}
                          className="px-3 py-1.5 rounded-xl bg-rose-500/20 text-rose-300 border border-rose-500/40 hover:bg-rose-500/30 font-bold text-xs cursor-pointer transition-colors"
                        >
                          Hard
                        </button>
                        <button
                          type="button"
                          onClick={() => handleRate("good")}
                          className="px-3 py-1.5 rounded-xl bg-indigo-500/30 text-indigo-200 border border-indigo-400/40 hover:bg-indigo-500/40 font-bold text-xs cursor-pointer transition-colors"
                        >
                          Good
                        </button>
                        <button
                          type="button"
                          onClick={() => handleRate("easy")}
                          className="px-3 py-1.5 rounded-xl bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 hover:bg-emerald-500/30 font-bold text-xs cursor-pointer transition-colors"
                        >
                          Easy
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Player Navigation Buttons */}
              <div className="flex items-center justify-between pt-2">
                <Button
                  variant="outline"
                  size="md"
                  onClick={handlePrev}
                  disabled={currentCardIdx === 0}
                  className="shadow-xs"
                >
                  <ChevronLeft className="w-4 h-4 mr-1" /> Previous Card
                </Button>

                <Button
                  variant="outline"
                  size="md"
                  onClick={() => setIsFlipped(!isFlipped)}
                  className="shadow-xs"
                >
                  <RotateCw className="w-4 h-4 mr-1.5" /> Flip
                </Button>

                <Button
                  variant="primary"
                  size="md"
                  onClick={handleNext}
                  disabled={currentCardIdx === cards.length - 1}
                  className="shadow-md shadow-indigo-600/25"
                >
                  Next Card <ChevronRight className="w-4 h-4 ml-1" />
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
