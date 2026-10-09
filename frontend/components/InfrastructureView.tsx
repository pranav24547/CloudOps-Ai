"use client";

import React, { useState } from "react";
import { Server, Database, Box, HardDrive, AlertTriangle, ShieldCheck, ShieldAlert, RefreshCw } from "lucide-react";

interface InfrastructureViewProps {
  resources: {
    instances?: any[];
    databases?: any[];
    buckets?: any[];
    alarms?: any[];
  };
  onRefresh: () => Promise<void>;
  isRefreshing: boolean;
}

export function InfrastructureView({ resources, onRefresh, isRefreshing }: InfrastructureViewProps) {
  const [subTab, setSubTab] = useState<"ec2" | "rds" | "s3" | "alarms">("ec2");

  const instances = resources.instances || [];
  const databases = resources.databases || [];
  const buckets = resources.buckets || [];
  const alarms = resources.alarms || [];

  return (
    <div className="space-y-6">
      {/* Top Header & Subtabs */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-base font-bold text-white">Live Infrastructure Map</h2>
          <p className="text-xs text-slate-400">Queried dynamically via AWS, GitHub & Docker Model Context Protocol (MCP) servers</p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex rounded-xl bg-slate-900/90 p-1 border border-slate-800 text-xs">
            <button
              onClick={() => setSubTab("ec2")}
              className={`rounded-lg px-3 py-1 font-semibold transition-all ${
                subTab === "ec2" ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-white"
              }`}
            >
              EC2 ({instances.length})
            </button>
            <button
              onClick={() => setSubTab("rds")}
              className={`rounded-lg px-3 py-1 font-semibold transition-all ${
                subTab === "rds" ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-white"
              }`}
            >
              RDS ({databases.length})
            </button>
            <button
              onClick={() => setSubTab("s3")}
              className={`rounded-lg px-3 py-1 font-semibold transition-all ${
                subTab === "s3" ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-white"
              }`}
            >
              S3 ({buckets.length})
            </button>
            <button
              onClick={() => setSubTab("alarms")}
              className={`rounded-lg px-3 py-1 font-semibold transition-all ${
                subTab === "alarms" ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-white"
              }`}
            >
              Alarms ({alarms.length})
            </button>
          </div>

          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-semibold text-slate-200 transition-all hover:bg-slate-700 disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* EC2 Tab */}
      {subTab === "ec2" && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {instances.map((inst: any) => {
            const isRunning = inst.state === "running";
            return (
              <div
                key={inst.instance_id}
                className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-5 shadow-xl transition-all hover:border-slate-700"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Server className="h-4 w-4 text-indigo-400" />
                    <span className="font-bold text-xs text-white">{inst.name || inst.instance_id}</span>
                  </div>
                  <span
                    className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${
                      isRunning ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" : "bg-slate-700 text-slate-300"
                    }`}
                  >
                    {inst.state}
                  </span>
                </div>

                <div className="mt-4 space-y-1.5 font-mono text-[11px] text-slate-400">
                  <div className="flex justify-between">
                    <span>ID:</span>
                    <span className="text-slate-200">{inst.instance_id}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Type:</span>
                    <span className="text-slate-200">{inst.instance_type}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Zone:</span>
                    <span className="text-slate-200">{inst.availability_zone}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Private IP:</span>
                    <span className="text-slate-200">{inst.private_ip || "—"}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Public IP:</span>
                    <span className="text-slate-200">{inst.public_ip || "None"}</span>
                  </div>
                </div>

                {inst.tags && Object.keys(inst.tags).length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1.5 pt-3 border-t border-slate-800">
                    {Object.entries(inst.tags).map(([k, v]) => (
                      <span key={k} className="rounded bg-slate-800/80 px-2 py-0.5 text-[10px] text-slate-300 font-mono">
                        {k}: {String(v)}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* RDS Tab */}
      {subTab === "rds" && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {databases.map((db: any) => (
            <div key={db.identifier} className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-5 shadow-xl">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Database className="h-4 w-4 text-emerald-400" />
                  <span className="font-bold text-xs text-white">{db.identifier}</span>
                </div>
                <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-bold text-emerald-400 border border-emerald-500/20 uppercase">
                  {db.status}
                </span>
              </div>

              <div className="mt-4 space-y-1.5 font-mono text-[11px] text-slate-400">
                <div className="flex justify-between">
                  <span>Engine:</span>
                  <span className="text-slate-200">{db.engine}</span>
                </div>
                <div className="flex justify-between">
                  <span>Class:</span>
                  <span className="text-slate-200">{db.class}</span>
                </div>
                <div className="flex justify-between">
                  <span>High Availability:</span>
                  <span className="text-emerald-400 font-semibold">Multi-AZ Active</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* S3 Tab */}
      {subTab === "s3" && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {buckets.map((b: any) => (
            <div key={b.name} className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-5 shadow-xl">
              <div className="flex items-center gap-2">
                <HardDrive className="h-4 w-4 text-purple-400" />
                <span className="font-bold text-xs text-white truncate" title={b.name}>{b.name}</span>
              </div>
              <div className="mt-3 font-mono text-[11px] text-slate-400">
                <div>Region: <span className="text-slate-200">{b.region}</span></div>
                <div className="mt-1 flex items-center gap-1.5 text-emerald-400 text-xs font-semibold">
                  <ShieldCheck className="h-3.5 w-3.5" />
                  <span>Public Access Blocked</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Alarms Tab */}
      {subTab === "alarms" && (
        <div className="space-y-3">
          {alarms.map((a: any) => {
            const isAlarm = a.state === "ALARM";
            return (
              <div
                key={a.name}
                className={`flex items-center justify-between rounded-xl border p-4 shadow-lg ${
                  isAlarm ? "border-rose-500/40 bg-rose-950/20" : "border-slate-800 bg-slate-900/60"
                }`}
              >
                <div className="flex items-center gap-3">
                  <AlertTriangle className={`h-5 w-5 ${isAlarm ? "text-rose-400 animate-pulse" : "text-slate-400"}`} />
                  <div>
                    <div className="font-bold text-xs text-white">{a.name}</div>
                    <div className="font-mono text-[11px] text-slate-400 mt-0.5">
                      Metric: {a.metric} • Condition: {a.threshold}
                    </div>
                  </div>
                </div>

                <span
                  className={`rounded-full px-2.5 py-1 text-xs font-bold uppercase ${
                    isAlarm ? "bg-rose-500 text-white shadow-md shadow-rose-500/30" : "bg-emerald-500/10 text-emerald-400"
                  }`}
                >
                  {a.state}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
