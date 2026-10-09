"""Simulated GitHub backend for demo mode.

Includes realistic deployment history for orders-api:
- Commit `9f3c2ab` ("optimize query batching for orders API") deployed 13 minutes ago as deployment #184
- Commit `8c1d5fa` ("v1.8.3 stable release") before it
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class SimulatedGitHubBackend:
    mode = "demo"

    def __init__(self, repo: str = "acme-corp/orders-api") -> None:
        self.repo = repo
        self._now_ref = _now()
        deploy_time = self._now_ref - timedelta(minutes=13)

        self.commits = [
            {
                "sha": "9f3c2ab71e84dfa10b4293810283c7491d9e2a84",
                "short_sha": "9f3c2ab",
                "message": "feat(orders): add customer order history endpoint without composite index",
                "author": "alex.dev@acme.com",
                "timestamp": _iso(deploy_time - timedelta(minutes=4)),
                "changed_files": ["api/routes/orders.py", "db/queries.py"],
            },
            {
                "sha": "8c1d5fa32b9087ec128734918237498172938471",
                "short_sha": "8c1d5fa",
                "message": "release: v1.8.3 stable release",
                "author": "ci-bot@acme.com",
                "timestamp": _iso(deploy_time - timedelta(days=2)),
                "changed_files": ["version.txt"],
            },
            {
                "sha": "4a7b9c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b",
                "short_sha": "4a7b9c1",
                "message": "fix(auth): update token expiration window",
                "author": "sarah.sre@acme.com",
                "timestamp": _iso(deploy_time - timedelta(days=5)),
                "changed_files": ["middleware/auth.py"],
            },
        ]

        self.workflow_runs = [
            {
                "run_id": "184",
                "name": "Deploy Production (orders-api)",
                "status": "completed",
                "conclusion": "success",
                "head_sha": "9f3c2ab",
                "event": "push",
                "started_at": _iso(deploy_time - timedelta(minutes=3)),
                "completed_at": _iso(deploy_time),
                "url": f"https://github.com/{self.repo}/actions/runs/184",
            },
            {
                "run_id": "183",
                "name": "CI Tests & Lint",
                "status": "completed",
                "conclusion": "success",
                "head_sha": "9f3c2ab",
                "event": "pull_request",
                "started_at": _iso(deploy_time - timedelta(minutes=15)),
                "completed_at": _iso(deploy_time - timedelta(minutes=10)),
                "url": f"https://github.com/{self.repo}/actions/runs/183",
            },
        ]

        self.pull_requests = [
            {
                "number": 42,
                "title": "Add customer order history lookup API",
                "state": "merged",
                "merged_at": _iso(deploy_time - timedelta(minutes=5)),
                "user": "alex.dev",
                "head_branch": "feature/order-history",
                "base_branch": "main",
            }
        ]

        self.issues: list[dict[str, Any]] = []

    def get_repository_info(self) -> dict[str, Any]:
        return {
            "repository": self.repo,
            "default_branch": "main",
            "open_issues_count": len(self.issues) + 2,
            "stars": 48,
            "description": "Production orders API microservice",
            "last_pushed_at": self.commits[0]["timestamp"],
        }

    def get_recent_commits(self, limit: int = 5) -> list[dict[str, Any]]:
        return self.commits[:limit]

    def get_commit_details(self, commit_sha: str) -> dict[str, Any]:
        for c in self.commits:
            if c["sha"].startswith(commit_sha) or c["short_sha"] == commit_sha:
                return {
                    **c,
                    "stats": {"additions": 142, "deletions": 18, "total": 160},
                    "patch_summary": (
                        "Added query: SELECT o.*, i.* FROM orders o JOIN order_items i "
                        "ON i.order_id = o.id WHERE o.customer_email = $1 ORDER BY o.created_at DESC"
                    ),
                }
        raise ValueError(f"Commit '{commit_sha}' not found")

    def list_pull_requests(self, state: str = "all") -> list[dict[str, Any]]:
        return [pr for pr in self.pull_requests if state == "all" or pr["state"] == state]

    def get_pull_request(self, pr_number: int) -> dict[str, Any]:
        for pr in self.pull_requests:
            if pr["number"] == pr_number:
                return pr
        raise ValueError(f"Pull request #{pr_number} not found")

    def get_workflow_runs(self, limit: int = 5) -> list[dict[str, Any]]:
        return self.workflow_runs[:limit]

    def get_workflow_status(self, run_id: str) -> dict[str, Any]:
        for r in self.workflow_runs:
            if r["run_id"] == str(run_id):
                return r
        raise ValueError(f"Workflow run '{run_id}' not found")

    def trigger_workflow(self, workflow_id: str, ref: str = "main") -> dict[str, Any]:
        new_id = str(int(self.workflow_runs[0]["run_id"]) + 1)
        run = {
            "run_id": new_id,
            "name": f"Workflow {workflow_id}",
            "status": "queued",
            "conclusion": None,
            "head_sha": self.commits[0]["short_sha"],
            "event": "workflow_dispatch",
            "started_at": _iso(_now()),
            "completed_at": None,
            "url": f"https://github.com/{self.repo}/actions/runs/{new_id}",
        }
        self.workflow_runs.insert(0, run)
        return {"workflow_id": workflow_id, "run_id": new_id, "status": "triggered", "ref": ref}

    def rollback_deployment(self, target_commit: str = "8c1d5fa") -> dict[str, Any]:
        try:
            import sys
            from pathlib import Path

            sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
            import sim_state

            sim_state.set_simulated_state({"rollback_applied": True, "target_commit": target_commit})
        except Exception:
            pass

        new_id = str(int(self.workflow_runs[0]["run_id"]) + 1)
        run = {
            "run_id": new_id,
            "name": "Rollback Deployment (orders-api)",
            "status": "in_progress",
            "conclusion": None,
            "head_sha": target_commit[:7],
            "event": "rollback_dispatch",
            "started_at": _iso(_now()),
            "completed_at": None,
            "url": f"https://github.com/{self.repo}/actions/runs/{new_id}",
        }
        self.workflow_runs.insert(0, run)
        return {
            "status": "rollback_initiated",
            "target_commit": target_commit,
            "workflow_run_id": new_id,
            "message": f"Rollback to {target_commit} initiated in deployment pipeline",
        }

    def create_issue(self, title: str, description: str) -> dict[str, Any]:
        issue = {
            "number": len(self.issues) + 101,
            "title": title,
            "body": description,
            "state": "open",
            "created_at": _iso(_now()),
        }
        self.issues.append(issue)
        return issue
