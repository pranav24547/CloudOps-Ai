"use client";

import React, { useState, useRef, useEffect } from "react";
import { Send, Bot, User as UserIcon, Terminal, Clock, CheckCircle2, XCircle, AlertCircle, ChevronDown, ChevronRight, Sparkles } from "lucide-react";

export interface TimelineEvent {
  type: string;
  ts?: string;
  server?: string;
  tool?: string;
  arguments?: Record<string, any>;
  result?: string;
  duration_ms?: number;
  ok?: boolean;
  status?: string;
  risk?: string;
  text?: string;
  report?: string;
  message?: string;
  actions?: any[];
}

export interface ChatMessage {
  id: string;
  sender: "user" | "agent";
  text?: string;
  report?: string;
  timestamp: string;
  timeline?: TimelineEvent[];
}

interface AgentChatProps {
  messages: ChatMessage[];
  onSendMessage: (text: string) => Promise<void>;
  isLoading: boolean;
  liveTimeline: TimelineEvent[];
}

export function AgentChat({
  messages,
  onSendMessage,
  isLoading,
  liveTimeline,
}: AgentChatProps) {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, liveTimeline]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    const msg = input.trim();
    setInput("");
    onSendMessage(msg);
  };

  const quickPrompts = [
    { label: "🚨 Investigate Orders API Latency", text: "Production API latency suddenly increased. Find out what happened and fix it if possible." },
    { label: "🔄 Rollback Deployment #184", text: "Rollback orders-api deployment #184 to commit 8c1d5fa and verify application health." },
    { label: "🛡️ AWS Security Audit", text: "Check my AWS environment for security issues across S3 buckets and security groups." },
    { label: "💰 AWS Cost & Idle Instances", text: "Analyze AWS compute utilization and identify idle instances or cost optimizations." },
  ];

  return (
    <div className="flex h-[calc(100vh-16rem)] min-h-[500px] flex-col rounded-2xl border border-slate-800/80 bg-slate-900/60 shadow-2xl backdrop-blur-xl">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 px-6 py-3.5 bg-slate-950/40">
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
            <Bot className="h-4 w-4" />
          </div>
          <div>
            <h2 className="text-xs font-bold text-white">Autonomous Agent Conversation</h2>
            <p className="text-[10px] text-slate-400">Dynamic MCP tool calling with LangGraph state machine</p>
          </div>
        </div>

        {isLoading && (
          <div className="flex items-center gap-2 rounded-full bg-indigo-500/10 px-3 py-1 text-xs text-indigo-300 border border-indigo-500/20">
            <span className="h-2 w-2 rounded-full bg-indigo-400 animate-ping"></span>
            <span>Agent reasoning...</span>
          </div>
        )}
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center text-center max-w-md mx-auto">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 shadow-inner">
              <Sparkles className="h-7 w-7" />
            </div>
            <h3 className="mt-4 text-base font-bold text-white">Ready to operate infrastructure</h3>
            <p className="mt-1 text-xs text-slate-400 leading-relaxed">
              Ask CloudOps AI to investigate latency, inspect CloudWatch logs, correlate GitHub deployments, or audit security posture.
            </p>

            {/* Quick action buttons */}
            <div className="mt-6 flex flex-col gap-2 w-full">
              {quickPrompts.map((qp, i) => (
                <button
                  key={i}
                  onClick={() => onSendMessage(qp.text)}
                  className="rounded-xl border border-slate-800 bg-slate-950/60 px-4 py-2.5 text-left text-xs font-medium text-slate-300 transition-all hover:border-indigo-500/40 hover:bg-indigo-950/20 hover:text-white"
                >
                  {qp.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex gap-3.5 ${msg.sender === "user" ? "justify-end" : "justify-start"}`}
          >
            {msg.sender === "agent" && (
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-indigo-600 text-white shadow-md shadow-indigo-600/20">
                <Bot className="h-4 w-4" />
              </div>
            )}

            <div className={`max-w-2xl rounded-2xl p-4.5 text-xs shadow-md ${
              msg.sender === "user"
                ? "bg-gradient-to-r from-indigo-600 to-indigo-700 text-white rounded-tr-none"
                : "bg-slate-950/90 text-slate-200 border border-slate-800/90 rounded-tl-none"
            }`}>
              {msg.text && <p className="leading-relaxed whitespace-pre-wrap">{msg.text}</p>}

              {/* Historic Timeline if available */}
              {msg.timeline && msg.timeline.length > 0 && (
                <div className="mt-3 pt-3 border-t border-slate-800/80">
                  <TimelineList events={msg.timeline} />
                </div>
              )}

              {/* Final Report Block */}
              {msg.report && (
                <div className="mt-3 rounded-xl border border-slate-800 bg-black/40 p-4 font-sans text-xs prose prose-invert prose-xs max-w-none">
                  <div className="font-mono text-[10px] uppercase tracking-wider text-indigo-400 font-bold mb-2">
                    Autonomous Incident Analysis
                  </div>
                  <div className="whitespace-pre-wrap leading-relaxed text-slate-200">
                    {msg.report}
                  </div>
                </div>
              )}

              <span className="mt-2 block text-[10px] opacity-60 text-right">
                {new Date(msg.timestamp).toLocaleTimeString()}
              </span>
            </div>

            {msg.sender === "user" && (
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-slate-800 text-slate-300 border border-slate-700">
                <UserIcon className="h-4 w-4" />
              </div>
            )}
          </div>
        ))}

        {/* Live Active Timeline (events streaming in real-time) */}
        {isLoading && liveTimeline.length > 0 && (
          <div className="ml-11 max-w-2xl rounded-2xl border border-indigo-500/30 bg-slate-950/80 p-4 shadow-xl">
            <div className="flex items-center gap-2 mb-3 text-xs font-semibold text-indigo-300">
              <Terminal className="h-3.5 w-3.5" />
              <span>Real-Time MCP Execution Timeline</span>
            </div>
            <TimelineList events={liveTimeline} />
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Form */}
      <form onSubmit={handleSubmit} className="border-t border-slate-800 p-4 bg-slate-950/60">
        <div className="flex items-center gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your DevOps request (e.g. 'Investigate why orders-api latency is high')..."
            disabled={isLoading}
            className="flex-1 rounded-xl border border-slate-700 bg-slate-900/90 px-4 py-3 text-xs text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-600 text-white shadow-lg shadow-indigo-600/30 transition-all hover:bg-indigo-500 disabled:opacity-50"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </form>
    </div>
  );
}

function TimelineList({ events }: { events: TimelineEvent[] }) {
  const [expanded, setExpanded] = useState<Record<number, boolean>>({});

  const toggle = (idx: number) => {
    setExpanded((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  return (
    <div className="space-y-2 text-xs font-mono">
      {events.map((ev, idx) => {
        const isToolCall = ev.type === "tool_call_started" || ev.type === "tool_call_finished";
        if (!isToolCall && ev.type !== "approval_decision") return null;

        const isOk = ev.ok !== false;
        const isOpen = !!expanded[idx];

        return (
          <div key={idx} className="rounded-lg border border-slate-800/80 bg-slate-900/40 p-2.5">
            <div
              className="flex items-center justify-between cursor-pointer select-none"
              onClick={() => toggle(idx)}
            >
              <div className="flex items-center gap-2">
                {ev.type === "tool_call_started" ? (
                  <span className="h-2 w-2 rounded-full bg-amber-400 animate-pulse"></span>
                ) : isOk ? (
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                ) : (
                  <XCircle className="h-3.5 w-3.5 text-rose-400" />
                )}

                <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-indigo-300 font-semibold uppercase">
                  {ev.server}
                </span>

                <span className="text-slate-200 font-semibold">{ev.tool}()</span>
              </div>

              <div className="flex items-center gap-2">
                {ev.duration_ms !== undefined && (
                  <span className="text-[10px] text-slate-400">{ev.duration_ms}ms</span>
                )}
                {isOpen ? <ChevronDown className="h-3 w-3 text-slate-400" /> : <ChevronRight className="h-3 w-3 text-slate-400" />}
              </div>
            </div>

            {isOpen && (
              <div className="mt-2 space-y-1.5 border-t border-slate-800 pt-2 text-[11px]">
                {ev.arguments && (
                  <div>
                    <span className="text-slate-400">Args:</span>
                    <pre className="mt-0.5 overflow-x-auto rounded bg-black/40 p-1.5 text-slate-300">
                      {JSON.stringify(ev.arguments, null, 2)}
                    </pre>
                  </div>
                )}
                {ev.result && (
                  <div>
                    <span className="text-slate-400">Result:</span>
                    <pre className="mt-0.5 max-h-36 overflow-y-auto rounded bg-black/40 p-1.5 text-slate-300">
                      {typeof ev.result === "string" ? ev.result : JSON.stringify(ev.result, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
