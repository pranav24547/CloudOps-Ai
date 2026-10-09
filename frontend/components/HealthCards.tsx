"use client";

import React from "react";
import { Server, Database, Box, AlertTriangle, CheckCircle, HardDrive } from "lucide-react";

interface HealthCardsProps {
  resources: {
    instances?: Array<{ state: string; name?: string }>;
    databases?: Array<{ status: string; identifier?: string }>;
    buckets?: Array<{ name: string }>;
    alarms?: Array<{ state: string; name: string }>;
  };
  metrics?: {
    agent?: { total_runs: number; total_tool_calls: number };
    incidents?: { open: number };
  };
}

export function HealthCards({ resources, metrics }: HealthCardsProps) {
  const instances = resources.instances || [];
  const databases = resources.databases || [];
  const buckets = resources.buckets || [];
  const alarms = resources.alarms || [];

  const runningInstances = instances.filter((i) => i.state === "running").length;
  const activeAlarms = alarms.filter((a) => a.state === "ALARM").length;

  const cards = [
    {
      title: "EC2 Compute",
      count: instances.length,
      detail: `${runningInstances} Running • ${instances.length - runningInstances} Stopped`,
      status: runningInstances > 0 ? "healthy" : "warning",
      icon: Server,
      gradient: "from-blue-500/20 to-indigo-500/10",
      accent: "text-blue-400",
    },
    {
      title: "RDS Databases",
      count: databases.length,
      detail: `${databases.filter((d) => d.status === "available").length} Available (Multi-AZ)`,
      status: "healthy",
      icon: Database,
      gradient: "from-emerald-500/20 to-teal-500/10",
      accent: "text-emerald-400",
    },
    {
      title: "CloudWatch Alarms",
      count: activeAlarms,
      detail: activeAlarms > 0 ? `${activeAlarms} In Alarm State` : "All Systems Nominal",
      status: activeAlarms > 0 ? "critical" : "healthy",
      icon: AlertTriangle,
      gradient: activeAlarms > 0 ? "from-rose-500/30 to-amber-500/20" : "from-emerald-500/20 to-teal-500/10",
      accent: activeAlarms > 0 ? "text-rose-400" : "text-emerald-400",
      pulse: activeAlarms > 0,
    },
    {
      title: "S3 Storage",
      count: buckets.length,
      detail: "Encrypted & Versioned",
      status: "healthy",
      icon: HardDrive,
      gradient: "from-purple-500/20 to-pink-500/10",
      accent: "text-purple-400",
    },
  ];

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((card, idx) => {
        const Icon = card.icon;
        return (
          <div
            key={idx}
            className={`relative overflow-hidden rounded-2xl border border-slate-800/80 bg-slate-900/60 p-5 shadow-xl transition-all hover:border-slate-700 hover:shadow-2xl`}
          >
            {/* Background ambient gradient */}
            <div className={`absolute -right-8 -top-8 h-28 w-28 rounded-full bg-gradient-to-br ${card.gradient} blur-2xl`}></div>

            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                {card.title}
              </span>
              <div className={`rounded-xl bg-slate-800/70 p-2.5 ${card.accent}`}>
                <Icon className={`h-4 w-4 ${card.pulse ? "animate-pulse" : ""}`} />
              </div>
            </div>

            <div className="mt-4 flex items-baseline gap-2">
              <span className="text-3xl font-extrabold tracking-tight text-white">
                {card.count}
              </span>
              {card.pulse && (
                <span className="inline-flex items-center rounded-full bg-rose-500/10 px-2 py-0.5 text-xs font-medium text-rose-400 border border-rose-500/20">
                  Critical
                </span>
              )}
            </div>

            <p className="mt-2 text-xs text-slate-400">{card.detail}</p>
          </div>
        );
      })}
    </div>
  );
}
