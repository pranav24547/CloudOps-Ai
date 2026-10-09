"""Live AWS backend backed by boto3.

Credentials are NEVER passed in or hard-coded: boto3 resolves them through the
standard AWS credential chain (env vars, shared config/SSO profile, container
or instance role). The IAM principal used by this server should be scoped with
least privilege - see ``docs/security.md`` for the read-only and operator
policies.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _tags(tag_list: list[dict[str, str]] | None) -> dict[str, str]:
    return {t["Key"]: t["Value"] for t in (tag_list or [])}


class LiveAWSBackend:
    mode = "live"

    def __init__(self, region: str | None = None) -> None:
        self.region = region or os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "ap-south-1"
        self.app_namespace = os.getenv("APP_METRICS_NAMESPACE", "CloudOps/App")
        self.log_group_prefix = os.getenv("APP_LOG_GROUP_PREFIX", "/app/")
        cfg = Config(region_name=self.region, retries={"max_attempts": 4, "mode": "adaptive"})
        session = boto3.session.Session()
        self.ec2 = session.client("ec2", config=cfg)
        self.cw = session.client("cloudwatch", config=cfg)
        self.logs = session.client("logs", config=cfg)
        self.s3 = session.client("s3", config=cfg)
        self.rds = session.client("rds", config=cfg)

    # ================================================================== EC2
    @staticmethod
    def _instance_summary(i: dict[str, Any]) -> dict[str, Any]:
        tags = _tags(i.get("Tags"))
        return {
            "instance_id": i["InstanceId"],
            "name": tags.get("Name"),
            "instance_type": i.get("InstanceType"),
            "state": i.get("State", {}).get("Name"),
            "availability_zone": i.get("Placement", {}).get("AvailabilityZone"),
            "private_ip": i.get("PrivateIpAddress"),
            "public_ip": i.get("PublicIpAddress"),
            "tags": tags,
        }

    def list_ec2_instances(self, state: str | None = None) -> list[dict[str, Any]]:
        filters = [{"Name": "instance-state-name", "Values": [state]}] if state else []
        out: list[dict[str, Any]] = []
        for page in self.ec2.get_paginator("describe_instances").paginate(Filters=filters):
            for r in page["Reservations"]:
                out.extend(self._instance_summary(i) for i in r["Instances"])
        return out

    def _describe(self, instance_id: str) -> dict[str, Any]:
        resp = self.ec2.describe_instances(InstanceIds=[instance_id])
        for r in resp["Reservations"]:
            for i in r["Instances"]:
                return i
        raise ValueError(f"Instance '{instance_id}' not found")

    def get_ec2_instance(self, instance_id: str) -> dict[str, Any]:
        i = self._describe(instance_id)
        data = self._instance_summary(i)
        data.update({
            "launch_time": _iso(i["LaunchTime"]),
            "security_groups": i.get("SecurityGroups", []),
            "vpc_id": i.get("VpcId"),
            "subnet_id": i.get("SubnetId"),
            "iam_instance_profile": (i.get("IamInstanceProfile") or {}).get("Arn"),
            "monitoring": i.get("Monitoring", {}).get("State"),
        })
        return data

    def get_ec2_status(self, instance_id: str) -> dict[str, Any]:
        resp = self.ec2.describe_instance_status(InstanceIds=[instance_id], IncludeAllInstances=True)
        if not resp["InstanceStatuses"]:
            raise ValueError(f"Instance '{instance_id}' not found")
        s = resp["InstanceStatuses"][0]
        return {
            "instance_id": instance_id,
            "state": s["InstanceState"]["Name"],
            "system_status": s.get("SystemStatus", {}).get("Status"),
            "instance_status": s.get("InstanceStatus", {}).get("Status"),
            "scheduled_events": [e.get("Description") for e in s.get("Events", [])],
        }

    def restart_ec2(self, instance_id: str) -> dict[str, Any]:
        before = self._describe(instance_id)["State"]["Name"]
        self.ec2.reboot_instances(InstanceIds=[instance_id])
        return {"instance_id": instance_id, "action": "reboot", "previous_state": before,
                "message": "Reboot request accepted"}

    def start_ec2(self, instance_id: str) -> dict[str, Any]:
        r = self.ec2.start_instances(InstanceIds=[instance_id])["StartingInstances"][0]
        return {"instance_id": instance_id, "previous_state": r["PreviousState"]["Name"],
                "current_state": r["CurrentState"]["Name"]}

    def stop_ec2(self, instance_id: str) -> dict[str, Any]:
        r = self.ec2.stop_instances(InstanceIds=[instance_id])["StoppingInstances"][0]
        return {"instance_id": instance_id, "previous_state": r["PreviousState"]["Name"],
                "current_state": r["CurrentState"]["Name"]}

    # ================================================================== CloudWatch
    def _metric(self, namespace: str, name: str, dims: dict[str, str], minutes: int, period: int,
                stat: str = "Average", unit_label: str | None = None, scale: float = 1.0) -> dict[str, Any]:
        end = datetime.now(timezone.utc)
        resp = self.cw.get_metric_statistics(
            Namespace=namespace, MetricName=name,
            Dimensions=[{"Name": k, "Value": v} for k, v in dims.items()],
            StartTime=end - timedelta(minutes=minutes), EndTime=end, Period=period, Statistics=[stat],
        )
        dps = sorted(resp["Datapoints"], key=lambda d: d["Timestamp"])
        points = [{"timestamp": _iso(d["Timestamp"]), "value": round(d[stat] * scale, 3)} for d in dps]
        values = [p["value"] for p in points]
        unit = unit_label or (dps[0]["Unit"] if dps else "None")
        if not values:
            return {"unit": unit, "latest": None, "average": None, "maximum": None, "minimum": None,
                    "datapoints": [], "note": "No datapoints in range"}
        return {"unit": unit, "latest": values[-1], "average": round(sum(values) / len(values), 3),
                "maximum": max(values), "minimum": min(values), "datapoints": points}

    def get_cpu_metrics(self, instance_id: str, minutes: int = 30, period: int = 60) -> dict[str, Any]:
        m = self._metric("AWS/EC2", "CPUUtilization", {"InstanceId": instance_id}, minutes, period)
        return {"instance_id": instance_id, "metric": "CPUUtilization", **m}

    def get_memory_metrics(self, instance_id: str, minutes: int = 30, period: int = 60) -> dict[str, Any]:
        m = self._metric("CWAgent", "mem_used_percent", {"InstanceId": instance_id}, minutes, period)
        return {"instance_id": instance_id, "metric": "mem_used_percent", "namespace": "CWAgent", **m}

    def get_network_metrics(self, instance_id: str, minutes: int = 30, period: int = 60) -> dict[str, Any]:
        d = {"InstanceId": instance_id}
        return {
            "instance_id": instance_id,
            "network_in": self._metric("AWS/EC2", "NetworkIn", d, minutes, period, "Sum"),
            "network_out": self._metric("AWS/EC2", "NetworkOut", d, minutes, period, "Sum"),
        }

    def get_application_metrics(self, service: str, minutes: int = 30, period: int = 60) -> dict[str, Any]:
        d = {"Service": service}
        ns = self.app_namespace
        return {
            "service": service,
            "namespace": ns,
            "p99_latency_ms": self._metric(ns, "Latency", d, minutes, period, "Maximum", "Milliseconds"),
            "requests_per_minute": self._metric(ns, "RequestCount", d, minutes, period, "Sum", "Count"),
            "error_rate_percent": self._metric(ns, "ErrorRate", d, minutes, period, "Average", "Percent"),
        }

    def get_application_logs(self, service: str, minutes: int = 30, filter_pattern: str | None = None,
                             limit: int = 50) -> dict[str, Any]:
        group = f"{self.log_group_prefix}{service}"
        start = int((datetime.now(timezone.utc) - timedelta(minutes=minutes)).timestamp() * 1000)
        kwargs: dict[str, Any] = {"logGroupName": group, "startTime": start, "limit": min(limit, 1000)}
        if filter_pattern:
            kwargs["filterPattern"] = f'"{filter_pattern}"'
        try:
            resp = self.logs.filter_log_events(**kwargs)
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                raise ValueError(f"Log group '{group}' not found") from e
            raise
        events = [{"timestamp": _iso(datetime.fromtimestamp(ev["timestamp"] / 1000, timezone.utc)),
                   "message": ev["message"].rstrip()} for ev in resp.get("events", [])]
        return {"log_group": group, "event_count": len(events), "events": events[-limit:]}

    def get_recent_alarms(self, state: str | None = "ALARM") -> list[dict[str, Any]]:
        kwargs: dict[str, Any] = {"MaxRecords": 100}
        if state:
            kwargs["StateValue"] = state
        out = []
        for a in self.cw.describe_alarms(**kwargs).get("MetricAlarms", []):
            out.append({
                "name": a["AlarmName"], "state": a["StateValue"],
                "metric": f'{a.get("Namespace")} {a.get("MetricName")}',
                "threshold": f'{a.get("ComparisonOperator")} {a.get("Threshold")}',
                "state_updated": _iso(a["StateUpdatedTimestamp"]),
                "dimensions": {d["Name"]: d["Value"] for d in a.get("Dimensions", [])},
                "reason": a.get("StateReason"),
            })
        return out

    # ================================================================== S3
    def list_buckets(self) -> list[dict[str, Any]]:
        out = []
        for b in self.s3.list_buckets().get("Buckets", []):
            try:
                loc = self.s3.get_bucket_location(Bucket=b["Name"]).get("LocationConstraint") or "us-east-1"
            except ClientError:
                loc = "unknown"
            out.append({"name": b["Name"], "region": loc, "created": _iso(b["CreationDate"])})
        return out

    def get_bucket_details(self, bucket: str) -> dict[str, Any]:
        versioning = self.s3.get_bucket_versioning(Bucket=bucket).get("Status", "Disabled")
        try:
            enc_rules = self.s3.get_bucket_encryption(Bucket=bucket)["ServerSideEncryptionConfiguration"]["Rules"]
            encryption = enc_rules[0]["ApplyServerSideEncryptionByDefault"]["SSEAlgorithm"]
        except ClientError:
            encryption = "none"
        loc = self.s3.get_bucket_location(Bucket=bucket).get("LocationConstraint") or "us-east-1"
        return {"name": bucket, "region": loc, "versioning": versioning, "encryption": encryption}

    def check_bucket_public_access(self, bucket: str) -> dict[str, Any]:
        findings: list[str] = []
        try:
            pab = self.s3.get_public_access_block(Bucket=bucket)["PublicAccessBlockConfiguration"]
        except ClientError:
            pab = {}
            findings.append("No bucket-level Public Access Block configured")
        try:
            policy_public = self.s3.get_bucket_policy_status(Bucket=bucket)["PolicyStatus"]["IsPublic"]
        except ClientError:
            policy_public = False
        if policy_public:
            findings.append("Bucket policy makes the bucket public")
        acl = self.s3.get_bucket_acl(Bucket=bucket)
        for g in acl.get("Grants", []):
            uri = g.get("Grantee", {}).get("URI", "")
            if uri.endswith("/AllUsers") or uri.endswith("/AuthenticatedUsers"):
                findings.append(f"ACL grants {g['Permission']} to {uri.rsplit('/', 1)[-1]}")
        fully_blocked = bool(pab) and all(pab.values())
        return {"bucket": bucket, "is_public": (policy_public or any("ACL" in f for f in findings))
                and not fully_blocked, "public_access_block": pab,
                "policy_allows_public_read": policy_public, "findings": findings}

    # ================================================================== RDS
    def list_databases(self) -> list[dict[str, Any]]:
        out = []
        for page in self.rds.get_paginator("describe_db_instances").paginate():
            for d in page["DBInstances"]:
                out.append({"identifier": d["DBInstanceIdentifier"], "engine": d["Engine"],
                            "class": d["DBInstanceClass"], "status": d["DBInstanceStatus"],
                            "tags": _tags(d.get("TagList"))})
        return out

    def get_database_status(self, database: str) -> dict[str, Any]:
        try:
            d = self.rds.describe_db_instances(DBInstanceIdentifier=database)["DBInstances"][0]
        except ClientError as e:
            if e.response["Error"]["Code"] == "DBInstanceNotFound":
                raise ValueError(f"Database '{database}' not found") from e
            raise
        return {"identifier": database, "status": d["DBInstanceStatus"], "engine": d["Engine"],
                "engine_version": d["EngineVersion"], "instance_class": d["DBInstanceClass"],
                "multi_az": d["MultiAZ"], "allocated_storage_gb": d["AllocatedStorage"],
                "endpoint": (d.get("Endpoint") or {}).get("Address"),
                "pending_maintenance": d.get("PendingModifiedValues", {})}

    def get_database_metrics(self, database: str, minutes: int = 30, period: int = 60) -> dict[str, Any]:
        d = {"DBInstanceIdentifier": database}
        return {
            "identifier": database,
            "cpu_percent": self._metric("AWS/RDS", "CPUUtilization", d, minutes, period),
            "read_latency_ms": self._metric("AWS/RDS", "ReadLatency", d, minutes, period,
                                            unit_label="Milliseconds", scale=1000),
            "write_latency_ms": self._metric("AWS/RDS", "WriteLatency", d, minutes, period,
                                             unit_label="Milliseconds", scale=1000),
            "database_connections": self._metric("AWS/RDS", "DatabaseConnections", d, minutes, period),
            "read_iops": self._metric("AWS/RDS", "ReadIOPS", d, minutes, period),
        }
