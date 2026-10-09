variable "aws_region" {
  description = "AWS deployment region"
  type        = string
  default     = "ap-south-1"
}

variable "environment" {
  description = "Environment name (production, staging, dev)"
  type        = string
  default     = "production"
}

variable "vpc_cidr" {
  description = "CIDR block for the CloudOps VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "instance_type" {
  description = "EC2 instance size for the API tier"
  type        = string
  default     = "t3.large"
}

variable "db_instance_class" {
  description = "RDS database instance class"
  type        = string
  default     = "db.t3.medium"
}

variable "db_username" {
  description = "Master database username"
  type        = string
  default     = "cloudops_admin"
}

variable "db_password" {
  description = "Master database password"
  type        = string
  sensitive   = true
  default     = "ChangeMeInVault123!"
}
