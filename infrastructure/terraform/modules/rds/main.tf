resource "aws_db_subnet_group" "rds" {
  name       = "cloudops-db-subnet-group"
  subnet_ids = var.private_subnet_ids

  tags = {
    Name = "cloudops-db-subnet-group"
  }
}

resource "aws_security_group" "rds_sg" {
  name        = "cloudops-rds-sg"
  description = "Access to RDS from EC2 web servers"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [var.web_security_group_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "cloudops-rds-sg"
  }
}

resource "aws_db_instance" "orders_db" {
  identifier             = "orders-db"
  allocated_storage      = 100
  engine                 = "postgres"
  engine_version         = "16.3"
  instance_class         = var.db_instance_class
  username               = var.db_username
  password               = var.db_password
  db_subnet_group_name   = aws_db_subnet_group.rds.name
  vpc_security_group_ids = [aws_security_group.rds_sg.id]
  multi_az               = true
  skip_final_snapshot    = true
  deletion_protection    = false

  tags = {
    App = "orders-api"
    Env = var.environment
  }
}

output "db_endpoint" {
  value = aws_db_instance.orders_db.endpoint
}

output "db_identifier" {
  value = aws_db_instance.orders_db.identifier
}

variable "vpc_id" { type = string }
variable "private_subnet_ids" { type = list(string) }
variable "web_security_group_id" { type = string }
variable "db_instance_class" { type = string }
variable "db_username" { type = string }
variable "db_password" { type = string }
variable "environment" { type = string }
