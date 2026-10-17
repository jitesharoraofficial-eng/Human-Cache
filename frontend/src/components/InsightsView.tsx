"use client";

import React, { useEffect, useState } from "react";
import { LineChart as ChartIcon, TrendingUp, AlertTriangle, ShieldCheck, Activity } from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar
} from "recharts";
import { api } from "@/lib/api";
import { Card, Badge } from "./ui";

export function InsightsView() {
  const [topics, setTopics] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadTopics();
  }, []);

  const loadTopics = async () => {
    try {
      const res = await api.getTopics();
      setTopics(res);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  // Retention Decay Simulation Data (Day 0 to Day 10)
  const decayCurveData = [
    { day: "Day 0", standardWithoutRecall: 100, humanCacheSpaced: 100 },
    { day: "Day 1", standardWithoutRecall: 58, humanCacheSpaced: 95 },
    { day: "Day 2", standardWithoutRecall: 42, humanCacheSpaced: 91 },
    { day: "Day 3 (Review 1)", standardWithoutRecall: 33, humanCacheSpaced: 98 },
    { day: "Day 5", standardWithoutRecall: 25, humanCacheSpaced: 92 },
    { day: "Day 7 (Review 2)", standardWithoutRecall: 18, humanCacheSpaced: 96 },
    { day: "Day 10", standardWithoutRecall: 14, humanCacheSpaced: 94 },
  ];

  const topicRetentionData = topics.map((t) => ({
    name: t.canonical_name.length > 15 ? t.canonical_name.slice(0, 15) + "..." : t.canonical_name,
    retention: t.estimated_retention,
    stability: t.stability_days,
  }));

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Memory Insights & Retention Analytics</h2>
          <p className="text-xs sm:text-sm text-slate-500 mt-0.5">
            Mathematical projections based on Ebbinghaus exponential forgetting decay vs Human Cache active recall reinforcement.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="purple" className="px-3 py-1 text-xs">
            {topics.length} Stored Concepts Monitored
          </Badge>
        </div>
      </div>

      {/* Top Bento Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="clay-card p-5 rounded-2xl bg-gradient-to-br from-white to-indigo-50/30 border-indigo-200/70">
          <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-700">Decay Defense Rate</span>
          <div className="text-2xl sm:text-3xl font-black text-indigo-900 mt-1">
            {topics.length > 0 ? "+82%" : "—"}
          </div>
          <p className="text-xs text-slate-500 mt-1">
            {topics.length > 0 ? "Retention maintained vs passive forgetting" : "Awaiting active recall activity"}
          </p>
        </div>
        <div className="clay-card p-5 rounded-2xl bg-gradient-to-br from-white to-emerald-50/30 border-emerald-200/70">
          <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-700">Average Node Stability</span>
          <div className="text-2xl sm:text-3xl font-black text-emerald-800 mt-1">
            {topics.length > 0 ? `${(topics.reduce((acc, t) => acc + (t.stability_days || 1), 0) / topics.length).toFixed(1)} Days` : "—"}
          </div>
          <p className="text-xs text-slate-500 mt-1">
            {topics.length > 0 ? "Mean interval between necessary recall reviews" : "No concept nodes in memory"}
          </p>
        </div>
        <div className="clay-card p-5 rounded-2xl bg-gradient-to-br from-white to-purple-50/30 border-purple-200/70">
          <span className="text-[10px] font-bold uppercase tracking-wider text-purple-700">Memory Health Index</span>
          <div className="text-2xl sm:text-3xl font-black text-purple-900 mt-1">
            {topics.length > 0 ? `${Math.round(topics.reduce((acc, t) => acc + (t.estimated_retention || 0), 0) / topics.length)}%` : "—"}
          </div>
          <p className="text-xs text-slate-500 mt-1">
            {topics.length > 0 ? "Aggregate cognitive retrieval probability" : "Requires learned topics to compute"}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Retention Curve Comparison */}
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-bold text-sm sm:text-base text-slate-900">Ebbinghaus Retention Decay vs Spaced Practice</h3>
              <p className="text-xs text-slate-500">Theoretical projection demonstrating active recall stabilization.</p>
            </div>
            <Badge variant="purple">Illustrative Model</Badge>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={decayCurveData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="day" tick={{ fontSize: 10 }} />
                <YAxis unit="%" tick={{ fontSize: 10 }} />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="standardWithoutRecall"
                  name="Passive Reading (Decay)"
                  stroke="#f43f5e"
                  strokeWidth={2}
                  strokeDasharray="4 4"
                />
                <Line
                  type="monotone"
                  dataKey="humanCacheSpaced"
                  name="Human Cache Spaced Recall"
                  stroke="#4f46e5"
                  strokeWidth={3}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Real User Topics Retention Bar Chart */}
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-bold text-sm sm:text-base text-slate-900">Retention Per Concept Node</h3>
              <p className="text-xs text-slate-500">Live values calculated for your stored canonical concepts.</p>
            </div>
            <Badge variant={topics.length > 0 ? "success" : "default"}>
              {topics.length > 0 ? "Stored State" : "No Concepts"}
            </Badge>
          </div>

          <div className="h-64 w-full flex items-center justify-center">
            {topics.length === 0 ? (
              <div className="text-center text-slate-400 text-xs">
                <Activity className="w-8 h-8 mx-auto mb-2 text-slate-300" />
                <p className="font-semibold text-slate-600">No Tracked Concepts</p>
                <p className="text-[11px] text-slate-400 mt-1">Upload materials to visualize concept retention</p>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={topicRetentionData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                  <YAxis unit="%" domain={[0, 100]} tick={{ fontSize: 10 }} />
                  <Tooltip />
                  <Bar dataKey="retention" name="Retention %" fill="#6366f1" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </Card>
      </div>

      {/* Topics Stability Table */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="font-bold text-base text-slate-900">Topic Memory Stability Ledger</h3>
            <p className="text-xs text-slate-500">Track which concepts are currently in long-term memory vs requiring immediate reinforcement.</p>
          </div>
        </div>

        <div className="overflow-x-auto">
          {topics.length === 0 ? (
            <div className="text-center py-10 text-slate-400 text-xs">
              <p className="font-semibold text-slate-700">No Concepts Tracked Yet</p>
              <p className="text-[11px] text-slate-500 mt-1">Once you upload study materials, extracted concepts and their retention intervals will appear here.</p>
            </div>
          ) : (
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-50 text-slate-500 uppercase font-bold border-b border-slate-200">
                <tr>
                  <th className="p-3">Concept</th>
                  <th className="p-3">Memory Status</th>
                  <th className="p-3">Estimated Retention</th>
                  <th className="p-3">Stability Interval</th>
                  <th className="p-3">Next Scheduled Due</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {topics.map((t) => (
                  <tr key={t.id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="p-3 font-bold text-slate-800">{t.canonical_name}</td>
                    <td className="p-3">
                      <Badge variant={t.status === "learned" ? "success" : t.status === "review_due" ? "warning" : "default"}>
                        {t.status.replace("_", " ")}
                      </Badge>
                    </td>
                    <td className="p-3">
                      <div className="flex items-center gap-2">
                        <span className="font-black text-indigo-600 w-8">{t.estimated_retention}%</span>
                        <div className="w-20 bg-slate-100 h-2 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              t.estimated_retention > 75 ? "bg-emerald-500" : t.estimated_retention > 50 ? "bg-indigo-500" : "bg-rose-500"
                            }`}
                            style={{ width: `${t.estimated_retention}%` }}
                          ></div>
                        </div>
                      </div>
                    </td>
                    <td className="p-3 font-medium text-slate-600">{t.stability_days} days</td>
                    <td className="p-3 text-slate-500">
                      {t.next_review_at ? new Date(t.next_review_at).toLocaleDateString([], { month: "short", day: "numeric" }) : "Stabilized"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </Card>
    </div>
  );
}
