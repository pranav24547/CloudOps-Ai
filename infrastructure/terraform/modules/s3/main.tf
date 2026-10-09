resource "aws_s3_bucket" "artifacts" {
  bucket        = "cloudops-deploy-artifacts-${var.environment}"
  force_destroy = true

  tags = {
    Name = "cloudops-deploy-artifacts"
    Env  = var.environment
  }
}

resource "aws_s3_bucket_versioning" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

output "bucket_name" {
  value = aws_s3_bucket.artifacts.id
}

variable "environment" { type = string }
