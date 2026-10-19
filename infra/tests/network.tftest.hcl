mock_provider "aws" {
  mock_data "aws_availability_zones" {
    defaults = { names = ["us-east-1a", "us-east-1b"] }
  }
}
run "network_isolation" {
  command = plan
  module { source = "./modules/network" }
  variables { name = "platform-test" }
  assert {
    condition     = length(aws_subnet.public) == 2 && length(aws_subnet.private) == 2 && length(aws_subnet.database) == 2 && length(aws_nat_gateway.this) == 2
    error_message = "All subnet tiers and NAT gateways must span two AZs."
  }
  assert {
    condition     = length(aws_route_table.database.route) == 0
    error_message = "Database subnets must not have an internet default route."
  }
  assert {
    condition     = alltrue([for s in aws_subnet.private : s.map_public_ip_on_launch == false])
    error_message = "Application subnets must not assign public IPs."
  }
  assert {
    condition     = alltrue([for rule in aws_security_group.database.ingress : rule.from_port == 5432 && rule.to_port == 5432 && length(coalesce(rule.cidr_blocks, [])) == 0])
    error_message = "Database access must use security-group references on port 5432."
  }
  assert {
    condition     = alltrue([for rule in aws_security_group.task.egress : rule.from_port == 443 && rule.to_port == 443 && rule.protocol == "tcp"])
    error_message = "Web-tier internet egress must be restricted to HTTPS."
  }
}
