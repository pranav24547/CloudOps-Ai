"""Simulated Docker backend for demo mode.

Includes local/deployment container runtime information:
- orders-api container instances
- container health stats (memory, CPU, restarts)
- container logs showing queries and errors
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class SimulatedDockerBackend:
    mode = "demo"

    def __init__(self) -> None:
        self.containers = {
            "c_orders_1": {
                "id": "c_orders_1",
                "name": "orders-api-prod-1",
                "image": "acme/orders-api:v1.8.4",
                "status": "running",
                "state": "running",
                "created": _iso(_now() - timedelta(minutes=13)),
                "ports": {"8000/tcp": "8001"},
                "cpu_percent": 91.5,
                "memory_mb": 768.0,
                "memory_limit_mb": 1024.0,
                "restart_count": 0,
            },
            "c_orders_2": {
                "id": "c_orders_2",
                "name": "orders-api-prod-2",
                "image": "acme/orders-api:v1.8.4",
                "status": "running",
                "state": "running",
                "created": _iso(_now() - timedelta(minutes=13)),
                "ports": {"8000/tcp": "8002"},
                "cpu_percent": 87.2,
                "memory_mb": 740.0,
                "memory_limit_mb": 1024.0,
                "restart_count": 0,
            },
            "c_gateway": {
                "id": "c_gateway",
                "name": "api-gateway-nginx",
                "image": "nginx:alpine",
                "status": "running",
                "state": "running",
                "created": _iso(_now() - timedelta(days=10)),
                "ports": {"80/tcp": "80", "443/tcp": "443"},
                "cpu_percent": 3.1,
                "memory_mb": 45.0,
                "memory_limit_mb": 512.0,
                "restart_count": 0,
            },
            "c_cache": {
                "id": "c_cache",
                "name": "redis-cache",
                "image": "redis:7-alpine",
                "status": "running",
                "state": "running",
                "created": _iso(_now() - timedelta(days=20)),
                "ports": {"6379/tcp": "6379"},
                "cpu_percent": 1.8,
                "memory_mb": 82.0,
                "memory_limit_mb": 512.0,
                "restart_count": 0,
            },
        }

        self.images = [
            {"id": "sha256:9f3c2ab...", "repository": "acme/orders-api", "tag": "v1.8.4", "size_mb": 142.5},
            {"id": "sha256:8c1d5fa...", "repository": "acme/orders-api", "tag": "v1.8.3", "size_mb": 139.8},
            {"id": "sha256:a1b2c3d...", "repository": "nginx", "tag": "alpine", "size_mb": 23.4},
            {"id": "sha256:e5f6a7b...", "repository": "redis", "tag": "7-alpine", "size_mb": 35.1},
        ]

    def _find_container(self, identifier: str) -> dict[str, Any]:
        for c in self.containers.values():
            if c["id"] == identifier or c["name"] == identifier:
                return c
        raise ValueError(f"Container '{identifier}' not found")

    def list_containers(self, all_containers: bool = False) -> list[dict[str, Any]]:
        return list(self.containers.values())

    def get_container_status(self, container: str) -> dict[str, Any]:
        c = self._find_container(container)
        return {
            "id": c["id"],
            "name": c["name"],
            "image": c["image"],
            "status": c["status"],
            "state": c["state"],
            "ports": c["ports"],
            "restart_count": c["restart_count"],
        }

    def get_container_logs(self, container: str, lines: int = 50) -> dict[str, Any]:
        c = self._find_container(container)
        if "orders" in c["name"]:
            logs = [
                "[2026-10-05T09:47:00Z] [INFO] orders-api v1.8.4 listening on port 8000",
                "[2026-10-05T09:47:12Z] [INFO] Database pool connected (max=20)",
                "[2026-10-05T09:48:02Z] [WARN] Query execution slow: 2840ms for customer history",
                "[2026-10-05T09:48:45Z] [ERROR] DB pool exhausted: 20 active connections waiting for queries",
                "[2026-10-05T09:49:15Z] [WARN] GET /api/orders/history 504 Gateway Timeout after 3000ms",
            ]
        else:
            logs = [f"[2026-10-05T09:40:00Z] [INFO] Service {c['name']} healthy and accepting traffic"]
        return {"container": container, "lines": logs[-lines:]}

    def get_container_stats(self, container: str) -> dict[str, Any]:
        c = self._find_container(container)
        return {
            "container": container,
            "cpu_percent": c["cpu_percent"],
            "memory_usage_mb": c["memory_mb"],
            "memory_limit_mb": c["memory_limit_mb"],
            "memory_percent": round((c["memory_mb"] / c["memory_limit_mb"]) * 100, 2),
        }

    def restart_container(self, container: str) -> dict[str, Any]:
        c = self._find_container(container)
        c["restart_count"] += 1
        c["status"] = "running"
        return {
            "container": container,
            "action": "restart",
            "status": "restarted",
            "message": f"Container {c['name']} restarted successfully",
        }

    def list_images(self) -> list[dict[str, Any]]:
        return self.images
