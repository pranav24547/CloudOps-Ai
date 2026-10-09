"""Live GitHub backend powered by GitHub REST API."""

from __future__ import annotations

import os
from typing import Any

import httpx


class LiveGitHubBackend:
    mode = "live"

    def __init__(self, repo: str | None = None, token: str | None = None) -> None:
        self.repo = repo or os.getenv("GITHUB_REPOSITORY", "acme-corp/orders-api")
        self.token = token or os.getenv("GITHUB_TOKEN", "")
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "CloudOps-MCP-Server",
        }
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"

    def _client(self) -> httpx.Client:
        return httpx.Client(base_url="https://api.github.com", headers=self.headers, timeout=15.0)

    def get_repository_info(self) -> dict[str, Any]:
        with self._client() as c:
            r = c.get(f"/repos/{self.repo}")
            r.raise_for_status()
            data = r.json()
            return {
                "repository": data.get("full_name"),
                "default_branch": data.get("default_branch"),
                "open_issues_count": data.get("open_issues_count"),
                "stars": data.get("stargazers_count"),
                "description": data.get("description"),
                "last_pushed_at": data.get("pushed_at"),
            }

    def get_recent_commits(self, limit: int = 5) -> list[dict[str, Any]]:
        with self._client() as c:
            r = c.get(f"/repos/{self.repo}/commits", params={"per_page": limit})
            r.raise_for_status()
            return [
                {
                    "sha": item["sha"],
                    "short_sha": item["sha"][:7],
                    "message": item["commit"]["message"],
                    "author": item["commit"]["author"]["name"],
                    "timestamp": item["commit"]["author"]["date"],
                }
                for item in r.json()
            ]

    def get_commit_details(self, commit_sha: str) -> dict[str, Any]:
        with self._client() as c:
            r = c.get(f"/repos/{self.repo}/commits/{commit_sha}")
            r.raise_for_status()
            data = r.json()
            return {
                "sha": data["sha"],
                "short_sha": data["sha"][:7],
                "message": data["commit"]["message"],
                "author": data["commit"]["author"]["name"],
                "timestamp": data["commit"]["author"]["date"],
                "stats": data.get("stats"),
                "changed_files": [f["filename"] for f in data.get("files", [])],
            }

    def list_pull_requests(self, state: str = "all") -> list[dict[str, Any]]:
        with self._client() as c:
            r = c.get(f"/repos/{self.repo}/pulls", params={"state": state, "per_page": 10})
            r.raise_for_status()
            return [
                {
                    "number": pr["number"],
                    "title": pr["title"],
                    "state": pr["state"],
                    "merged_at": pr.get("merged_at"),
                    "user": pr["user"]["login"],
                    "head_branch": pr["head"]["ref"],
                    "base_branch": pr["base"]["ref"],
                }
                for pr in r.json()
            ]

    def get_pull_request(self, pr_number: int) -> dict[str, Any]:
        with self._client() as c:
            r = c.get(f"/repos/{self.repo}/pulls/{pr_number}")
            r.raise_for_status()
            return r.json()

    def get_workflow_runs(self, limit: int = 5) -> list[dict[str, Any]]:
        with self._client() as c:
            r = c.get(f"/repos/{self.repo}/actions/runs", params={"per_page": limit})
            r.raise_for_status()
            data = r.json()
            return [
                {
                    "run_id": str(item["id"]),
                    "name": item["name"],
                    "status": item["status"],
                    "conclusion": item["conclusion"],
                    "head_sha": item["head_sha"][:7],
                    "event": item["event"],
                    "started_at": item["created_at"],
                    "completed_at": item["updated_at"],
                    "url": item["html_url"],
                }
                for item in data.get("workflow_runs", [])
            ]

    def get_workflow_status(self, run_id: str) -> dict[str, Any]:
        with self._client() as c:
            r = c.get(f"/repos/{self.repo}/actions/runs/{run_id}")
            r.raise_for_status()
            item = r.json()
            return {
                "run_id": str(item["id"]),
                "name": item["name"],
                "status": item["status"],
                "conclusion": item["conclusion"],
                "head_sha": item["head_sha"][:7],
                "event": item["event"],
                "url": item["html_url"],
            }

    def trigger_workflow(self, workflow_id: str, ref: str = "main") -> dict[str, Any]:
        with self._client() as c:
            r = c.post(f"/repos/{self.repo}/actions/workflows/{workflow_id}/dispatches", json={"ref": ref})
            r.raise_for_status()
            return {"workflow_id": workflow_id, "status": "dispatched", "ref": ref}

    def rollback_deployment(self, target_commit: str) -> dict[str, Any]:
        return self.trigger_workflow("rollback.yml", ref=target_commit)

    def create_issue(self, title: str, description: str) -> dict[str, Any]:
        with self._client() as c:
            r = c.post(f"/repos/{self.repo}/issues", json={"title": title, "body": description})
            r.raise_for_status()
            data = r.json()
            return {"number": data["number"], "title": data["title"], "url": data["html_url"]}
