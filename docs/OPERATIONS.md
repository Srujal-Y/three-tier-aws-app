# Operations

## Deploy and observe

Use unique image tags for every release. Apply the new image URLs through Terraform; do not register task revisions outside Terraform. Check ECS service events and target group health if the service fails to stabilize. Failed deployments roll back when a previous healthy deployment exists.

Inspect `/ecs/three-tier-dev/api` and `/ecs/three-tier-dev/web` in CloudWatch Logs. Check the `three-tier-dev` dashboard, RDS events, and SNS subscriptions. A healthy `/healthz` with failing `/api/readyz` means process health passed but database access failed: inspect DB security-group ingress, secret permissions, database status, and TLS settings. Tasks that cannot start often indicate absent ECR images, an execution-role issue, or broken NAT routes. Alarms need a confirmed SNS subscription for email delivery.

## State

For shared deployment, first create an S3 bucket with versioning, encryption, and public access blocked. Restrict its IAM access to deployment operators. Add a Terraform `backend "s3" {}` block inside `infra/versions.tf`, then initialize with the following options, replacing placeholders:

```powershell
terraform -chdir=infra init -migrate-state -backend-config="bucket=YOUR_STATE_BUCKET" -backend-config="key=three-tier/dev.tfstate" -backend-config="region=us-east-1" -backend-config="encrypt=true" -backend-config="use_lockfile=true"
```

Use one state key per environment. Never share state or plan artifacts publicly. Keep backend setup outside this application's destroy lifecycle.

## Backup and restore

RDS automated backups retain seven days; use point-in-time restore to a NEW DB instance via the RDS console. Restore into the isolated subnet group with the API-only DB security group. Validate data and credentials, then import/adopt the restored instance into Terraform and update its address/secret outputs before applying the ECS task revision. Plan carefully to avoid Terraform replacing the restored database. Run the smoke test against the application after cutover. Rehearse recovery in a separate environment; no restore drill has been performed by this project.

## Cleanup

Back up anything needed. Set `deletion_protection = false` through Terraform and apply that change first. Empty ECR repositories explicitly after deciding whether images must be retained; repositories intentionally do not force-delete images. Then run `terraform -chdir=infra plan -destroy` and `terraform -chdir=infra destroy`. RDS takes a final snapshot named ENVIRONMENT_NAME-final, which remains billable until separately removed. If that name already exists, choose another final_snapshot_identifier before destroying. CloudWatch exports and snapshots may outlive the stack; inspect the account for retained resources. Removing files or Terraform state does not remove AWS resources.
