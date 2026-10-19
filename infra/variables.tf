variable "region" { default = "us-east-1" }
variable "name" { default = "three-tier" }
variable "environment" { default = "dev" }
variable "web_image" { type = string }
variable "api_image" { type = string }
variable "certificate_arn" {
  type    = string
  default = null
}
variable "alarm_email" {
  type    = string
  default = null
}
variable "deletion_protection" { default = true }
