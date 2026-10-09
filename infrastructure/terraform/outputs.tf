output "vpc_id" {
  description = "ID of the CloudOps VPC"
  value       = module.vpc.vpc_id
}

output "ec2_instance_ids" {
  description = "IDs of the deployed EC2 instances"
  value       = module.ec2.instance_ids
}

output "rds_endpoint" {
  description = "Database connection endpoint"
  value       = module.rds.db_endpoint
}

output "s3_bucket_name" {
  description = "Name of the deployment artifacts S3 bucket"
  value       = module.s3.bucket_name
}
