module "vpc" {
  source      = "./modules/vpc"
  cidr_block  = var.vpc_cidr
  aws_region  = var.aws_region
  environment = var.environment
}

module "ec2" {
  source        = "./modules/ec2"
  vpc_id        = module.vpc.vpc_id
  subnet_ids    = module.vpc.public_subnet_ids
  instance_type = var.instance_type
  environment   = var.environment
}

module "rds" {
  source                = "./modules/rds"
  vpc_id                = module.vpc.vpc_id
  private_subnet_ids    = module.vpc.private_subnet_ids
  web_security_group_id = module.ec2.security_group_id
  db_instance_class     = var.db_instance_class
  db_username           = var.db_username
  db_password           = var.db_password
  environment           = var.environment
}

module "s3" {
  source      = "./modules/s3"
  environment = var.environment
}

module "cloudwatch" {
  source = "./modules/cloudwatch"
}
