mock_provider "aws" {}
run "database_protection" {
  command = plan
  module { source = "./modules/database" }
  variables {
    name                = "platform-test"
    subnets             = ["subnet-12345678", "subnet-87654321"]
    security_group      = "sg-12345678"
    deletion_protection = true
  }
  assert {
    condition     = aws_db_instance.this.multi_az && aws_db_instance.this.storage_encrypted && !aws_db_instance.this.publicly_accessible
    error_message = "Database must be encrypted, private and Multi-AZ."
  }
  assert {
    condition     = aws_db_instance.this.manage_master_user_password && aws_db_instance.this.deletion_protection && !aws_db_instance.this.skip_final_snapshot && aws_db_instance.this.backup_retention_period >= 7
    error_message = "Managed credentials, deletion protection, final snapshots and backups are required."
  }
}
