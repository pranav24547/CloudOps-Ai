"use client";

import React, { useState } from "react";
import { Shield, CheckCircle2, XCircle, ChevronDown, ChevronRight, Search } from "lucide-react";

interface AuditEntry {
  id: string;
  run_id: string;
  user_request?: string;
  server: string;
  tool: string;
  arguments: Record<string, any>;
  result?: string;
  duration_ms: number;
  ok: boolean;
  risk: string;
  reason?: string;
  approved_by?: string;
  timestamp: string;
}

interface AuditViewProps {
  entries: AuditEntry[];
}

export function AuditView({ entries }: AuditViewProps) {
  const [filterServer, setFilterServer] = useState<string>("all");
  const [filterRisk, setFilterRisk] = useState<string>("all");
  const [search, setSearch] = useState<string>("");
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const toggle = (id: string) => {
    setExpanded((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const filtered = entries.filter((e) => {
    if (filterServer !== "all" && e.server !== filterServer) return false;
    if (filterRisk !== "all" && e.risk !== filterRisk) return false;
    if (search && !e.tool.toLowerCase().includes(search.toLowerCase()) && !e.server.toLowerCase().includes(search.toLowerCase())) {
      return false;
    }
    return true;
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <Shield className="h-5 w-5 text-indigo-400" />
            Immutable Audit Ledger
          </h2>
          <p className="text-xs text-slate-400">Complete cryptographically verifiable record of every MCP tool call, argument, and authorization</p>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-2.5">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search tools..."
            className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
          />

          <select
            value={filterServer}
            onChange={(e) => setFilterServer(e.target.value)}
            className="rounded-xl border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-xs font-semibold text-slate-200"
          >
            <option value="all">All Servers</option>
            <option value="aws">AWS MCP</option>
            <option value="github">GitHub MCP</option>
            <option value="docker">Docker MCP</option>
          </select>

          <select
            value={filterRisk}
            onChange={(e) => setFilterRisk(e.target.value)}
            className="rounded-xl border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-xs font-semibold text-slate-200"
          >
            <option value="all">All Risks</option>
            <option value="read">READ</option>
            <option value="low">LOW</option>
            <option value="medium">MEDIUM</option>
            <option value="high">HIGH</option>
          </select>
        </div>
      </div>

      {/* Ledger Table */}
      <div className="overflow-hidden rounded-2xl border border-slate-800/80 bg-slate-900/60 shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/60 text-[11px] font-bold uppercase tracking-wider text-slate-400 border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4">MCP Server</th>
                <th className="py-3 px-4">Tool Invocation</th>
                <th className="py-3 px-4">Risk Tier</th>
                <th className="py-3 px-4">Latency</th>
                <th className="py-3 px-4">Approved By</th>
                <th className="py-3 px-4 text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono text-xs">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-500 font-sans">
                    No matching audit records found.
                  </td>
                </tr>
              ) : (
                filtered.map((item) => {
                  const isOpen = !!expanded[item.id];
                  const isHigh = item.risk === "high";
                  const isMedium = item.risk === "medium";

                  return (
                    <React.Fragment key={item.id}>
                      <tr className="hover:bg-slate-800/30 transition-colors">
                        <td className="py-3 px-4">
                          {item.ok ? (
                            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                          ) : (
                            <XCircle className="h-4 w-4 text-rose-400" />
                          )}
                        </td>
                        <td className="py-3 px-4 text-slate-400 text-[11px]">
                          {new Date(item.timestamp).toLocaleTimeString()}
                        </td>
                        <td className="py-3 px-4">
                          <span className="rounded bg-slate-800 px-2 py-0.5 text-[10px] font-bold uppercase text-indigo-300">
                            {item.server}
                          </span>
                        </td>
                        <td className="py-3 px-4 font-semibold text-slate-200">
                          {item.tool}()
                        </td>
                        <td className="py-3 px-4">
                          <span
                            className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${
                              isHigh
                                ? "bg-rose-500/20 text-rose-400 border border-rose-500/30"
                                : isMedium
                                ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                                : "bg-slate-800 text-slate-400"
                            }`}
                          >
                            {item.risk}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-slate-400">{item.duration_ms}ms</td>
                        <td className="py-3 px-4 text-slate-300 font-sans text-xs">
                          {item.approved_by || "—"}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <button
                            onClick={() => toggle(item.id)}
                            className="rounded-lg p-1 hover:bg-slate-800 text-slate-400 hover:text-white"
                          >
                            {isOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                          </button>
                        </td>
                      </tr>

                      {isOpen && (
                        <tr className="bg-black/30 font-sans">
                          <td colSpan={8} className="p-4 space-y-2">
                            {item.user_request && (
                              <div className="text-xs">
                                <span className="text-slate-400 font-semibold">User Request:</span>{" "}
                                <span className="text-slate-200 italic">"{item.user_request}"</span>
                              </div>
                            )}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs font-mono">
                              <div>
                                <span className="text-slate-400 font-semibold font-sans">Parameters:</span>
                                <pre className="mt-1 overflow-x-auto rounded bg-slate-950 p-2 text-emerald-300 text-[11px]">
                                  {JSON.stringify(item.arguments || {}, null, 2)}
                                </pre>
                              </div>
                              <div>
                                <span className="text-slate-400 font-semibold font-sans">Return Payload:</span>
                                <pre className="mt-1 max-h-40 overflow-y-auto rounded bg-slate-950 p-2 text-slate-300 text-[11px]">
                                  {item.result || "None"}
                                </pre>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
