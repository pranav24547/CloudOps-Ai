# CloudOps AI Agent Architecture

## 1. High-Level Architecture Overview

CloudOps AI is an agentic platform designed to operate live cloud infrastructure through the **Model Context Protocol (MCP)**. Rather than relying on rigid, pre-scripted automation or simple question-answering LLM chat, CloudOps AI decouples infrastructure reasoning from external APIs via standardized MCP clients and servers.

```
                         +-----------------------+
                         |      Web Browser      |
                         |   (Next.js Dashboard) |
                         +-----------+-----------+
                                     |  HTTP REST / SSE Stream
                                     v
                         +-----------------------+
                         |    FastAPI Backend    |
                         |   - JWT Auth & RBAC   |
                         |   - Audit Ledger      |
                         |   - State Checkpoint  |
                         +-----------+-----------+
                                     |
                                     v
                         +-----------------------+
                         |    LangGraph Agent    |
                         |   - Dynamic Reasoning |
                         |   - Policy Gatekeeper |
                         |   - HITL Interrupter  |
                         +-----------+-----------+
                                     |
                                     v
                         +-----------------------+
                         |   MCP Client Layer    |
                         | (Tools Discovery/Call)|
                         +-----------+-----------+
                                     |
         +---------------------------+---------------------------+
         | (HTTP/SSE or Stdio)       | (HTTP/SSE or Stdio)       | (HTTP/SSE or Stdio)
         v                           v                           v
+------------------+        +------------------+        +------------------+
|  AWS MCP Server  |        | GitHub MCP Server|        | Docker MCP Server|
| (Port 8101)      |        | (Port 8102)      |        | (Port 8103)      |
+--------+---------+        +--------+---------+        +--------+---------+
         |                           |                           |
         v                           v                           v
AWS Services (EC2, CW,      GitHub API / Actions        Docker Engine / SDK
RDS, S3, CloudTrail)
```

---

## 2. LangGraph State Machine Workflow

The agent uses a cyclic, stateful graph implemented in LangGraph:

```
[START]
   |
   v
[discover] ----> Connect to MCP servers, discover available tools via MCP tools/list
   |
   v
[reason] <----+
   |          |
   |-- (Needs tools?) --------------------------------------+
   |                                                        |
   |-- (Has conclusion?) --> [report] -> [END]              |
   |                                                        |
   v                                                        |
[gate] ---------> Validate arguments with JSONSchema        |
   |              Check user role RBAC                      |
   |              Check risk level & ToolAnnotations        |
   |                                                        |
   |-- (High/Med risk?) -> [approval] -> (Interrupt graph)  |
   |                              |                         |
   |                              +-> (Human approved)      |
   |                                     |                  |
   +-- (Read or auto-approved) ---------->+                  |
                                         |                  |
                                         v                  |
                                     [execute] -------------+
                                         | (Calls MCP tools/call)
                                         | (Records verification requirements)
```

### Key Graph Nodes

1. **`discover`**: Refreshes MCP servers at runtime. If a server is down or added dynamically, the LLM's available tool definitions change without requiring agent code modification.
2. **`reason`**: The LLM reasons over the user request and existing context. It selects one or more tool calls or formulates the final incident analysis report.
3. **`gate`**: Enforces zero-trust policy. Arguments are validated against tool input schemas. Actions with side effects (`restart_ec2`, `stop_ec2`, `rollback_deployment`) are flagged for human approval.
4. **`approval`**: Uses LangGraph's native `interrupt()`. The state is saved into the checkpointer. Execution freezes until an authenticated operator or admin posts an approval decision.
5. **`execute`**: Concurrently runs read tools, sequentially runs approved write tools, marks verification requirements, and appends `ToolMessage` payloads to the conversation state.
6. **`report`**: Emits the final structured markdown report and flags any unaddressed incident gaps.

---

## 3. Streaming and Auditing Flow

- All agent activities stream to the frontend via **Server-Sent Events (SSE)**.
- Every tool call, along with parameters, timestamps, execution latency in milliseconds, risk level, and approving human, is asynchronously committed to PostgreSQL / SQLite via SQLAlchemy.
