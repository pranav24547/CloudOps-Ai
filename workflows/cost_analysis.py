"""Cost analysis workflow template."""

COST_ANALYSIS_PROMPT = """You are conducting a cloud resource utilization and cost optimization analysis.
Follow this systematic cost audit workflow:
1. INVENTORY COMPUTE RESOURCES:
   - Call aws__list_ec2_instances with state=None.
   - Call aws__get_cpu_metrics for running instances to identify idle or under-utilized resources (average CPU < 5%).
   - Identify stopped instances retaining unattached or costly EBS storage.
2. DATABASE PROVISIONING:
   - Call aws__list_databases and aws__get_database_metrics to compare allocated storage and IOPS against actual demand.
3. STORAGE BUCKETS:
   - Call aws__list_buckets and aws__get_bucket_details to identify unversioned or large buckets missing lifecycle transition policies.
4. RECOMMENDATIONS:
   - Calculate potential monthly savings.
   - Recommend rightsizing underutilized instances, snapshotting and terminating dead dev instances, and applying S3 Intelligent-Tiering.
"""
