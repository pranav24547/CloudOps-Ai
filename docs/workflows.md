# Supported Autonomous CloudOps Workflows

CloudOps AI ships with 5 core agentic workflows:

---

## Workflow 1: Incident Investigation & Multi-Source Correlation

**Prompt Trigger:** *"Investigate why my application is experiencing high latency."*

1. **Alarms Detection:** Agent queries `aws__get_recent_alarms` and identifies `orders-api-p99-latency-high`.
2. **Signal Correlation:**
   - `aws__get_application_metrics`: p99 latency spiked from 220ms to 2800ms.
   - `aws__get_cpu_metrics`: EC2 CPU utilization at 91%.
   - `aws__get_application_logs`: Repeated `DB pool exhausted: timeout acquiring connection after 3000ms`.
   - `aws__get_database_metrics`: RDS read latency up +340%, active database connections maxed.
3. **CI/CD Integration:**
   - `github__get_workflow_runs`: Deployment #184 completed 13 minutes ago.
   - `github__get_commit_details`: Commit `9f3c2ab` added an un-indexed JOIN query across `orders` and `order_items`.
4. **Root Cause Analysis:** Concludes that deployment #184 introduced the database regression with 92% confidence.
5. **Remediation Recommendation:** Proposes rollback to commit `8c1d5fa`.

---

## Workflow 2: Automated Deployment Rollback & Verification

**Prompt Trigger:** *"Rollback deployment #184 and verify application health."*

1. **Pre-check:** Confirms deployment status and target rollback commit.
2. **Approval Gating:** Rollback is flagged as `HIGH` risk. LangGraph halts for human approval.
3. **Execution:** Once approved, calls `github__rollback_deployment` or `docker__restart_container`.
4. **Post-Action Verification:**
   - Queries `aws__get_ec2_status` and `aws__get_application_metrics`.
   - Verifies p99 latency returns to ~220ms.
   - Verifies CloudWatch alarms resolve back to `OK`.

---

## Workflow 3: Cloud Security Audit

**Prompt Trigger:** *"Run a security audit on my AWS infrastructure."*

1. **S3 Audit:** Evaluates bucket policies, Public Access Block configurations, and open ACLs.
2. **Security Groups:** Analyzes ingress rules for unrestricted SSH (port 22) or open database ports.
3. **IAM & Credentials:** Checks for inactive keys and un-restricted policies.
4. **Report:** Generates categorized findings (CRITICAL, HIGH, MEDIUM, LOW) with remediation steps.

---

## Workflow 4: Cost & Utilization Optimization

**Prompt Trigger:** *"Analyze AWS costs and identify opportunities for optimization."*

1. **Idle Compute:** Discovers instances running at < 5% CPU utilization.
2. **Orphaned Storage:** Detects stopped EC2 instances retaining unattached or redundant EBS volumes.
3. **Database Rightsizing:** Compares provisioned IOPS against baseline query traffic.
4. **Report:** Projects monthly savings and suggests rightsizing candidates.

---

## Workflow 5: Container Crash-Loop Remediation

**Prompt Trigger:** *"Orders API container is crashing. Diagnose and recover it."*

1. Inspects container runtime state with `docker__get_container_status`.
2. Inspects recent crash logs with `docker__get_container_logs`.
3. Proposes container restart with `docker__restart_container` (LOW/MEDIUM risk).
4. Verifies container health and port binding status.
