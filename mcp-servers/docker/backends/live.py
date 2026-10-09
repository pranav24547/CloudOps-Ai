"""Live Docker backend using Docker engine API or CLI."""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any


class LiveDockerBackend:
    mode = "live"

    def __init__(self) -> None:
        self.docker_bin = shutil.which("docker")
        if not self.docker_bin:
            raise RuntimeError("Docker command-line binary is not installed or not in PATH")

    def _run(self, *args: str) -> str:
        cmd = [self.docker_bin, *args]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return res.stdout.strip()

    def list_containers(self, all_containers: bool = False) -> list[dict[str, Any]]:
        args = ["ps", "--format", "{{json .}}"]
        if all_containers:
            args.insert(1, "-a")
        out = self._run(*args)
        containers = []
        for line in out.splitlines():
            if line:
                d = json.loads(line)
                containers.append({
                    "id": d.get("ID"),
                    "name": d.get("Names"),
                    "image": d.get("Image"),
                    "status": d.get("Status"),
                    "state": d.get("State"),
                    "ports": d.get("Ports"),
                })
        return containers

    def get_container_status(self, container: str) -> dict[str, Any]:
        out = self._run("inspect", container)
        data = json.loads(out)[0]
        return {
            "id": data["Id"][:12],
            "name": data["Name"].lstrip("/"),
            "image": data["Config"]["Image"],
            "state": data["State"]["Status"],
            "restart_count": data["RestartCount"],
        }

    def get_container_logs(self, container: str, lines: int = 50) -> dict[str, Any]:
        out = self._run("logs", "--tail", str(lines), container)
        return {"container": container, "lines": out.splitlines()}

    def get_container_stats(self, container: str) -> dict[str, Any]:
        out = self._run("stats", "--no-stream", "--format", "{{json .}}", container)
        d = json.loads(out)
        return {"container": container, "raw": d}

    def restart_container(self, container: str) -> dict[str, Any]:
        self._run("restart", container)
        return {"container": container, "action": "restart", "status": "success"}

    def list_images(self) -> list[dict[str, Any]]:
        out = self._run("images", "--format", "{{json .}}")
        images = []
        for line in out.splitlines():
            if line:
                d = json.loads(line)
                images.append({
                    "repository": d.get("Repository"),
                    "tag": d.get("Tag"),
                    "id": d.get("ID"),
                    "size": d.get("Size"),
                })
        return images
