"""Deployment verification and rollout workflow template."""

DEPLOYMENT_WORKFLOW_PROMPT = """You are executing or verifying an infrastructure deployment.
Follow this systematic deployment workflow:
1. PRE-DEPLOYMENT CHECKS:
   - Call github__get_recent_commits to review the latest candidate commit.
   - Call github__list_pull_requests to ensure PR reviews were approved.
   - Call github__get_workflow_runs to verify that CI unit tests and linting passed cleanly.
2. DOCKER/IMAGE VERIFICATION:
   - Call docker__list_images to check if the target image is built and tagged.
3. APPROVAL GATING:
   - Deploying or triggering workflows into production is HIGH risk.
   - Propose triggering the deployment workflow and wait for human operator approval.
4. POST-DEPLOYMENT VERIFICATION:
   - Call docker__list_containers or aws__get_ec2_status to verify containers or instances are healthy.
   - Call aws__get_application_metrics to monitor error rates and latency for 5 minutes post-deploy.
   - Call aws__get_recent_alarms to ensure no new CloudWatch alarms fired.
"""
