# Security and Governance Model

## 1. Authentication & Role-Based Access Control (RBAC)

CloudOps AI uses stateless JWT tokens (`HS256`) and bcrypt password hashing.

### User Roles Matrix

| Capability | VIEWER | OPERATOR | ADMIN |
|---|:---:|:---:|:---:|
| Inspect Dashboard & Telemetry | YES | YES | YES |
| Ask Questions & Investigate Incidents | YES | YES | YES |
| Trigger Read-Only MCP Tools | YES | YES | YES |
| Propose Write Operations | NO | YES | YES |
| Approve Low / Medium Risk Actions | NO | YES | YES |
| Approve High Risk Actions (Stop/Rollback) | NO | YES | YES |
| Manage User Roles & Configure MCP Servers | NO | NO | YES |

---

## 2. Least-Privilege AWS IAM Policies

The AWS MCP server never runs under root or Administrator credentials.

### Recommended Read-Only Policy (`cloudops-observer-policy`)
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:Describe*",
        "cloudwatch:GetMetricStatistics",
        "cloudwatch:DescribeAlarms",
        "logs:FilterLogEvents",
        "logs:DescribeLogGroups",
        "s3:ListAllMyBuckets",
        "s3:GetBucketLocation",
        "s3:GetBucketVersioning",
        "s3:GetBucketPolicyStatus",
        "s3:GetBucketAcl",
        "s3:GetPublicAccessBlock",
        "rds:DescribeDBInstances"
      ],
      "Resource": "*"
    }
  ]
}
```

### Remediator Policy (`cloudops-remediator-policy`)
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:RebootInstances",
        "ec2:StartInstances",
        "ec2:StopInstances"
      ],
      "Resource": "arn:aws:ec2:*:*:instance/*",
      "Condition": {
        "StringEquals": {
          "aws:ResourceTag/App": "orders-api"
        }
      }
    }
  ]
}
```

---

## 3. Human-in-the-Loop (HITL) Interruption

When a write tool is proposed:
1. The LangGraph state machine triggers `interrupt()`.
2. The agent pauses execution and persists the pending action in the database.
3. The dashboard displays an interactive approval modal detailing:
   - Tool name and exact JSON arguments
   - Reasoning string supplied by the LLM
   - Assessed risk rating
4. When approved by an authorized user, `/api/approval/{id}` resumes the thread using `Command(resume=decision)`.
