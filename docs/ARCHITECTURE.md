# Architecture review

## Purpose

This project demonstrates the engineering behind a containerised AWS service: independently deployable application tiers, explicit trust boundaries, infrastructure tests, deployment controls, and recovery checks. The task board is deliberately small so reviewers can trace a request from the load balancer to persistent storage.

## Design decisions

| Decision | Reason | Trade-off |
| --- | --- | --- |
| ECS Fargate rather than managed application servers | Run containers without patching EC2 hosts | Less host-level control; task sizing and startup still need measurement |
| Two AZs with one NAT gateway per AZ | Keep an AZ's outbound traffic independent of the other AZ | Higher baseline cost than a single NAT gateway |
| Separate web and API services behind path-based ALB routing | Independent deployments, scaling, IAM roles, and security groups | More services and target groups to operate |
| Isolated RDS subnets and Multi-AZ standby | Limit database exposure and support managed failover | Multi-AZ is availability within one region, not cross-region disaster recovery |
| RDS-managed Secrets Manager credentials | Avoid putting database passwords in Terraform variables and task definitions | Per-operation secret reads add latency and API cost |
| Immutable ECR release tags | Make deployments traceable and prevent an existing tag changing | Retention and cleanup need explicit management |
| Separate liveness and readiness endpoints | Keep transient database failures from cycling every container | Monitoring must check readiness separately from ALB process health |
| CPU target tracking with a minimum of two tasks | Preserve a baseline of application redundancy | Load testing is needed to justify scaling thresholds and task sizes |

## Trust boundaries

Internet traffic reaches only the public ALB. Web and API tasks run in private application subnets without public addresses. The ALB reaches only the configured application ports. Web task egress is HTTPS-only; API egress allows HTTPS for AWS services plus PostgreSQL to database subnets. Only the API security group is accepted by RDS. Database route tables have no internet routes.

The ECS execution role can pull images and publish logs. The web task role has no application permissions. The API task role can read only the selected RDS secret. API requests use parameterised SQL; the UI renders user-supplied text through `textContent`. Generated request IDs support diagnosis without recording task titles or request bodies in request logs.

## Failure handling

ECS maintains two tasks per service and uses an ALB health check, startup grace period, and deployment circuit breaker. The API returns a generic 503 when database access fails; it does not return exception details. Connection, statement, and lock timeouts bound common database failure paths. The local recovery test proves that a persisted task survives both database and API container restarts.

Terraform tests check intended network isolation and database protection using a mocked AWS provider. These tests do not demonstrate that AWS created resources correctly or that Multi-AZ failover works. ECS placement, NAT behavior, RDS failover, alarm delivery, and backup restoration need cloud acceptance tests.

## Production considerations for a regulated environment

This is a portfolio reference implementation, not an approved banking service. Before production use, establish identity and access controls, mandatory HTTPS with validated certificates, application authorisation, and an approved secrets and key-management policy. Separate the schema migration identity from a least-privilege database runtime user.

Adopt centrally controlled remote Terraform state, CI deployment through short-lived federated credentials, protected branches, independent change review, and tested rollback procedures. Add an approved image and dependency scanning process, supply-chain attestations, VPC flow logs, ALB access logs, and central audit retention. ECR image scanning is enabled, but this repository does not enforce scan findings as a release gate.

Agree measurable availability, latency, RTO, and RPO objectives; establish them through load tests and scheduled restore/failover drills. Evaluate application authentication, WAF rules, rate limits, data classification, regional residency, incident response, and cross-region recovery against the actual workload and organisational requirements. No bank certification or regulatory compliance is claimed.

## Reviewer walkthrough

1. Run the stack and create a task at http://localhost:8080.
2. Run `python scripts/smoke.py` to exercise the database-backed API.
3. Run `python scripts/resilience.py` to restart the database and API while checking retained data.
4. Run `terraform -chdir=infra test` to check infrastructure invariants without AWS credentials.
5. Review the IAM secret policy, security-group references, CloudWatch alarms, and deployment circuit breaker.
6. Review the CI run and the remaining cloud acceptance steps in the verification record.
