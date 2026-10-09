"use client";

import React, { useState } from "react";
import { AlertOctagon, CheckCircle2, XCircle, ShieldAlert, Cpu } from "lucide-react";

interface ApprovalRequest {
  id?: string;
  interrupt_id?: string;
  risk: string;
  actions: Array<{
    call_id: string;
    server: string;
    tool: string;
    arguments: Record<string, any>;
    risk: string;
    reason?: string;
  }>;
}

interface ApprovalModalProps {
  request: ApprovalRequest | null;
  onDecision: (approved: boolean, comment?: string) => Promise<void>;
  isSubmitting: boolean;
}

export function ApprovalModal({ request, onDecision, isSubmitting }: ApprovalModalProps) {
  const [comment, setComment] = useState("");

  if (!request) return null;

  const action = request.actions?.[0];
  const isHighRisk = request.risk?.toLowerCase() === "high";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-xl overflow-hidden rounded-2xl border border-rose-500/30 bg-[#0f172a] shadow-2xl shadow-rose-950/40">
        {/* Top Warning Banner */}
        <div className="flex items-center gap-3 bg-gradient-to-r from-rose-900/60 to-amber-900/40 px-6 py-4 border-b border-rose-500/20">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-rose-500/20 text-rose-400 border border-rose-500/30">
            <ShieldAlert className="h-5 w-5 animate-pulse" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              Action Approval Required
              <span className={`rounded-full px-2.5 py-0.5 text-xs font-black uppercase ${
                isHighRisk ? "bg-rose-500 text-white" : "bg-amber-500/20 text-amber-300 border border-amber-500/30"
              }`}>
                {request.risk} RISK
              </span>
            </h3>
            <p className="text-xs text-rose-200/80">
              The AI Agent is requesting authorization to execute an infrastructure modification.
            </p>
          </div>
        </div>

        {/* Content Body */}
        <div className="p-6 space-y-4">
          {/* Target Tool & Server */}
          <div className="rounded-xl bg-slate-900/80 border border-slate-800 p-4">
            <div className="text-xs text-slate-400 uppercase font-semibold">Target Operation</div>
            <div className="mt-1 font-mono text-sm text-indigo-300 font-semibold flex items-center gap-2">
              <span className="rounded bg-indigo-500/20 px-1.5 py-0.5 text-xs text-indigo-400">
                {action?.server?.toUpperCase()} MCP
              </span>
              <span>{action?.tool}()</span>
            </div>

            {/* Arguments */}
            <div className="mt-3">
              <span className="text-xs text-slate-400 font-semibold">Parameters:</span>
              <pre className="mt-1 overflow-x-auto rounded-lg bg-black/50 p-2.5 font-mono text-xs text-emerald-300">
                {JSON.stringify(action?.arguments || {}, null, 2)}
              </pre>
            </div>
          </div>

          {/* Reasoning */}
          {action?.reason && (
            <div className="rounded-xl bg-slate-900/50 border border-slate-800/80 p-4 text-xs">
              <span className="text-slate-400 font-semibold uppercase">Agent Justification:</span>
              <p className="mt-1 text-slate-300 italic">{action.reason}</p>
            </div>
          )}

          {/* Optional Approver Comment */}
          <div>
            <label className="text-xs font-semibold text-slate-400">
              Operator Notes / Comment (Recorded in Audit Ledger):
            </label>
            <input
              type="text"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="e.g., Approved after verifying on-call schedule"
              className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-900 px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
            />
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-3 border-t border-slate-800/80 bg-slate-900/40 px-6 py-4">
          <button
            onClick={() => onDecision(false, comment)}
            disabled={isSubmitting}
            className="flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-800 px-4 py-2 text-xs font-semibold text-slate-300 transition-all hover:bg-slate-700 hover:text-white disabled:opacity-50"
          >
            <XCircle className="h-4 w-4 text-slate-400" />
            Reject Action
          </button>

          <button
            onClick={() => onDecision(true, comment)}
            disabled={isSubmitting}
            className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 px-5 py-2 text-xs font-semibold text-white shadow-lg shadow-emerald-600/30 transition-all hover:from-emerald-500 hover:to-teal-500 disabled:opacity-50"
          >
            <CheckCircle2 className="h-4 w-4" />
            {isSubmitting ? "Executing..." : "Approve & Execute Action"}
          </button>
        </div>
      </div>
    </div>
  );
}
