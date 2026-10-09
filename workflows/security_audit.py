"""Security audit workflow template."""

SECURITY_AUDIT_PROMPT = """You are conducting a cloud infrastructure security audit.
Follow this systematic security review workflow:
1. S3 BUCKET EXPOSURE:
   - Call aws__list_buckets to identify all storage buckets.
   - For each bucket, call aws__check_bucket_public_access to identify public read/write policies, open ACLs, or disabled Public Access Blocks.
2. EC2 SECURITY GROUPS & INSTANCES:
   - Call aws__list_ec2_instances and inspect security group rules.
   - Flag any security group allowing inbound SSH (port 22) or open database ports from 0.0.0.0/0.
   - Detect stopped or orphaned instances that still incur EBS volume risks.
3. DATABASE EXPOSURE:
   - Call aws__list_databases and aws__get_database_status to verify Multi-AZ deployment and encryption settings.
4. GENERATE AUDIT REPORT:
   - Group findings by severity: CRITICAL, HIGH, MEDIUM, LOW.
   - Provide concrete remediation recommendations with risk ratings.
   - Do NOT perform destructive modifications without explicit approval.
"""
