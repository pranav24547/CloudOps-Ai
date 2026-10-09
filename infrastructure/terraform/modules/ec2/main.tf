resource "aws_security_group" "web_sg" {
  name        = "cloudops-web-sg"
  description = "Security group for web instances"
  vpc_id      = var.vpc_id

  ingress {
    description = "HTTP ingress"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS ingress"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "cloudops-web-sg"
  }
}

resource "aws_instance" "orders_api" {
  count                  = 2
  ami                    = "ami-0dee22c13ea7a9a67" # Ubuntu 24.04 LTS
  instance_type          = var.instance_type
  subnet_id              = var.subnet_ids[count.index % length(var.subnet_ids)]
  vpc_security_group_ids = [aws_security_group.web_sg.id]
  monitoring             = true

  tags = {
    Name = "prod-orders-api-${count.index + 1}"
    App  = "orders-api"
    Env  = var.environment
  }
}

output "instance_ids" {
  value = aws_instance.orders_api[*].id
}

output "security_group_id" {
  value = aws_security_group.web_sg.id
}

variable "vpc_id" { type = string }
variable "subnet_ids" { type = list(string) }
variable "instance_type" { type = string }
variable "environment" { type = string }
