import React from "react";
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function Badge({
  children,
  variant = "default",
  className = ""
}: {
  children: React.ReactNode;
  variant?: "default" | "success" | "warning" | "danger" | "purple" | "outline" | "clay";
  className?: string;
}) {
  const styles = {
    default: "bg-blue-50 text-blue-700 border-blue-200/80 shadow-xs",
    success: "bg-emerald-50 text-emerald-700 border-emerald-200/80 shadow-xs",
    warning: "bg-amber-50 text-amber-700 border-amber-200/80 shadow-xs",
    danger: "bg-rose-50 text-rose-700 border-rose-200/80 shadow-xs",
    purple: "bg-indigo-50 text-indigo-700 border-indigo-200/80 shadow-xs",
    outline: "border-slate-200 text-slate-700 bg-white shadow-xs",
    clay: "bg-slate-100 text-slate-800 border-slate-200/90 shadow-inner"
  };
  return (
    <span
      className={cn(
        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border transition-all",
        styles[variant],
        className
      )}
    >
      {children}
    </span>
  );
}

export function Card({
  children,
  className = "",
  interactive = false
}: {
  children: React.ReactNode;
  className?: string;
  interactive?: boolean;
}) {
  return (
    <div
      className={cn(
        interactive ? "clay-card-interactive" : "clay-card",
        "p-5 md:p-6",
        className
      )}
    >
      {children}
    </div>
  );
}

export function Button({
  children,
  onClick,
  variant = "primary",
  size = "md",
  disabled = false,
  className = "",
  type = "button",
  title = ""
}: {
  children: React.ReactNode;
  onClick?: () => void;
  variant?: "primary" | "secondary" | "outline" | "danger" | "ghost" | "clay";
  size?: "sm" | "md" | "lg";
  disabled?: boolean;
  className?: string;
  type?: "button" | "submit";
  title?: string;
}) {
  const base =
    "inline-flex items-center justify-center font-medium rounded-xl transition-all focus:outline-hidden disabled:opacity-50 disabled:pointer-events-none cursor-pointer active:scale-95";
  const sizes = {
    sm: "px-3 py-1.5 text-xs gap-1.5 rounded-lg",
    md: "px-4 py-2 text-sm gap-2 rounded-xl",
    lg: "px-6 py-3 text-base gap-2.5 rounded-2xl shadow-md"
  };
  const variants = {
    primary:
      "bg-gradient-to-r from-indigo-600 to-violet-600 text-white hover:from-indigo-700 hover:to-violet-700 shadow-md shadow-indigo-500/20 border border-indigo-500/30",
    secondary:
      "bg-slate-100 text-slate-800 hover:bg-slate-200 border border-slate-200 shadow-xs",
    outline:
      "border border-slate-300/90 text-slate-700 hover:bg-slate-50 shadow-xs bg-white",
    danger:
      "bg-rose-600 text-white hover:bg-rose-700 shadow-xs border border-rose-500",
    ghost:
      "text-slate-600 hover:bg-slate-100 hover:text-slate-900 border border-transparent",
    clay:
      "bg-white text-indigo-700 hover:bg-indigo-50/50 border border-indigo-100 shadow-sm"
  };

  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      title={title}
      className={cn(base, sizes[size], variants[variant], className)}
    >
      {children}
    </button>
  );
}

export function ProgressBar({
  value,
  max = 100,
  className = "",
  color = "indigo"
}: {
  value: number;
  max?: number;
  className?: string;
  color?: "indigo" | "emerald" | "amber" | "rose";
}) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  const colorMap = {
    indigo: "bg-indigo-600",
    emerald: "bg-emerald-500",
    amber: "bg-amber-500",
    rose: "bg-rose-500"
  };
  return (
    <div className={cn("w-full bg-slate-200/80 rounded-full h-2 overflow-hidden", className)}>
      <div
        className={cn("h-full rounded-full transition-all duration-500", colorMap[color])}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  actionLabel,
  onAction
}: {
  icon: React.ElementType;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
}) {
  return (
    <div className="clay-card-tint p-8 text-center rounded-2xl border border-dashed border-slate-300 flex flex-col items-center justify-center">
      <div className="w-12 h-12 rounded-2xl bg-indigo-50 border border-indigo-200 flex items-center justify-center text-indigo-600 mb-3 shadow-xs">
        <Icon className="w-6 h-6" />
      </div>
      <h3 className="text-sm font-bold text-slate-800">{title}</h3>
      <p className="text-xs text-slate-500 mt-1 max-w-sm">{description}</p>
      {actionLabel && onAction && (
        <Button size="sm" variant="primary" onClick={onAction} className="mt-4">
          {actionLabel}
        </Button>
      )}
    </div>
  );
}
