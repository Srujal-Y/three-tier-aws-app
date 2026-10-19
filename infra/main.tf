locals { name = "${var.name}-${var.environment}" }
module "network" {
  source = "./modules/network"
  name   = local.name
}
module "database" {
  source              = "./modules/database"
  name                = local.name
  subnets             = module.network.database_subnets
  security_group      = module.network.database_sg
  deletion_protection = var.deletion_protection
}
module "services" {
  api_sg          = module.network.api_sg
  source          = "./modules/services"
  name            = local.name
  vpc_id          = module.network.vpc_id
  public_subnets  = module.network.public_subnets
  private_subnets = module.network.private_subnets
  alb_sg          = module.network.alb_sg
  task_sg         = module.network.task_sg
  db_host         = module.database.host
  secret_arn      = module.database.secret_arn
  web_image       = var.web_image
  api_image       = var.api_image
  certificate_arn = var.certificate_arn
}
module "monitoring" {
  source     = "./modules/monitoring"
  name       = local.name
  cluster    = module.services.cluster
  db_id      = module.database.id
  alb_suffix = module.services.alb_suffix
  email      = var.alarm_email
}
output "url" { value = "${var.certificate_arn == null ? "http" : "https"}://${module.services.dns}" }
output "repositories" { value = module.services.repositories }
output "cluster" { value = module.services.cluster }
