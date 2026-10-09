"use client";

import React from "react";
import { Activity, Shield, Terminal, Server, Cpu, CheckCircle2, AlertTriangle } from "lucide-react";

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  userRole: string;
  setUserRole: (role: string) => void;
  mcpStatus: Record<string, { status: string; tools?: number }>;
}

export function Navbar({
  activeTab,
  setActiveTab,
  userRole,
  setUserRole,
  mcpStatus,
}: NavbarProps) {
  const tabs = [
    { id: "agent", label: "Agent Console", icon: Terminal },
    { id: "infrastructure", label: "Infrastructure", icon: Server },
    { id: "incidents", label: "Incidents", icon: AlertTriangle },
    { id: "audit", label: "Audit Ledger", icon: Shield },
  ];

  return (
    <header className="sticky top-0 z-40 border-b border-slate-800 bg-[#0b1120]/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 shadow-lg shadow-indigo-500/20">
            <Cpu className="h-5 w-5 text-white" />
            <span className="absolute -right-0.5 -top-0.5 flex h-3 w-3">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex h-3 w-3 rounded-full bg-emerald-500"></span>
            </span>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-lg font-bold tracking-tight text-white">CloudOps<span className="text-indigo-400">.AI</span></span>
              <span className="rounded-full bg-indigo-500/10 px-2 py-0.5 text-xs font-semibold text-indigo-400 border border-indigo-500/20">
                MCP Agent
              </span>
            </div>
            <p className="text-xs text-slate-400">Autonomous Cloud & DevOps Assistant</p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="hidden md:flex items-center gap-1 rounded-xl bg-slate-900/60 p-1 border border-slate-800/80">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 rounded-lg px-3.5 py-1.5 text-xs font-medium transition-all ${
                  isActive
                    ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
                }`}
              >
                <Icon className="h-3.5 w-3.5" />
                {tab.label}
              </button>
            );
          })}
        </nav>

        {/* Right Section: MCP Server Pills & Role Selector */}
        <div className="flex items-center gap-4">
          {/* MCP Server Indicators */}
          <div className="hidden lg:flex items-center gap-2 text-xs">
            {["aws", "github", "docker"].map((server) => {
              const info = mcpStatus[server];
              const isConnected = info?.status === "connected";
              return (
                <div
                  key={server}
                  className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 border ${
                    isConnected
                      ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                      : "border-slate-800 bg-slate-900 text-slate-400"
                  }`}
                  title={`${server.toUpperCase()} MCP Server: ${info?.status || "connecting"}`}
                >
                  <span className={`h-1.5 w-1.5 rounded-full ${isConnected ? "bg-emerald-400" : "bg-amber-400"}`}></span>
                  <span className="font-mono text-[11px] uppercase">{server}</span>
                  {info?.tools ? <span className="text-[10px] opacity-70">({info.tools})</span> : null}
                </div>
              );
            })}
          </div>

          {/* User Role Selector */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">Role:</span>
            <select
              value={userRole}
              onChange={(e) => setUserRole(e.target.value)}
              className="rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-1 text-xs font-semibold text-indigo-300 focus:border-indigo-500 focus:outline-none"
            >
              <option value="operator">OPERATOR (Read/Write)</option>
              <option value="admin">ADMIN (All)</option>
              <option value="viewer">VIEWER (Read-Only)</option>
            </select>
          </div>
        </div>
      </div>
    </header>
  );
}
