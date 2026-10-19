variable "name" { type = string }
variable "cluster" { type = string }
variable "db_id" { type = string }
variable "alb_suffix" { type = string }
variable "email" { type = string }
data "aws_region" "current" {}
resource "aws_sns_topic" "alerts" { name = "${var.name}-alerts" }
resource "aws_sns_topic_subscription" "email" {
  count     = var.email == null ? 0 : 1
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.email
}
locals {
  alarms = {
    web_cpu    = { namespace = "AWS/ECS", metric = "CPUUtilization", dimensions = { ClusterName = var.cluster, ServiceName = "web" }, threshold = 80, comparison = "GreaterThanThreshold", statistic = "Average" }
    api_cpu    = { namespace = "AWS/ECS", metric = "CPUUtilization", dimensions = { ClusterName = var.cluster, ServiceName = "api" }, threshold = 80, comparison = "GreaterThanThreshold", statistic = "Average" }
    api_memory = { namespace = "AWS/ECS", metric = "MemoryUtilization", dimensions = { ClusterName = var.cluster, ServiceName = "api" }, threshold = 85, comparison = "GreaterThanThreshold", statistic = "Average" }
    db_cpu     = { namespace = "AWS/RDS", metric = "CPUUtilization", dimensions = { DBInstanceIdentifier = var.db_id }, threshold = 80, comparison = "GreaterThanThreshold", statistic = "Average" }
    db_storage = { namespace = "AWS/RDS", metric = "FreeStorageSpace", dimensions = { DBInstanceIdentifier = var.db_id }, threshold = 5368709120, comparison = "LessThanThreshold", statistic = "Average" }
    alb_errors = { namespace = "AWS/ApplicationELB", metric = "HTTPCode_Target_5XX_Count", dimensions = { LoadBalancer = var.alb_suffix }, threshold = 10, comparison = "GreaterThanThreshold", statistic = "Sum" }
  }
}
resource "aws_cloudwatch_metric_alarm" "this" {
  for_each            = local.alarms
  alarm_name          = "${var.name}-${each.key}"
  namespace           = each.value.namespace
  metric_name         = each.value.metric
  dimensions          = each.value.dimensions
  comparison_operator = each.value.comparison
  threshold           = each.value.threshold
  statistic           = each.value.statistic
  period              = 60
  evaluation_periods  = 3
  treat_missing_data  = "missing"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
}
resource "aws_cloudwatch_dashboard" "this" {
  dashboard_name = var.name
  dashboard_body = jsonencode({ widgets = [for k, v in local.alarms : {
    type = "metric", width = 12, height = 6,
    properties = { title = k, region = data.aws_region.current.region, period = 60, stat = v.statistic,
    metrics = [concat([v.namespace, v.metric], flatten([for dk, dv in v.dimensions : [dk, dv]]))] }
  }] })
}
