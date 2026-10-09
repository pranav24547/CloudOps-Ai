resource "aws_cloudwatch_metric_alarm" "cpu_high" {
  alarm_name          = "orders-api-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 60
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Orders API EC2 CPU utilization exceeded 80%"

  dimensions = {
    AutoScalingGroupName = "prod-orders-api"
  }
}

resource "aws_cloudwatch_metric_alarm" "p99_latency" {
  alarm_name          = "orders-api-p99-latency-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "Latency"
  namespace           = "CloudOps/App"
  period              = 60
  statistic           = "Maximum"
  threshold           = 1000 # 1000ms = 1.0s
  alarm_description   = "Orders API p99 latency exceeded 1000ms"

  dimensions = {
    Service = "orders-api"
  }
}

resource "aws_cloudwatch_log_group" "orders_api" {
  name              = "/app/orders-api"
  retention_in_days = 30
}
