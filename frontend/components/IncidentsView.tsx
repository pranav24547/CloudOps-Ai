"use client";

import React, { useState } from "react";
import { AlertCircle, CheckCircle2, Clock, PlusCircle } from "lucide-react";

interface Incident {
  id: string;
  title: string;
  severity: string;
  status: string;
  service: string;
  root_cause?: string;
  resolution?: string;
  created_at: string;
  resolved_at?: string;
}

interface IncidentsViewProps {
  incidents: Incident[];
  onUpdateStatus: (incidentId: string, newStatus: string) => Promise<void>;
  onCreateIncident: (data: { title: string; severity: string; service: string }) => Promise<void>;
}

export function IncidentsView({
  incidents,
  onUpdateStatus,
  onCreateIncident,
}: IncidentsViewProps) {
  const [showCreate, setShowCreate] = useState(false);
  const [title, setTitle] = useState("");
  const [severity, setSeverity] = useState("HIGH");
  const [service, setService] = useState("orders-api");

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    await onCreateIncident({ title, severity, service });
    setTitle("");
    setShowCreate(false);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-base font-bold text-white">Incident Response & Tracking</h2>
          <p className="text-xs text-slate-400">Auditable operational incident lifecycle managed by CloudOps AI</p>
        </div>

        <button
          onClick={() => setShowCreate(!showCreate)}
          className="flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-lg shadow-indigo-600/30 transition-all hover:bg-indigo-500"
        >
          <PlusCircle className="h-4 w-4" />
          Report Incident
        </button>
      </div>

      {/* Create Incident Modal / Inline Box */}
      {showCreate && (
        <form onSubmit={handleCreate} className="rounded-2xl border border-indigo-500/30 bg-slate-900/90 p-5 shadow-xl space-y-4">
          <h3 className="text-xs font-bold uppercase text-indigo-400">Declare Operational Incident</h3>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div className="sm:col-span-2">
              <label className="text-xs text-slate-400 font-semibold">Incident Title:</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g., Latency spike on orders API after v1.8.4 deployment"
                className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-white focus:border-indigo-500 focus:outline-none"
                required
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 font-semibold">Severity:</label>
              <select
                value={severity}
                onChange={(e) => setSeverity(e.target.value)}
                className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-white focus:border-indigo-500 focus:outline-none font-semibold"
              >
                <option value="CRITICAL">CRITICAL (Sev 1)</option>
                <option value="HIGH">HIGH (Sev 2)</option>
                <option value="MEDIUM">MEDIUM (Sev 3)</option>
                <option value="LOW">LOW (Sev 4)</option>
              </select>
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setShowCreate(false)}
              className="rounded-xl border border-slate-700 px-3.5 py-1.5 text-xs text-slate-400 hover:text-white"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="rounded-xl bg-indigo-600 px-4 py-1.5 text-xs font-semibold text-white shadow hover:bg-indigo-500"
            >
              Submit Incident
            </button>
          </div>
        </form>
      )}

      {/* Incidents List */}
      <div className="space-y-4">
        {incidents.length === 0 ? (
          <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-8 text-center text-xs text-slate-400">
            No incidents recorded. All services operating normally.
          </div>
        ) : (
          incidents.map((inc) => {
            const isResolved = inc.status === "RESOLVED";
            return (
              <div
                key={inc.id}
                className={`rounded-2xl border p-5 shadow-xl transition-all ${
                  isResolved
                    ? "border-slate-800/80 bg-slate-900/40"
                    : "border-rose-500/30 bg-slate-900/80"
                }`}
              >
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-center gap-3">
                    <span
                      className={`rounded-full px-2.5 py-0.5 text-[10px] font-black uppercase ${
                        inc.severity === "CRITICAL"
                          ? "bg-rose-600 text-white"
                          : inc.severity === "HIGH"
                          ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                          : "bg-blue-500/20 text-blue-300"
                      }`}
                    >
                      {inc.severity}
                    </span>
                    <h3 className="font-bold text-sm text-white">{inc.title}</h3>
                  </div>

                  {/* Status Dropdown */}
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-400">Status:</span>
                    <select
                      value={inc.status}
                      onChange={(e) => onUpdateStatus(inc.id, e.target.value)}
                      className="rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1 text-xs font-semibold text-slate-200 focus:border-indigo-500 focus:outline-none"
                    >
                      <option value="OPEN">OPEN</option>
                      <option value="INVESTIGATING">INVESTIGATING</option>
                      <option value="MITIGATED">MITIGATED</option>
                      <option value="RESOLVED">RESOLVED</option>
                    </select>
                  </div>
                </div>

                {/* Details */}
                <div className="mt-3 grid grid-cols-1 gap-2 text-xs text-slate-300 sm:grid-cols-2 pt-3 border-t border-slate-800/80">
                  <div>
                    <span className="text-slate-500 font-semibold">Service:</span> {inc.service}
                  </div>
                  <div>
                    <span className="text-slate-500 font-semibold">Opened:</span> {new Date(inc.created_at).toLocaleString()}
                  </div>
                  {inc.root_cause && (
                    <div className="sm:col-span-2 rounded-lg bg-black/40 p-2.5 text-xs font-mono text-slate-300">
                      <span className="text-indigo-400 font-bold">Identified Root Cause:</span> {inc.root_cause}
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
