# CloudOps AI Agent
### Autonomous Cloud Infrastructure & DevOps Assistant Powered by Model Context Protocol (MCP)

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Model Context Protocol](https://img.shields.io/badge/MCP-Protocol%20v1-green.svg)](https://modelcontextprotocol.io/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Stateful%20Graph-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 1. Project Overview

**CloudOps AI Agent** is a production-style, autonomous Site Reliability and DevOps assistant capable of operating real cloud infrastructure through the open **Model Context Protocol (MCP)**.

Rather than acting as a static chatbot that regurgitates generic AWS documentation, CloudOps AI acts as an **autonomous agentic system**:
- **Observes** live infrastructure across AWS (EC2, CloudWatch, RDS, S3), GitHub (commits, PRs, Actions), and Docker containers.
- **Reasons** over telemetry signals, correlating metrics, logs, and deployment timestamps across independent systems.
- **Selects tools dynamically** via standardized MCP discovery without hardcoded rules.
- **Gates sensitive operations** behind a strict **Human-in-the-Loop (HITL)** approval workflow.
- **Executes approved remediations** (restarts, rollbacks, workflow dispatches).
- **Verifies the result** post-remediation using observability probes to ensure the issue is truly resolved.
- **Maintains an auditable, tamper-resistant ledger** of all agent actions, tool calls, and human approvals.

---

## 2. Problem Statement

Modern cloud applications generate massive telemetry footprints across disparate silos:
- AWS CloudWatch CPU and memory metrics
- Distributed application logs and tracebacks
- Relational database IOPS and query latencies
- GitHub commit histories and CI/CD deployment pipelines
- Container daemon health states and restart counters

When a production outage or latency regression occurs, engineers must manually swivel across multiple browser consoles:
```text
Application Latency Spikes
         ↓
Check AWS EC2 Metrics
         ↓
Check CloudWatch Metrics & Logs
         ↓
Check RDS Latency & Active Connections
         ↓
Check GitHub Recent Commits & Deployments
         ↓
Correlate Timestamps & Isolate Root Cause
         ↓
Obtain Approvals & Apply Remediation
         ↓
Verify Recovery
```

**CloudOps AI Agent automates this multi-stage investigation and remediation loop end-to-end.**

---

## 3. Core Architecture

```text
                         ┌───────────────────────┐
                         │   Next.js Dashboard   │
                         └───────────┬───────────┘
                                     │ HTTP REST / SSE Stream
                                     ↓
                         ┌───────────────────────┐
                         │    FastAPI Backend    │
                         │ (JWT, RBAC, DB Ledger)│
                         └───────────┬───────────┘
                                     │
                                     ↓
                         ┌───────────────────────┐
                         │    LangGraph Agent    │
                         │(Cyclic Reasoning Flow)│
                         └───────────┬───────────┘
                                     │
                                     ↓
                         ┌───────────────────────┐
                         │    MCP Client Layer   │
                         └───────────┬───────────┘
                                     │
               ┌─────────────────────┼─────────────────────┐
               │ Streamable HTTP/Stdio│ Streamable HTTP/Stdio│ Streamable HTTP/Stdio
               ↓                     ↓                     ↓
      ┌────────────────┐    ┌────────────────┐    ┌────────────────┐
      │   AWS MCP      │    │   GitHub MCP   │    │   Docker MCP   │
      │    Server      │    │     Server     │    │     Server     │
      └───────┬────────┘    └───────┬────────┘    └───────┬────────┘
              │                     │                     │
              ↓                     ↓                     ↓
        AWS Services           GitHub API             Docker
     (EC2, CW, RDS, S3)      (Commits, Actions)    (Engine / SDK)
```

---

## 4. MCP Decoupling: Why MCP Wins

Without MCP, agents are tightly coupled to custom Python SDK wrappers:
```
LLM Agent ──> Proprietary Boto3 Wrapper ──> AWS
```

With the Model Context Protocol, the agent operates through an open standard:
```
LLM Agent ──> MCP Client ──[tools/list & tools/call]──> MCP Server ──> Real API
```

Benefits:
1. **Dynamic Tool Discovery:** The agent queries available tools at runtime via `tools/list`. Adding a new MCP server requires zero agent code changes.
2. **Standardized Tool Annotations:** Tools declare `readOnlyHint` and `destructiveHint`, enabling automated security risk categorization.
3. **Transport Flexibility:** Identical code runs over **Streamable HTTP** (for distributed microservices) or **Stdio** (for local CLI debugging).

---

## 5. Technology Stack

- **Agent Framework:** LangGraph (cyclic stateful execution, checkpoints, human interrupts)
- **Playbooks & Workflows:** Built-in playbooks for Incident Response, Security Audits, Deployment Safety, and Cost Optimization
- **Tool Protocol:** Model Context Protocol (MCP Python SDK v1)
- **Backend API:** FastAPI, Pydantic v2 / pydantic-settings, SQLAlchemy 2.0 (asyncio)
- **Databases:** PostgreSQL (production / Docker) & SQLite / aiosqlite (local dev fallback)
- **LLM Integrations:** Default provider is **Google Gemini** (`gemini-2.5-flash`), with swappable support for **Anthropic** (`claude-sonnet-4-5`), **OpenAI** (`gpt-4.1`), and a zero-dependency **Scripted Demo** (`LLM_PROVIDER=demo`)
- **Infrastructure as Code:** Terraform (AWS VPC, EC2, RDS, S3, CloudWatch)
- **Containerization:** Docker & Docker Compose (5 multi-stage container images)
- **CI/CD:** GitHub Actions (Ruff Lint, Pytest Suite, Multi-Image Docker Build)
- **Security:** JWT authentication, RBAC (Viewer, Operator, Admin), bcrypt, least-privilege IAM

---

## 6. Real-World Demonstration: Incident Investigation & Rollback

The system features a deterministic, realistic simulation scenario (`CLOUDOPS_MODE=demo`) that mirrors a real-world incident without requiring an active AWS bill. The simulated AWS and GitHub MCP servers share dynamic state (`sim_state.py`), so rolling back a deployment in GitHub immediately restores AWS latency baseline and resolves CloudWatch alarms during verification:

```text
USER:
"Production API latency suddenly increased. Find out what happened and fix it if possible."

AGENT:
Investigating infrastructure telemetry...

MCP → AWS (aws__get_recent_alarms)
  Found ALARM: 'orders-api-p99-latency-high'

MCP → AWS (aws__get_application_metrics)
  p99 latency spiked from 220ms → 2,800ms

MCP → AWS (aws__get_application_logs)
  Detected: "DB pool exhausted: timeout acquiring connection after 3000ms"
  Slow query: "SELECT o.*, i.* FROM orders o JOIN order_items i WHERE o.customer_email = $1"

MCP → AWS (aws__get_database_metrics)
  RDS read latency increased +340%
  Active database connections: 20/20 (maxed out)

MCP → GitHub (github__get_workflow_runs & github__get_recent_commits)
  Deployment #184 completed 13 minutes ago
  Commit 9f3c2ab: "add customer order history endpoint without composite index"

AGENT:
I have identified the root cause with 92% confidence.
Deployment #184 introduced an un-indexed JOIN query that exhausted database connections.

RECOMMENDED ACTION:
Rollback production deployment to previous stable release (commit 8c1d5fa).
Risk Level: HIGH
Human Approval Required.

[APPROVE]  [REJECT]
--------------------------------------------------------------------------------
HUMAN OPERATOR:
Approve.

AGENT:
Executing rollback...

MCP → GitHub (github__rollback_deployment)
  Rollback dispatch initiated for commit 8c1d5fa

MCP → AWS (aws__get_application_metrics & aws__get_recent_alarms)
  Post-action verification probe running...
  p99 latency returned to 215ms
  Alarms status: OK

AGENT:
✓ Incident Resolved.
Duration: 4 minutes 12 seconds.
Auditable report saved to database.
```

---

## 7. Security and Governance

### Risk-Based Tool Categorization
| Tier | Criteria | Tools | Approval Required? |
|---|---|---|:---:|
| **READ** | `readOnlyHint=True` | `list_ec2_instances`, `get_cpu_metrics`, `get_application_logs`, `list_buckets` | **No** |
| **LOW** | Non-destructive write | `create_issue`, `restart_container` | Configurable |
| **MEDIUM** | Disruptive, recoverable | `restart_ec2`, `start_ec2` | **Yes** |
| **HIGH** | Destructive / state-changing | `stop_ec2`, `rollback_deployment`, `trigger_workflow` | **Strict Yes** |

### Role-Based Access Control (RBAC)
- **`VIEWER`**: Can inspect infrastructure, view telemetry, and ask questions. Cannot execute writes or approvals.
- **`OPERATOR`**: Can initiate investigations and approve operational actions (restarts, rollbacks).
- **`ADMIN`**: Full platform management, user administration, and system configuration.

---

## 8. Quickstart & Local Installation

### Prerequisites
- Python 3.11+
- Node.js 20+ (for frontend dashboard)
- Git

### 1. Clone & Set Up Python Virtual Environment
```bash
git clone https://github.com/your-username/cloudops-ai-agent.git
cd cloudops-ai-agent

python -m venv .venv
# On Windows:
.\.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements-dev.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
*(By default, `CLOUDOPS_MODE=demo` is active with `LLM_PROVIDER=demo`, allowing complete end-to-end functionality without cloud credentials. If you provide a `GEMINI_API_KEY`, the agent automatically uses Google Gemini 2.5 Flash as the default model).*

### 3. Run the Automated Test Suite
Run the 22 comprehensive tests verifying all MCP servers, agent workflows, and backend endpoints:
```bash
pytest tests -v
```

### 4. Start the Services

#### Option A: Running with Docker Compose
```bash
docker compose up --build
```
- Dashboard: http://localhost:3000
- Backend API Docs: http://localhost:8000/docs
- AWS MCP Server: http://localhost:8101/mcp
- GitHub MCP Server: http://localhost:8102/mcp
- Docker MCP Server: http://localhost:8103/mcp

#### Option B: Running Natively with Launcher
```bash
python run_local.py
```
This boots all 3 MCP servers in background subprocesses and starts the FastAPI backend with hot reloading.

### 5. Default Development Accounts
| Role | Email | Password |
|---|---|---|
| **Admin** | `admin@cloudops.ai` | `admin123` |
| **Operator** | `operator@cloudops.ai` | `operator123` |
| **Viewer** | `viewer@cloudops.ai` | `viewer123` |

---

## 9. API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/login` | Authenticate user & issue JWT bearer token |
| `GET` | `/api/auth/me` | Current user profile & role |
| `POST` | `/api/agent/chat` | Stream autonomous agent reasoning via Server-Sent Events (SSE) |
| `GET` | `/api/resources` | Query EC2, RDS, S3, and Alarms via real-time MCP |
| `GET` | `/api/metrics` | Observability metrics on runs, tool calls, and infrastructure |
| `GET` | `/api/incidents` | List active and historical incidents |
| `POST` | `/api/incidents` | Create a new operational incident |
| `GET` | `/api/runs/{run_id}` | Detailed trace of an agent run including tool calls |
| `GET` | `/api/approvals` | List pending human approval requests |
| `POST` | `/api/approval/{id}` | Approve or reject a gated action (resumes agent via SSE) |
| `GET` | `/api/audit` | Query immutable audit log of all tool calls |

---

## 10. Infrastructure as Code (Terraform)

The `infrastructure/terraform/` directory contains modular Terraform configuration for AWS:
```bash
cd infrastructure/terraform
terraform init
terraform plan
```
Provisions:
- Multi-AZ VPC with public and private subnets, Internet Gateway, and Route Tables
- EC2 orders-api instances with CloudWatch agent monitoring
- Multi-AZ PostgreSQL RDS database with dedicated security groups
- Versioned S3 deployment artifact storage with Public Access Block
- CloudWatch metric alarms (CPU utilization, p99 latency) and application log groups

---

## 11. Resume Highlights

- **Agentic Cloud Operations:** Engineered an autonomous Site Reliability Assistant leveraging **LangGraph, Model Context Protocol (MCP), and FastAPI**, capable of dynamically diagnosing cloud latency issues and executing multi-step remediations.
- **Cross-Domain Signal Correlation:** Built multi-source correlation engine integrating **AWS CloudWatch, EC2, RDS, GitHub Actions, and Docker**, identifying database query regressions with over 90% confidence.
- **Zero-Trust Safety & Governance:** Implemented **Human-in-the-Loop (HITL)** graph interrupts for destructive operations, strict RBAC authorization, and an auditable ledger recording every tool call, risk tier, and operator decision.
- **Enterprise-Grade DevOps:** Authored modular **Terraform** IaC provisioning production AWS infrastructure, containerized microservices with **Docker Compose**, and implemented **GitHub Actions** CI/CD with automated test verification.
