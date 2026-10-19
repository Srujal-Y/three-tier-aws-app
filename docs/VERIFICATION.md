# Verification record

## Reproducible local checks

| Check | Result | Command |
| --- | --- | --- |
| API validation, errors, request IDs, headers, payload limits, bound SQL parameters | 9 tests passed | `.venv/Scripts/python -m unittest discover -s tests -v` |
| Terraform syntax and provider schema | Passed | `terraform -chdir=infra validate` |
| Terraform formatting | Passed | `terraform -chdir=infra fmt -check -recursive` |
| Network and database policy assertions | 2 test runs passed | `terraform -chdir=infra test` |
| Linux API and web images | Built successfully | `docker compose up --build -d --wait` |
| Database readiness and create/read/update/delete | Passed | `python scripts/smoke.py` |
| Data retained after database and API restarts | Passed | `python scripts/resilience.py` |
| GitHub Actions | Automated on every push and pull request | [Workflow runs](https://github.com/Srujal-Y/three-tier-aws-app/actions) |

The unit tests use mocked database calls. The smoke and recovery tests use the real PostgreSQL container through the local gateway. Recovery tests restart local services and should run only in a development environment. Terraform policy tests use a mocked AWS provider and do not create cloud resources. No account credentials are needed for those tests.

## Cloud acceptance: pending AWS account access

- Review and apply the full Terraform plan using authenticated deployment credentials.
- Confirm tasks run without public IPs in two AZs and only approved security-group paths succeed.
- Verify HTTPS using the actual domain and ACM certificate.
- Run the CRUD smoke test against the deployed endpoint.
- Exercise a failed image deployment and confirm circuit-breaker rollback.
- Generate controlled test traffic and confirm scaling and CloudWatch alarm delivery.
- Rotate the managed database credential and verify subsequent requests succeed.
- Perform an RDS failover and a point-in-time restore drill; record observed recovery times and data recovery.
- Review image/dependency scan findings and complete workload-specific access and audit controls.

No cloud runtime, compliance, load-test, or disaster-recovery result is implied by the local checks.
