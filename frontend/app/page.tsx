"use client";

import React, { useState, useEffect } from "react";
import { Navbar } from "../components/Navbar";
import { HealthCards } from "../components/HealthCards";
import { AgentChat, ChatMessage, TimelineEvent } from "../components/AgentChat";
import { InfrastructureView } from "../components/InfrastructureView";
import { IncidentsView } from "../components/IncidentsView";
import { AuditView } from "../components/AuditView";
import { ApprovalModal } from "../components/ApprovalModal";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState<string>("agent");
  const [userRole, setUserRole] = useState<string>("operator");
  const [token, setToken] = useState<string>("");

  // Data states
  const [resources, setResources] = useState<any>({ instances: [], databases: [], buckets: [], alarms: [] });
  const [metrics, setMetrics] = useState<any>({});
  const [incidents, setIncidents] = useState<any[]>([]);
  const [auditEntries, setAuditEntries] = useState<any[]>([]);
  const [mcpStatus, setMcpStatus] = useState<Record<string, any>>({});
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Chat & Agent states
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [liveTimeline, setLiveTimeline] = useState<TimelineEvent[]>([]);
  const [pendingApproval, setPendingApproval] = useState<any | null>(null);
  const [isSubmittingApproval, setIsSubmittingApproval] = useState(false);
  const [activeApprovalId, setActiveApprovalId] = useState<string | null>(null);

  // 1. Initial Login based on selected role
  useEffect(() => {
    async function loginAsRole() {
      try {
        const credentials: Record<string, { email: string; pass: string }> = {
          operator: { email: "operator@cloudops.ai", pass: "operator123" },
          admin: { email: "admin@cloudops.ai", pass: "admin123" },
          viewer: { email: "viewer@cloudops.ai", pass: "viewer123" },
        };
        const cred = credentials[userRole] || credentials.operator;
        const res = await fetch(`${API_BASE}/api/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: cred.email, password: cred.pass }),
        });
        if (res.ok) {
          const data = await res.json();
          setToken(data.access_token);
        }
      } catch (err) {
        console.warn("Auth error or backend not yet up:", err);
      }
    }
    loginAsRole();
  }, [userRole]);

  // 2. Fetch dashboard data when token is ready
  const fetchData = async () => {
    if (!token) return;
    setIsRefreshing(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };

      const [resRes, resMet, resInc, resAud] = await Promise.all([
        fetch(`${API_BASE}/api/resources`, { headers }).then((r) => (r.ok ? r.json() : null)),
        fetch(`${API_BASE}/api/metrics`, { headers }).then((r) => (r.ok ? r.json() : null)),
        fetch(`${API_BASE}/api/incidents`, { headers }).then((r) => (r.ok ? r.json() : [])),
        fetch(`${API_BASE}/api/audit`, { headers }).then((r) => (r.ok ? r.json() : [])),
      ]);

      if (resRes) {
        setResources(resRes);
        if (resRes.mcp_servers) setMcpStatus(resRes.mcp_servers);
      }
      if (resMet) setMetrics(resMet);
      if (resInc) setIncidents(resInc);
      if (resAud) setAuditEntries(resAud);
    } catch (err) {
      console.error("Failed fetching data:", err);
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    if (token) {
      fetchData();
    }
  }, [token]);

  // 3. Process SSE chunk streams with buffering to prevent lost events
  const handleStream = async (reader: ReadableStreamDefaultReader<Uint8Array>, currentTimeline: TimelineEvent[]) => {
    const decoder = new TextDecoder();
    let accumulatedText = "";
    let finalReport = "";
    let approvalReq: any = null;
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      // Keep unfinished partial line in buffer
      buffer = lines.pop() ?? "";

      for (const rawLine of lines) {
        const line = rawLine.trim();
        if (!line.startsWith("data: ")) continue;
        const jsonStr = line.slice(6).trim();
        if (!jsonStr) continue;

        try {
          const ev: TimelineEvent = JSON.parse(jsonStr);
          currentTimeline.push(ev);
          setLiveTimeline([...currentTimeline]);

          if (ev.type === "agent_message" && ev.text) {
            accumulatedText = ev.text;
          } else if (ev.type === "final_report" && ev.report) {
            finalReport = ev.report;
          } else if (ev.type === "run_completed" && ev.report) {
            finalReport = ev.report;
          } else if (ev.type === "approval_required") {
            approvalReq = ev;
            setPendingApproval(ev);
            const directId = (ev as any).approval_id || (ev as any).actions?.[0]?.approval_id;
            if (directId) {
              setActiveApprovalId(directId);
            }
          }
        } catch {
          // ignore chunk parse errors
        }
      }
    }

    return { accumulatedText, finalReport, approvalReq };
  };

  // 4. Send user message to agent
  const handleSendMessage = async (text: string) => {
    if (!token || isLoading) return;

    const userMsg: ChatMessage = {
      id: `usr_${Date.now()}`,
      sender: "user",
      text,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);
    setLiveTimeline([]);

    try {
      const res = await fetch(`${API_BASE}/api/agent/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ message: text }),
      });

      if (!res.ok || !res.body) {
        throw new Error(`Agent error: ${res.statusText}`);
      }

      const timelineAcc: TimelineEvent[] = [];
      const reader = res.body.getReader();
      const { accumulatedText, finalReport, approvalReq } = await handleStream(reader, timelineAcc);

      // Check if we need to query the approvals list for matching record
      if (approvalReq) {
        const directId = approvalReq.approval_id || approvalReq.actions?.[0]?.approval_id;
        if (directId) {
          setActiveApprovalId(directId);
        } else {
          try {
            const apprListRes = await fetch(`${API_BASE}/api/approvals?status=pending`, {
              headers: { Authorization: `Bearer ${token}` },
            });
            if (apprListRes.ok) {
              const list = await apprListRes.json();
              const matched = list.find((item: any) =>
                (approvalReq.interrupt_id && item.interrupt_id === approvalReq.interrupt_id) ||
                (approvalReq.run_id && item.run_id === approvalReq.run_id)
              ) || list[0];
              if (matched) {
                setActiveApprovalId(matched.id);
              }
            }
          } catch (e) {
            console.warn("Could not query approvals list", e);
          }
        }
      }

      // Add agent response message
      if (accumulatedText || finalReport || timelineAcc.length > 0) {
        const agentMsg: ChatMessage = {
          id: `ag_${Date.now()}`,
          sender: "agent",
          text: accumulatedText || (approvalReq ? "Action requiring human approval proposed:" : undefined),
          report: finalReport,
          timestamp: new Date().toISOString(),
          timeline: [...timelineAcc],
        };
        setMessages((prev) => [...prev, agentMsg]);
      }

      // Refresh dashboard resources/audit
      fetchData();
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: `err_${Date.now()}`,
          sender: "agent",
          text: `⚠️ Error executing request: ${err.message}`,
          timestamp: new Date().toISOString(),
        },
      ]);
    } finally {
      setIsLoading(false);
      setLiveTimeline([]);
    }
  };

  // 5. Handle Human Decision on Approval
  const handleApprovalDecision = async (approved: boolean, comment?: string) => {
    if (!token || !activeApprovalId) {
      setPendingApproval(null);
      return;
    }

    setIsSubmittingApproval(true);
    try {
      const res = await fetch(`${API_BASE}/api/approval/${activeApprovalId}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ approved, comment }),
      });

      setPendingApproval(null);
      setActiveApprovalId(null);

      if (res.ok && res.body) {
        setIsLoading(true);
        const timelineAcc: TimelineEvent[] = [];
        const reader = res.body.getReader();
        const { accumulatedText, finalReport } = await handleStream(reader, timelineAcc);

        const resumedMsg: ChatMessage = {
          id: `ag_resumed_${Date.now()}`,
          sender: "agent",
          text: accumulatedText || (approved ? "Action approved. Executing and verifying result:" : "Action rejected by operator."),
          report: finalReport,
          timestamp: new Date().toISOString(),
          timeline: [...timelineAcc],
        };
        setMessages((prev) => [...prev, resumedMsg]);
        fetchData();
      }
    } catch (err: any) {
      console.error("Failed submitting approval:", err);
    } finally {
      setIsSubmittingApproval(false);
      setIsLoading(false);
      setLiveTimeline([]);
    }
  };

  // 6. Update Incident Status
  const handleUpdateIncident = async (incidentId: string, newStatus: string) => {
    if (!token) return;
    try {
      await fetch(`${API_BASE}/api/incidents/${incidentId}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ status: newStatus }),
      });
      fetchData();
    } catch (e) {
      console.error(e);
    }
  };

  // 7. Create Incident
  const handleCreateIncident = async (data: { title: string; severity: string; service: string }) => {
    if (!token) return;
    try {
      await fetch(`${API_BASE}/api/incidents`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(data),
      });
      fetchData();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="min-h-screen bg-[#090d16] text-slate-100 flex flex-col">
      {/* Navigation Bar */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        userRole={userRole}
        setUserRole={setUserRole}
        mcpStatus={mcpStatus}
      />

      {/* Main Container */}
      <main className="flex-1 mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Top Telemetry & Health Summary Cards */}
        <HealthCards resources={resources} metrics={metrics} />

        {/* Tab Content */}
        {activeTab === "agent" && (
          <AgentChat
            messages={messages}
            onSendMessage={handleSendMessage}
            isLoading={isLoading}
            liveTimeline={liveTimeline}
          />
        )}

        {activeTab === "infrastructure" && (
          <InfrastructureView
            resources={resources}
            onRefresh={fetchData}
            isRefreshing={isRefreshing}
          />
        )}

        {activeTab === "incidents" && (
          <IncidentsView
            incidents={incidents}
            onUpdateStatus={handleUpdateIncident}
            onCreateIncident={handleCreateIncident}
          />
        )}

        {activeTab === "audit" && (
          <AuditView entries={auditEntries} />
        )}
      </main>

      {/* Human Approval Modal */}
      <ApprovalModal
        request={pendingApproval}
        onDecision={handleApprovalDecision}
        isSubmitting={isSubmittingApproval}
      />
    </div>
  );
}
