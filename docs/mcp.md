# Model Context Protocol (MCP) in CloudOps AI

## 1. What is Model Context Protocol?

The **Model Context Protocol (MCP)** is an open, standardized protocol created by Anthropic that standardizes how AI applications connect to external data sources and tools.

Traditional architectures tightly couple the AI logic to proprietary SDKs:
```
[LLM Agent] ---> [Custom Python Boto3 Code] ---> [AWS]
            ---> [Custom GitHub SDK Code]   ---> [GitHub]
            ---> [Custom Docker Socket Code] ---> [Docker]
```

With MCP, the agent becomes a universal client:
```
[LLM Agent] ---> [MCP Client] === (JSON-RPC) ===> [AWS MCP Server]    ---> [AWS]
                                             ===> [GitHub MCP Server] ---> [GitHub]
                                             ===> [Docker MCP Server] ---> [Docker]
```

---

## 2. Why Real MCP Matters

CloudOps AI uses genuine MCP servers adhering to the MCP 2024-11-05 spec:
- Supports **Streamable HTTP** (for distributed microservices) and **Stdio** (for local CLI debugging).
- Implements `tools/list` with typed JSONSchema parameter specifications.
- Implements `tools/call` for execution.
- Implements `resources/read` for declarative infrastructure environment metadata (`aws://environment`, `github://repository`, `docker://containers`).

---

## 3. Tool Annotations & Safety Contract

Every tool exposed by our MCP servers includes `ToolAnnotations`:
- `readOnlyHint`: Indicates whether an operation produces side effects.
  - `True`: Tool only observes (`list_ec2_instances`, `get_cpu_metrics`, `get_workflow_runs`).
  - `False`: Tool modifies infrastructure state (`restart_ec2`, `rollback_deployment`).
- `destructiveHint`: Distinguishes recoverable disruptive changes (`restart_ec2`) from dangerous operations (`stop_ec2`, `rollback_deployment`).

The MCP client translates these annotations into a four-tier risk classification:
1. **READ**: Safely auto-executed by viewer, operator, and admin roles.
2. **LOW**: Modifies non-critical deployment objects (e.g. `create_issue`).
3. **MEDIUM**: Disruptive but recoverable actions (e.g. `restart_ec2`, `restart_container`). Always prompts human approval unless explicitly auto-approved in dev mode.
4. **HIGH**: Destructive infrastructure alterations (e.g. `stop_ec2`, `rollback_deployment`, `trigger_workflow`). Strict human-in-the-loop authorization required.
