"""Simulated AWS backend ("demo mode").

Provides a deterministic, time-relative AWS environment so the MCP server,
agent and dashboard can be developed and demoed without an AWS account.

The scenario: the production ``orders-api`` service started suffering high
latency ~13 minutes ago. CPU on the API instances climbed, RDS read latency
rose ~340 %, and application logs show slow, un-indexed queries right after a
new version (1.8.4) started. Nothing here tells the agent *what* to conclude;
it only exposes raw signals through the same interface as the live backend.

The world is mutable: start/stop/reboot change instance state, and a reboot
only provides temporary relief (the root cause is not the instance), which lets
the agent's verification step observe that a remediation did *not* work.
"""

from __future__ import annotations

import hashlib
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _noise(key: str, bucket: int, amplitude: float) -> float:
    """Deterministic pseudo-random noise in [-amplitude, amplitude]."""
    digest = hashlib.sha256(f"{key}:{bucket}".encode()).digest()
    return ((digest[0] / 255.0) * 2 - 1) * amplitude


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass
class _Instance:
    instance_id: str
    name: str
    instance_type: str
    state: str
    az: str
    private_ip: str
    public_ip: str | None
    tags: dict[str, str]
    security_groups: list[dict[str, str]]
    launch_time: datetime
    cpu_baseline: float
    cpu_incident: float | None  # None => unaffected by incident
    last_reboot: datetime | None = None
    state_changed_at: datetime | None = None


@dataclass
class _World:
    started: datetime = field(default_factory=_now)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def __post_init__(self) -> None:
        self.incident_start = self.started - timedelta(minutes=13)
        launch = self.started - timedelta(days=41)
        web_sg = [{"GroupId": "sg-0web4a1c", "GroupName": "orders-api-web"}]
        self.instances: dict[str, _Instance] = {
            i.instance_id: i
            for i in [
                _Instance("i-0a1f3c9e7b2d41001", "prod-orders-api-1", "t3.large", "running",
                          "ap-south-1a", "10.0.1.21", "13.233.10.21",
                          {"Name": "prod-orders-api-1", "App": "orders-api", "Env": "production"},
                          web_sg, launch, 34.0, 91.0),
                _Instance("i-0a1f3c9e7b2d41002", "prod-orders-api-2", "t3.large", "running",
                          "ap-south-1b", "10.0.2.22", "13.233.10.22",
                          {"Name": "prod-orders-api-2", "App": "orders-api", "Env": "production"},
                          web_sg, launch, 31.0, 87.0),
                _Instance("i-0b7e2d4c6a8f93003", "staging-orders-api", "t3.medium", "running",
                          "ap-south-1a", "10.1.1.10", None,
                          {"Name": "staging-orders-api", "App": "orders-api", "Env": "staging"},
                          web_sg, launch, 12.0, None),
                _Instance("i-0c5d8e1f2a3b64004", "dev-sandbox-1", "t3.xlarge", "stopped",
                          "ap-south-1a", "10.2.1.5", None,
                          {"Name": "dev-sandbox-1", "Env": "development", "Owner": "pranav"},
                          [{"GroupId": "sg-0dev77", "GroupName": "dev-default"}],
                          launch - timedelta(days=120), 0.0, None),
                _Instance("i-0d9a7b5c3e1f25005", "bastion-host", "t3.micro", "running",
                          "ap-south-1a", "10.0.0.5", "13.233.10.5",
                          {"Name": "bastion-host", "Role": "bastion", "Env": "production"},
                          [{"GroupId": "sg-0ssh0open", "GroupName": "bastion-ssh"}],
                          launch, 2.0, None),
            ]
        }
        self.databases: dict[str, dict[str, Any]] = {
            "orders-db": {
                "engine": "postgres", "engine_version": "16.3", "class": "db.t3.medium",
                "status": "available", "multi_az": True, "storage_gb": 100,
                "endpoint": "orders-db.c9xk2l.ap-south-1.rds.amazonaws.com",
                "tags": {"App": "orders-api", "Env": "production"}, "affected": True,
            },
            "analytics-db": {
                "engine": "mysql", "engine_version": "8.0.36", "class": "db.t3.small",
                "status": "available", "multi_az": False, "storage_gb": 50,
                "endpoint": "analytics-db.c9xk2l.ap-south-1.rds.amazonaws.com",
                "tags": {"App": "analytics", "Env": "production"}, "affected": False,
            },
        }
        self.buckets: dict[str, dict[str, Any]] = {
            "cloudops-deploy-artifacts": {"region": "ap-south-1", "public": False, "versioning": "Enabled",
                                          "encryption": "aws:kms", "objects": 1284, "size_gb": 18.4},
            "orders-app-static-assets": {"region": "ap-south-1", "public": True, "versioning": "Suspended",
                                         "encryption": None, "objects": 9312, "size_gb": 4.2},
            "cloudtrail-logs-prod": {"region": "ap-south-1", "public": False, "versioning": "Enabled",
                                     "encryption": "AES256", "objects": 55210, "size_gb": 61.7},
        }

    # ------------------------------------------------------------------ helpers
    def in_incident(self, t: datetime) -> bool:
        return t >= self.incident_start

    def incident_factor(self, t: datetime) -> float:
        """0 before the incident, ramps to 1 over 2 minutes after it starts; returns 0 if rollback applied."""
        try:
            import sys
            from pathlib import Path

            sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
            import sim_state

            if sim_state.is_rollback_applied():
                return 0.0
        except Exception:
            pass

        if t < self.incident_start:
            return 0.0
        return min(1.0, (t - self.incident_start).total_seconds() / 120.0)


_WORLD: _World | None = None
_WORLD_LOCK = threading.Lock()


def _world() -> _World:
    global _WORLD
    with _WORLD_LOCK:
        if _WORLD is None:
            _WORLD = _World()
        return _WORLD


def reset_world() -> None:
    """Reset the simulated environment (used by tests)."""
    global _WORLD
    with _WORLD_LOCK:
        _WORLD = None
    try:
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        import sim_state

        sim_state.reset_simulated_state()
    except Exception:
        pass


class SimulatedAWSBackend:
    """Implements the same interface as ``LiveAWSBackend`` against fake data."""

    mode = "demo"

    def __init__(self, region: str = "ap-south-1") -> None:
        self.region = region

    # ================================================================== EC2
    def _get_instance(self, instance_id: str) -> _Instance:
        inst = _world().instances.get(instance_id)
        if inst is None:
            raise ValueError(f"Instance '{instance_id}' not found")
        return inst

    @staticmethod
    def _instance_summary(i: _Instance) -> dict[str, Any]:
        return {
            "instance_id": i.instance_id,
            "name": i.name,
            "instance_type": i.instance_type,
            "state": i.state,
            "availability_zone": i.az,
            "private_ip": i.private_ip,
            "public_ip": i.public_ip,
            "tags": i.tags,
        }

    def list_ec2_instances(self, state: str | None = None) -> list[dict[str, Any]]:
        w = _world()
        return [
            self._instance_summary(i)
            for i in w.instances.values()
            if state is None or i.state == state
        ]

    def get_ec2_instance(self, instance_id: str) -> dict[str, Any]:
        i = self._get_instance(instance_id)
        data = self._instance_summary(i)
        data.update({
            "launch_time": _iso(i.launch_time),
            "security_groups": i.security_groups,
            "vpc_id": "vpc-0cloudops01",
            "subnet_id": "subnet-0a" if i.az.endswith("a") else "subnet-0b",
            "iam_instance_profile": "cloudops-app-instance-profile" if "orders" in i.name else None,
            "monitoring": "enabled",
        })
        return data

    def get_ec2_status(self, instance_id: str) -> dict[str, Any]:
        i = self._get_instance(instance_id)
        running = i.state == "running"
        return {
            "instance_id": i.instance_id,
            "state": i.state,
            "system_status": "ok" if running else "not-applicable",
            "instance_status": "ok" if running else "not-applicable",
            "last_reboot": _iso(i.last_reboot) if i.last_reboot else None,
        }

    def _change_state(self, instance_id: str, allowed_from: set[str], new_state: str) -> dict[str, Any]:
        w = _world()
        with w.lock:
            i = self._get_instance(instance_id)
            if i.state not in allowed_from:
                raise ValueError(f"Instance {instance_id} is '{i.state}'; cannot transition to '{new_state}'")
            previous = i.state
            i.state = new_state
            i.state_changed_at = _now()
            if new_state == "running" and previous == "running":
                i.last_reboot = _now()
        return {"instance_id": instance_id, "previous_state": previous, "current_state": i.state}

    def restart_ec2(self, instance_id: str) -> dict[str, Any]:
        result = self._change_state(instance_id, {"running"}, "running")
        result["action"] = "reboot"
        result["message"] = "Reboot request accepted"
        return result

    def start_ec2(self, instance_id: str) -> dict[str, Any]:
        return self._change_state(instance_id, {"stopped"}, "running")

    def stop_ec2(self, instance_id: str) -> dict[str, Any]:
        return self._change_state(instance_id, {"running"}, "stopped")

    # ================================================================== CloudWatch
    @staticmethod
    def _series(minutes: int, period_s: int, fn) -> list[dict[str, Any]]:
        end = _now().replace(second=0, microsecond=0)
        n = max(1, (minutes * 60) // period_s)
        points = []
        for k in range(n, 0, -1):
            t = end - timedelta(seconds=(k - 1) * period_s)
            points.append({"timestamp": _iso(t), "value": round(fn(t, int(t.timestamp()) // period_s), 2)})
        return points

    @staticmethod
    def _summarise(points: list[dict[str, Any]], unit: str) -> dict[str, Any]:
        values = [p["value"] for p in points] or [0.0]
        return {
            "unit": unit,
            "latest": values[-1],
            "average": round(sum(values) / len(values), 2),
            "maximum": max(values),
            "minimum": min(values),
            "datapoints": points,
        }

    def _cpu_value(self, i: _Instance, t: datetime, bucket: int) -> float:
        w = _world()
        if i.state != "running" and (i.state_changed_at is None or t >= i.state_changed_at):
            return 0.0
        value = i.cpu_baseline
        if i.cpu_incident is not None:
            value += (i.cpu_incident - i.cpu_baseline) * w.incident_factor(t)
            if i.last_reboot and t >= i.last_reboot:
                # Reboot gives temporary relief, then load returns (root cause not fixed).
                since = (t - i.last_reboot).total_seconds()
                relief = max(0.0, 1 - since / 300.0)
                value -= (value - i.cpu_baseline) * 0.6 * relief
        return max(0.0, min(100.0, value + _noise(i.instance_id, bucket, 3.0)))

    def get_cpu_metrics(self, instance_id: str, minutes: int = 30, period: int = 60) -> dict[str, Any]:
        i = self._get_instance(instance_id)
        pts = self._series(minutes, period, lambda t, b: self._cpu_value(i, t, b))
        return {"instance_id": instance_id, "metric": "CPUUtilization", **self._summarise(pts, "Percent")}

    def get_memory_metrics(self, instance_id: str, minutes: int = 30, period: int = 60) -> dict[str, Any]:
        i = self._get_instance(instance_id)
        w = _world()

        def mem(t: datetime, b: int) -> float:
            if i.state != "running":
                return 0.0
            base = 48.0 if i.cpu_incident is not None else 30.0
            if i.cpu_incident is not None:
                base += 36.0 * w.incident_factor(t)
            return base + _noise(i.instance_id + "mem", b, 2.0)

        pts = self._series(minutes, period, mem)
        return {"instance_id": instance_id, "metric": "mem_used_percent", "namespace": "CWAgent",
                **self._summarise(pts, "Percent")}

    def get_network_metrics(self, instance_id: str, minutes: int = 30, period: int = 60) -> dict[str, Any]:
        i = self._get_instance(instance_id)
        w = _world()

        def net(t: datetime, b: int, direction: str) -> float:
            if i.state != "running":
                return 0.0
            base = 42_000_000.0 if i.cpu_incident is not None else 1_500_000.0
            if i.cpu_incident is not None:
                base *= 1 + 0.15 * w.incident_factor(t)  # traffic only mildly up
            return base + _noise(i.instance_id + direction, b, base * 0.05)

        return {
            "instance_id": instance_id,
            "network_in": self._summarise(self._series(minutes, period, lambda t, b: net(t, b, "in")), "Bytes"),
            "network_out": self._summarise(self._series(minutes, period, lambda t, b: net(t, b, "out")), "Bytes"),
        }

    def get_application_metrics(self, service: str, minutes: int = 30, period: int = 60) -> dict[str, Any]:
        w = _world()
        if service not in {"orders-api", "analytics"}:
            raise ValueError(f"No application metrics found for service '{service}'")
        affected = service == "orders-api"

        def latency(t: datetime, b: int) -> float:
            base = 220.0 if affected else 140.0
            if affected:
                base += 2580.0 * w.incident_factor(t)
            return base + _noise(service + "lat", b, base * 0.06)

        def requests(t: datetime, b: int) -> float:
            base = 1850.0 if affected else 120.0
            if affected:
                base *= 1 + 0.12 * w.incident_factor(t)
            return base + _noise(service + "req", b, base * 0.05)

        def errors(t: datetime, b: int) -> float:
            base = 0.3
            if affected:
                base += 6.5 * w.incident_factor(t)
            return max(0.0, base + _noise(service + "err", b, 0.2))

        return {
            "service": service,
            "namespace": "CloudOps/App",
            "p99_latency_ms": self._summarise(self._series(minutes, period, latency), "Milliseconds"),
            "requests_per_minute": self._summarise(self._series(minutes, period, requests), "Count"),
            "error_rate_percent": self._summarise(self._series(minutes, period, errors), "Percent"),
        }

    def get_application_logs(self, service: str, minutes: int = 30, filter_pattern: str | None = None,
                             limit: int = 50) -> dict[str, Any]:
        w = _world()
        if service not in {"orders-api", "analytics"}:
            raise ValueError(f"Log group '/app/{service}' not found")
        start = _now() - timedelta(minutes=minutes)
        events: list[dict[str, Any]] = []
        if service == "orders-api":
            deploy = w.incident_start - timedelta(seconds=45)
            events.append({"timestamp": deploy - timedelta(minutes=20), "level": "INFO",
                           "message": "GET /api/orders 200 212ms"})
            events.append({"timestamp": deploy, "level": "INFO",
                           "message": "Starting orders-api version=1.8.4 commit=9f3c2ab pid=1"})
            events.append({"timestamp": deploy + timedelta(seconds=8), "level": "INFO",
                           "message": "Connected to database orders-db (pool size=20)"})
            t = w.incident_start + timedelta(seconds=20)
            k = 0
            while t < _now():
                if k % 3 == 0:
                    events.append({"timestamp": t, "level": "WARN",
                                   "message": ("Slow query (2,4%02dms): SELECT o.*, i.* FROM orders o JOIN "
                                               "order_items i ON i.order_id = o.id WHERE o.customer_email = $1 "
                                               "ORDER BY o.created_at DESC" % (10 + k % 80))})
                elif k % 3 == 1:
                    events.append({"timestamp": t, "level": "ERROR",
                                   "message": "DB pool exhausted: timeout acquiring connection after 3000ms "
                                              "(active=20, idle=0, waiting=37)"})
                else:
                    events.append({"timestamp": t, "level": "WARN",
                                   "message": "GET /api/orders/history 504 upstream timeout after 3012ms"})
                t += timedelta(seconds=25)
                k += 1
        else:
            t = start
            while t < _now():
                events.append({"timestamp": t, "level": "INFO", "message": "Batch job heartbeat ok"})
                t += timedelta(minutes=5)

        events = [e for e in events if e["timestamp"] >= start]
        if filter_pattern:
            needle = filter_pattern.lower()
            events = [e for e in events if needle in e["message"].lower() or needle in e["level"].lower()]
        events = events[-limit:]
        return {
            "log_group": f"/app/{service}",
            "event_count": len(events),
            "events": [{**e, "timestamp": _iso(e["timestamp"])} for e in events],
        }

    def get_recent_alarms(self, state: str | None = "ALARM") -> list[dict[str, Any]]:
        w = _world()
        recovered = False
        try:
            import sys
            from pathlib import Path

            sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
            import sim_state

            recovered = sim_state.is_rollback_applied()
        except Exception:
            pass

        alarms = [
            {"name": "orders-api-p99-latency-high", "state": "OK" if recovered else "ALARM",
             "metric": "CloudOps/App p99_latency_ms", "threshold": "> 1000 ms for 3 datapoints",
             "state_updated": _iso(w.incident_start + timedelta(minutes=3)),
             "dimensions": {"Service": "orders-api"}},
            {"name": "orders-db-read-latency-high", "state": "OK" if recovered else "ALARM",
             "metric": "AWS/RDS ReadLatency", "threshold": "> 0.05 s for 3 datapoints",
             "state_updated": _iso(w.incident_start + timedelta(minutes=4)),
             "dimensions": {"DBInstanceIdentifier": "orders-db"}},
            {"name": "prod-orders-api-cpu-high", "state": "OK" if recovered else "ALARM",
             "metric": "AWS/EC2 CPUUtilization", "threshold": "> 80 % for 5 datapoints",
             "state_updated": _iso(w.incident_start + timedelta(minutes=6)),
             "dimensions": {"AutoScalingGroupName": "prod-orders-api"}},
            {"name": "analytics-db-storage-low", "state": "OK",
             "metric": "AWS/RDS FreeStorageSpace", "threshold": "< 5 GB",
             "state_updated": _iso(w.started - timedelta(days=3)),
             "dimensions": {"DBInstanceIdentifier": "analytics-db"}},
        ]
        return [a for a in alarms if state is None or a["state"] == state]

    # ================================================================== S3
    def _get_bucket(self, bucket: str) -> dict[str, Any]:
        b = _world().buckets.get(bucket)
        if b is None:
            raise ValueError(f"Bucket '{bucket}' not found")
        return b

    def list_buckets(self) -> list[dict[str, Any]]:
        w = _world()
        return [{"name": n, "region": b["region"], "created": _iso(w.started - timedelta(days=200))}
                for n, b in w.buckets.items()]

    def get_bucket_details(self, bucket: str) -> dict[str, Any]:
        b = self._get_bucket(bucket)
        return {"name": bucket, "region": b["region"], "versioning": b["versioning"],
                "encryption": b["encryption"] or "none", "object_count": b["objects"],
                "size_gb": b["size_gb"]}

    def check_bucket_public_access(self, bucket: str) -> dict[str, Any]:
        b = self._get_bucket(bucket)
        public = b["public"]
        return {
            "bucket": bucket,
            "is_public": public,
            "public_access_block": {
                "BlockPublicAcls": not public, "IgnorePublicAcls": not public,
                "BlockPublicPolicy": not public, "RestrictPublicBuckets": not public,
            },
            "policy_allows_public_read": public,
            "findings": ["Bucket policy grants s3:GetObject to Principal '*'"] if public else [],
        }

    # ================================================================== RDS
    def _get_db(self, database: str) -> dict[str, Any]:
        db = _world().databases.get(database)
        if db is None:
            raise ValueError(f"Database '{database}' not found")
        return db

    def list_databases(self) -> list[dict[str, Any]]:
        return [{"identifier": n, "engine": d["engine"], "class": d["class"], "status": d["status"],
                 "tags": d["tags"]} for n, d in _world().databases.items()]

    def get_database_status(self, database: str) -> dict[str, Any]:
        d = self._get_db(database)
        return {"identifier": database, "status": d["status"], "engine": d["engine"],
                "engine_version": d["engine_version"], "instance_class": d["class"],
                "multi_az": d["multi_az"], "allocated_storage_gb": d["storage_gb"],
                "endpoint": d["endpoint"], "pending_maintenance": []}

    def get_database_metrics(self, database: str, minutes: int = 30, period: int = 60) -> dict[str, Any]:
        d = self._get_db(database)
        w = _world()
        affected = d["affected"]

        def f(base: float, incident_mult: float, key: str, noise: float):
            def inner(t: datetime, b: int) -> float:
                v = base
                if affected:
                    v *= 1 + (incident_mult - 1) * w.incident_factor(t)
                return max(0.0, v + _noise(database + key, b, v * noise))
            return inner

        return {
            "identifier": database,
            "cpu_percent": self._summarise(self._series(minutes, period, f(28.0, 2.9, "cpu", 0.05)), "Percent"),
            "read_latency_ms": self._summarise(self._series(minutes, period, f(4.1, 4.4, "rl", 0.06)),
                                               "Milliseconds"),
            "write_latency_ms": self._summarise(self._series(minutes, period, f(2.3, 1.2, "wl", 0.06)),
                                                "Milliseconds"),
            "database_connections": self._summarise(self._series(minutes, period, f(18.0, 2.2, "conn", 0.04)),
                                                    "Count"),
            "read_iops": self._summarise(self._series(minutes, period, f(310.0, 3.6, "riops", 0.05)),
                                         "Count/Second"),
        }
